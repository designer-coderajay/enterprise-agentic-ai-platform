# Enterprise Agentic AI Platform

> **The Use Case:** An enterprise-grade, multi-agent backend capable of autonomous reasoning, tool execution, and self-correction over corporate data.
> **The Architecture:** LangGraph (State Orchestration) + FastMCP (Tool Abstraction) + FastAPI/WebSockets (Real-time Streaming) deployed on AWS EKS.
> **The Impact:** Moves beyond standard "search and summarize" RAG. This system plans multi-step actions, queries live databases, critiques its own output, and natively integrates with external APIs without hardcoded business logic. 

## The Problem
Standard RAG systems fail at multi-step reasoning. If a user asks a complex question requiring data from a PDF, a live PostgreSQL database, and a Slack notification, a traditional linear pipeline breaks. Hardcoding these integrations creates technical debt, and relying on a single LLM call for complex logic guarantees hallucinations and fragile execution.

## The Solution
A dynamic, multi-agent architecture. We use LangGraph to orchestrate a continuous Planner-Executor-Critic loop. The LLM is decoupled from the tools using the Model Context Protocol (MCP). When the agent needs to query a database or read a document, it routes the request to isolated, scalable MCP servers. If the final answer is weak, the Critic node rejects it and forces the Executor to try again.

## Business Impact
* **Autonomous Task Execution:** The system actively figures out *how* to solve a problem using available tools, reducing the need for human intervention.
* **Self-Healing Accuracy:** The built-in Critic loop ensures the model revises its own work up to 3 times before returning an answer to the user.
* **Infinite Extensibility:** Adding a new tool (like a Jira or Salesforce integration) simply means spinning up a new MCP server. Zero changes are required to the core agent logic.

## Deep Dive Architecture: Agent Loop & Tool Execution

An agentic system operates dynamically. Instead of a straight line, data moves through an orchestrated state machine (LangGraph) and calls external microservices (MCP) as needed.

```text
========================================================================
PHASE 1: INGESTION & USER REQUEST (Input Handling)
========================================================================
[Raw Enterprise Data]    <- PDFs, S3 URIs, URLs
      │
      ▼
[LlamaIndex Pipeline]    <- Semantic Splitter + OpenAI Embeddings
      │
      ▼
[Qdrant Vector DB]       <- Stores dense vectors + sparse BM25 indices
      │
      ▼
[User Prompt]            <- Sent via Next.js UI over WebSocket
========================================================================

========================================================================
PHASE 2: LANGGRAPH REASONING LOOP (State Machine)
========================================================================
[Memory Retrieval]       <- Pulls historical conversation context
      │
      ▼
[Planner Agent]          <- Breaks prompt into a multi-step execution plan
      │
      ▼
[Executor Agent] ────┐   <- Evaluates the plan and determines required tools
      │              │
      │              ▼
      │        [FastMCP Servers via Streamable HTTP]
      │        ├─> [PostgreSQL MCP] -> Runs SQL queries on live DB
      │        ├─> [Document MCP]   -> Runs Hybrid Search on Qdrant
      │        └─> [Notify MCP]     -> Triggers Slack/Webhook alerts
      │              │
      │              │ (Returns tool execution results back to state)
      ▼              │
[Critic Agent] <─────┘   <- Scores the assembled answer against the prompt
      │
      ├─> (If Score < Threshold & Revisions < 3) -> Routes back to [Executor]
      │
      ▼
(If Score Pass or Max Revisions Hit)
      │
      ▼
[WebSocket Stream]       <- Streams the final verified response to the UI
========================================================================
```

---

## Key Technical Stack

| Layer | Technology |
|-------|-----------|
| Agent Orchestration | LangGraph v0.3 (StateGraph, checkpointing, time-travel) |
| LLM | Claude Sonnet via LangChain |
| MCP Servers | FastMCP + Streamable HTTP transport (OAuth 2.1 ready) |
| RAG | LlamaIndex + Qdrant (hybrid dense+sparse search) + Cohere reranking |
| Embeddings | OpenAI `text-embedding-3-large` |
| API | FastAPI async + WebSocket streaming |
| Frontend | Next.js 14 App Router + shadcn/ui + Zustand |
| Observability | LangSmith + Langfuse + Prometheus + Grafana |
| Infra | EKS + Terraform + GitHub Actions + ArgoCD |

---

## Quick Start

```bash
cd ~/Desktop/enterprise-agentic-ai-platform
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, LANGSMITH_API_KEY, OPENAI_API_KEY

# Full stack with Docker Compose
make dev-full

# Or individual services
make mcp-start    # Start 3 MCP servers (:8001, :8002, :8003)
make dev          # FastAPI backend on :8000
cd frontend && npm install && npm run dev   # Next.js on :3000
```

