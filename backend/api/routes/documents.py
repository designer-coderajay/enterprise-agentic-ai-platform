"""Document ingestion and management endpoints."""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from pathlib import Path
import tempfile
import shutil
from backend.rag.ingestion import ingest_documents

router = APIRouter()


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    collection: str = "enterprise_knowledge",
    background_tasks: BackgroundTasks = None,
):
    """Upload and ingest a document into the knowledge base."""
    if not file.filename.endswith((".pdf", ".txt", ".md", ".docx")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=Path(file.filename).suffix
    ) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    if background_tasks:
        background_tasks.add_task(ingest_documents, tmp_path, collection)
        return {"message": "Document queued for ingestion", "filename": file.filename}

    result = await ingest_documents(tmp_path, collection)
    return result
