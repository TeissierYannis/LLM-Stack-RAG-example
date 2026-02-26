"""Assistant CRUD API: create, read, update, delete custom assistants."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AssistantCreate, AssistantOut, AssistantUpdate
from app.core.database import get_db
from app.models.assistant import Assistant
from app.models.document import Document
from app.rag.vectorstore import delete_collection, ensure_collection

router = APIRouter(prefix="/assistants", tags=["assistants"])


def _make_collection_name(assistant_id: uuid.UUID) -> str:
    """Generate a Qdrant collection name from assistant ID."""
    return f"assistant_{str(assistant_id).replace('-', '')[:12]}"


@router.post("", response_model=AssistantOut)
async def create_assistant(data: AssistantCreate, db: AsyncSession = Depends(get_db)):
    """Create a new assistant with its own RAG knowledge base."""
    assistant_id = uuid.uuid4()
    collection_name = _make_collection_name(assistant_id)

    assistant = Assistant(
        id=assistant_id,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        model=data.model,
        embedding_model=data.embedding_model,
        qdrant_collection=collection_name,
        avatar_color=data.avatar_color,
        chunk_size=data.chunk_size,
        chunk_overlap=data.chunk_overlap,
        top_k=data.top_k,
    )
    db.add(assistant)
    await db.commit()
    await db.refresh(assistant)

    # Pre-create the Qdrant collection
    await ensure_collection(collection_name)

    return AssistantOut(
        id=assistant.id,
        name=assistant.name,
        description=assistant.description,
        system_prompt=assistant.system_prompt,
        model=assistant.model,
        embedding_model=assistant.embedding_model,
        qdrant_collection=assistant.qdrant_collection,
        avatar_color=assistant.avatar_color,
        chunk_size=assistant.chunk_size,
        chunk_overlap=assistant.chunk_overlap,
        top_k=assistant.top_k,
        document_count=0,
        created_at=assistant.created_at,
        updated_at=assistant.updated_at,
    )


@router.get("", response_model=list[AssistantOut])
async def list_assistants(db: AsyncSession = Depends(get_db)):
    """List all assistants with document counts."""
    stmt = (
        select(Assistant, func.count(Document.id).label("doc_count"))
        .outerjoin(Document)
        .group_by(Assistant.id)
        .order_by(Assistant.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        AssistantOut(
            id=a.id,
            name=a.name,
            description=a.description,
            system_prompt=a.system_prompt,
            model=a.model,
            embedding_model=a.embedding_model,
            qdrant_collection=a.qdrant_collection,
            avatar_color=a.avatar_color,
            chunk_size=a.chunk_size,
            chunk_overlap=a.chunk_overlap,
            top_k=a.top_k,
            document_count=doc_count,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a, doc_count in rows
    ]


@router.get("/{assistant_id}", response_model=AssistantOut)
async def get_assistant(assistant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific assistant."""
    stmt = (
        select(Assistant, func.count(Document.id).label("doc_count"))
        .outerjoin(Document)
        .where(Assistant.id == assistant_id)
        .group_by(Assistant.id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Assistant not found")

    a, doc_count = row
    return AssistantOut(
        id=a.id,
        name=a.name,
        description=a.description,
        system_prompt=a.system_prompt,
        model=a.model,
        embedding_model=a.embedding_model,
        qdrant_collection=a.qdrant_collection,
        avatar_color=a.avatar_color,
        chunk_size=a.chunk_size,
        chunk_overlap=a.chunk_overlap,
        top_k=a.top_k,
        document_count=doc_count,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


@router.patch("/{assistant_id}", response_model=AssistantOut)
async def update_assistant(
    assistant_id: uuid.UUID, data: AssistantUpdate, db: AsyncSession = Depends(get_db)
):
    """Update an assistant's configuration."""
    assistant = await db.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assistant, field, value)

    await db.commit()
    await db.refresh(assistant)

    # Get document count
    count_result = await db.execute(
        select(func.count(Document.id)).where(Document.assistant_id == assistant_id)
    )
    doc_count = count_result.scalar() or 0

    return AssistantOut(
        id=assistant.id,
        name=assistant.name,
        description=assistant.description,
        system_prompt=assistant.system_prompt,
        model=assistant.model,
        embedding_model=assistant.embedding_model,
        qdrant_collection=assistant.qdrant_collection,
        avatar_color=assistant.avatar_color,
        chunk_size=assistant.chunk_size,
        chunk_overlap=assistant.chunk_overlap,
        top_k=assistant.top_k,
        document_count=doc_count,
        created_at=assistant.created_at,
        updated_at=assistant.updated_at,
    )


@router.delete("/{assistant_id}")
async def delete_assistant(assistant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete an assistant, its documents, its Qdrant collection, and stored files."""
    from app.core.storage import delete_prefix

    assistant = await db.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    # Delete the entire Qdrant collection
    await delete_collection(assistant.qdrant_collection)

    # Delete all stored files for this assistant
    try:
        await delete_prefix(str(assistant_id))
    except Exception:
        pass  # Best effort cleanup

    # Cascade will delete documents; conversations keep assistant_id=NULL
    await db.delete(assistant)
    await db.commit()

    return {"detail": "Assistant deleted", "id": str(assistant_id)}
