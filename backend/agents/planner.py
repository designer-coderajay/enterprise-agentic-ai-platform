"""Planner Agent: breaks complex tasks into ordered steps."""
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from backend.agents.state import AgentState

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are a strategic planning agent. Your job is to decompose complex tasks 
into a clear, ordered list of executable steps.

Rules:
- Each step must be specific and actionable
- Steps should be ordered by dependency
- Maximum 6 steps per plan
- Each step on its own line starting with a number

Output format:
1. [First step]
2. [Second step]
...

Available tools you can reference:
- search_knowledge_base: Search internal documents
- query_database: Run SQL queries
- fetch_github: Get code/issues from GitHub
- fetch_notion: Get pages from Notion
- send_notification: Send Slack/email alerts
- web_search: Search the internet via Exa
"""


class PlannerAgent:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def plan(self, state: AgentState) -> AgentState:
        logger.info(f"[Planner] Creating plan for task: {state.task[:80]}...")

        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Task: {state.task}

Retrieved context from memory:
{state.retrieved_context[:2000] if state.retrieved_context else "No prior context"}

Create a step-by-step plan to complete this task.
"""),
        ]

        response = await self.llm.ainvoke(messages)
        plan_text = response.content

        # Parse numbered steps
        steps = []
        for line in plan_text.strip().split("\n"):
            line = line.strip()
            if line and line[0].isdigit() and "." in line:
                step = line.split(".", 1)[1].strip()
                if step:
                    steps.append(step)

        if not steps:
            steps = [state.task]  # fallback: treat task as single step

        logger.info(f"[Planner] Generated {len(steps)} steps")
        state.plan = steps
        state.current_step = 0
        state.messages = state.messages + [response]

        return state
