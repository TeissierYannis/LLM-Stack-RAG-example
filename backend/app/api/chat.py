"""Chat API endpoint with RAG and streaming support."""

import json
import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import ChatRequest, ChatResponse, SourceReference
from app.core.database import get_db
from app.models.conversation import Conversation, Message
from app.rag.retriever import build_rag_messages, retrieve_context
from app.services.chat import stream_completion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Stream chat response with RAG context."""

    # Get or create conversation
    if request.conversation_id:
        conversation = await db.get(Conversation, request.conversation_id)
        if not conversation:
            conversation = Conversation(id=request.conversation_id, model=request.model or "default-completion")
            db.add(conversation)
    else:
        conversation = Conversation(model=request.model or "default-completion")
        db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.commit()

    # Retrieve RAG context
    context = ""
    sources = []
    if request.use_rag:
        context, sources = await retrieve_context(request.message)

    # Build conversation history
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    history_messages = history_result.scalars().all()
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in history_messages[:-1]  # Exclude the message we just added
    ]

    # Build RAG-enhanced messages
    messages = build_rag_messages(request.message, context, conversation_history)

    # Format sources for response
    source_refs = [
        {
            "filename": s["filename"],
            "chunk_index": s["chunk_index"],
            "score": s["score"],
            "text_preview": s["text"][:200],
        }
        for s in sources
    ]

    async def event_generator():
        full_response = []
        try:
            # Send sources first
            yield {"event": "sources", "data": json.dumps(source_refs)}
            yield {"event": "meta", "data": json.dumps({"conversation_id": str(conversation.id)})}

            async for chunk in stream_completion(messages, model=request.model):
                full_response.append(chunk)
                yield {"event": "message", "data": chunk}

            # Save assistant message
            assistant_content = "".join(full_response)
            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_content,
                sources=json.dumps(source_refs) if source_refs else None,
            )
            db.add(assistant_msg)

            # Update conversation title from first message
            if len(history_messages) <= 1:
                conversation.title = request.message[:100]

            await db.commit()
            yield {"event": "done", "data": ""}

        except Exception as e:
            logger.exception("Error during chat streaming")
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Non-streaming chat endpoint."""
    from app.services.chat import get_completion

    # Get or create conversation
    if request.conversation_id:
        conversation = await db.get(Conversation, request.conversation_id)
        if not conversation:
            conversation = Conversation(id=request.conversation_id, model=request.model or "default-completion")
            db.add(conversation)
    else:
        conversation = Conversation(model=request.model or "default-completion")
        db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # Save user message
    user_msg = Message(conversation_id=conversation.id, role="user", content=request.message)
    db.add(user_msg)
    await db.commit()

    # RAG retrieval
    context = ""
    sources = []
    if request.use_rag:
        context, sources = await retrieve_context(request.message)

    messages = build_rag_messages(request.message, context)
    response_text = await get_completion(messages, model=request.model)

    source_refs = [
        SourceReference(
            filename=s["filename"],
            chunk_index=s["chunk_index"],
            score=s["score"],
            text_preview=s["text"][:200],
        )
        for s in sources
    ]

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        sources=json.dumps([sr.model_dump() for sr in source_refs]) if source_refs else None,
    )
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        message=response_text,
        sources=source_refs,
    )
