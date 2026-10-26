from datetime import datetime, timedelta, timezone


def iso(delta):
    return (datetime.now(timezone.utc) + delta).isoformat()


def mk(client, h, **kw):
    r = client.post("/api/tickets", json={"title": "Some ticket", **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def tech_id(client, h, name):
    users = client.get("/api/users/technicians", headers=h).json()
    return next(u["id"] for u in users if u["username"] == name)


def test_dashboard_is_staff_only(client, login):
    assert client.get("/api/dashboard", headers=login("user1")).status_code == 403
    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/api/dashboard", headers=login("tech1")).status_code == 200


def test_counters_priorities_and_workload(client, login):
    admin, user = login("admin"), login("user1")
    t1 = mk(client, user, priority="critical", due_at=iso(-timedelta(days=1)))  # late
    t2 = mk(client, user, priority="high", due_at=iso(timedelta(days=1)))       # not late
    t3 = mk(client, user, priority="high")
    done = mk(client, user, priority="low", due_at=iso(-timedelta(days=2)))     # late but resolved
    tid = tech_id(client, admin, "tech1")
    for t in (t1, t2):
        client.post(f"/api/tickets/{t['id']}/assign", json={"technician_id": tid}, headers=admin)
    client.post(f"/api/tickets/{done['id']}/assign", json={"technician_id": tid}, headers=admin)
    client.post(f"/api/tickets/{done['id']}/status", json={"status": "resolved"}, headers=admin)

    d = client.get("/api/dashboard", headers=admin).json()
    assert d["late"] == 1
    assert d["unassigned"] == 1  # t3
    assert d["open"] == 1 and d["in_progress"] == 2
    assert d["priorities"] == {"critical": 1, "high": 2, "medium": 0, "low": 0}
    by_name = {w["name"]: w for w in d["workload"]}
    assert by_name["Tech1"] == {"technician_id": tid, "name": "Tech1", "active": 2, "late": 1}
    assert by_name["Tech2"]["active"] == 0  # technicians without tickets still listed
    assert t3["id"]  # keep the unassigned ticket referenced


def test_late_filter_on_ticket_list(client, login):
    admin, user = login("admin"), login("user1")
    late = mk(client, user, due_at=iso(-timedelta(days=1)))
    mk(client, user, due_at=iso(timedelta(days=1)))
    mk(client, user)
    r = client.get("/api/tickets?late=true", headers=admin).json()
    assert [t["id"] for t in r] == [late["id"]]
