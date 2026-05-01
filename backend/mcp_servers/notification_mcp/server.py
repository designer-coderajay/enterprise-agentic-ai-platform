"""
Notification MCP Server — sends alerts via Slack, Email, and Webhook.
"""
import json
import logging
from mcp.server.fastmcp import FastMCP
import httpx
from backend.core.config import settings

logger = logging.getLogger(__name__)
mcp = FastMCP(name="Notification MCP Server", version="1.0.0")


@mcp.tool()
async def send_slack_message(channel: str, message: str, blocks: list | None = None) -> str:
    """
    Send a message to a Slack channel.

    Args:
        channel: Channel name or ID (e.g., '#general' or 'C1234567')
        message: Plain text message
        blocks: Optional Slack Block Kit blocks for rich formatting

    Returns:
        JSON with success status and message timestamp
    """
    if not settings.slack_bot_token:
        return json.dumps({"error": "Slack token not configured"})

    payload: dict = {"channel": channel, "text": message}
    if blocks:
        payload["blocks"] = blocks

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
            json=payload,
        )
        data = response.json()
        if data.get("ok"):
            return json.dumps({"success": True, "ts": data.get("ts"), "channel": channel})
        return json.dumps({"error": data.get("error", "Unknown Slack error")})


@mcp.tool()
async def send_webhook(url: str, payload: dict, headers: dict | None = None) -> str:
    """
    Send a POST request to a webhook endpoint.

    Args:
        url: Webhook URL
        payload: JSON payload to send
        headers: Optional HTTP headers

    Returns:
        JSON with response status and body
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers or {})
            return json.dumps({
                "status_code": response.status_code,
                "success": response.is_success,
                "body": response.text[:500],
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def create_slack_reminder(user_id: str, text: str, time_unix: int) -> str:
    """
    Create a Slack reminder for a user.

    Args:
        user_id: Slack user ID
        text: Reminder message
        time_unix: Unix timestamp for when to send the reminder

    Returns:
        JSON with reminder ID
    """
    if not settings.slack_bot_token:
        return json.dumps({"error": "Slack token not configured"})

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/reminders.add",
            headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
            json={"text": text, "time": time_unix, "user": user_id},
        )
        data = response.json()
        return json.dumps({"success": data.get("ok"), "reminder_id": data.get("reminder", {}).get("id")})


if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    session_manager = StreamableHTTPSessionManager(
        app=mcp._mcp_server, json_response=True, stateless=True
    )
    app = Starlette(routes=[Mount("/mcp", app=session_manager.handle_request)])
    uvicorn.run(app, host="0.0.0.0", port=settings.notification_mcp_port)
