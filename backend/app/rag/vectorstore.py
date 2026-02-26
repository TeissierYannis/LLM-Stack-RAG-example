"""Qdrant vector store for document chunks. Each assistant has its own collection."""

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


async def ensure_collection(collection_name: str, vector_size: int = 1024):
    """Create collection if it doesn't exist."""
    client = get_qdrant_client()
    collections = client.get_collections().collections
    existing = [c.name for c in collections]

    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {collection_name}")


async def delete_collection(collection_name: str):
    """Delete an entire collection (used when deleting an assistant)."""
    client = get_qdrant_client()
    try:
        client.delete_collection(collection_name=collection_name)
        logger.info(f"Deleted Qdrant collection: {collection_name}")
    except Exception:
        logger.warning(f"Collection {collection_name} not found for deletion")


async def store_chunks(
    collection_name: str,
    document_id: str,
    filename: str,
    chunks: list[str],
    embeddings: list[list[float]],
):
    """Store document chunks with their embeddings in a specific collection."""
    client = get_qdrant_client()

    await ensure_collection(collection_name, vector_size=len(embeddings[0]))

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

    client.upsert(collection_name=collection_name, points=points)
    logger.info(f"Stored {len(points)} chunks for document {document_id} in {collection_name}")


async def search_similar(
    collection_name: str,
    query_embedding: list[float],
    top_k: int | None = None,
) -> list[dict]:
    """Search for similar chunks in a specific collection."""
    client = get_qdrant_client()
    k = top_k or settings.top_k_results

    try:
        results = client.query_points(
            collection_name=collection_name,
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
        logger.exception(f"Error searching Qdrant collection {collection_name}")
        return []


async def delete_document_chunks(collection_name: str, document_id: str):
    """Delete all chunks for a given document in a specific collection."""
    client = get_qdrant_client()
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
    )
