"""Executor Agent: executes plan steps using MCP tools."""
import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client

from backend.agents.state import AgentState
from backend.core.config import settings

logger = logging.getLogger(__name__)

EXECUTOR_SYSTEM_PROMPT = """You are an execution agent. You have access to tools via MCP servers.
Execute tasks precisely. When using tools:
1. Choose the most appropriate tool for each step
2. Pass correct parameters
3. Synthesize tool outputs into coherent answers
4. Always cite your sources

If a tool fails, try an alternative approach before giving up."""


class ExecutorAgent:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def _get_mcp_tools(self) -> list[dict]:
        """Discover and return all available MCP tools."""
        tools = []
        mcp_endpoints = [
            f"http://localhost:{settings.postgres_mcp_port}/mcp",
            f"http://localhost:{settings.document_mcp_port}/mcp",
            f"http://localhost:{settings.notification_mcp_port}/mcp",
        ]
        for endpoint in mcp_endpoints:
            try:
                async with streamablehttp_client(endpoint) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        for tool in result.tools:
                            tools.append({
                                "name": tool.name,
                                "description": tool.description,
                                "input_schema": tool.inputSchema,
                                "_endpoint": endpoint,
                            })
            except Exception as e:
                logger.warning(f"Could not connect to MCP at {endpoint}: {e}")
        return tools

    async def _call_mcp_tool(self, tool_name: str, tool_args: dict, endpoint: str) -> str:
        """Call a specific MCP tool and return string result."""
        try:
            async with streamablehttp_client(endpoint) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, tool_args)
                    return result.content[0].text if result.content else "No result"
        except Exception as e:
            return f"Tool call failed: {str(e)}"

    async def execute(self, state: AgentState) -> AgentState:
        logger.info(f"[Executor] Executing step {state.current_step + 1}/{len(state.plan)}")

        current_step = state.plan[state.current_step] if state.plan else state.task
        tools = await self._get_mcp_tools()

        # Build tool bindings for Claude
        tool_definitions = [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"],
            }
            for t in tools
        ]

        messages = [
            SystemMessage(content=EXECUTOR_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Original task: {state.task}
Current step: {current_step}
Previous results: {json.dumps(state.tool_results[-3:], indent=2) if state.tool_results else "None"}
Critique from last round: {state.critique if state.critique else "None"}

Execute this step using the available tools.
"""),
        ]

        llm_with_tools = self.llm.bind_tools(tool_definitions) if tool_definitions else self.llm
        response = await llm_with_tools.ainvoke(messages)

        tool_results = list(state.tool_results)

        # Process tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Find endpoint for this tool
                endpoint = next(
                    (t["_endpoint"] for t in tools if t["name"] == tool_name),
                    f"http://localhost:{settings.postgres_mcp_port}/mcp",
                )

                result = await self._call_mcp_tool(tool_name, tool_args, endpoint)
                tool_results.append({
                    "step": state.current_step,
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result,
                })
                logger.info(f"[Executor] Tool '{tool_name}' returned: {result[:100]}...")

        # Synthesize final answer
        synthesis_prompt = f"""
Based on the tool results:
{json.dumps(tool_results, indent=2)}

Provide a comprehensive answer to: {state.task}
Include citations from tool results where applicable.
"""
        synthesis = await self.llm.ainvoke([HumanMessage(content=synthesis_prompt)])

        state.tool_results = tool_results
        state.final_answer = synthesis.content
        state.current_step = min(state.current_step + 1, len(state.plan) - 1)
        state.messages = state.messages + [response, synthesis]
        state.revision_count = state.revision_count + 1

        return state
