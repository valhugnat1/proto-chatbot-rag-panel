"""Agent tools.

Two tools, intentionally minimal for the prototype:

- `search_knowledge_base`: dense retrieval over the BNP knowledge base
  (scraped from group.bnpparibas), backed by pgvector.
- `check_account`: lookup over a hardcoded `fake_clients.json` file.
  Naive on purpose — in the real architecture this would be gated by
  OIDC + RBAC.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Path to the fake clients file (relative to the `app/` package)
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_FAKE_CLIENTS_PATH = _DATA_DIR / "fake_clients.json"


# ---------------------------------------------------------------------------
# Tool 1 — knowledge base search (RAG)
# ---------------------------------------------------------------------------


@tool
async def search_knowledge_base(query: str) -> str:
    """Recherche dans la base de connaissances BNP Paribas (FAQ, fiches \
produits, tarifs, actualités du groupe). À utiliser pour toute question \
générale sur les produits et services BNP.

    Args:
        query: La question ou les mots-clés à rechercher, en français de \
préférence.

    Returns:
        Un extrait textuel des passages les plus pertinents, avec leurs \
sources (URL).
    """
    # Lazy import so the tool module can be imported without a live DB
    # (e.g. during unit tests or when the agent boots before ingestion).
    try:
        from app.rag.vector_store import get_vector_store
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to import vector store: %s", exc)
        return "La base de connaissances n'est pas disponible pour le moment."

    try:
        store = get_vector_store()
        results = await store.asimilarity_search_with_score(query=query, k=5)
    except Exception as exc:
        logger.warning("Vector store search failed: %s", exc)
        return (
            "La base de connaissances n'est pas disponible pour le moment "
            "(la base n'a peut-être pas encore été indexée)."
        )

    # langchain-postgres returns cosine *distance* (lower = more similar).
    filtered = [(doc, score) for doc, score in results if score < 0.5]

    if not filtered:
        return "Aucun résultat pertinent trouvé dans la base de connaissances."

    chunks: list[str] = []
    for doc, score in filtered:
        source = doc.metadata.get("source", "source inconnue")
        title = doc.metadata.get("title", "")
        header = f"[Source: {source}]"
        if title:
            header += f" — {title}"
        chunks.append(f"{header}\n{doc.page_content.strip()}")

    return "\n\n---\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Tool 2 — fake account lookup
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_fake_clients() -> list[dict[str, Any]]:
    if not _FAKE_CLIENTS_PATH.exists():
        logger.warning("fake_clients.json not found at %s", _FAKE_CLIENTS_PATH)
        return []
    with _FAKE_CLIENTS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("fake_clients.json must contain a JSON array")
    return data


def _format_client(client: dict[str, Any]) -> str:
    lines = [f"Client : {client['name']}"]
    for acc in client.get("accounts", []):
        lines.append(
            f"- {acc['type']} (•••{acc['iban_last4']}) : "
            f"{acc['balance']:.2f} €"
        )
    card = client.get("card")
    if card:
        lines.append(f"Carte : {card['type']} (statut : {card['status']})")
    return "\n".join(lines)


@tool
def check_account(client_name: str) -> str:
    """Récupère le solde et les informations de compte d'un client BNP \
Paribas à partir de son nom complet.

    Args:
        client_name: Nom complet du client (prénom + nom), insensible à la \
casse.

    Returns:
        Un résumé textuel des comptes du client, ou un message d'erreur si \
le client est introuvable.
    """
    clients = _load_fake_clients()
    target = client_name.strip().lower()
    for client in clients:
        if client["name"].lower() == target:
            return _format_client(client)
    return "Aucun client trouvé avec ce nom."


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = [search_knowledge_base, check_account]
