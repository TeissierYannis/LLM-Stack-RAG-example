"""OpenTelemetry instrumentation for tracing and metrics.

Supports exporting to:
- OTLP endpoint (Jaeger, Grafana Tempo, Datadog, New Relic, etc.)
- Console (development)
- Disabled (default)

Traces cover:
- HTTP requests (FastAPI)
- Database queries (SQLAlchemy)
- External HTTP calls (httpx)
- Custom RAG pipeline spans
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_tracer = None


def setup_telemetry(app=None):
    """Initialize OpenTelemetry if configured.

    Call this at application startup. Requires OTEL_EXPORTER_ENDPOINT to be set.
    """
    if not settings.otel_exporter_endpoint:
        logger.info("OpenTelemetry disabled (OTEL_EXPORTER_ENDPOINT not set)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        resource = Resource.create({
            "service.name": settings.otel_service_name,
            "service.version": "1.0.0",
            "deployment.environment": settings.environment,
        })

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        global _tracer
        _tracer = trace.get_tracer("enterprise-chat-rag")

        # Auto-instrument libraries
        if app:
            FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()

        logger.info(f"OpenTelemetry enabled → {settings.otel_exporter_endpoint}")

    except ImportError:
        logger.warning("OpenTelemetry packages not installed, tracing disabled")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")


def get_tracer():
    """Get the global tracer (or a no-op if telemetry is disabled)."""
    global _tracer
    if _tracer is None:
        from opentelemetry import trace
        _tracer = trace.get_tracer("enterprise-chat-rag")
    return _tracer
