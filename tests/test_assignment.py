"""Assignment: rules, history and notification hand-off (Aya)."""
from app.config import settings


def mk(client, h, title="Printer broken", **kw):
    r = client.post("/api/tickets", json={"title": title, **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def uid(client, login, username):
    return client.get("/api/auth/me", headers=login(username)).json()["id"]


def assign(client, headers, ticket_id, technician_id):
    return client.post(f"/api/tickets/{ticket_id}/assign", json={"technician_id": technician_id}, headers=headers)


def events(client, headers, ticket_id, type_=None):
    evs = client.get(f"/api/tickets/{ticket_id}", headers=headers).json()["events"]
    return [e for e in evs if type_ is None or e["type"] == type_]


def test_assigning_an_open_ticket_moves_it_to_in_progress(client, login):
    t = mk(client, login("user1"))
    r = assign(client, login("admin"), t["id"], uid(client, login, "tech1"))
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert r.json()["technician"]["id"] == uid(client, login, "tech1")
    changes = events(client, login("admin"), t["id"], "status_changed")
    assert [(e["old_value"], e["new_value"]) for e in changes] == [("open", "in_progress")]


def test_reassignment_keeps_both_entries_in_history(client, login):
    admin = login("admin")
    t = mk(client, login("user1"))
    assign(client, admin, t["id"], uid(client, login, "tech1"))
    assign(client, admin, t["id"], uid(client, login, "tech2"))
    history = [(e["old_value"], e["new_value"]) for e in events(client, admin, t["id"], "assigned")]
    assert history == [(None, "tech1"), ("tech1", "tech2")]
    # reassigning must not push the status back or forward again
    assert client.get(f"/api/tickets/{t['id']}", headers=admin).json()["status"] == "in_progress"


def test_unassign_is_recorded(client, login):
    admin = login("admin")
    t = mk(client, login("user1"))
    assign(client, admin, t["id"], uid(client, login, "tech1"))
    r = assign(client, admin, t["id"], None)
    assert r.status_code == 200 and r.json()["technician"] is None
    last = events(client, admin, t["id"], "assigned")[-1]
    assert (last["old_value"], last["new_value"]) == ("tech1", None)


def test_regular_user_cannot_assign(client, login):
    t = mk(client, login("user1"))
    r = assign(client, login("user1"), t["id"], uid(client, login, "tech1"))
    assert r.status_code == 403


def test_technician_can_take_a_ticket_but_not_give_it_away(client, login):
    t = mk(client, login("user1"))
    tech1 = login("tech1")
    assert assign(client, tech1, t["id"], uid(client, login, "tech1")).status_code == 200
    assert assign(client, tech1, t["id"], uid(client, login, "tech2")).status_code == 403


def test_assignee_must_be_staff_and_exist(client, login):
    admin = login("admin")
    t = mk(client, login("user1"))
    assert assign(client, admin, t["id"], uid(client, login, "user2")).status_code == 422
    assert assign(client, admin, t["id"], 99999).status_code == 422
    assert events(client, admin, t["id"], "assigned") == []  # nothing recorded on failure


def test_assign_unknown_ticket_is_404(client, login):
    assert assign(client, login("admin"), 99999, uid(client, login, "tech1")).status_code == 404


def test_assignment_enqueues_a_notification_but_unassign_does_not(client, login, monkeypatch):
    from app import tasks
    queued = []
    monkeypatch.setattr(settings, "notifications_enabled", True)
    monkeypatch.setattr(tasks.send_notification, "delay", lambda *a, **k: queued.append(a))
    admin = login("admin")
    t = mk(client, login("user1"))
    assign(client, admin, t["id"], uid(client, login, "tech1"))
    assert [(a[0], a[1]) for a in queued] == [("assigned", t["id"])]
    assign(client, admin, t["id"], None)
    assert len(queued) == 1


def test_assignment_still_succeeds_when_the_broker_is_down(client, login, monkeypatch):
    from app import tasks

    def boom(*a, **k):
        raise ConnectionError("redis is down")

    monkeypatch.setattr(settings, "notifications_enabled", True)
    monkeypatch.setattr(tasks.send_notification, "delay", boom)
    t = mk(client, login("user1"))
    r = assign(client, login("admin"), t["id"], uid(client, login, "tech1"))
    assert r.status_code == 200


def test_notification_task_retries_are_bounded():
    from app import tasks
    task = tasks.send_notification
    assert task.max_retries == settings.notification_max_retries
    assert OSError in task.autoretry_for
