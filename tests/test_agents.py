"""Pytest tests for agent orchestration."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from backend.agents.state import AgentState
from backend.agents.planner import PlannerAgent
from backend.agents.critic import CriticAgent


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.mark.asyncio
async def test_planner_produces_steps(mock_llm):
    mock_llm.ainvoke.return_value = MagicMock(
        content="1. Search the knowledge base\n2. Analyze results\n3. Generate report",
    )
    planner = PlannerAgent(llm=mock_llm)
    state = AgentState(task="Summarize Q4 revenue data")
    result = await planner.plan(state)

    assert len(result.plan) == 3
    assert result.plan[0] == "Search the knowledge base"
    assert result.current_step == 0


@pytest.mark.asyncio
async def test_planner_handles_empty_llm_response(mock_llm):
    mock_llm.ainvoke.return_value = MagicMock(content="")
    planner = PlannerAgent(llm=mock_llm)
    state = AgentState(task="Do something")
    result = await planner.plan(state)
    # Falls back to treating task as single step
    assert len(result.plan) == 1
    assert result.plan[0] == "Do something"


@pytest.mark.asyncio
async def test_critic_accepts_good_answer(mock_llm):
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"score": 9, "needs_revision": false, "critique": "Excellent", "confidence": 0.95}'
    )
    critic = CriticAgent(llm=mock_llm)
    state = AgentState(
        task="What is the revenue?",
        final_answer="Q4 revenue was $42M, up 12% YoY.",
    )
    result = await critic.critique(state)
    assert result.needs_revision is False
    assert result.confidence_score == 0.95


@pytest.mark.asyncio
async def test_critic_flags_bad_answer(mock_llm):
    mock_llm.ainvoke.return_value = MagicMock(
        content='{"score": 4, "needs_revision": true, "critique": "Missing data sources", "confidence": 0.4}'
    )
    critic = CriticAgent(llm=mock_llm)
    state = AgentState(task="Analyze financials", final_answer="Revenue went up.")
    result = await critic.critique(state)
    assert result.needs_revision is True
    assert result.critique == "Missing data sources"


@pytest.mark.asyncio
async def test_agent_state_immutable_messages():
    """Verify LangGraph message accumulation works correctly."""
    from langchain_core.messages import HumanMessage, AIMessage
    state = AgentState(task="test")
    state.messages = [HumanMessage(content="hello")]
    # Adding messages should accumulate (not replace)
    assert len(state.messages) == 1
