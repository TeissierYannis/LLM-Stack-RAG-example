"""Embedding service using LiteLLM proxy."""

import httpx

from app.core.config import settings
from app.core.langfuse_client import create_generation, end_generation


async def get_embeddings(texts: list[str], trace=None) -> list[list[float]]:
    """Get embeddings for a list of texts via LiteLLM proxy."""
    generation = create_generation(
        trace, name="embedding", model=settings.embedding_model,
        input={"text_count": len(texts), "total_chars": sum(len(t) for t in texts)},
    )

    try:
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
            usage = data.get("usage")
            embeddings = [item["embedding"] for item in data["data"]]

            end_generation(generation, output={"dimensions": len(embeddings[0]) if embeddings else 0}, usage=usage)
            return embeddings
    except Exception as e:
        end_generation(generation, status_message=str(e), level="ERROR")
        raise


async def get_single_embedding(text: str, trace=None) -> list[float]:
    """Get embedding for a single text."""
    embeddings = await get_embeddings([text], trace=trace)
    return embeddings[0]
