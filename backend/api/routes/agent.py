"""
Agent REST routes — synchronous invoke and thread management.
WebSocket streaming is in backend/main.py directly.
"""
import uuid
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend.agents.state import AgentState

logger = logging.getLogger(__name__)
router = APIRouter()


class AgentInvokeRequest(BaseModel):
    task: str
    user_id: str = "anonymous"
    thread_id: str | None = None
    metadata: dict = {}


class AgentInvokeResponse(BaseModel):
    thread_id: str
    answer: str
    confidence: float
    citations: list[dict]
    tool_results: list[dict]


@router.post("/invoke", response_model=AgentInvokeResponse, summary="Synchronous agent invocation")
async def invoke_agent(request: AgentInvokeRequest):
    """Invoke the multi-agent pipeline synchronously.
    For real-time streaming, use WebSocket /ws/agent/{thread_id}.
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    from backend.agents.graph import build_graph
    graph = build_graph()
    initial_state = AgentState(
        task=request.task,
        task_id=str(uuid.uuid4()),
        user_id=request.user_id,
        metadata=request.metadata,
    )
    config = {"configurable": {"thread_id": thread_id}}
    try:
        final_state = await graph.ainvoke(initial_state.model_dump(), config=config)
    except Exception as e:
        logger.error(f"Agent invoke failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return AgentInvokeResponse(
        thread_id=thread_id,
        answer=final_state.get("final_answer", ""),
        confidence=final_state.get("confidence_score", 0.0),
        citations=final_state.get("citations", []),
        tool_results=final_state.get("tool_results", []),
    )


@router.get("/threads", summary="List active thread IDs")
async def list_threads():
    """Returns placeholder — thread management backed by Postgres checkpointer."""
    return {"threads": [], "note": "Thread listing requires Postgres checkpointer connection"}
