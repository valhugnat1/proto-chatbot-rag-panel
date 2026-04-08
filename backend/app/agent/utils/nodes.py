"""Graph node functions.

For the prototype we use `create_react_agent` from `langgraph.prebuilt`,
which builds the standard ReAct loop (LLM node + ToolNode) for us.
This module exposes the LLM and the ToolNode in case we ever want to
build the graph by hand for debugging.
"""
from langchain_mistralai import ChatMistralAI
from langgraph.prebuilt import ToolNode

from app.agent.utils.tools import TOOLS
from app.config import settings


def build_llm() -> ChatMistralAI:
    """Instantiate the chat model with tools bound."""
    return ChatMistralAI(
        model=settings.mistral_model,
        api_key=settings.mistral_api_key,
        temperature=0.1,
    )


def build_tool_node() -> ToolNode:
    return ToolNode(TOOLS)
