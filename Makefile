.PHONY: dev build test lint deploy clean

# ── Development ──────────────────────────────────────────────────
dev:
	docker compose up -d postgres redis qdrant
	uvicorn backend.main:app --reload --port 8000 &
	cd frontend && npm run dev

dev-full:
	docker compose up --build

# ── MCP Servers ──────────────────────────────────────────────────
mcp-start:
	python -m backend.mcp_servers.postgres_mcp.server &
	python -m backend.mcp_servers.document_mcp.server &
	python -m backend.mcp_servers.notification_mcp.server &

# ── Database ─────────────────────────────────────────────────────
db-migrate:
	alembic upgrade head

db-rollback:
	alembic downgrade -1

db-reset:
	alembic downgrade base && alembic upgrade head

# ── Testing ──────────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ --cov=backend --cov-report=html --cov-report=term

# ── Linting ───────────────────────────────────────────────────────
lint:
	ruff check backend/ tests/
	mypy backend/ --ignore-missing-imports

# ── Production Build ──────────────────────────────────────────────
build:
	docker build -t enterprise-agentic-ai -f infra/docker/backend.Dockerfile .

# ── K8s Deploy ───────────────────────────────────────────────────
deploy-staging:
	kubectl apply -f infra/k8s/ -n agentic-ai
	kubectl rollout status deployment/agentic-backend -n agentic-ai

# ── Load Test ─────────────────────────────────────────────────────
load-test:
	locust -f tests/load_test.py --host http://localhost:8000 --users 100 --spawn-rate 10

# ── Clean ─────────────────────────────────────────────────────────
clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
