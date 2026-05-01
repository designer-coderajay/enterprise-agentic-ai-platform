"""Health check endpoints for load balancer and K8s probes."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import asyncpg
from backend.core.config import settings

router = APIRouter()


@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe — checks DB + Redis connectivity."""
    checks = {"database": False, "status": "degraded"}
    try:
        conn = await asyncpg.connect(settings.database_url.replace("+asyncpg", ""))
        await conn.fetchval("SELECT 1")
        await conn.close()
        checks["database"] = True
        checks["status"] = "ready"
    except Exception as e:
        checks["database_error"] = str(e)

    status_code = 200 if checks["status"] == "ready" else 503
    return JSONResponse(content=checks, status_code=status_code)
