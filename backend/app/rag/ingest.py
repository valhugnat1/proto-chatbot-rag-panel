"""Dynamic RAG ingestion script from a single URL."""
import argparse
import asyncio
import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.scraper import crawl
from app.rag.sites import SiteConfig
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

async def run_ingestion(url: str, max_pages: int, max_depth: int) -> None:
    # 1. Initialize configuration directly from URL
    site = SiteConfig(
        seed_url=url,
        max_pages=max_pages,
        max_depth=max_depth
    )

    logger.info(f"--- Starting pipeline for URL: {url} ---")
    logger.info(f"Config: domain={site.domain}, max_pages={max_pages}, max_depth={max_depth}")

    # 2. Scrape website
    logger.info("1/3 Scraping website...")
    pages = await crawl(site)
    
    if not pages:
        logger.warning("No pages were scraped. Exiting.")
        return

    # 3. Split content into chunks
    logger.info("2/3 Splitting content into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=150
    )
    
    docs, ids = [], []
    for page in pages:
        chunks = splitter.split_text(page.content)
        for i, chunk in enumerate(chunks):
            docs.append(
                Document(
                    page_content=f"Source: {page.url}\nTitle: {page.title}\n\n{chunk}",
                    metadata={"source": page.url, "title": page.title}
                )
            )
            ids.append(f"{page.url}::{i}")
            
    logger.info(f"Created {len(docs)} chunks from {len(pages)} pages.")

    # 4. Upsert into vector store
    logger.info("3/3 Indexing chunks into Vector DB...")
    store = get_vector_store()
    await store.aadd_documents(documents=docs, ids=ids)
    
    logger.info("--- Ingestion successfully completed! ---")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    parser = argparse.ArgumentParser(description="Dynamic RAG Ingestion")
    parser.add_argument("--url", required=True, help="Seed URL to start scraping from")
    parser.add_argument("--max-pages", type=int, default=20, help="Max pages to crawl")
    parser.add_argument("--max-depth", type=int, default=2, help="Max depth to crawl")
    args = parser.parse_args()

    asyncio.run(run_ingestion(args.url, args.max_pages, args.max_depth))