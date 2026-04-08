"""Health endpoint.

Returns `{"status": "ok", "db": "ok" | "down"}`. Used by Scaleway's
container healthcheck.
"""
from __future__ import annotations

import logging

import psycopg
from fastapi import APIRouter

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _psycopg_dsn() -> str:
    """Convert the SQLAlchemy-style DSN to a plain psycopg one.

    `langchain-postgres` expects `postgresql+psycopg://…`, but `psycopg.connect`
    wants `postgresql://…`.
    """
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)


@router.get("/health")
async def health() -> dict[str, str]:
    db_status = "ok"
    try:
        with psycopg.connect(_psycopg_dsn(), connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        db_status = "down"
    return {"status": "ok", "db": db_status}
