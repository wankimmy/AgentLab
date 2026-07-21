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


@celery_app.task(name="run_evaluation")
def run_evaluation_task(run_id: str) -> None:
    import uuid

    from app.evaluations.runner import run_evaluation_sync

    run_evaluation_sync(uuid.UUID(run_id))


@celery_app.task(name="generate_eval_cases")
def generate_eval_cases_task(job_id: str) -> None:
    import uuid

    from app.core.db import SessionLocal
    from app.evaluations.case_generation import generate_draft_cases_sync
    from app.models.entities import BackgroundJob

    with SessionLocal() as db:
        job = db.get(BackgroundJob, uuid.UUID(job_id))
        if not job:
            return
        payload = job.payload or {}
        generate_draft_cases_sync(
            db,
            job_id=job.id,
            dataset_version_id=uuid.UUID(str(payload["dataset_version_id"])),
            agent_version_id=uuid.UUID(str(payload["agent_version_id"])),
        )
        db.commit()


@celery_app.task(name="analyse_prompt")
def analyse_prompt_task(job_id: str) -> None:
    import uuid

    from app.core.db import SessionLocal
    from app.models.entities import BackgroundJob, PromptRecommendationSource
    from app.prompts.analyser import analyse_prompt_sync

    with SessionLocal() as db:
        job = db.get(BackgroundJob, uuid.UUID(job_id))
        if not job:
            return
        payload = job.payload or {}
        analyse_prompt_sync(
            db,
            job_id=job.id,
            agent_version_id=uuid.UUID(str(payload["agent_version_id"])),
            user_id=uuid.UUID(str(payload["user_id"])),
            source=PromptRecommendationSource(payload.get("source", "analyse")),
        )
        db.commit()


@celery_app.task(name="run_red_team")
def run_red_team_task(job_id: str, run_id: str) -> None:
    import uuid

    from app.core.db import SessionLocal
    from app.red_team.service import run_red_team_sync

    with SessionLocal() as db:
        run_red_team_sync(db, job_id=uuid.UUID(job_id), run_id=uuid.UUID(run_id))
        db.commit()


@celery_app.task(name="summarize_comparison")
def summarize_comparison_task(comparison_id: str) -> None:
    import uuid

    from app.core.db import SessionLocal
    from app.comparisons.summary import summarize_comparison_sync

    with SessionLocal() as db:
        summarize_comparison_sync(db, uuid.UUID(comparison_id))
        db.commit()
