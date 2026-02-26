"""Conversation history API."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import ConversationDetail, ConversationSummary, MessageOut
from app.core.database import get_db
from app.models.assistant import Assistant
from app.models.conversation import Conversation, Message

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    assistant_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List conversations, optionally filtered by assistant."""
    stmt = (
        select(
            Conversation,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
    )
    if assistant_id:
        stmt = stmt.where(Conversation.assistant_id == assistant_id)

    result = await db.execute(stmt)
    rows = result.all()

    # Batch fetch assistant names
    assistant_ids = {conv.assistant_id for conv, _ in rows if conv.assistant_id}
    assistant_names = {}
    if assistant_ids:
        a_result = await db.execute(select(Assistant).where(Assistant.id.in_(assistant_ids)))
        for a in a_result.scalars().all():
            assistant_names[a.id] = a.name

    return [
        ConversationSummary(
            id=conv.id,
            assistant_id=conv.assistant_id,
            assistant_name=assistant_names.get(conv.assistant_id) if conv.assistant_id else None,
            title=conv.title,
            model=conv.model,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=count,
        )
        for conv, count in rows
    ]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a conversation with all messages."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    sorted_messages = sorted(conv.messages, key=lambda m: m.created_at)

    return ConversationDetail(
        id=conv.id,
        assistant_id=conv.assistant_id,
        title=conv.title,
        model=conv.model,
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                sources=m.sources,
                created_at=m.created_at,
            )
            for m in sorted_messages
        ],
    )


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a conversation and all its messages."""
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conv)
    await db.commit()
    return {"detail": "Conversation deleted"}
