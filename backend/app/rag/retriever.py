"""RAG retriever: embedding search → reranking → context building."""

from app.core.langfuse_client import create_span, end_span
from app.rag.embeddings import get_single_embedding
from app.rag.reranker import rerank
from app.rag.vectorstore import search_similar

DEFAULT_SYSTEM_PROMPT = """Tu es un assistant d'entreprise intelligent. Tu réponds aux questions en te basant sur les documents fournis dans le contexte.

Règles:
- Réponds de manière précise et concise en te basant sur le contexte fourni
- Si le contexte ne contient pas l'information, dis-le clairement
- Cite les sources (nom de fichier) quand tu utilises une information du contexte
- Réponds dans la langue de la question"""

RAG_PROMPT_TEMPLATE = """Contexte (documents pertinents):
---
{context}
---

Question: {question}"""


async def retrieve_context(
    collection_name: str,
    query: str,
    top_k: int | None = None,
    trace=None,
) -> tuple[str, list[dict]]:
    """Retrieve relevant context: vector search → rerank → format.

    Pipeline:
    1. Embed query → vector similarity search (retrieves 2x top_k candidates)
    2. Rerank candidates with cross-encoder (if configured)
    3. Take top_k results and format as context string

    Returns:
        Tuple of (formatted context string, list of source documents)
    """
    k = top_k or 5
    # Retrieve more candidates for reranking to improve recall
    search_k = k * 2

    span = create_span(
        trace, name="rag-retrieval",
        input={"query": query, "collection": collection_name, "top_k": k, "search_k": search_k},
    )

    query_embedding = await get_single_embedding(query, trace=span)
    results = await search_similar(collection_name, query_embedding, top_k=search_k)

    if not results:
        end_span(span, output={"chunks_found": 0})
        return "", []

    # Rerank (no-op if rerank_model is not configured)
    results = await rerank(query, results, top_n=k, trace=span)

    # Trim to final top_k
    results = results[:k]

    context_parts = []
    for r in results:
        context_parts.append(f"[Source: {r['filename']}]\n{r['text']}")

    context = "\n\n".join(context_parts)

    end_span(span, output={
        "chunks_found": len(results),
        "sources": [r["filename"] for r in results],
        "context_length": len(context),
    })
    return context, results


def build_rag_messages(
    query: str,
    context: str,
    system_prompt: str | None = None,
    conversation_history: list[dict] | None = None,
) -> list[dict]:
    """Build the message list for the LLM call with RAG context."""
    prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
    messages = [{"role": "system", "content": prompt}]

    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)

    # Add the current query with context
    if context:
        user_content = RAG_PROMPT_TEMPLATE.format(context=context, question=query)
    else:
        user_content = query

    messages.append({"role": "user", "content": user_content})
    return messages
