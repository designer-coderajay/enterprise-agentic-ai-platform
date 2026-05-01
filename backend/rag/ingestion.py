"""Document ingestion pipeline using LlamaIndex."""
import logging
from pathlib import Path
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.ingestion import IngestionPipeline
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient
from backend.core.config import settings

logger = logging.getLogger(__name__)


async def get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


async def ingest_documents(
    source_path: str,
    collection_name: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """
    Ingest documents from a directory or file path into Qdrant.
    Uses semantic chunking for intelligent splitting.
    """
    collection = collection_name or settings.qdrant_collection
    logger.info(f"Ingesting documents from {source_path} into '{collection}'")

    embed_model = OpenAIEmbedding(
        model="text-embedding-3-large",
        api_key=settings.openai_api_key,
        dimensions=3072,
    )
    Settings.embed_model = embed_model

    client = await get_qdrant_client()
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection,
        enable_hybrid=True,  # Sparse + dense hybrid search
    )

    # Semantic chunking: splits at natural semantic boundaries
    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=embed_model,
    )

    pipeline = IngestionPipeline(
        transformations=[splitter],
        vector_store=vector_store,
    )

    # Load documents
    reader = SimpleDirectoryReader(
        input_dir=source_path if Path(source_path).is_dir() else None,
        input_files=[source_path] if Path(source_path).is_file() else None,
        recursive=True,
        filename_as_id=True,
    )
    documents = reader.load_data()

    # Add metadata
    if metadata:
        for doc in documents:
            doc.metadata.update(metadata)

    # Run pipeline
    nodes = await pipeline.arun(documents=documents)
    logger.info(f"Ingested {len(nodes)} chunks from {len(documents)} documents")

    return {
        "documents_processed": len(documents),
        "chunks_created": len(nodes),
        "collection": collection,
    }
