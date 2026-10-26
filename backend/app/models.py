"""Shared schema. Tables owned by Doha (tickets), reused by Aya (assignment/notifications)
and Maryam (incidents: add columns/tables via a migration, do not edit existing ones silently)."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))  # user | technician | admin


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="general")
    priority: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    source: Mapped[str] = mapped_column(String(20), default="user", index=True)  # user | monitoring
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator: Mapped[User | None] = relationship(foreign_keys=[creator_id])
    technician: Mapped[User | None] = relationship(foreign_keys=[technician_id])
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="ticket", order_by="Comment.id", cascade="all, delete-orphan")
    events: Mapped[list["TicketEvent"]] = relationship(
        back_populates="ticket", order_by="TicketEvent.id", cascade="all, delete-orphan")

class Incident(Base):
    __tablename__ = "incidents"

    __table_args__ = (
        Index(
            "ix_incidents_fingerprint_status",
            "fingerprint",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("tickets.id"),
        nullable=True,
        index=True,
    )
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    service: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    grafana_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        nullable=False,
    )
    recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
        nullable=False,
    )

class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ticket: Mapped[Ticket] = relationship(back_populates="comments")
    author: Mapped[User | None] = relationship()


class TicketEvent(Base):
    """History: created | status_changed | assigned | field_changed | commented."""
    __tablename__ = "ticket_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(30))
    field: Mapped[str | None] = mapped_column(String(50), nullable=True)
    old_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ticket: Mapped[Ticket] = relationship(back_populates="events")
    actor: Mapped[User | None] = relationship()
