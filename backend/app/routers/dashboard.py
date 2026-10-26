from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import STAFF, require_roles
from ..models import Ticket, User, now

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

ACTIVE = ("open", "in_progress")
PRIORITIES = ("critical", "high", "medium", "low")


@router.get("")
def dashboard(db: Session = Depends(get_db), _: User = Depends(require_roles(*STAFF))):
    """Staff-only counters: open/late tickets, priorities, workload per technician, active incidents."""
    active = Ticket.status.in_(ACTIVE)
    late = (Ticket.due_at.is_not(None)) & (Ticket.due_at < now())

    by_priority = dict(db.execute(
        select(Ticket.priority, func.count()).where(active).group_by(Ticket.priority)).all())

    workload = db.execute(
        select(User.id, User.full_name, func.count(Ticket.id),
               func.coalesce(func.sum(case((late, 1), else_=0)), 0))
        .join(Ticket, (Ticket.technician_id == User.id) & active, isouter=True)
        .where(User.role.in_(STAFF)).group_by(User.id, User.full_name).order_by(User.full_name)).all()

    return {
        "open": db.scalar(select(func.count()).where(Ticket.status == "open")) or 0,
        "in_progress": db.scalar(select(func.count()).where(Ticket.status == "in_progress")) or 0,
        "late": db.scalar(select(func.count()).where(active, late)) or 0,
        "unassigned": db.scalar(select(func.count()).where(active, Ticket.technician_id.is_(None))) or 0,
        "incidents": db.scalar(select(func.count()).where(active, Ticket.source == "monitoring")) or 0,
        "priorities": {p: by_priority.get(p, 0) for p in PRIORITIES},
        "workload": [{"technician_id": i, "name": n, "active": a, "late": int(l)} for i, n, a, l in workload],
    }
