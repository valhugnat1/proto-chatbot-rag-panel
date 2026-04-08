"""Agent state schema.

We use the built-in `MessagesState` from LangGraph: a single `messages`
field with an additive reducer. No custom fields needed for the prototype.
"""
from langgraph.graph import MessagesState

__all__ = ["MessagesState"]
