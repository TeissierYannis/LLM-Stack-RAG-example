"""Celery worker for background document processing.

Instead of processing documents synchronously in the upload request,
heavy tasks (parsing, OCR, chunking, embedding) run in the background.
This keeps the API responsive even for large files.

Usage:
    celery -A app.worker worker --loglevel=info
"""

import logging
import uuid

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "enterprise-chat-rag",
    broker=settings.celery_broker_url or settings.redis_url,
    backend=settings.celery_result_backend or settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # One task at a time (heavy processing)
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(
    self,
    document_id: str,
    assistant_id: str,
    collection_name: str,
    filename: str,
    file_type: str,
    storage_key: str,
):
    """Background task: download file from storage, parse, chunk, embed, store.

    This runs in a Celery worker process, separate from the API.
    """
    import asyncio

    asyncio.run(
        _async_process_document(
            document_id, assistant_id, collection_name, filename, file_type, storage_key
        )
    )


async def _async_process_document(
    document_id: str,
    assistant_id: str,
    collection_name: str,
    filename: str,
    file_type: str,
    storage_key: str,
):
    """Async document processing pipeline (runs inside Celery task)."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.models.document import Document
    from app.rag.chunker import chunk_text
    from app.rag.embeddings import get_embeddings
    from app.rag.parser import parse_document
    from app.rag.vectorstore import store_chunks
    from app.core.storage import download_file

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        doc = await db.get(Document, uuid.UUID(document_id))
        if not doc:
            logger.error(f"Document {document_id} not found")
            return

        try:
            # 1. Download from object storage
            content = await download_file(storage_key)

            # 2. Parse (async — supports cloud OCR)
            text = await parse_document(content, file_type)
            doc.content_preview = text[:500]

            # 3. Chunk
            chunks = chunk_text(text)
            doc.chunk_count = len(chunks)

            if not chunks:
                doc.status = "error"
                doc.error_message = "No text content extracted"
                await db.commit()
                return

            # 4. Embed (in batches)
            all_embeddings = []
            batch_size = 32
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                batch_embeddings = await get_embeddings(batch)
                all_embeddings.extend(batch_embeddings)

            # 5. Store in Qdrant
            await store_chunks(
                collection_name=collection_name,
                document_id=document_id,
                filename=filename,
                chunks=chunks,
                embeddings=all_embeddings,
            )

            doc.status = "ready"
            await db.commit()
            logger.info(f"[worker] Ingested {filename}: {len(chunks)} chunks → {collection_name}")

        except Exception as e:
            doc.status = "error"
            doc.error_message = str(e)
            await db.commit()
            logger.exception(f"[worker] Error ingesting {filename}")

    await engine.dispose()
