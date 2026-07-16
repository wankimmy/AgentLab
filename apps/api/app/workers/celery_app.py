from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "agentlab",
    broker=settings.broker_url,
    backend=settings.result_backend,
)
celery_app.conf.task_always_eager = settings.app_env == "test"
celery_app.conf.task_eager_propagates = True
celery_app.autodiscover_tasks(["app.workers"])


@celery_app.task(name="process_document")
def process_document_task(document_id: str) -> None:
    import uuid

    from app.knowledge.pipeline import process_document_sync

    process_document_sync(uuid.UUID(document_id))


@celery_app.task(name="reindex_document")
def reindex_document_task(document_id: str) -> None:
    process_document_task(document_id)
