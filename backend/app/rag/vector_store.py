"""Vector store factory.

Returns a memoized `PGVector` instance backed by Mistral embeddings. The
underlying tables (`langchain_pg_collection`, `langchain_pg_embedding`)
are auto-created on first use; the only DB-side prerequisite is
`CREATE EXTENSION IF NOT EXISTS vector;`.

Note on async_mode: we use async_mode=True so that `aadd_documents` and
`asimilarity_search_with_score` work — without it, langchain-postgres'
internal `_async_engine` is never initialized and any `a*` call raises
`AssertionError: _async_engine not found`. Sync methods (`add_documents`,
`similarity_search`) are NOT available when async_mode=True; you must
use the async variants.

References:
- https://github.com/langchain-ai/langchain-postgres/issues/100
- https://github.com/langchain-ai/langgraph/discussions/3904
"""
from functools import lru_cache

from langchain_mistralai import MistralAIEmbeddings
from langchain_postgres import PGVector

from app.config import settings

COLLECTION_NAME = "bnp_kb"


@lru_cache(maxsize=1)
def get_vector_store() -> PGVector:
    embeddings = MistralAIEmbeddings(
        model=settings.mistral_embed_model,
        api_key=settings.mistral_api_key,
    )
    # `connection` must be a postgresql+psycopg:// DSN — when async_mode=True,
    # langchain-postgres builds an AsyncEngine from this string under the hood.
    return PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=settings.database_url,
        use_jsonb=True,
        async_mode=True,
        create_extension=True,
    )