"""Document parser: extracts text from PDF, DOCX, Markdown, TXT, and images (OCR)."""

import io
import logging
import re

import markdown
import pypdf
from docx import Document as DocxDocument
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

# Minimum text length to consider a PDF page as "text-based" (not scanned)
MIN_TEXT_LENGTH = 50


def _ocr_image(image: Image.Image) -> str:
    """Run Tesseract OCR on a PIL Image."""
    return pytesseract.image_to_string(image, lang="fra+eng")


def parse_pdf(content: bytes) -> str:
    """Parse PDF: tries text extraction first, falls back to OCR for scanned pages."""
    reader = pypdf.PdfReader(io.BytesIO(content))
    text_parts = []
    scanned_pages = []

    # First pass: try text extraction
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if len(text.strip()) >= MIN_TEXT_LENGTH:
            text_parts.append(text)
        else:
            scanned_pages.append(i)

    # Second pass: OCR on pages that had no/little text
    if scanned_pages:
        logger.info(f"Running OCR on {len(scanned_pages)} scanned pages")
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(content, dpi=300)
        for page_idx in scanned_pages:
            if page_idx < len(images):
                ocr_text = _ocr_image(images[page_idx])
                if ocr_text.strip():
                    text_parts.insert(page_idx, ocr_text)

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


def parse_image(content: bytes) -> str:
    """Extract text from an image using Tesseract OCR."""
    image = Image.open(io.BytesIO(content))
    # Convert to RGB if needed (e.g. RGBA PNGs, palette images)
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    text = _ocr_image(image)
    if not text.strip():
        raise ValueError("OCR could not extract any text from this image")
    return text


def parse_tiff(content: bytes) -> str:
    """Extract text from multi-page TIFF using OCR."""
    image = Image.open(io.BytesIO(content))
    text_parts = []
    try:
        page = 0
        while True:
            image.seek(page)
            frame = image.copy()
            if frame.mode not in ("L", "RGB"):
                frame = frame.convert("RGB")
            text = _ocr_image(frame)
            if text.strip():
                text_parts.append(text)
            page += 1
    except EOFError:
        pass
    if not text_parts:
        raise ValueError("OCR could not extract any text from this TIFF")
    return "\n\n".join(text_parts)


PARSERS = {
    "pdf": parse_pdf,
    "docx": parse_docx,
    "md": parse_markdown,
    "txt": parse_txt,
    # OCR image formats
    "png": parse_image,
    "jpg": parse_image,
    "jpeg": parse_image,
    "webp": parse_image,
    "bmp": parse_image,
    "tiff": parse_tiff,
    "tif": parse_tiff,
}


def parse_document(content: bytes, file_type: str) -> str:
    parser = PARSERS.get(file_type)
    if not parser:
        raise ValueError(f"Unsupported file type: {file_type}")
    return parser(content)
