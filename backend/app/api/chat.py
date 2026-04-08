"""Chat completions endpoint — OpenAI-compatible (simplified).

POST /v1/chat/completions
- Request: `{messages: [{role, content}], stream: bool}`
- Response (stream=true): SSE stream of `data: {...}` chunks ending with `data: [DONE]`
- Response (stream=false): single OpenAI-shaped JSON object

Token streaming uses LangGraph's `astream_events(version="v2")`, filtering on
`on_chat_model_stream` events so that we only forward tokens emitted by the
LLM node (and not, say, intermediate tool output).
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import AsyncIterator, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agent import graph
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    stream: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_lc_messages(messages: list[ChatMessage]) -> list[BaseMessage]:
    """Convert OpenAI-shaped messages to LangChain message objects.

    The system prompt is injected by `create_react_agent` itself, so we drop
    any inbound `system` role to avoid duplicating it.
    """
    converted: list[BaseMessage] = []
    for m in messages:
        if m.role == "user":
            converted.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            converted.append(AIMessage(content=m.content))
        elif m.role == "system":
            # Skip — handled by the agent's own prompt
            continue
    return converted


def _sse_chunk(content: str, completion_id: str, model: str) -> str:
    """Format one OpenAI-style streaming chunk as an SSE `data:` line."""
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None,
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_done() -> str:
    return "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Streaming generator
# ---------------------------------------------------------------------------


async def _stream_response(
    lc_messages: list[BaseMessage],
    completion_id: str,
) -> AsyncIterator[str]:
    """Yield SSE chunks by streaming model events from the LangGraph agent."""
    model_name = settings.mistral_model
    config = {"recursion_limit": settings.agent_recursion_limit}

    try:
        async for event in graph.astream_events(
            {"messages": lc_messages},
            config=config,
            version="v2",
        ):
            # Token-level events from any chat-model node in the graph.
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk is None:
                    continue
                # `chunk.content` may be a string or a list of content parts.
                content = chunk.content
                if isinstance(content, list):
                    text = "".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict) and part.get("type") == "text"
                    )
                else:
                    text = content or ""
                if text:
                    yield _sse_chunk(text, completion_id, model_name)
    except Exception as exc:
        logger.exception("Error during agent streaming: %s", exc)
        err_payload = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": f"\n\n[Erreur interne : {exc}]"},
                    "finish_reason": "stop",
                }
            ],
        }
        yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"

    yield _sse_done()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    lc_messages = _to_lc_messages(request.messages)
    if not lc_messages:
        raise HTTPException(
            status_code=400,
            detail="messages must contain at least one user or assistant turn",
        )

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

    if request.stream:
        return StreamingResponse(
            _stream_response(lc_messages, completion_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # disable nginx buffering
            },
        )

    # --- Non-streaming path -------------------------------------------------
    config = {"recursion_limit": settings.agent_recursion_limit}
    try:
        result = await graph.ainvoke({"messages": lc_messages}, config=config)
    except Exception as exc:
        logger.exception("Agent invocation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    final_messages = result.get("messages", [])
    final_text = ""
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and msg.content:
            content = msg.content
            if isinstance(content, list):
                final_text = "".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
            else:
                final_text = content
            break

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": settings.mistral_model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": final_text},
                "finish_reason": "stop",
            }
        ],
    }