---

## MCP Servers

| Server | Port | Tools |
|--------|------|-------|
| `postgres_mcp` | 8001 | `query_database`, `list_tables`, `insert_record` |
| `document_mcp` | 8002 | `extract_text_from_pdf`, `extract_tables_from_pdf`, `search_document` |
| `notification_mcp` | 8003 | `send_slack_message`, `send_webhook`, `create_slack_reminder` |

All MCP servers use **Streamable HTTP transport** (the April 2026 standard — SSE deprecated).

---

## Agent Loop

```python
# Planner → Executor → Critic → (revise?) loop
def should_revise(state: AgentState):
    if state.needs_revision and state.revision_count < MAX_REVISIONS:  # MAX=3
        return "executor"
    return "END"

# Graph nodes
graph.add_node("memory_retrieval", memory_retrieval_node)
graph.add_node("planner", planner_node)
graph.add_node("executor", executor_node)
graph.add_node("critic", critic_node)

# Critic loop — prevents infinite revision
graph.add_conditional_edges("critic", should_revise, {
    "executor": "executor",
    "END": END
})
```

---

## RAG Pipeline

- **Ingestion**: LlamaIndex `IngestionPipeline` with `SemanticSplitterNodeParser`
- **Vector Store**: Qdrant with `enable_hybrid=True` (dense + sparse BM25)
- **Retrieval**: Score-threshold filtering + sorted by relevance
- **Supported Sources**: S3 URIs, local PDFs, URLs

```bash
# Ingest documents
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -F "files=@annual_report.pdf"
```

---

## WebSocket Streaming

```javascript
// Client receives agent step-by-step reasoning in real time
ws.onmessage = (event) => {
  const { type, node, data } = JSON.parse(event.data);
  if (type === "node_update") {
    // Show agent reasoning: planner → executor → critic
    appendAgentStep(node, data);
  }
};
```

---

## Running Tests

```bash
make test       # All tests
make test-cov   # With coverage
pytest tests/test_agents.py -v -s   # Agent tests with output
```

---

## Deployment

```bash
# Terraform: EKS (us-east-1) + RDS + ElastiCache + S3
cd infra/terraform && terraform init && terraform apply

# CI/CD: GitHub Actions
# push to main → pytest → ECR push → kubectl rolling update
```

**Kubernetes**: HPA scales 3→20 replicas on CPU (70%) and memory (80%).

---

## Resume Bullet Points 🚀

- **Designed** production multi-agent RAG platform using LangGraph v0.3 StateGraph with Planner-Executor-Critic loop, supporting 3× self-revision and human-in-the-loop interruption
- **Built** 3 production MCP servers (PostgreSQL, Document, Notification) using FastMCP + Streamable HTTP transport (April 2026 standard) with asyncpg connection pooling
- **Implemented** hybrid RAG pipeline (dense + sparse search) with LlamaIndex, Qdrant, semantic chunking, and Cohere reranking; ingests PDFs, S3 documents, URLs
- **Architected** real-time WebSocket streaming API with FastAPI and Next.js 14 showing live agent reasoning; falls back to REST seamlessly
- **Integrated** LangSmith + Langfuse tracing, Prometheus custom metrics (tokens, latency, tool calls), and Grafana dashboards for full observability
- **Deployed** on AWS EKS with HPA (3→20 replicas), Terraform IaC, ArgoCD GitOps, GitHub Actions CI/CD

---

## Folder Structure

```
enterprise-agentic-ai-platform/
├── backend/
│   ├── agents/         # state, graph, planner, executor, critic, memory
│   ├── rag/            # ingestion pipeline + retriever (LlamaIndex + Qdrant)
│   ├── mcp_servers/    # postgres_mcp, document_mcp, notification_mcp
│   ├── api/            # FastAPI routes (health, documents)
│   ├── observability/  # LangSmith + Prometheus metrics
│   └── main.py         # FastAPI app (REST + WebSocket)
├── frontend/           # Next.js 14 chat UI + agent trace sidebar
├── infra/
│   ├── k8s/            # Deployment, HPA, ConfigMaps
│   ├── terraform/      # EKS, RDS, ElastiCache, S3
│   ├── docker/         # Backend + frontend Dockerfiles
│   └── .github/        # CI/CD workflow
├── tests/              # pytest-asyncio agent tests
├── docker-compose.yml  # Full local stack (11 services)
└── Makefile            # All dev commands
```
