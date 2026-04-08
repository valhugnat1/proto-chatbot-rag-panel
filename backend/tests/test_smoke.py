"""Smoke tests.

Goal: catch import errors and basic logic regressions without requiring a
live Mistral API key or a running Postgres. We set a fake env var, then
import key modules and exercise the pure-Python pieces.
"""
from __future__ import annotations

import os

# Set env vars BEFORE importing app modules so pydantic-settings is happy.
os.environ.setdefault("MISTRAL_API_KEY", "test-key-not-real")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://bnp:bnp@localhost:5432/bnp",
)


def test_config_loads():
    from app.config import settings

    assert settings.mistral_api_key == "test-key-not-real"
    assert settings.mistral_model.startswith("mistral")


def test_check_account_known_client():
    from app.agent.utils.tools import check_account

    # Tools decorated with @tool are runnables; .invoke executes them.
    result = check_account.invoke({"client_name": "Jean Dupont"})
    assert "Jean Dupont" in result
    assert "Compte courant" in result
    assert "2547.83" in result


def test_check_account_case_insensitive():
    from app.agent.utils.tools import check_account

    result = check_account.invoke({"client_name": "marie martin"})
    assert "Marie Martin" in result


def test_check_account_unknown_client():
    from app.agent.utils.tools import check_account

    result = check_account.invoke({"client_name": "Inconnu Personne"})
    assert "Aucun client" in result


def test_app_imports():
    """Importing the FastAPI app must not raise."""
    from app.main import app

    assert app is not None
    routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
    assert "/health" in routes
    assert "/v1/chat/completions" in routes
