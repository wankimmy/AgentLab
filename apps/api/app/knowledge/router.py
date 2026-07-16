import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.config import settings
from app.core.db import get_db
from app.knowledge.pipeline import process_document_sync
from app.models.entities import (
    Document,
    DocumentChunk,
    DocumentStatus,
    KnowledgeCollection,
    ReadinessStatus,
)
from app.schemas.knowledge import (
    ChunkResponse,
    CollectionCreate,
    CollectionResponse,
    CollectionUpdate,
    DocumentDetail,
    DocumentResponse,
    ReadyCheckResponse,
    ReindexResponse,
)
from app.workers.celery_app import process_document_task, reindex_document_task

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

CHECKLIST_KEYS = [
    "authoritative_source",
    "source_owner",
    "effective_date",
    "review_schedule",
    "sensitive_data_removed",
]


def _collection_response(db: Session, collection: KnowledgeCollection) -> CollectionResponse:
    doc_count = db.query(Document).filter(Document.collection_id == collection.id).count()
    ready_count = (
        db.query(Document)
        .filter(
            Document.collection_id == collection.id,
            Document.status == DocumentStatus.ready,
        )
        .count()
    )
    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        purpose=collection.purpose,
        readiness_status=collection.readiness_status,
        planning_metadata=collection.planning_metadata or {},
        document_count=doc_count,
        ready_document_count=ready_count,
    )


