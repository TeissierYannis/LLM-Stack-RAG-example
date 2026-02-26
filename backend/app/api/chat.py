"""Chat API endpoint with RAG and streaming support, scoped by assistant."""

import json
import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import ChatRequest, ChatResponse, SourceReference
from app.core.config import settings
from app.core.database import get_db
from app.models.assistant import Assistant
from app.models.conversation import Conversation, Message
from app.rag.retriever import build_rag_messages, retrieve_context
from app.services.chat import stream_completion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


async def _resolve_assistant(db: AsyncSession, request: ChatRequest) -> Assistant | None:
    """Resolve the assistant from the request (via assistant_id or existing conversation)."""
    if request.assistant_id:
        return await db.get(Assistant, request.assistant_id)
    if request.conversation_id:
        conv = await db.get(Conversation, request.conversation_id)
        if conv and conv.assistant_id:
            return await db.get(Assistant, conv.assistant_id)
    return None


@router.post("/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Stream chat response with RAG context from the assistant's knowledge base."""

    # Resolve assistant (optional - chat works without one too)
    assistant = await _resolve_assistant(db, request)
    model = request.model or (assistant.model if assistant else "default-completion")

    # Get or create conversation
    if request.conversation_id:
        conversation = await db.get(Conversation, request.conversation_id)
        if not conversation:
            conversation = Conversation(
                id=request.conversation_id,
                assistant_id=request.assistant_id,
                model=model,
            )
            db.add(conversation)
    else:
        conversation = Conversation(
            assistant_id=request.assistant_id,
            model=model,
        )
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

    # Retrieve RAG context from assistant's collection
    context = ""
    sources = []
    if request.use_rag and assistant:
        context, sources = await retrieve_context(
            assistant.qdrant_collection,
            request.message,
            top_k=assistant.top_k,
        )

    # Build conversation history
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    history_messages = history_result.scalars().all()
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in history_messages[:-1]
    ]

    # Build RAG-enhanced messages with assistant's system prompt
    system_prompt = assistant.system_prompt if assistant else None
    messages = build_rag_messages(request.message, context, system_prompt, conversation_history)

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
            yield {"event": "sources", "data": json.dumps(source_refs)}
            yield {"event": "meta", "data": json.dumps({"conversation_id": str(conversation.id)})}

            async for chunk in stream_completion(messages, model=model):
                full_response.append(chunk)
                yield {"event": "message", "data": chunk}

            assistant_content = "".join(full_response)
            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_content,
                sources=json.dumps(source_refs) if source_refs else None,
            )
            db.add(assistant_msg)

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
    """Non-streaming chat endpoint with assistant-scoped RAG."""
    from app.services.chat import get_completion

    assistant = await _resolve_assistant(db, request)
    model = request.model or (assistant.model if assistant else "default-completion")

    # Get or create conversation
    if request.conversation_id:
        conversation = await db.get(Conversation, request.conversation_id)
        if not conversation:
            conversation = Conversation(
                id=request.conversation_id,
                assistant_id=request.assistant_id,
                model=model,
            )
            db.add(conversation)
    else:
        conversation = Conversation(assistant_id=request.assistant_id, model=model)
        db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    user_msg = Message(conversation_id=conversation.id, role="user", content=request.message)
    db.add(user_msg)
    await db.commit()

    # RAG retrieval from assistant's collection
    context = ""
    sources = []
    if request.use_rag and assistant:
        context, sources = await retrieve_context(
            assistant.qdrant_collection,
            request.message,
            top_k=assistant.top_k,
        )

    system_prompt = assistant.system_prompt if assistant else None
    messages = build_rag_messages(request.message, context, system_prompt)
    response_text = await get_completion(messages, model=model)

    source_refs = [
        SourceReference(
            filename=s["filename"],
            chunk_index=s["chunk_index"],
            score=s["score"],
            text_preview=s["text"][:200],
        )
        for s in sources
    ]

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
