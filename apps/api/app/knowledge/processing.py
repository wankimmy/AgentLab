import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

ALLOWED_EXTENSIONS = {".md", ".txt", ".csv", ".pdf"}
MAX_FILE_BYTES = 10 * 1024 * 1024
CHUNK_SIZE = 3200
CHUNK_OVERLAP = 400


@dataclass
class TextChunk:
    content: str
    heading: str | None
    page_number: int | None
    token_count: int


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def validate_upload(filename: str, size: int) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    if size > MAX_FILE_BYTES:
        raise ValueError("File exceeds 10MB limit")


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in {".md", ".txt"}:
        return data.decode("utf-8", errors="replace")
    if ext == ".csv":
        return _extract_faq_csv(data)
    if ext == ".pdf":
        return _extract_pdf(data)
    raise ValueError(f"Unsupported extension: {ext}")


def _extract_faq_csv(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    blocks: list[str] = []
    for row in reader:
        question = row.get("question") or row.get("Question") or row.get("q") or ""
        answer = row.get("answer") or row.get("Answer") or row.get("a") or ""
        if question or answer:
            blocks.append(f"Q: {question}\nA: {answer}")
    if not blocks:
        return text
    return "\n\n".join(blocks)


def _extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    combined = "\n\n".join(pages).strip()
    if not combined:
        raise ValueError("PDF contains no extractable text")
    return combined


def chunk_text(text: str) -> list[TextChunk]:
    sections = re.split(r"(?=^#{1,3}\s)", text, flags=re.MULTILINE)
    chunks: list[TextChunk] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        heading = None
        if section.startswith("#"):
            lines = section.split("\n", 1)
            heading = lines[0].lstrip("#").strip()
            body = lines[1] if len(lines) > 1 else ""
        else:
            body = section
        body = body.strip()
        if not body:
            continue
        start = 0
        while start < len(body):
            end = min(len(body), start + CHUNK_SIZE)
            piece = body[start:end].strip()
            if piece:
                chunks.append(
                    TextChunk(
                        content=piece,
                        heading=heading,
                        page_number=None,
                        token_count=estimate_tokens(piece),
                    )
                )
            if end >= len(body):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
    if not chunks and text.strip():
        chunks.append(
            TextChunk(
                content=text.strip(),
                heading=None,
                page_number=None,
                token_count=estimate_tokens(text),
            )
        )
    return chunks
