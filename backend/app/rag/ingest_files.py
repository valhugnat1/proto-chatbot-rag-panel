"""Local file RAG ingestion script.

Reads every `.txt` file from `app/data/fake_pages/` and indexes them into the
same pgvector collection used by the web scraper ingestion. Re-running the
script fully replaces any previously indexed version of each file.
"""
import asyncio
import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import text

from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

# Folder containing the .txt files to ingest.
# Resolved from this file: backend/app/rag/ingest_files.py -> backend/app/data/fake_pages
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "fake_pages"

# GitHub URL used as the canonical `source` for each file.
SOURCE_URL_PREFIX = (
    "https://github.com/valhugnat1/proto-chatbot-rag-panel"
    "/tree/main/backend/app/data/fake_pages"
)


async def _delete_existing_source(store, source: str) -> None:
    """Delete all chunks previously indexed under this source URL.

    PGVector's `aadd_documents(ids=...)` already overwrites rows with matching
    ids, but if the new version of the file produces *fewer* chunks than
    before, the extra old chunks would stay orphaned. So we wipe the source
    first, then re-insert.
    """
    async with store.session_maker() as session:
        await session.execute(
            text(
                "DELETE FROM langchain_pg_embedding "
                "WHERE cmetadata->>'source' = :source"
            ),
            {"source": source},
        )
        await session.commit()


async def run_ingestion() -> None:
    if not DATA_DIR.is_dir():
        logger.error(f"Data folder not found: {DATA_DIR}")
        return

    txt_files = sorted(DATA_DIR.glob("*.txt"))
    if not txt_files:
        logger.warning(f"No .txt files found in {DATA_DIR}")
        return

    logger.info(f"--- Ingesting {len(txt_files)} file(s) from {DATA_DIR} ---")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    store = get_vector_store()

    total_chunks = 0
    for path in txt_files:
        source = f"{SOURCE_URL_PREFIX}/{path.name}"
        title = path.stem
        content = path.read_text(encoding="utf-8").strip()

        if not content:
            logger.warning(f"Skipping empty file: {path.name}")
            continue

        # 1. Wipe any previous version of this file from the DB.
        await _delete_existing_source(store, source)

        # 2. Split into chunks (same settings as the web ingestion).
        chunks = splitter.split_text(content)
        docs, ids = [], []
        for i, chunk in enumerate(chunks):
            docs.append(
                Document(
                    page_content=f"Source: {source}\nTitle: {title}\n\n{chunk}",
                    metadata={"source": source, "title": title},
                )
            )
            ids.append(f"{source}::{i}")

        # 3. Insert fresh chunks.
        await store.aadd_documents(documents=docs, ids=ids)
        total_chunks += len(docs)
        logger.info(f"Indexed {path.name}: {len(docs)} chunks")

    logger.info(f"--- Done. Total: {total_chunks} chunks from {len(txt_files)} file(s) ---")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    asyncio.run(run_ingestion())