"""Assistant model: custom assistants with isolated RAG knowledge bases."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Assistant(Base):
    __tablename__ = "assistants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(
        Text,
        default="Tu es un assistant d'entreprise intelligent. Réponds de manière précise et concise en te basant sur le contexte fourni.",
    )
    model: Mapped[str] = mapped_column(default="default-completion")
    embedding_model: Mapped[str] = mapped_column(default="default-embedding")
    # Each assistant gets its own Qdrant collection: "assistant_{id_short}"
    qdrant_collection: Mapped[str] = mapped_column(unique=True)
    avatar_color: Mapped[str] = mapped_column(default="#3b82f6")  # For UI
    chunk_size: Mapped[int] = mapped_column(default=512)
    chunk_overlap: Mapped[int] = mapped_column(default=100)
    top_k: Mapped[int] = mapped_column(default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["Document"]] = relationship(back_populates="assistant", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="assistant")


# Avoid circular imports - these are resolved by SQLAlchemy via string refs
from app.models.document import Document  # noqa: E402, F811
from app.models.conversation import Conversation  # noqa: E402, F811
