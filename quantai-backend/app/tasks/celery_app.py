from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "quantai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.market_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Scheduled tasks (beat)
    beat_schedule={
        "refresh-market-data-daily": {
            "task": "app.tasks.market_tasks.refresh_all_assets",
            "schedule": 86400,  # every 24h
        },
    },
)
