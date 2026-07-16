import uuid
from pathlib import Path

from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.knowledge.processing import chunk_text, extract_text
from app.models.entities import (
    BackgroundJob,
    Document,
    DocumentChunk,
    DocumentStatus,
    JobStatus,
)
from app.providers.embeddings import get_embedding_provider


def process_document_sync(document_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        _process_document(db, document_id)
        db.commit()


def _process_document(db: Session, document_id: uuid.UUID) -> None:
    document = db.get(Document, document_id)
    if not document:
        return
    document.status = DocumentStatus.processing
    db.flush()

    job = BackgroundJob(
        job_type="process_document",
        status=JobStatus.running,
        document_id=document.id,
    )
    db.add(job)
    db.flush()

    try:
        path = Path(document.storage_path)
        data = path.read_bytes()
        extracted = extract_text(document.filename, data)
        document.extracted_text = extracted
        chunks = chunk_text(extracted)
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

        provider = get_embedding_provider()
        model_name = settings.embedding_model if settings.embedding_api_key else "mock-embed"
        document.embedding_model = model_name

        texts = [c.content for c in chunks]
        vectors = provider.embed(texts) if texts else []

        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False)):
            chunk_row = DocumentChunk(
                document_id=document.id,
                content=chunk.content,
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                heading=chunk.heading,
                chunk_metadata={},
                sort_order=idx,
            )
            db.add(chunk_row)
            db.flush()
            vec_literal = "[" + ",".join(str(v) for v in vector) + "]"
            db.execute(
                text("UPDATE document_chunks SET embedding = :vec::vector WHERE id = :id"),
                {"vec": vec_literal, "id": str(chunk_row.id)},
            )

        document.chunk_count = len(chunks)
        document.status = DocumentStatus.ready
        document.error_info = None
        job.status = JobStatus.completed
    except Exception as exc:
        document.status = DocumentStatus.failed
        document.error_info = {"message": str(exc)}
        job.status = JobStatus.failed
        job.error = str(exc)
