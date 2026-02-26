"""Document parser: extracts text from PDF, DOCX, Markdown, and TXT files."""

import io

import markdown
import pypdf
from docx import Document as DocxDocument


def parse_pdf(content: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(content))
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n\n".join(text_parts)


def parse_docx(content: bytes) -> str:
    doc = DocxDocument(io.BytesIO(content))
    return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())


def parse_markdown(content: bytes) -> str:
    html = markdown.markdown(content.decode("utf-8"))
    # Strip HTML tags for plain text
    import re

    clean = re.sub(r"<[^>]+>", "", html)
    return clean


def parse_txt(content: bytes) -> str:
    return content.decode("utf-8")


PARSERS = {
    "pdf": parse_pdf,
    "docx": parse_docx,
    "md": parse_markdown,
    "txt": parse_txt,
}


def parse_document(content: bytes, file_type: str) -> str:
    parser = PARSERS.get(file_type)
    if not parser:
        raise ValueError(f"Unsupported file type: {file_type}")
    return parser(content)
