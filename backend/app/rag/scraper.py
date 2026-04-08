"""Generic BFS web crawler driven by a `SiteConfig` profile.

Designed to be a "good citizen":
- Respects `robots.txt` (unless `ignore_robots=True`).
- Politeness delay between requests.
- Identifiable but realistic User-Agent (browser-like by default).
- Hard caps on number of pages and depth.
- Stays on the configured allowed domain.
- Skips obvious asset URLs and out-of-scope path prefixes.

Extracts main content with `trafilatura`, which strips navigation, footers
and cookie banners far better than naive `soup.get_text()`.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.rag.sites import SiteConfig

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15.0


@dataclass
class ScrapedPage:
    url: str
    title: str
    depth: int
    content: str
    scraped_at: str


# ---------------------------------------------------------------------------
# URL filters
# ---------------------------------------------------------------------------


def _normalize_url(base: str, link: str) -> str | None:
    """Resolve a link relative to `base` and strip the fragment."""
    if not link:
        return None
    absolute = urljoin(base, link)
    absolute, _ = urldefrag(absolute)
    return absolute


def _is_allowed(url: str, site: SiteConfig) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    domain = site.domain
    if parsed.netloc != domain and not parsed.netloc.endswith("." + domain):
        return False
    path_lower = parsed.path.lower()
    if any(path_lower.endswith(ext) for ext in site.excluded_extensions):
        return False
    # Lowercase prefix comparison so that "/wiki/Spécial:" matches
    # "/wiki/spécial:page_au_hasard" regardless of case.
    if any(path_lower.startswith(prefix.lower()) for prefix in site.excluded_path_prefixes):
        return False
    return True


# ---------------------------------------------------------------------------
# Robots.txt
# ---------------------------------------------------------------------------


def _allow_all_parser() -> RobotFileParser:
    """Return a RobotFileParser that allows everything.

    Trick : feed it a synthetic 'User-agent: *\\nDisallow:' ruleset so that
    can_fetch() returns True for any URL. An empty parser does NOT do this —
    it returns False for everything, which was the bug in the previous
    version.
    """
    rp = RobotFileParser()
    rp.parse(["User-agent: *", "Disallow:"])
    return rp


def _load_robots(site: SiteConfig) -> RobotFileParser:
    """Fetch robots.txt with the site's headers (urllib gets blocked easily).

    On any failure (network error, 403, 404), we fall back to allow-all so
    that the crawl isn't silently blocked. The user can also force this via
    `site.ignore_robots = True`.
    """
    if site.ignore_robots:
        logger.info("Ignoring robots.txt for %s (ignore_robots=True)", site.domain)
        return _allow_all_parser()

    robots_url = f"https://{site.domain}/robots.txt"
    try:
        with httpx.Client(
            headers=site.build_headers(),
            timeout=10.0,
            follow_redirects=True,
        ) as client:
            resp = client.get(robots_url)
        if resp.status_code == 200:
            rp = RobotFileParser()
            rp.parse(resp.text.splitlines())
            logger.info("Loaded robots.txt from %s", robots_url)
            return rp
        logger.warning(
            "robots.txt fetch returned HTTP %s for %s — assuming allow-all",
            resp.status_code, robots_url,
        )
    except Exception as exc:
        logger.warning(
            "Failed to load robots.txt from %s: %s — assuming allow-all",
            robots_url, exc,
        )
    return _allow_all_parser()


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


def _extract_title(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
    except Exception:  # pragma: no cover
        pass
    return ""


def _extract_links(html: str, base_url: str, site: SiteConfig) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        normalized = _normalize_url(base_url, a["href"])
        if normalized and _is_allowed(normalized, site):
            links.append(normalized)
    return links


def _extract_main_content(html: str) -> str:
    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_recall=False,
    )
    return (extracted or "").strip()


# ---------------------------------------------------------------------------
# Crawl loop
# ---------------------------------------------------------------------------


async def crawl(site: SiteConfig) -> list[ScrapedPage]:
    """Run a depth-limited BFS crawl over the configured site."""
    rp = _load_robots(site)
    headers = site.build_headers()
    effective_ua = headers["User-Agent"]

    visited: set[str] = set()
    pages: list[ScrapedPage] = []
    queue: deque[tuple[str, int]] = deque([(site.seed_url, 0)])

    stats = {
        "fetched": 0,
        "ok": 0,
        "non_200": 0,
        "non_html": 0,
        "too_short": 0,
        "robots_blocked": 0,
        "fetch_errors": 0,
    }

    async with httpx.AsyncClient(
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:
        while queue and len(pages) < site.max_pages:
            url, depth = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            if depth > site.max_depth:
                continue
            if not _is_allowed(url, site):
                continue
            if not rp.can_fetch(effective_ua, url):
                logger.debug("Blocked by robots.txt: %s", url)
                stats["robots_blocked"] += 1
                continue

            stats["fetched"] += 1
            try:
                response = await client.get(url)
            except Exception as exc:
                logger.warning("Fetch failed for %s: %s", url, exc)
                stats["fetch_errors"] += 1
                continue

            if response.status_code != 200:
                logger.warning("HTTP %s for %s — skipping", response.status_code, url)
                stats["non_200"] += 1
                continue

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                stats["non_html"] += 1
                continue

            html = response.text
            content = _extract_main_content(html)
            if len(content) >= site.min_content_chars:
                title = _extract_title(html)
                pages.append(
                    ScrapedPage(
                        url=url,
                        title=title,
                        depth=depth,
                        content=content,
                        scraped_at=datetime.now(timezone.utc).isoformat(),
                    )
                )
                stats["ok"] += 1
                logger.info(
                    "[%d/%d] depth=%d %s",
                    len(pages), site.max_pages, depth, url,
                )
            else:
                stats["too_short"] += 1
                logger.debug(
                    "Content too short (%d chars) for %s", len(content), url,
                )

            if depth < site.max_depth:
                for link in _extract_links(html, url, site):
                    if link not in visited:
                        queue.append((link, depth + 1))

            await asyncio.sleep(site.politeness_delay)

    logger.info(
        "Crawl summary: fetched=%d ok=%d non_200=%d non_html=%d "
        "too_short=%d robots_blocked=%d fetch_errors=%d",
        stats["fetched"], stats["ok"], stats["non_200"], stats["non_html"],
        stats["too_short"], stats["robots_blocked"], stats["fetch_errors"],
    )
    if not pages:
        logger.error(
            "No pages were successfully scraped. Common causes: "
            "(1) the site blocks the User-Agent → try a different --user-agent, "
            "(2) network egress is blocked, "
            "(3) the seed URL is wrong, "
            "(4) all paths are excluded → check the site's excluded_path_prefixes."
        )

    return pages


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def save_pages(pages: list[ScrapedPage], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for page in pages:
            f.write(json.dumps(asdict(page), ensure_ascii=False) + "\n")
    logger.info("Saved %d pages to %s", len(pages), output_path)


def load_pages(input_path: Path) -> list[ScrapedPage]:
    pages: list[ScrapedPage] = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            pages.append(ScrapedPage(**data))
    return pages