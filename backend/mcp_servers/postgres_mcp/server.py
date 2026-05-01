"""
PostgreSQL MCP Server — exposes DB operations as MCP tools.
Transport: Streamable HTTP (production standard, OAuth 2.1 ready)
"""
import asyncio
import json
import logging
from mcp.server.fastmcp import FastMCP
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
import asyncpg
from backend.core.config import settings

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="PostgreSQL MCP Server",
    version="1.0.0",
    description="Exposes PostgreSQL database operations as MCP tools",
)

# Connection pool (shared across requests)
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url.replace("+asyncpg", ""),
            min_size=5,
            max_size=20,
        )
    return _pool


@mcp.tool()
async def query_database(
    sql: str,
    params: list | None = None,
    max_rows: int = 100,
) -> str:
    """
    Execute a read-only SQL query against the database.

    Args:
        sql: SQL SELECT query to execute
        params: Optional query parameters (prevents SQL injection)
        max_rows: Maximum rows to return (default 100)

    Returns:
        JSON string with query results
    """
    if not sql.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are allowed"})

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *(params or []))
            results = [dict(row) for row in rows[:max_rows]]
            return json.dumps({
                "rows": results,
                "count": len(results),
                "truncated": len(rows) > max_rows,
            }, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def list_tables() -> str:
    """List all tables in the database with their column information."""
    sql = """
        SELECT
            t.table_name,
            array_agg(c.column_name || ' ' || c.data_type ORDER BY c.ordinal_position) as columns
        FROM information_schema.tables t
        JOIN information_schema.columns c ON t.table_name = c.table_name
        WHERE t.table_schema = 'public'
        GROUP BY t.table_name
        ORDER BY t.table_name
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql)
            tables = [{"table": r["table_name"], "columns": r["columns"]} for r in rows]
            return json.dumps(tables, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def insert_record(table: str, data: dict) -> str:
    """
    Insert a record into a database table.

    Args:
        table: Table name
        data: Dictionary of column:value pairs

    Returns:
        JSON with inserted record ID
    """
    cols = list(data.keys())
    vals = list(data.values())
    placeholders = ", ".join(f"${i+1}" for i in range(len(cols)))
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) RETURNING id"

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchrow(sql, *vals)
            return json.dumps({"inserted_id": result["id"] if result else None})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount

    session_manager = StreamableHTTPSessionManager(
        app=mcp._mcp_server,
        event_store=None,
        json_response=True,
        stateless=True,
    )

    starlette_app = Starlette(
        routes=[Mount("/mcp", app=session_manager.handle_request)]
    )

    uvicorn.run(starlette_app, host="0.0.0.0", port=settings.postgres_mcp_port)
