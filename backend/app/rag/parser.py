"""Document parser: extracts text from PDF, DOCX, Markdown, TXT, and images.

OCR is delegated to the ocr module which supports cloud providers
(AWS Textract, Azure Document Intelligence, Google Document AI) with
automatic fallback to local Tesseract.
"""

import asyncio
import io
import logging
import re

import markdown
import pypdf
from docx import Document as DocxDocument
from PIL import Image

from app.rag.ocr import ocr_extract, ocr_image

logger = logging.getLogger(__name__)

# Minimum text length to consider a PDF page as "text-based" (not scanned)
MIN_TEXT_LENGTH = 50


async def parse_pdf(content: bytes) -> str:
    """Parse PDF: tries text extraction first, falls back to OCR for scanned pages.

    If there are scanned pages, uses the configured OCR provider (cloud or local).
    """
    reader = pypdf.PdfReader(io.BytesIO(content))
    text_parts: list[str] = []
    scanned_pages: list[int] = []

    # First pass: try text extraction
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if len(text.strip()) >= MIN_TEXT_LENGTH:
            text_parts.append(text)
        else:
            scanned_pages.append(i)

    # All pages have text — no OCR needed
    if not scanned_pages:
        return "\n\n".join(text_parts)

    logger.info(f"Running OCR on {len(scanned_pages)} scanned pages")

    # Try cloud OCR on the entire PDF first (more efficient than page-by-page)
    try:
        ocr_text = await ocr_extract(content, "pdf")
        if ocr_text and ocr_text.strip():
            # If we got some native text pages too, merge them
            if text_parts:
                # Insert OCR text at the scanned page positions
                # For simplicity with cloud OCR, just append OCR result
                return "\n\n".join(text_parts) + "\n\n" + ocr_text
            return ocr_text
    except Exception as e:
        logger.warning(f"Full-PDF OCR failed ({e}), trying page-by-page")

    # Fallback: page-by-page OCR using PIL images
    from pdf2image import convert_from_bytes

    images = convert_from_bytes(content, dpi=300)
    for page_idx in scanned_pages:
        if page_idx < len(images):
            try:
                ocr_text = await ocr_image(images[page_idx])
                if ocr_text.strip():
                    text_parts.insert(page_idx, ocr_text)
            except Exception as e:
                logger.warning(f"OCR failed on page {page_idx}: {e}")

    return "\n\n".join(text_parts)


def parse_docx(content: bytes) -> str:
    doc = DocxDocument(io.BytesIO(content))
    return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())


def parse_markdown(content: bytes) -> str:
    html = markdown.markdown(content.decode("utf-8"))
    clean = re.sub(r"<[^>]+>", "", html)
    return clean


def parse_txt(content: bytes) -> str:
    return content.decode("utf-8")


async def parse_image(content: bytes) -> str:
    """Extract text from an image using the configured OCR provider."""
    text = await ocr_extract(content, "png")
    if not text.strip():
        raise ValueError("OCR could not extract any text from this image")
    return text


async def parse_tiff(content: bytes) -> str:
    """Extract text from multi-page TIFF.

    Tries cloud OCR on the full file first; falls back to page-by-page local OCR.
    """
    # Try cloud OCR on the entire TIFF
    try:
        text = await ocr_extract(content, "tiff")
        if text and text.strip():
            return text
    except Exception as e:
        logger.warning(f"Cloud OCR failed for TIFF ({e}), falling back to page-by-page")

    # Page-by-page fallback
    image = Image.open(io.BytesIO(content))
    text_parts = []
    try:
        page = 0
        while True:
            image.seek(page)
            frame = image.copy()
            if frame.mode not in ("L", "RGB"):
                frame = frame.convert("RGB")
            text = await ocr_image(frame)
            if text.strip():
                text_parts.append(text)
            page += 1
    except EOFError:
        pass
    if not text_parts:
        raise ValueError("OCR could not extract any text from this TIFF")
    return "\n\n".join(text_parts)


# Parsers that need async
_ASYNC_PARSERS = {
    "pdf": parse_pdf,
    "png": parse_image,
    "jpg": parse_image,
    "jpeg": parse_image,
    "webp": parse_image,
    "bmp": parse_image,
    "tiff": parse_tiff,
    "tif": parse_tiff,
}

# Parsers that are sync (no OCR needed)
_SYNC_PARSERS = {
    "docx": parse_docx,
    "md": parse_markdown,
    "txt": parse_txt,
}


async def parse_document(content: bytes, file_type: str) -> str:
    """Parse a document, using cloud or local OCR as needed.

    This is now async to support cloud OCR providers.
    """
    if file_type in _ASYNC_PARSERS:
        return await _ASYNC_PARSERS[file_type](content)
    if file_type in _SYNC_PARSERS:
        return _SYNC_PARSERS[file_type](content)
    raise ValueError(f"Unsupported file type: {file_type}")
