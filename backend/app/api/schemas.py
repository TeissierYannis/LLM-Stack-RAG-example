"""Pydantic schemas for API request/response."""

import uuid
from datetime import datetime

from pydantic import BaseModel


# --- Chat ---
class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None
    model: str | None = None
    use_rag: bool = True


class SourceReference(BaseModel):
    filename: str
    chunk_index: int
    score: float
    text_preview: str


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message: str
    sources: list[SourceReference]


# --- Conversation ---
class ConversationSummary(BaseModel):
    id: uuid.UUID
    title: str
    model: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sources: str | None
    created_at: datetime


class ConversationDetail(BaseModel):
    id: uuid.UUID
    title: str
    model: str
    messages: list[MessageOut]


# --- Document ---
class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    content_preview: str | None
    status: str
    error_message: str | None
    created_at: datetime


# --- Models ---
class ModelInfo(BaseModel):
    name: str
    provider: str
    model_type: str  # "completion" or "embedding"


class ModelsResponse(BaseModel):
    completion_models: list[ModelInfo]
    embedding_models: list[ModelInfo]
