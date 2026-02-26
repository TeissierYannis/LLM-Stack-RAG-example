"""Document ingestion service: parse, chunk, embed, and store.

Supports two modes:
- Synchronous (default): full pipeline runs in the upload request
- Background (Celery): file stored in object storage, processing queued
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.langfuse_client import (
    create_span,
    create_trace,
    end_span,
    flush,
)
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
    # Create a Langfuse trace for the full ingestion
    trace = create_trace(
        name="document-ingestion",
        metadata={
            "filename": filename,
            "file_type": file_type,
            "file_size": len(content),
            "collection": collection_name,
            "assistant_id": str(assistant_id),
        },
        tags=["ingestion"],
    )

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
    storage_span = create_span(trace, name="upload-storage", input={"provider": settings.storage_provider})
    storage_key = await upload_file(
        str(assistant_id), str(doc.id), filename, content
    )
    doc.storage_key = storage_key
    await db.commit()
    end_span(storage_span, output={"storage_key": storage_key})

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
        end_span(create_span(trace, name="celery-queued"), output={"queued": True})
        flush()
        return doc

    # Synchronous processing
    try:
        parse_span = create_span(trace, name="parse-document", input={"file_type": file_type})
        text = await parse_document(content, file_type)
        doc.content_preview = text[:500]
        end_span(parse_span, output={"text_length": len(text)})

        chunk_span = create_span(trace, name="chunk-text", input={"text_length": len(text)})
        chunks = chunk_text(text)
        doc.chunk_count = len(chunks)
        end_span(chunk_span, output={"chunk_count": len(chunks)})

        if not chunks:
            doc.status = "error"
            doc.error_message = "No text content extracted"
            await db.commit()
            flush()
            return doc

        embed_span = create_span(trace, name="embed-chunks", input={"chunk_count": len(chunks)})
        all_embeddings = []
        for i in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[i : i + EMBED_BATCH_SIZE]
            batch_embeddings = await get_embeddings(batch, trace=embed_span)
            all_embeddings.extend(batch_embeddings)
        end_span(embed_span, output={"embeddings_count": len(all_embeddings)})

        store_span = create_span(trace, name="store-vectors", input={"collection": collection_name})
        await store_chunks(
            collection_name=collection_name,
            document_id=str(doc.id),
            filename=filename,
            chunks=chunks,
            embeddings=all_embeddings,
        )
        end_span(store_span, output={"stored": len(chunks)})

        doc.status = "ready"
        await db.commit()
        logger.info(f"Ingested document {filename}: {len(chunks)} chunks → {collection_name}")
        flush()
        return doc

    except Exception as e:
        doc.status = "error"
        doc.error_message = str(e)
        await db.commit()
        logger.exception(f"Error ingesting document {filename}")
        flush()
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
