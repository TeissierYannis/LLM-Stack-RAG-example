"""Langfuse LLM observability integration.

Provides trace/span/generation helpers for the entire RAG pipeline.
All functions are no-ops when Langfuse is disabled (LANGFUSE_ENABLED=false).

Usage:
    trace = create_trace(name="chat", user_id="user-1", metadata={...})
    with span(trace, name="rag-retrieval") as s:
        # ... do retrieval ...
        s.update(output={"chunks": 5})
    generation = create_generation(trace, name="llm-call", model="claude-sonnet", input=messages)
    generation.end(output=response_text, usage={...})
"""

import logging
from contextlib import contextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

_langfuse = None
_initialized = False


def get_langfuse():
    """Get or initialize the Langfuse client (singleton). Returns None if disabled."""
    global _langfuse, _initialized

    if _initialized:
        return _langfuse

    _initialized = True

    if not settings.langfuse_enabled:
        logger.info("Langfuse disabled (LANGFUSE_ENABLED=false)")
        return None

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("Langfuse enabled but missing keys — disabling")
        return None

    try:
        from langfuse import Langfuse

        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            release=settings.environment,
        )
        logger.info(f"Langfuse initialized → {settings.langfuse_host}")
        return _langfuse
    except Exception as e:
        logger.warning(f"Failed to initialize Langfuse: {e}")
        return None


def create_trace(*, name: str, user_id: str | None = None, session_id: str | None = None,
                 metadata: dict | None = None, tags: list[str] | None = None):
    """Create a top-level Langfuse trace. Returns None if disabled."""
    client = get_langfuse()
    if not client:
        return None
    try:
        return client.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or [],
        )
    except Exception as e:
        logger.warning(f"Langfuse create_trace failed: {e}")
        return None


def create_span(trace, *, name: str, input: dict | None = None, metadata: dict | None = None):
    """Create a span (sub-operation) within a trace. Returns None if trace is None."""
    if trace is None:
        return None
    try:
        return trace.span(name=name, input=input, metadata=metadata or {})
    except Exception as e:
        logger.warning(f"Langfuse create_span failed: {e}")
        return None


def end_span(span_obj, *, output=None, status_message: str | None = None, level: str | None = None):
    """End a span with output data."""
    if span_obj is None:
        return
    try:
        kwargs = {}
        if output is not None:
            kwargs["output"] = output
        if status_message:
            kwargs["status_message"] = status_message
        if level:
            kwargs["level"] = level
        span_obj.end(**kwargs)
    except Exception as e:
        logger.warning(f"Langfuse end_span failed: {e}")


@contextmanager
def span_context(trace, *, name: str, input: dict | None = None, metadata: dict | None = None):
    """Context manager for spans — automatically ends the span on exit."""
    s = create_span(trace, name=name, input=input, metadata=metadata)
    try:
        yield s
    except Exception as exc:
        end_span(s, status_message=str(exc), level="ERROR")
        raise
    else:
        end_span(s)


def create_generation(trace_or_span, *, name: str, model: str, input: list | dict | str | None = None,
                      model_parameters: dict | None = None, metadata: dict | None = None):
    """Create a generation (LLM call) observation. Returns None if parent is None."""
    if trace_or_span is None:
        return None
    try:
        return trace_or_span.generation(
            name=name,
            model=model,
            input=input,
            model_parameters=model_parameters or {},
            metadata=metadata or {},
        )
    except Exception as e:
        logger.warning(f"Langfuse create_generation failed: {e}")
        return None


def end_generation(generation, *, output=None, usage: dict | None = None,
                   status_message: str | None = None, level: str | None = None):
    """End a generation with output and usage info."""
    if generation is None:
        return
    try:
        kwargs = {}
        if output is not None:
            kwargs["output"] = output
        if usage:
            kwargs["usage"] = usage
        if status_message:
            kwargs["status_message"] = status_message
        if level:
            kwargs["level"] = level
        generation.end(**kwargs)
    except Exception as e:
        logger.warning(f"Langfuse end_generation failed: {e}")


def score_trace(trace, *, name: str, value: float, comment: str | None = None):
    """Add a score to a trace (e.g., user feedback, quality metric)."""
    if trace is None:
        return
    try:
        trace.score(name=name, value=value, comment=comment)
    except Exception as e:
        logger.warning(f"Langfuse score_trace failed: {e}")


def flush():
    """Flush pending Langfuse events. Call on shutdown."""
    client = get_langfuse()
    if client:
        try:
            client.flush()
        except Exception as e:
            logger.warning(f"Langfuse flush failed: {e}")
