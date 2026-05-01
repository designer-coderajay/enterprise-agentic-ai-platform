"""LangGraph agent state definitions."""
from typing import Annotated, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
import operator


class AgentState(BaseModel):
    """Shared state across all agents in the graph."""

    # Conversation messages (auto-merged by LangGraph)
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    # Current task being worked on
    task: str = ""
    task_id: str = ""
    user_id: str = ""

    # Planning output
    plan: list[str] = Field(default_factory=list)
    current_step: int = 0

    # Execution results
    tool_results: Annotated[list[dict], operator.add] = Field(default_factory=list)
    retrieved_context: str = ""

    # Critic feedback
    critique: str = ""
    needs_revision: bool = False
    revision_count: int = 0

    # Final output
    final_answer: str = ""
    citations: list[dict] = Field(default_factory=list)
    confidence_score: float = 0.0

    # Control flow
    next_node: str = ""
    error: str | None = None
    is_done: bool = False

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
