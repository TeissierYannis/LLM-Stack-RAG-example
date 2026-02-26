"""Reranking module: improves RAG precision with cross-encoder scoring.

After initial vector search retrieves candidate chunks, the reranker
re-scores them using a cross-encoder model for more accurate relevance
ranking. This significantly improves answer quality.

Supports:
- LiteLLM reranking (via Cohere, Bedrock, etc.)
- Disabled mode (passthrough, default)
"""

import logging

import httpx

from app.core.config import settings
from app.core.langfuse_client import create_span, end_span

logger = logging.getLogger(__name__)


async def rerank(
    query: str,
    documents: list[dict],
    top_n: int | None = None,
    trace=None,
) -> list[dict]:
    """Rerank retrieved documents using a cross-encoder model.

    If reranking is disabled or fails, returns the original documents unchanged.

    Args:
        query: The user's search query
        documents: List of retrieved chunk dicts (must have "text" key)
        top_n: Number of results to keep after reranking
        trace: Langfuse trace/span for observability

    Returns:
        Reranked (and possibly pruned) list of documents
    """
    if not settings.rerank_model or not documents:
        return documents

    top_n = top_n or len(documents)

    span = create_span(
        trace, name="rerank",
        input={"query": query, "candidates": len(documents), "top_n": top_n, "model": settings.rerank_model},
    )

    try:
        texts = [doc["text"] for doc in documents]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.litellm_proxy_url}/rerank",
                json={
                    "model": settings.rerank_model,
                    "query": query,
                    "documents": texts,
                    "top_n": top_n,
                },
                headers={
                    "Authorization": f"Bearer {settings.litellm_master_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

        # Reorder documents based on reranker scores
        reranked = []
        for result in data.get("results", []):
            idx = result["index"]
            doc = documents[idx].copy()
            doc["rerank_score"] = result["relevance_score"]
            reranked.append(doc)

        logger.info(
            f"Reranked {len(documents)} → {len(reranked)} chunks "
            f"(scores: {[round(d['rerank_score'], 3) for d in reranked[:3]]})"
        )
        end_span(span, output={
            "reranked_count": len(reranked),
            "top_scores": [round(d["rerank_score"], 3) for d in reranked[:3]],
        })
        return reranked

    except Exception as e:
        logger.warning(f"Reranking failed ({e}), using original ranking")
        end_span(span, status_message=str(e), level="WARNING")
        return documents
