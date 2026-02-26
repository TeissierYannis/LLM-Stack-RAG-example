"""Document ingestion service: parse, chunk, embed, and store.

Supports two modes:
- Synchronous (default): full pipeline runs in the upload request
- Background (Celery): file stored in object storage, processing queued
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import delete_file, delete_prefix, upload_file
from app.models.document import Document
from app.rag.chunker import chunk_text
from app.rag.embeddings import get_embeddings
from app.rag.parser import parse_document
from app.rag.vectorstore import delete_document_chunks, store_chunks

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 32


async def ingest_document(
    db: AsyncSession,
    assistant_id: uuid.UUID,
    collection_name: str,
    filename: str,
    file_type: str,
    content: bytes,
) -> Document:
    """Full document ingestion pipeline.

    If USE_CELERY=true, stores the file in object storage and queues
    a background task. Otherwise processes synchronously.
    """
    doc = Document(
        id=uuid.uuid4(),
        assistant_id=assistant_id,
        filename=filename,
        file_type=file_type,
        file_size=len(content),
        status="processing",
    )
    db.add(doc)
    await db.commit()

    # Store raw file in object storage (S3/GCS/Azure/local)
    storage_key = await upload_file(
        str(assistant_id), str(doc.id), filename, content
    )
    doc.storage_key = storage_key
    await db.commit()

    if settings.use_celery:
        # Queue background processing
        from app.worker import process_document_task
        process_document_task.delay(
            document_id=str(doc.id),
            assistant_id=str(assistant_id),
            collection_name=collection_name,
            filename=filename,
            file_type=file_type,
            storage_key=storage_key,
        )
        logger.info(f"Queued document {filename} for background processing")
        return doc

    # Synchronous processing
    try:
        text = await parse_document(content, file_type)
        doc.content_preview = text[:500]

        chunks = chunk_text(text)
        doc.chunk_count = len(chunks)

        if not chunks:
            doc.status = "error"
            doc.error_message = "No text content extracted"
            await db.commit()
            return doc

        all_embeddings = []
        for i in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[i : i + EMBED_BATCH_SIZE]
            batch_embeddings = await get_embeddings(batch)
            all_embeddings.extend(batch_embeddings)

        await store_chunks(
            collection_name=collection_name,
            document_id=str(doc.id),
            filename=filename,
            chunks=chunks,
            embeddings=all_embeddings,
        )

        doc.status = "ready"
        await db.commit()
        logger.info(f"Ingested document {filename}: {len(chunks)} chunks → {collection_name}")
        return doc

    except Exception as e:
        doc.status = "error"
        doc.error_message = str(e)
        await db.commit()
        logger.exception(f"Error ingesting document {filename}")
        raise


async def remove_document(db: AsyncSession, document_id: uuid.UUID, collection_name: str):
    """Remove a document and its chunks from DB, vector store, and object storage."""
    doc = await db.get(Document, document_id)
    if not doc:
        return None

    await delete_document_chunks(collection_name, str(document_id))

    # Remove from object storage
    if doc.storage_key:
        try:
            await delete_file(doc.storage_key)
        except Exception:
            logger.warning(f"Could not delete storage file: {doc.storage_key}")

    await db.delete(doc)
    await db.commit()
    return doc
