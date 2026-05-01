"""
LangGraph Multi-Agent Orchestration Graph.
Pattern: Supervisor → Planner → Executor → Critic → (loop or done)
Uses checkpoint-based state persistence for durability.
"""
import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_anthropic import ChatAnthropic

from backend.agents.state import AgentState
from backend.agents.planner import PlannerAgent
from backend.agents.executor import ExecutorAgent
from backend.agents.critic import CriticAgent
from backend.agents.memory import MemoryAgent
from backend.core.config import settings

logger = logging.getLogger(__name__)

MAX_REVISIONS = 3


def should_revise(state: AgentState) -> str:
    """Router: decide whether to revise or finalize."""
    if state.error:
        return "handle_error"
    if state.needs_revision and state.revision_count < MAX_REVISIONS:
        return "executor"
    return END


def route_after_plan(state: AgentState) -> str:
    """Router: after planning, go to executor."""
    if not state.plan:
        return "handle_error"
    return "executor"


async def handle_error(state: AgentState) -> AgentState:
    """Graceful error handler node."""
    logger.error(f"Agent error: {state.error}")
    state.final_answer = (
        f"I encountered an error while processing your request: {state.error}. "
        "Please try rephrasing or contact support."
    )
    state.is_done = True
    return state


def build_graph(checkpointer=None) -> StateGraph:
    """Construct and compile the multi-agent graph."""

    llm = ChatAnthropic(
        model=settings.primary_model,
        api_key=settings.anthropic_api_key,
        temperature=0,
        max_tokens=4096,
    )

    planner = PlannerAgent(llm=llm)
    executor = ExecutorAgent(llm=llm)
    critic = CriticAgent(llm=llm)
    memory = MemoryAgent()

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("memory_retrieval", memory.retrieve)
    graph.add_node("planner", planner.plan)
    graph.add_node("executor", executor.execute)
    graph.add_node("critic", critic.critique)
    graph.add_node("handle_error", handle_error)

    # Edges
    graph.add_edge(START, "memory_retrieval")
    graph.add_edge("memory_retrieval", "planner")
    graph.add_conditional_edges("planner", route_after_plan)
    graph.add_edge("executor", "critic")
    graph.add_conditional_edges("critic", should_revise)

    return graph.compile(checkpointer=checkpointer, interrupt_before=["handle_error"])


async def create_graph_with_persistence(db_url: str) -> StateGraph:
    """Production graph with PostgreSQL checkpointing for durability."""
    checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
    await checkpointer.setup()
    return build_graph(checkpointer=checkpointer)
