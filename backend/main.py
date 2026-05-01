"""
Enterprise Agentic AI Platform — FastAPI Application Entry Point.
Streaming WebSocket + REST endpoints for multi-agent interactions.
"""
import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.database import engine, Base
from backend.agents.graph import build_graph
from backend.agents.state import AgentState
from backend.observability.tracing import setup_tracing
from backend.api.routes import agent, health, documents

logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup and shutdown events."""
    logger.info("🚀 Starting Enterprise Agentic AI Platform")
    setup_tracing()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.agent_graph = build_graph()
    logger.info("✅ Agent graph compiled with LangGraph")
    yield
    logger.info("🛑 Shutting down")
    await engine.dispose()


app = FastAPI(
    title="Enterprise Agentic AI Platform",
    description="Multi-agent RAG platform with MCP tool integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])


class AgentRequest(BaseModel):
    task: str
    user_id: str = "anonymous"
    thread_id: str | None = None
    metadata: dict = {}


class AgentResponse(BaseModel):
    thread_id: str
    answer: str
    confidence: float
    citations: list[dict]
    tool_results: list[dict]


@app.post("/api/v1/agent/invoke", response_model=AgentResponse)
async def invoke_agent(request: AgentRequest):
    """Synchronous agent invocation — waits for complete response."""
    thread_id = request.thread_id or str(uuid.uuid4())
    graph = app.state.agent_graph

    initial_state = AgentState(
        task=request.task,
        task_id=str(uuid.uuid4()),
        user_id=request.user_id,
        metadata=request.metadata,
    )

    config = {"configurable": {"thread_id": thread_id}}
    final_state = await graph.ainvoke(initial_state.model_dump(), config=config)

    return AgentResponse(
        thread_id=thread_id,
        answer=final_state.get("final_answer", ""),
        confidence=final_state.get("confidence_score", 0.0),
        citations=final_state.get("citations", []),
        tool_results=final_state.get("tool_results", []),
    )


@app.websocket("/ws/agent/{thread_id}")
async def agent_websocket(websocket: WebSocket, thread_id: str):
    """Real-time streaming agent via WebSocket. Streams each agent step."""
    await websocket.accept()
    graph = app.state.agent_graph

    try:
        while True:
            data = await websocket.receive_json()
            task = data.get("task", "")
            user_id = data.get("user_id", "anonymous")

            initial_state = AgentState(task=task, user_id=user_id)
            config = {"configurable": {"thread_id": thread_id}}

            # Stream each node's output
            async for chunk in graph.astream(
                initial_state.model_dump(),
                config=config,
                stream_mode="updates",
            ):
                for node_name, node_output in chunk.items():
                    await websocket.send_json({
                        "type": "node_update",
                        "node": node_name,
                        "data": {
                            "final_answer": node_output.get("final_answer", ""),
                            "plan": node_output.get("plan", []),
                            "confidence": node_output.get("confidence_score", 0),
                        },
                    })

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {thread_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()
