"""Document ingestion service: parse, chunk, embed, and store."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.rag.chunker import chunk_text
from app.rag.embeddings import get_embeddings
from app.rag.parser import parse_document
from app.rag.vectorstore import delete_document_chunks, store_chunks

logger = logging.getLogger(__name__)

# Max batch size for embedding requests
EMBED_BATCH_SIZE = 32


async def ingest_document(
    db: AsyncSession,
    assistant_id: uuid.UUID,
    collection_name: str,
    filename: str,
    file_type: str,
    content: bytes,
) -> Document:
    """Full document ingestion pipeline: parse → chunk → embed → store in assistant's collection."""
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

    try:
        # 1. Parse
        text = parse_document(content, file_type)
        doc.content_preview = text[:500]

        # 2. Chunk
        chunks = chunk_text(text)
        doc.chunk_count = len(chunks)

        if not chunks:
            doc.status = "error"
            doc.error_message = "No text content extracted"
            await db.commit()
            return doc

        # 3. Embed (in batches)
        all_embeddings = []
        for i in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[i : i + EMBED_BATCH_SIZE]
            batch_embeddings = await get_embeddings(batch)
            all_embeddings.extend(batch_embeddings)

        # 4. Store in assistant's Qdrant collection
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
    """Remove a document and its chunks from both DB and vector store."""
    doc = await db.get(Document, document_id)
    if not doc:
        return None

    await delete_document_chunks(collection_name, str(document_id))
    await db.delete(doc)
    await db.commit()
    return doc
