"""Qdrant vector store for document chunks."""

import uuid
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


async def ensure_collection(vector_size: int = 1024):
    """Create collection if it doesn't exist."""
    client = get_qdrant_client()
    collections = client.get_collections().collections
    existing = [c.name for c in collections]

    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {settings.qdrant_collection}")


async def store_chunks(
    document_id: str,
    filename: str,
    chunks: list[str],
    embeddings: list[list[float]],
):
    """Store document chunks with their embeddings in Qdrant."""
    client = get_qdrant_client()

    # Ensure collection exists with correct vector size
    await ensure_collection(vector_size=len(embeddings[0]))

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "document_id": document_id,
                "filename": filename,
                "chunk_index": i,
                "text": chunk,
            },
        )
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    logger.info(f"Stored {len(points)} chunks for document {document_id}")


async def search_similar(query_embedding: list[float], top_k: int | None = None) -> list[dict]:
    """Search for similar chunks using query embedding."""
    client = get_qdrant_client()
    k = top_k or settings.top_k_results

    try:
        results = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_embedding,
            limit=k,
            with_payload=True,
        )

        return [
            {
                "text": point.payload["text"],
                "filename": point.payload["filename"],
                "document_id": point.payload["document_id"],
                "chunk_index": point.payload["chunk_index"],
                "score": point.score,
            }
            for point in results.points
        ]
    except Exception:
        logger.exception("Error searching Qdrant")
        return []


async def delete_document_chunks(document_id: str):
    """Delete all chunks for a given document."""
    client = get_qdrant_client()
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
    )
