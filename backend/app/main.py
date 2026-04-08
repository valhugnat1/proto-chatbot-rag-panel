"""FastAPI application entrypoint.

Wires CORS, routers, and basic logging. The app is exported as `app` and
served by uvicorn (`uvicorn app.main:app`).
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health
from app.config import settings


def _configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def create_app() -> FastAPI:
    _configure_logging()

    app = FastAPI(
        title="BNP-like Banking Chatbot — Backend",
        description=(
            "POC backend: FastAPI + LangGraph ReAct agent + Mistral + pgvector. "
            "OpenAI-compatible /v1/chat/completions endpoint with SSE streaming."
        ),
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, tags=["health"])
    app.include_router(chat.router, tags=["chat"])

    return app


app = create_app()
