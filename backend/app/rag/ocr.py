"""Cloud OCR providers with local Tesseract fallback.

Supports:
- AWS Textract (via boto3)
- Azure Document Intelligence (via azure-ai-documentintelligence)
- Google Document AI (via google-cloud-documentai)
- Local Tesseract (fallback, always available)

Provider is selected via OCR_PROVIDER env var. If the cloud provider
fails, it falls back to Tesseract automatically.
"""

import io
import logging
from enum import Enum

from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


class OCRProvider(str, Enum):
    LOCAL = "local"
    AWS_TEXTRACT = "aws_textract"
    AZURE_DOCUMENT_INTELLIGENCE = "azure_di"
    GOOGLE_DOCUMENT_AI = "google_docai"
    AUTO = "auto"  # tries cloud providers in order, falls back to local


# ---------------------------------------------------------------------------
# Local Tesseract
# ---------------------------------------------------------------------------

def _ocr_tesseract(image: Image.Image) -> str:
    """Run Tesseract OCR on a PIL Image."""
    import pytesseract
    return pytesseract.image_to_string(image, lang="fra+eng")


def _ocr_tesseract_bytes(content: bytes, file_type: str) -> str:
    """Run Tesseract OCR on raw bytes (image or PDF pages)."""
    import pytesseract

    if file_type == "pdf":
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(content, dpi=300)
        parts = []
        for img in images:
            text = pytesseract.image_to_string(img, lang="fra+eng")
            if text.strip():
                parts.append(text)
        return "\n\n".join(parts)
    else:
        image = Image.open(io.BytesIO(content))
        if image.mode not in ("L", "RGB"):
            image = image.convert("RGB")
        return pytesseract.image_to_string(image, lang="fra+eng")


# ---------------------------------------------------------------------------
# AWS Textract
# ---------------------------------------------------------------------------

async def _ocr_aws_textract(content: bytes, file_type: str) -> str:
    """Extract text using AWS Textract.

    Uses DetectDocumentText for images, and AnalyzeDocument for PDFs.
    For large PDFs (>5MB or >1 page), uses async StartDocumentTextDetection.
    """
    import boto3

    client = boto3.client(
        "textract",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )

    if file_type == "pdf" and len(content) > 5 * 1024 * 1024:
        # Large PDFs: use async API via S3 (requires S3 bucket)
        logger.warning("PDF too large for sync Textract, falling back to local OCR")
        raise ValueError("PDF too large for synchronous Textract (>5MB)")

    response = client.detect_document_text(
        Document={"Bytes": content}
    )

    lines = []
    for block in response.get("Blocks", []):
        if block["BlockType"] == "LINE":
            lines.append(block["Text"])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Azure Document Intelligence
# ---------------------------------------------------------------------------

async def _ocr_azure_di(content: bytes, file_type: str) -> str:
    """Extract text using Azure AI Document Intelligence (formerly Form Recognizer)."""
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential

    client = DocumentIntelligenceClient(
        endpoint=settings.azure_di_endpoint,
        credential=AzureKeyCredential(settings.azure_di_key),
    )

    content_type_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
    }
    content_type = content_type_map.get(file_type, "application/octet-stream")

    poller = client.begin_analyze_document(
        "prebuilt-read",
        analyze_request=content,
        content_type=content_type,
    )
    result = poller.result()

    pages_text = []
    for page in result.pages:
        lines = []
        for line in page.lines:
            lines.append(line.content)
        pages_text.append("\n".join(lines))

    return "\n\n".join(pages_text)


# ---------------------------------------------------------------------------
# Google Document AI
# ---------------------------------------------------------------------------

async def _ocr_google_docai(content: bytes, file_type: str) -> str:
    """Extract text using Google Document AI."""
    from google.cloud import documentai_v1 as documentai

    client = documentai.DocumentProcessorServiceClient()

    mime_type_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
    }
    mime_type = mime_type_map.get(file_type, "application/octet-stream")

    # processor_name format: projects/{project}/locations/{location}/processors/{processor_id}
    processor_name = settings.google_docai_processor

    raw_document = documentai.RawDocument(content=content, mime_type=mime_type)
    request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)

    result = client.process_document(request=request)
    return result.document.text


# ---------------------------------------------------------------------------
# Main OCR entry point
# ---------------------------------------------------------------------------

# Cloud provider dispatch
_CLOUD_PROVIDERS = {
    OCRProvider.AWS_TEXTRACT: _ocr_aws_textract,
    OCRProvider.AZURE_DOCUMENT_INTELLIGENCE: _ocr_azure_di,
    OCRProvider.GOOGLE_DOCUMENT_AI: _ocr_google_docai,
}

# Auto mode: try providers in this order
_AUTO_ORDER = [
    OCRProvider.AWS_TEXTRACT,
    OCRProvider.AZURE_DOCUMENT_INTELLIGENCE,
    OCRProvider.GOOGLE_DOCUMENT_AI,
]


def _is_provider_configured(provider: OCRProvider) -> bool:
    """Check if the cloud provider has its required credentials configured."""
    if provider == OCRProvider.AWS_TEXTRACT:
        return bool(settings.aws_region)
    elif provider == OCRProvider.AZURE_DOCUMENT_INTELLIGENCE:
        return bool(settings.azure_di_endpoint and settings.azure_di_key)
    elif provider == OCRProvider.GOOGLE_DOCUMENT_AI:
        return bool(settings.google_docai_processor)
    return False


async def ocr_extract(content: bytes, file_type: str) -> str:
    """Extract text from a document/image using the configured OCR provider.

    Falls back to local Tesseract if cloud provider fails or is unavailable.

    Args:
        content: raw file bytes
        file_type: file extension (pdf, png, jpg, etc.)

    Returns:
        Extracted text
    """
    provider = OCRProvider(settings.ocr_provider)

    # Direct local mode
    if provider == OCRProvider.LOCAL:
        logger.info("OCR: using local Tesseract")
        return _ocr_tesseract_bytes(content, file_type)

    # Specific cloud provider
    if provider in _CLOUD_PROVIDERS:
        try:
            logger.info(f"OCR: using {provider.value}")
            text = await _CLOUD_PROVIDERS[provider](content, file_type)
            if text and text.strip():
                return text
            logger.warning(f"OCR: {provider.value} returned empty text, falling back to Tesseract")
        except Exception as e:
            logger.warning(f"OCR: {provider.value} failed ({e}), falling back to Tesseract")
        return _ocr_tesseract_bytes(content, file_type)

    # Auto mode: try each configured cloud provider, fall back to local
    if provider == OCRProvider.AUTO:
        for p in _AUTO_ORDER:
            if not _is_provider_configured(p):
                continue
            try:
                logger.info(f"OCR auto: trying {p.value}")
                text = await _CLOUD_PROVIDERS[p](content, file_type)
                if text and text.strip():
                    return text
            except Exception as e:
                logger.warning(f"OCR auto: {p.value} failed ({e})")
                continue

        logger.info("OCR auto: all cloud providers failed or unconfigured, using Tesseract")
        return _ocr_tesseract_bytes(content, file_type)

    # Unknown provider, default to local
    return _ocr_tesseract_bytes(content, file_type)


async def ocr_image(image: Image.Image) -> str:
    """OCR a single PIL Image.

    For cloud providers, converts the image to PNG bytes first.
    """
    provider = OCRProvider(settings.ocr_provider)

    if provider == OCRProvider.LOCAL:
        return _ocr_tesseract(image)

    # Convert PIL Image to bytes for cloud providers
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    return await ocr_extract(png_bytes, "png")
