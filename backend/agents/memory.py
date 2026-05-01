"""Memory Agent: retrieves relevant context from RAG + conversation history."""
import logging
from backend.agents.state import AgentState
from backend.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)


class MemoryAgent:
    def __init__(self):
        self.retriever = RAGRetriever()

    async def retrieve(self, state: AgentState) -> AgentState:
        logger.info(f"[Memory] Retrieving context for: {state.task[:60]}...")
        try:
            results = await self.retriever.retrieve(
                query=state.task,
                top_k=5,
                collection=None,  # search all collections
            )
            context_parts = []
            citations = []
            for i, r in enumerate(results):
                context_parts.append(f"[{i+1}] {r['text']}")
                citations.append({
                    "index": i + 1,
                    "source": r.get("source", "unknown"),
                    "score": r.get("score", 0.0),
                })

            state.retrieved_context = "\n\n".join(context_parts)
            state.citations = citations
            logger.info(f"[Memory] Retrieved {len(results)} relevant chunks")

        except Exception as e:
            logger.warning(f"[Memory] Retrieval failed: {e}")
            state.retrieved_context = ""

        return state
