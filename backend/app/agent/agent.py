"""LangGraph ReAct agent — graph construction.

We use `create_react_agent` from `langgraph.prebuilt`, which assembles the
canonical ReAct loop (call_model → maybe_call_tools → call_model → …).

The `graph` symbol exported here is the compiled, runnable graph, also
referenced from `langgraph.json` so that `langgraph dev` can pick it up.
"""
from langgraph.prebuilt import create_react_agent

from app.agent.utils.nodes import build_llm
from app.agent.utils.prompts import SYSTEM_PROMPT
from app.agent.utils.tools import TOOLS

graph = create_react_agent(
    model=build_llm(),
    tools=TOOLS,
    prompt=SYSTEM_PROMPT,
)
