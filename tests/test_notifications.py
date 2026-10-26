from datetime import timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import notifications
from app.db import Base
from app.models import Comment, Ticket, User, now
from app.models_notification import Notification


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        for u, role in [("admin", "admin"), ("tech1", "technician"), ("user1", "user")]:
            session.add(User(username=u, full_name=u.title(), role=role, password_hash="x"))
        session.commit()
        yield session


def user(db, name):
    return db.scalar(select(User).where(User.username == name))


def make_ticket(db, **kw):
    t = Ticket(title="VPN down", creator_id=user(db, "user1").id, **kw)
    db.add(t)
    db.commit()
    return t


class Outbox:
    def __init__(self, fail_times=0):
        self.sent, self.fail_times = [], fail_times

    def __call__(self, to, subject, body):
        if self.fail_times:
            self.fail_times -= 1
            raise ConnectionRefusedError("smtp down")
        self.sent.append((to, subject))


def test_assigned_goes_to_the_technician(db):
    t = make_ticket(db, technician_id=user(db, "tech1").id)
    out = Outbox()
    assert notifications.deliver(db, "assigned", t.id, {"ref": "1"}, send=out) == 1
    assert out.sent[0][0] == "tech1@supportops.local"
    assert f"#{t.id}" in out.sent[0][1]


def test_same_event_is_not_sent_twice(db):
    t = make_ticket(db, technician_id=user(db, "tech1").id)
    out = Outbox()
    notifications.deliver(db, "assigned", t.id, {"ref": "1"}, send=out)
    assert notifications.deliver(db, "assigned", t.id, {"ref": "1"}, send=out) == 0
    assert len(out.sent) == 1
    assert notifications.deliver(db, "assigned", t.id, {"ref": "2"}, send=out) == 1  # real reassignment


def test_comment_notifies_the_other_party_not_the_author(db):
    t = make_ticket(db, technician_id=user(db, "tech1").id)
    c = Comment(ticket_id=t.id, author_id=user(db, "tech1").id, body="looking into it")
    db.add(c)
    db.commit()
    out = Outbox()
    notifications.deliver(db, "commented", t.id, {"comment_id": c.id, "ref": str(c.id)}, send=out)
    assert [to for to, _ in out.sent] == ["user1@supportops.local"]


def test_resolved_goes_to_the_creator(db):
    t = make_ticket(db, technician_id=user(db, "tech1").id)
    out = Outbox()
    notifications.deliver(db, "resolved", t.id, {"ref": "r"}, send=out)
    assert [to for to, _ in out.sent] == ["user1@supportops.local"]


def test_failed_send_raises_for_retry_then_succeeds_without_duplicate(db):
    t = make_ticket(db, technician_id=user(db, "tech1").id)
    out = Outbox(fail_times=1)
    with pytest.raises(ConnectionRefusedError):
        notifications.deliver(db, "assigned", t.id, {"ref": "1"}, send=out)
    row = db.scalar(select(Notification))
    assert (row.status, row.attempts) == ("failed", 1)
    assert notifications.deliver(db, "assigned", t.id, {"ref": "1"}, send=out) == 1  # the Celery retry
    row = db.scalar(select(Notification))
    assert (row.status, row.attempts, row.error) == ("sent", 2, None)
    assert len(out.sent) == 1


def test_overdue_is_notified_once_per_due_date(db):
    late = make_ticket(db, technician_id=user(db, "tech1").id, due_at=now() - timedelta(hours=1))
    make_ticket(db, technician_id=user(db, "tech1").id, due_at=now() + timedelta(hours=1))  # not late
    make_ticket(db, technician_id=user(db, "tech1").id, due_at=now() - timedelta(hours=1), status="resolved")
    out = Outbox()
    assert notifications.check_overdue(db, send=out) == 1
    assert notifications.check_overdue(db, send=out) == 0  # next beat tick: no repeat
    late.due_at = now() - timedelta(minutes=5)  # due date moved and missed again
    db.commit()
    assert notifications.check_overdue(db, send=out) == 1


def test_overdue_unassigned_goes_to_admins(db):
    make_ticket(db, due_at=now() - timedelta(hours=1))
    out = Outbox()
    notifications.check_overdue(db, send=out)
    assert [to for to, _ in out.sent] == ["admin@supportops.local"]


def test_one_failing_overdue_does_not_block_the_others(db):
    make_ticket(db, technician_id=user(db, "tech1").id, due_at=now() - timedelta(hours=2))
    make_ticket(db, technician_id=user(db, "tech1").id, due_at=now() - timedelta(hours=1))
    out = Outbox(fail_times=1)
    assert notifications.check_overdue(db, send=out) == 1


def test_notify_never_raises_when_broker_is_down(monkeypatch):
    monkeypatch.setattr(notifications.settings, "notifications_enabled", True)

    def boom(*a, **k):
        raise ConnectionError("redis down")

    from app import tasks
    monkeypatch.setattr(tasks.send_notification, "delay", boom)
    notifications.notify("assigned", 1, ref="x")  # must not raise
