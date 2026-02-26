"""Pydantic schemas for API request/response."""

import uuid
from datetime import datetime

from pydantic import BaseModel


# --- Assistant ---
class AssistantCreate(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str = "Tu es un assistant d'entreprise intelligent. Réponds de manière précise et concise en te basant sur le contexte fourni."
    model: str = "default-completion"
    embedding_model: str = "default-embedding"
    avatar_color: str = "#3b82f6"
    chunk_size: int = 512
    chunk_overlap: int = 100
    top_k: int = 5


class AssistantUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    embedding_model: str | None = None
    avatar_color: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    top_k: int | None = None


class AssistantOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    system_prompt: str
    model: str
    embedding_model: str
    qdrant_collection: str
    avatar_color: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


# --- Chat ---
class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None
    assistant_id: uuid.UUID | None = None
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
    assistant_id: uuid.UUID | None
    assistant_name: str | None = None
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
    assistant_id: uuid.UUID | None
    title: str
    model: str
    messages: list[MessageOut]


# --- Document ---
class DocumentOut(BaseModel):
    id: uuid.UUID
    assistant_id: uuid.UUID
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
