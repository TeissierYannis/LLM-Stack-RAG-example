"""RAG retriever: combines embedding search with context building."""

from app.rag.embeddings import get_single_embedding
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
) -> tuple[str, list[dict]]:
    """Retrieve relevant context for a query from a specific assistant's collection.

    Returns:
        Tuple of (formatted context string, list of source documents)
    """
    query_embedding = await get_single_embedding(query)
    results = await search_similar(collection_name, query_embedding, top_k=top_k)

    if not results:
        return "", []

    context_parts = []
    for r in results:
        context_parts.append(f"[Source: {r['filename']}]\n{r['text']}")

    context = "\n\n".join(context_parts)
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
