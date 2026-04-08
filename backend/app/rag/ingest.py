"""Ingestion CLI driven by site profiles.

Architecture:
    sites.py    → SiteConfig dataclass + SITES registry of profiles
    scraper.py  → generic crawl(site: SiteConfig)
    ingest.py   → CLI: pick a profile via --site, then optionally override

Examples:

    # List available site profiles
    python -m app.rag.ingest list-sites

    # Default site (bnp-group), default params
    python -m app.rag.ingest all

    # Hello bank with quick demo settings
    python -m app.rag.ingest all --site hellobank --max-pages 20 --max-depth 2

    # Wikipedia fallback (always works, no anti-bot)
    python -m app.rag.ingest all --site wikipedia-bnp

    # Override the seed URL of a registered profile
    python -m app.rag.ingest scrape --site mabanque \
        --seed-url https://mabanque.bnpparibas/credit/

    # Force a specific User-Agent if the default browser UA is blocked
    python -m app.rag.ingest scrape --site bnp-group \
        --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."

    # Bypass robots.txt entirely (use sparingly)
    python -m app.rag.ingest scrape --site hellobank --ignore-robots

    # Re-chunk without re-crawling (uses the cached pages.jsonl)
    python -m app.rag.ingest index --chunk-size 1500 --chunk-overlap 200
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import replace
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.scraper import crawl, load_pages, save_pages
from app.rag.sites import SITES, SiteConfig, get_site, list_sites
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

# Path to the cached scrape file
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PAGES_PATH = DATA_DIR / "scraped" / "pages.jsonl"

DEFAULT_SITE = "wikipedia-bnp"

# --- Default chunking parameters --------------------------------------------
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_EMBED_BATCH_SIZE = 50


# ---------------------------------------------------------------------------
# Build the effective SiteConfig from profile + CLI overrides
# ---------------------------------------------------------------------------


def _resolve_site(args: argparse.Namespace) -> SiteConfig:
    """Pick the site profile and apply CLI overrides on top of it."""
    site = get_site(args.site)

    overrides: dict = {}
    if args.seed_url is not None:
        overrides["seed_url"] = args.seed_url
    if args.max_pages is not None:
        overrides["max_pages"] = args.max_pages
    if args.max_depth is not None:
        overrides["max_depth"] = args.max_depth
    if args.delay is not None:
        overrides["politeness_delay"] = args.delay
    if args.user_agent is not None:
        overrides["user_agent"] = args.user_agent
    if args.ignore_robots:
        overrides["ignore_robots"] = True

    if overrides:
        site = replace(site, **overrides)
        logger.info("Applied CLI overrides: %s", list(overrides.keys()))

    return site


# ---------------------------------------------------------------------------
# scrape
# ---------------------------------------------------------------------------


async def cmd_scrape(site: SiteConfig) -> None:
    logger.info(
        "Starting crawl: site=%s seed=%s domain=%s max_pages=%d max_depth=%d delay=%.2fs",
        site.name, site.seed_url, site.domain,
        site.max_pages, site.max_depth, site.politeness_delay,
    )
    pages = await crawl(site)
    save_pages(pages, PAGES_PATH)
    logger.info("Done. %d pages saved to %s", len(pages), PAGES_PATH)


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------


def _build_documents(
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list[Document], list[str]]:
    if not PAGES_PATH.exists():
        raise FileNotFoundError(
            f"{PAGES_PATH} not found — run `scrape` first."
        )

    pages = load_pages(PAGES_PATH)
    logger.info("Loaded %d pages from cache", len(pages))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    documents: list[Document] = []
    ids: list[str] = []

    for page in pages:
        chunks = splitter.split_text(page.content)
        for i, chunk in enumerate(chunks):
            header = f"Source: {page.url}\nTitle: {page.title}\n\n"
            documents.append(
                Document(
                    page_content=header + chunk,
                    metadata={
                        "source": page.url,
                        "title": page.title,
                        "depth": page.depth,
                        "chunk_index": i,
                    },
                )
            )
            ids.append(f"{page.url}::{i}")

    logger.info("Produced %d chunks from %d pages", len(documents), len(pages))
    return documents, ids


async def cmd_index(
    chunk_size: int,
    chunk_overlap: int,
    batch_size: int,
) -> None:
    documents, ids = _build_documents(chunk_size, chunk_overlap)
    if not documents:
        logger.warning("No documents to index. Aborting.")
        return

    store = get_vector_store()
    total = len(documents)
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch_docs = documents[start:end]
        batch_ids = ids[start:end]
        logger.info("Indexing chunks %d–%d / %d …", start + 1, end, total)
        await store.aadd_documents(documents=batch_docs, ids=batch_ids)
    logger.info("Done. %d chunks indexed.", total)


# ---------------------------------------------------------------------------
# list-sites
# ---------------------------------------------------------------------------


def cmd_list_sites() -> None:
    print("Available site profiles:\n")
    for name in list_sites():
        site = SITES[name]
        print(f"  {name}")
        print(f"      seed       : {site.seed_url}")
        print(f"      domain     : {site.domain}")
        print(f"      max_pages  : {site.max_pages}")
        print(f"      max_depth  : {site.max_depth}")
        print(f"      delay      : {site.politeness_delay}s")
        print()


# ---------------------------------------------------------------------------
# Argparse helpers
# ---------------------------------------------------------------------------


def _add_scrape_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--site",
        default=DEFAULT_SITE,
        choices=list_sites(),
        help=f"Site profile to use (default: {DEFAULT_SITE}). Run `list-sites` to see all.",
    )
    parser.add_argument(
        "--seed-url",
        default=None,
        help="Override the profile's seed URL",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Override the profile's max pages cap",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Override the profile's max BFS depth",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Override the profile's politeness delay (seconds)",
    )
    parser.add_argument(
        "--user-agent",
        default=None,
        help="Override the profile's User-Agent header",
    )
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        help="Ignore robots.txt entirely (use sparingly)",
    )


def _add_index_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Character chunk size for the text splitter",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help="Character overlap between consecutive chunks",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_EMBED_BATCH_SIZE,
        help="Number of documents per embedding upsert batch",
    )


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="BNP RAG ingestion CLI (modular site profiles)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_scrape = subparsers.add_parser("scrape", help="Crawl the website")
    _add_scrape_args(p_scrape)

    p_index = subparsers.add_parser("index", help="Chunk + embed + upsert")
    _add_index_args(p_index)

    p_all = subparsers.add_parser("all", help="Run scrape then index")
    _add_scrape_args(p_all)
    _add_index_args(p_all)

    subparsers.add_parser("list-sites", help="List available site profiles")

    args = parser.parse_args()

    if args.command == "scrape":
        site = _resolve_site(args)
        asyncio.run(cmd_scrape(site))

    elif args.command == "index":
        asyncio.run(
            cmd_index(
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                batch_size=args.batch_size,
            )
        )

    elif args.command == "all":
        site = _resolve_site(args)

        async def _both() -> None:
            await cmd_scrape(site)
            await cmd_index(
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                batch_size=args.batch_size,
            )
        asyncio.run(_both())

    elif args.command == "list-sites":
        cmd_list_sites()

    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")
        sys.exit(2)


if __name__ == "__main__":
    main()