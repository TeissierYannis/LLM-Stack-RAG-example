"""Models listing API - shows available LLM models and OCR config."""

from fastapi import APIRouter

from app.api.schemas import ModelInfo, ModelsResponse, OCRInfoResponse
from app.core.config import settings

router = APIRouter(prefix="/models", tags=["models"])

AVAILABLE_MODELS = ModelsResponse(
    completion_models=[
        ModelInfo(name="claude-sonnet", provider="AWS Bedrock", model_type="completion"),
        ModelInfo(name="gpt-4o", provider="Azure AI Foundry", model_type="completion"),
        ModelInfo(name="gemini-flash", provider="Google Vertex AI", model_type="completion"),
        ModelInfo(name="default-completion", provider="Auto (load-balanced)", model_type="completion"),
    ],
    embedding_models=[
        ModelInfo(name="embed-titan", provider="AWS Bedrock", model_type="embedding"),
        ModelInfo(name="embed-azure", provider="Azure AI Foundry", model_type="embedding"),
        ModelInfo(name="embed-vertex", provider="Google Vertex AI", model_type="embedding"),
        ModelInfo(name="default-embedding", provider="Auto (load-balanced)", model_type="embedding"),
    ],
)

_OCR_PROVIDER_LABELS = {
    "local": "Tesseract (local)",
    "aws_textract": "AWS Textract",
    "azure_di": "Azure Document Intelligence",
    "google_docai": "Google Document AI",
    "auto": "Auto (cloud → local fallback)",
}


@router.get("", response_model=ModelsResponse)
async def list_models():
    """List all available models."""
    return AVAILABLE_MODELS


@router.get("/ocr", response_model=OCRInfoResponse)
async def get_ocr_info():
    """Return current OCR provider configuration."""
    provider = settings.ocr_provider
    return OCRInfoResponse(
        provider=provider,
        provider_label=_OCR_PROVIDER_LABELS.get(provider, provider),
        cloud_enabled=provider != "local",
    )
