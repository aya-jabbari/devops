from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import STAFF, current_user
from ..models import Comment, Ticket, TicketEvent, User
from ..notifications import notify
from ..schemas import (AssignIn, CommentIn, CommentOut, StatusIn, TicketCreate, TicketDetail,
                       TicketOut, TicketUpdate)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

# open -> in_progress -> resolved -> closed ; reopen allowed after resolution.
TRANSITIONS = {
    "open": {"in_progress"},
    "in_progress": {"resolved", "open"},
    "resolved": {"closed", "open"},
    "closed": set(),
}


def log(db: Session, ticket: Ticket, actor: User | None, type_: str,
        field=None, old=None, new=None):
    db.add(TicketEvent(ticket_id=ticket.id, actor_id=actor.id if actor else None, type=type_,
                       field=field, old_value=None if old is None else str(old),
                       new_value=None if new is None else str(new)))


def get_visible(db: Session, ticket_id: int, user: User) -> Ticket:
    """Server-side access check: users only see tickets they created (404 hides existence)."""
    t = db.get(Ticket, ticket_id)
    if not t or (user.role not in STAFF and t.creator_id != user.id):
        raise HTTPException(404, "Ticket not found")
    return t


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(data: TicketCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = Ticket(**data.model_dump(), creator_id=user.id, source="user")
    db.add(t)
    db.flush()
    log(db, t, user, "created")
    db.commit()
    return t


@router.get("", response_model=list[TicketOut])
def list_tickets(status: str | None = None, priority: str | None = None, source: str | None = None,
                 technician_id: int | None = None, q: str | None = None,
                 db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Ticket).order_by(Ticket.id.desc())
    if user.role not in STAFF:
        stmt = stmt.where(Ticket.creator_id == user.id)
    if status:
        stmt = stmt.where(Ticket.status == status)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)
    if source:
        stmt = stmt.where(Ticket.source == source)
    if technician_id:
        stmt = stmt.where(Ticket.technician_id == technician_id)
    if q:
        cond = Ticket.title.ilike(f"%{q}%")
        if q.strip().lstrip("#").isdigit():
            cond = or_(cond, Ticket.id == int(q.strip().lstrip("#")))
        stmt = stmt.where(cond)
    return db.scalars(stmt).all()


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return get_visible(db, ticket_id, user)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, data: TicketUpdate, db: Session = Depends(get_db),
                  user: User = Depends(current_user)):
    t = get_visible(db, ticket_id, user)
    changes = data.model_dump(exclude_unset=True)
    allowed = {"title", "description", "category", "priority", "due_at"} if user.role in STAFF \
        else {"title", "description", "category"}
    if set(changes) - allowed:
        raise HTTPException(403, f"Not allowed to edit: {', '.join(sorted(set(changes) - allowed))}")
    if t.status == "closed":
        raise HTTPException(409, "Closed tickets cannot be edited")
    for field, value in changes.items():
        old = getattr(t, field)
        if old != value:
            setattr(t, field, value)
            log(db, t, user, "field_changed", field, old, value)
    db.commit()
    return t


@router.post("/{ticket_id}/status", response_model=TicketOut)
def change_status(ticket_id: int, data: StatusIn, db: Session = Depends(get_db),
                  user: User = Depends(current_user)):
    t = get_visible(db, ticket_id, user)
    new = data.status
    if new not in TRANSITIONS[t.status]:
        raise HTTPException(409, f"Cannot go from {t.status} to {new}")
    # Requesters may only reopen their own resolved ticket.
    if user.role not in STAFF and not (t.status == "resolved" and new == "open"):
        raise HTTPException(403, "Only technicians can change this status")
    old, t.status = t.status, new
    if new == "resolved":
        t.resolved_at = datetime.now(timezone.utc)
    elif new == "open":
        t.resolved_at = None
    log(db, t, user, "status_changed", "status", old, new)
    db.commit()
    if new == "resolved":
        notify("resolved", t.id)
    return t


@router.post("/{ticket_id}/assign", response_model=TicketOut)
def assign(ticket_id: int, data: AssignIn, db: Session = Depends(get_db),
           user: User = Depends(current_user)):
    """Minimal version so the history table is exercised. Aya extends this (rules, notifications)."""
    if user.role not in STAFF:
        raise HTTPException(403, "Only staff can assign tickets")
    t = get_visible(db, ticket_id, user)
    target = db.get(User, data.technician_id) if data.technician_id else None
    if data.technician_id and (not target or target.role not in STAFF):
        raise HTTPException(422, "Assignee must be a technician or admin")
    if user.role == "technician" and data.technician_id not in (user.id, None):
        raise HTTPException(403, "Technicians can only assign tickets to themselves")
    old = t.technician.username if t.technician else None
    t.technician_id = data.technician_id
    if target and t.status == "open":
        t.status = "in_progress"
        log(db, t, user, "status_changed", "status", "open", "in_progress")
    log(db, t, user, "assigned", "technician", old, target.username if target else None)
    db.commit()
    db.refresh(t)
    if target:
        notify("assigned", t.id, technician_id=target.id)
    return t


@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(ticket_id: int, data: CommentIn, db: Session = Depends(get_db),
                user: User = Depends(current_user)):
    t = get_visible(db, ticket_id, user)
    if t.status == "closed":
        raise HTTPException(409, "Closed tickets cannot be commented")
    c = Comment(ticket_id=t.id, author_id=user.id, body=data.body)
    db.add(c)
    log(db, t, user, "commented")
    db.commit()
    notify("commented", t.id, comment_id=c.id)
    return c