def _get_user_collection(
    collection_id: uuid.UUID, user: CurrentUser, db: Session
) -> KnowledgeCollection:
    collection = (
        db.query(KnowledgeCollection)
        .filter(KnowledgeCollection.id == collection_id, KnowledgeCollection.user_id == user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w.\-]+", "_", Path(name).name)
    return cleaned or "upload.bin"


@router.get("/collections", response_model=list[CollectionResponse])
def list_collections(user: CurrentUser, db: Session = Depends(get_db)) -> list[CollectionResponse]:
    collections = (
        db.query(KnowledgeCollection)
        .filter(KnowledgeCollection.user_id == user.id)
        .order_by(KnowledgeCollection.created_at.desc())
        .all()
    )
    return [_collection_response(db, c) for c in collections]


@router.post("/collections", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    body: CollectionCreate, user: CurrentUser, db: Session = Depends(get_db)
) -> CollectionResponse:
    collection = KnowledgeCollection(
        user_id=user.id,
        name=body.name,
        description=body.description,
        purpose=body.purpose,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return _collection_response(db, collection)


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> CollectionResponse:
    collection = _get_user_collection(collection_id, user, db)
    return _collection_response(db, collection)


@router.patch("/collections/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: uuid.UUID,
    body: CollectionUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> CollectionResponse:
    collection = _get_user_collection(collection_id, user, db)
    if body.name is not None:
        collection.name = body.name
    if body.description is not None:
        collection.description = body.description
    if body.purpose is not None:
        collection.purpose = body.purpose
    if body.planning_metadata is not None:
        collection.planning_metadata = body.planning_metadata
    db.commit()
    db.refresh(collection)
    return _collection_response(db, collection)


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> None:
    collection = _get_user_collection(collection_id, user, db)
    db.delete(collection)
    db.commit()


@router.post("/collections/{collection_id}/ready-check", response_model=ReadyCheckResponse)
def ready_check(
    collection_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> ReadyCheckResponse:
    collection = _get_user_collection(collection_id, user, db)
    meta = collection.planning_metadata or {}
    checklist = {key: bool(meta.get(key)) for key in CHECKLIST_KEYS}
    ready_docs = (
        db.query(Document)
        .filter(
            Document.collection_id == collection.id,
            Document.status == DocumentStatus.ready,
        )
        .count()
    )
    messages: list[str] = []
    if ready_docs < 1:
        messages.append("At least one ready document is required.")
    for key, ok in checklist.items():
        if not ok:
            messages.append(f"Missing checklist field: {key}")
    ready = ready_docs >= 1 and all(checklist.values())
    if ready:
        collection.readiness_status = ReadinessStatus.ready
    elif ready_docs >= 1:
        collection.readiness_status = ReadinessStatus.ready_for_testing
    else:
        collection.readiness_status = ReadinessStatus.needs_preparation
    db.commit()
    return ReadyCheckResponse(
        ready=ready,
        readiness_status=collection.readiness_status,
        checklist=checklist,
        messages=messages,
    )


@router.post(
    "/collections/{collection_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    collection_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> DocumentResponse:
    from app.knowledge.processing import validate_upload

    collection = _get_user_collection(collection_id, user, db)
    filename = _safe_filename(file.filename or "upload.txt")
    data = await file.read()
    try:
        validate_upload(filename, len(data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document = Document(
        collection_id=collection.id,
        filename=filename,
        content_type=file.content_type or "",
        storage_path="",
        status=DocumentStatus.uploaded,
    )
    db.add(document)
    db.flush()

    upload_dir = Path(settings.uploads_dir) / str(collection.id) / str(document.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    dest.write_bytes(data)
    document.storage_path = str(dest)
    db.commit()
    db.refresh(document)

    if settings.app_env == "test":
        process_document_sync(document.id)
        db.refresh(document)
    else:
        process_document_task.delay(str(document.id))

    return DocumentResponse.model_validate(document)


@router.get("/collections/{collection_id}/documents", response_model=list[DocumentResponse])
def list_documents(
    collection_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> list[DocumentResponse]:
    _get_user_collection(collection_id, user, db)
    docs = (
        db.query(Document)
        .filter(Document.collection_id == collection_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> DocumentDetail:
    document = _get_user_document(document_id, user, db)
    return DocumentDetail.model_validate(document)


@router.get("/documents/{document_id}/text")
def get_document_text(
    document_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> dict[str, str]:
    document = _get_user_document(document_id, user, db)
    return {"text": document.extracted_text}


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkResponse])
def list_chunks(
    document_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> list[ChunkResponse]:
    document = _get_user_document(document_id, user, db)
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.sort_order)
        .all()
    )
    return [
        ChunkResponse(
            id=c.id,
            content=c.content,
            token_count=c.token_count,
            page_number=c.page_number,
            heading=c.heading,
            sort_order=c.sort_order,
            metadata=c.chunk_metadata or {},
        )
        for c in chunks
    ]


@router.post("/documents/{document_id}/reprocess", response_model=DocumentResponse)
def reprocess_document(
    document_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> DocumentResponse:
    document = _get_user_document(document_id, user, db)
    if settings.app_env == "test":
        process_document_sync(document.id)
    else:
        process_document_task.delay(str(document.id))
    db.refresh(document)
    return DocumentResponse.model_validate(document)


@router.post("/documents/{document_id}/reindex", response_model=ReindexResponse)
def reindex_document(
    document_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> ReindexResponse:
    from app.models.entities import BackgroundJob, JobStatus

    document = _get_user_document(document_id, user, db)
    estimated = document.chunk_count * 200
    job = BackgroundJob(
        job_type="reindex_document",
        status=JobStatus.pending,
        document_id=document.id,
        payload={"estimated_tokens": estimated},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    if settings.app_env == "test":
        process_document_sync(document.id)
        job.status = JobStatus.completed
        db.commit()
    else:
        reindex_document_task.delay(str(document.id))
    return ReindexResponse(
        job_id=job.id,
        message="Reindex queued. Embedding API usage may incur cost.",
        estimated_tokens=estimated,
    )


@router.post("/documents/{document_id}/archive", response_model=DocumentResponse)
def archive_document(
    document_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> DocumentResponse:
    document = _get_user_document(document_id, user, db)
    document.status = DocumentStatus.archived
    db.commit()
    db.refresh(document)
    return DocumentResponse.model_validate(document)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> None:
    document = _get_user_document(document_id, user, db)
    db.delete(document)
    db.commit()


def _get_user_document(document_id: uuid.UUID, user: CurrentUser, db: Session) -> Document:
    document = (
        db.query(Document)
        .join(KnowledgeCollection, KnowledgeCollection.id == Document.collection_id)
        .filter(Document.id == document_id, KnowledgeCollection.user_id == user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
