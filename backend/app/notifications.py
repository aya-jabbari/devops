"""Notification entry point (called by the tickets API) and delivery logic.

`notify` only enqueues a Celery task and never raises: the API must keep working
when Redis is down. `deliver` is plain DB + SMTP code so it can be tested without Celery.
kind: "assigned" | "commented" | "resolved" | "overdue"
"""
import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import settings
from .models import Comment, Ticket, User, now
from .models_notification import Notification

logger = logging.getLogger(__name__)

SUBJECTS = {
    "assigned": "[SupportOps] Ticket #{id} vous a été affecté : {title}",
    "commented": "[SupportOps] Nouveau commentaire sur le ticket #{id} : {title}",
    "resolved": "[SupportOps] Ticket #{id} résolu : {title}",
    "overdue": "[SupportOps] Ticket #{id} en retard : {title}",
}


def notify(kind: str, ticket_id: int, **extra) -> None:
    """`ref` (in extra) distinguishes two legitimate notifications of the same kind on one ticket."""
    if not settings.notifications_enabled:
        return
    try:
        from .tasks import send_notification  # local import: keeps the API importable without Celery wiring
        send_notification.delay(kind, ticket_id, extra)
    except Exception:  # broker down, etc.: never fail the API request
        logger.exception("notification %s for ticket %s could not be queued", kind, ticket_id)


def email_of(user: User) -> str:
    return f"{user.username}@{settings.mail_domain}"


def recipients(db: Session, kind: str, ticket: Ticket, extra: dict) -> list[User]:
    if kind == "assigned":
        found = [ticket.technician]
    elif kind == "resolved":
        found = [ticket.creator]
    elif kind == "commented":
        author_id = None
        if extra.get("comment_id"):
            comment = db.get(Comment, extra["comment_id"])
            author_id = comment.author_id if comment else None
        found = [u for u in (ticket.creator, ticket.technician) if u and u.id != author_id]
    elif kind == "overdue":
        found = [ticket.technician] if ticket.technician else list(
            db.scalars(select(User).where(User.role == "admin")))
    else:
        raise ValueError(f"unknown notification kind: {kind}")
    seen, unique = set(), []
    for user in found:
        if user and user.id not in seen:
            seen.add(user.id)
            unique.append(user)
    return unique


def send_mail(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.mail_from, to, subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.send_message(msg)


def deliver(db: Session, kind: str, ticket_id: int, extra: dict | None = None, send=send_mail) -> int:
    """Send the notification to each recipient once. Returns the number of mails sent.
    Raises the last send error AFTER trying everyone, so Celery can retry; recipients already
    marked `sent` are skipped on the retry."""
    extra = extra or {}
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        logger.warning("ticket %s not found, notification %s dropped", ticket_id, kind)
        return 0
    sent, last_error = 0, None
    for user in recipients(db, kind, ticket, extra):
        key = f"{kind}:{ticket.id}:{extra.get('ref', '')}:{user.id}"
        row = db.scalar(select(Notification).where(Notification.dedup_key == key))
        if row is None:
            row = Notification(dedup_key=key, kind=kind, ticket_id=ticket.id, recipient_id=user.id)
            db.add(row)
            try:
                db.commit()
            except IntegrityError:  # another worker created it first
                db.rollback()
                continue
        elif row.status == "sent":
            continue
        row.attempts += 1
        try:
            send(email_of(user), SUBJECTS[kind].format(id=ticket.id, title=ticket.title),
                 f"Bonjour {user.full_name},\n\n{SUBJECTS[kind].format(id=ticket.id, title=ticket.title)}\n"
                 f"Priorité : {ticket.priority} · Statut : {ticket.status}\n")
            row.status, row.sent_at, row.error = "sent", now(), None
            sent += 1
        except Exception as exc:  # noqa: BLE001
            row.status, row.error = "failed", str(exc)[:500]
            last_error = exc
            logger.warning("mail to %s failed (attempt %s): %s", user.username, row.attempts, exc)
        db.commit()
    if last_error:
        raise last_error
    return sent


def check_overdue(db: Session, send=send_mail) -> int:
    """Notify once per (ticket, due date). Changing the due date re-arms the notification."""
    tickets = db.scalars(select(Ticket).where(
        Ticket.due_at.is_not(None), Ticket.due_at < now(), Ticket.status.in_(("open", "in_progress"))))
    total = 0
    for t in tickets.all():
        try:
            total += deliver(db, "overdue", t.id, {"ref": t.due_at.isoformat()}, send=send)
        except Exception:  # noqa: BLE001  one failing mail must not block the other tickets
            logger.exception("overdue notification for ticket %s failed", t.id)
    return total
