"""Demo data. Run: python -m app.seed  (idempotent)."""
from datetime import timedelta

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import Ticket, TicketEvent, User, now
from .security import hash_password

USERS = [
    ("admin", "Admin SupportOps", "admin"),
    ("tech1", "Sara Technician", "technician"),
    ("tech2", "Omar Technician", "technician"),
    ("user1", "Layla User", "user"),
    ("user2", "Youssef User", "user"),
]


def seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User).limit(1)):
            print("Already seeded")
            return
        for username, name, role in USERS:  # demo password: <username>123
            db.add(User(username=username, full_name=name, role=role,
                        password_hash=hash_password(f"{username}123")))
        db.flush()
        by = {u.username: u for u in db.scalars(select(User))}
        demo = [
            ("Cannot connect to VPN", "network", "high", "user1", "tech1", "in_progress", 1),
            ("Printer on floor 2 jammed", "hardware", "low", "user1", None, "open", 5),
            ("Request access to shared drive", "access", "medium", "user2", "tech2", "resolved", -1),
            ("Laptop battery drains fast", "hardware", "medium", "user2", None, "open", -2),
        ]
        for title, cat, prio, creator, tech, status, due_days in demo:
            t = Ticket(title=title, description=f"Demo ticket: {title}.", category=cat, priority=prio,
                       status=status, creator_id=by[creator].id,
                       technician_id=by[tech].id if tech else None,
                       due_at=now() + timedelta(days=due_days),
                       resolved_at=now() if status == "resolved" else None)
            db.add(t)
            db.flush()
            db.add(TicketEvent(ticket_id=t.id, actor_id=by[creator].id, type="created"))
        db.commit()
        print("Seeded users (password = <username>123) and demo tickets")


if __name__ == "__main__":
    seed()
