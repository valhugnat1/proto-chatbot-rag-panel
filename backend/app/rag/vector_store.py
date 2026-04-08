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