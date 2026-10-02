from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "researchai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Import at the bottom (not the top) so `celery -A app.worker.celery_app
# worker` registers run_research_job even if nothing else imports tasks.py
# first — tasks.py imports `celery_app` back from this module, which is
# safe here because `celery_app` is already assigned above by the time
# this line runs.
from app.worker import tasks  # noqa: E402,F401
