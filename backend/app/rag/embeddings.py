"""Embedding service using LiteLLM proxy."""

import httpx

from app.core.config import settings


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a list of texts via LiteLLM proxy."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.litellm_proxy_url}/embeddings",
            json={
                "model": settings.embedding_model,
                "input": texts,
            },
            headers={
                "Authorization": f"Bearer {settings.litellm_master_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]


async def get_single_embedding(text: str) -> list[float]:
    """Get embedding for a single text."""
    embeddings = await get_embeddings([text])
    return embeddings[0]
