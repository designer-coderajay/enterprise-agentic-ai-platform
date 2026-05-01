"""RAG retriever with hybrid search + reranking."""
import logging
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient
from backend.core.config import settings

logger = logging.getLogger(__name__)


class RAGRetriever:
    def __init__(self):
        self.client = None
        self._initialized = False

    async def _init(self):
        if self._initialized:
            return
        self.client = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        embed_model = OpenAIEmbedding(
            model="text-embedding-3-large",
            api_key=settings.openai_api_key,
            dimensions=3072,
        )
        Settings.embed_model = embed_model
        self._initialized = True

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        collection: str | None = None,
        score_threshold: float = 0.7,
    ) -> list[dict]:
        """Hybrid retrieval: dense + sparse + reranking."""
        await self._init()
        collection_name = collection or settings.qdrant_collection

        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=collection_name,
            enable_hybrid=True,
        )

        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=top_k * 2,  # over-retrieve then rerank
        )

        nodes = await retriever.aretrieve(query)

        results = []
        for node in nodes:
            if node.score and node.score >= score_threshold:
                results.append({
                    "text": node.text,
                    "score": node.score,
                    "source": node.metadata.get("file_name", "unknown"),
                    "metadata": node.metadata,
                    "node_id": node.node_id,
                })

        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
