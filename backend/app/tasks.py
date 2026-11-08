import logging
import smtplib
from email.mime.text import MIMEText
import os

from . import notifications
from .celery_app import celery_app
from .config import settings
from .db import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.ping")
def ping(message: str = "pong") -> str:
    logger.info("ping reçu : %s", message)
    return message


@celery_app.task(name="app.tasks.notify_incident", bind=True, max_retries=3, default_retry_delay=60)
def notify_incident(self, incident_id: int, alert_name: str, severity: str, summary: str, grafana_url: str | None = None) -> str:
    logger.info("Envoi notification incident #%s [%s]: %s", incident_id, severity, alert_name)
    smtp_host = os.getenv("SMTP_HOST", "mailpit")
    smtp_port = int(os.getenv("SMTP_PORT", "1025"))
    sender = os.getenv("SMTP_FROM", "supportops-monitoring@example.com")
    recipient = os.getenv("INCIDENT_NOTIFICATION_EMAIL", "oncall@example.com")

    body = f"""Incident détecté par la supervision :
ID : #{incident_id}
Alerte : {alert_name}
Sévérité : {severity}
Résumé : {summary}
Grafana : {grafana_url or 'N/A'}
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"[ALERTE {severity.upper()}] {alert_name} - SupportOps"
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
            server.send_message(msg)
        logger.info("Notification e-mail envoyée pour l'incident #%s", incident_id)
        return f"Notification sent for incident #{incident_id}"
    except Exception as exc:
        logger.warning("Échec envoi mail incident #%s (retry dans 60s): %s", incident_id, exc)
        raise self.retry(exc=exc)


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
