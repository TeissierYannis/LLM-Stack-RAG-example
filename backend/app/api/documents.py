"""Document upload and management API."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import DocumentOut
from app.core.database import get_db
from app.models.document import Document
from app.services.document import ingest_document, remove_document

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {"pdf", "docx", "md", "txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("", response_model=DocumentOut)
async def upload_document(file: UploadFile, db: AsyncSession = Depends(get_db)):
    """Upload and process a document for RAG."""
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    # Read content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    doc = await ingest_document(db, file.filename, extension, content)
    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        content_preview=doc.content_preview,
        status=doc.status,
        error_message=doc.error_message,
        created_at=doc.created_at,
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all uploaded documents."""
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    return [
        DocumentOut(
            id=d.id,
            filename=d.filename,
            file_type=d.file_type,
            file_size=d.file_size,
            chunk_count=d.chunk_count,
            content_preview=d.content_preview,
            status=d.status,
            error_message=d.error_message,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.delete("/{document_id}")
async def delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a document and its vector embeddings."""
    doc = await remove_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"detail": "Document deleted", "id": str(document_id)}
