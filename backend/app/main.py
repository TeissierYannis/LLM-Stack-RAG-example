"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, conversations, documents, models
from app.core.config import settings
from app.core.database import init_db

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enterprise Chat RAG API",
    description="Chat d'entreprise avec RAG via LiteLLM (Bedrock, Azure Foundry, Vertex AI)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(models.router, prefix="/api")


@app.on_event("startup")
async def startup():
    logger.info("Starting Enterprise Chat RAG API")
    await init_db()
    logger.info("Database initialized")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "enterprise-chat-rag"}
