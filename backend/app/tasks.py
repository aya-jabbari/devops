import logging

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.ping")
def ping(message: str = "pong") -> str:
    logger.info("ping reçu : %s", message)
    return message
