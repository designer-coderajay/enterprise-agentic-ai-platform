"""Critic Agent: evaluates answer quality and flags revisions."""
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from backend.agents.state import AgentState

logger = logging.getLogger(__name__)

CRITIC_SYSTEM_PROMPT = """You are a quality control agent. Evaluate the answer produced by the executor.

Evaluate on:
1. ACCURACY: Is the answer factually correct and supported by tool results?
2. COMPLETENESS: Does it fully address the user's task?
3. CITATIONS: Are sources properly referenced?
4. CLARITY: Is it clear and well-structured?

Respond ONLY with valid JSON:
{
  "score": 0-10,
  "needs_revision": true/false,
  "critique": "specific actionable feedback",
  "confidence": 0.0-1.0
}

If score >= 7, set needs_revision to false."""


class CriticAgent:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def critique(self, state: AgentState) -> AgentState:
        import json
        logger.info(f"[Critic] Evaluating answer quality (revision {state.revision_count})")

        messages = [
            SystemMessage(content=CRITIC_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Original task: {state.task}

Answer produced:
{state.final_answer}

Tool results used:
{json.dumps(state.tool_results, indent=2)[:3000]}

Evaluate the answer quality.
"""),
        ]

        response = await self.llm.ainvoke(messages)

        try:
            # Extract JSON from response
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            evaluation = json.loads(content)
            state.critique = evaluation.get("critique", "")
            state.needs_revision = evaluation.get("needs_revision", False)
            state.confidence_score = evaluation.get("confidence", 0.8)

            score = evaluation.get("score", 7)
            logger.info(f"[Critic] Score: {score}/10, Needs revision: {state.needs_revision}")

        except json.JSONDecodeError:
            logger.warning("[Critic] Could not parse JSON evaluation, accepting answer as-is")
            state.needs_revision = False
            state.confidence_score = 0.7

        state.messages = state.messages + [response]
        return state
