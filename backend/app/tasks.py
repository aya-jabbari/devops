import logging

from . import notifications
from .celery_app import celery_app
from .config import settings
from .db import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.ping")
def ping(message: str = "pong") -> str:
    logger.info("ping reçu : %s", message)
    return message


@celery_app.task(
    name="app.tasks.send_notification",
    autoretry_for=(OSError,),  # smtplib errors are OSError subclasses
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=settings.notification_max_retries,
)
def send_notification(kind: str, ticket_id: int, extra: dict | None = None) -> int:
    with SessionLocal() as db:
        return notifications.deliver(db, kind, ticket_id, extra)


@celery_app.task(name="app.tasks.check_overdue")
def check_overdue() -> int:
    with SessionLocal() as db:
        return notifications.check_overdue(db)
