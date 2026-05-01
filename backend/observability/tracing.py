"""Observability: LangSmith tracing + Prometheus metrics + OpenTelemetry."""
import os
import logging
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from backend.core.config import settings

logger = logging.getLogger(__name__)

# Prometheus metrics
AGENT_REQUESTS_TOTAL = Counter(
    "agent_requests_total", "Total agent invocations", ["status", "model"]
)
AGENT_LATENCY_SECONDS = Histogram(
    "agent_latency_seconds", "Agent end-to-end latency",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)
AGENT_TOKENS_USED = Counter(
    "agent_tokens_used_total", "Total LLM tokens consumed", ["type", "model"]
)
ACTIVE_SESSIONS = Gauge("active_agent_sessions", "Currently active agent sessions")
TOOL_CALLS_TOTAL = Counter(
    "mcp_tool_calls_total", "MCP tool invocations", ["tool_name", "status"]
)
RAG_RETRIEVAL_LATENCY = Histogram(
    "rag_retrieval_latency_seconds", "RAG retrieval latency"
)


def setup_tracing():
    """Initialize LangSmith + Prometheus."""
    # LangSmith
    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        logger.info("✅ LangSmith tracing enabled")

    # Prometheus metrics server on :9090
    try:
        start_http_server(9090)
        logger.info("✅ Prometheus metrics server on :9090")
    except OSError:
        logger.warning("Prometheus metrics server already running")


def track_agent_request(status: str = "success", model: str = "claude"):
    AGENT_REQUESTS_TOTAL.labels(status=status, model=model).inc()


def track_token_usage(input_tokens: int, output_tokens: int, model: str):
    AGENT_TOKENS_USED.labels(type="input", model=model).inc(input_tokens)
    AGENT_TOKENS_USED.labels(type="output", model=model).inc(output_tokens)


def track_tool_call(tool_name: str, success: bool):
    status = "success" if success else "error"
    TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status=status).inc()
