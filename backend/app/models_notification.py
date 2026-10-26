"""Notification tracking (Aya). Kept out of models.py to avoid conflicts with the shared schema."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .models import now


class Notification(Base):
    """One row per (event, recipient). `dedup_key` is unique: it is what prevents duplicates
    on Celery retries, worker restarts and repeated overdue checks."""
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    dedup_key: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # assigned | commented | resolved | overdue
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending | sent | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
