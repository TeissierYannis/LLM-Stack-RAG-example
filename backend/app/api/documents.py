"""Document upload and management API, scoped per assistant."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import DocumentOut
from app.core.database import get_db
from app.models.assistant import Assistant
from app.models.document import Document
from app.services.document import ingest_document, remove_document

router = APIRouter(prefix="/assistants/{assistant_id}/documents", tags=["documents"])

ALLOWED_TYPES = {"pdf", "docx", "md", "txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _doc_out(d: Document) -> DocumentOut:
    return DocumentOut(
        id=d.id,
        assistant_id=d.assistant_id,
        filename=d.filename,
        file_type=d.file_type,
        file_size=d.file_size,
        chunk_count=d.chunk_count,
        content_preview=d.content_preview,
        status=d.status,
        error_message=d.error_message,
        created_at=d.created_at,
    )


@router.post("", response_model=DocumentOut)
async def upload_document(
    assistant_id: uuid.UUID, file: UploadFile, db: AsyncSession = Depends(get_db)
):
    """Upload a document into an assistant's knowledge base."""
    assistant = await db.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    doc = await ingest_document(
        db,
        assistant_id=assistant_id,
        collection_name=assistant.qdrant_collection,
        filename=file.filename,
        file_type=extension,
        content=content,
    )
    return _doc_out(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(assistant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List documents in an assistant's knowledge base."""
    assistant = await db.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    result = await db.execute(
        select(Document)
        .where(Document.assistant_id == assistant_id)
        .order_by(Document.created_at.desc())
    )
    return [_doc_out(d) for d in result.scalars().all()]


@router.delete("/{document_id}")
async def delete_document(
    assistant_id: uuid.UUID, document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """Delete a document from an assistant's knowledge base."""
    assistant = await db.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    doc = await remove_document(db, document_id, assistant.qdrant_collection)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"detail": "Document deleted", "id": str(document_id)}
