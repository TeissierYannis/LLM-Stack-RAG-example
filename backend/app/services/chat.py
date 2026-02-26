"""Chat service: handles LLM completion via LiteLLM proxy."""

import json
import logging
from collections.abc import AsyncGenerator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def stream_completion(
    messages: list[dict],
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream completion from LiteLLM proxy using SSE."""
    target_model = model or settings.completion_model

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{settings.litellm_proxy_url}/chat/completions",
            json={
                "model": target_model,
                "messages": messages,
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            headers={
                "Authorization": f"Bearer {settings.litellm_master_key}",
                "Content-Type": "application/json",
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue


async def get_completion(
    messages: list[dict],
    model: str | None = None,
) -> str:
    """Get a non-streaming completion from LiteLLM proxy."""
    target_model = model or settings.completion_model

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.litellm_proxy_url}/chat/completions",
            json={
                "model": target_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            headers={
                "Authorization": f"Bearer {settings.litellm_master_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
