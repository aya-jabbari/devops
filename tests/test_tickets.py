def mk(client, h, title="Printer broken", **kw):
    r = client.post("/api/tickets", json={"title": title, **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_login_wrong_password(client):
    assert client.post("/api/auth/login", json={"username": "admin", "password": "x"}).status_code == 401


def test_requires_auth(client):
    assert client.get("/api/tickets").status_code == 401


# --- access control ---------------------------------------------------------
def test_user_cannot_see_other_users_ticket(client, login):
    t = mk(client, login("user1"))
    assert client.get(f"/api/tickets/{t['id']}", headers=login("user2")).status_code == 404
    assert client.get("/api/tickets", headers=login("user2")).json() == []
    assert client.post(f"/api/tickets/{t['id']}/comments", json={"body": "hi"},
                       headers=login("user2")).status_code == 404


def test_staff_sees_all(client, login):
    mk(client, login("user1"))
    mk(client, login("user2"))
    assert len(client.get("/api/tickets", headers=login("tech1")).json()) == 2


def test_user_cannot_change_priority_or_status(client, login):
    h = login("user1")
    t = mk(client, h)
    assert client.patch(f"/api/tickets/{t['id']}", json={"priority": "critical"}, headers=h).status_code == 403
    assert client.post(f"/api/tickets/{t['id']}/status", json={"status": "in_progress"},
                       headers=h).status_code == 403


# --- lifecycle + history ----------------------------------------------------
def test_full_lifecycle_and_history(client, login):
    u, tech = login("user1"), login("tech1")
    t = mk(client, u)
    tid = t["id"]
    me = client.get("/api/auth/me", headers=tech).json()
    assert client.post(f"/api/tickets/{tid}/assign", json={"technician_id": me["id"]}, headers=tech).status_code == 200
    assert client.post(f"/api/tickets/{tid}/comments", json={"body": "Looking"}, headers=tech).status_code == 201
    r = client.post(f"/api/tickets/{tid}/status", json={"status": "resolved"}, headers=tech)
    assert r.status_code == 200 and r.json()["resolved_at"]
    # requester reopens, staff resolves again, then closes
    assert client.post(f"/api/tickets/{tid}/status", json={"status": "open"}, headers=u).status_code == 200
    assert client.post(f"/api/tickets/{tid}/status", json={"status": "in_progress"}, headers=tech).status_code == 200
    client.post(f"/api/tickets/{tid}/status", json={"status": "resolved"}, headers=tech)
    assert client.post(f"/api/tickets/{tid}/status", json={"status": "closed"}, headers=tech).status_code == 200
    d = client.get(f"/api/tickets/{tid}", headers=u).json()
    kinds = [e["type"] for e in d["events"]]
    assert kinds[0] == "created" and "assigned" in kinds and kinds.count("status_changed") >= 5
    assert len(d["comments"]) == 1
    assert client.post(f"/api/tickets/{tid}/comments", json={"body": "x"}, headers=u).status_code == 409


def test_invalid_transition(client, login):
    t = mk(client, login("user1"))
    r = client.post(f"/api/tickets/{t['id']}/status", json={"status": "closed"}, headers=login("tech1"))
    assert r.status_code == 409


def test_technician_cannot_assign_to_someone_else(client, login):
    t = mk(client, login("user1"))
    other = client.get("/api/auth/me", headers=login("tech2")).json()["id"]
    r = client.post(f"/api/tickets/{t['id']}/assign", json={"technician_id": other}, headers=login("tech1"))
    assert r.status_code == 403
    assert client.post(f"/api/tickets/{t['id']}/assign", json={"technician_id": other},
                       headers=login("admin")).status_code == 200


# --- filters / search ---------------------------------------------------------
def test_filters_and_search(client, login):
    h = login("tech1")
    a = mk(client, login("user1"), "VPN down", priority="high")
    mk(client, login("user1"), "Printer jam", priority="low")
    assert [t["id"] for t in client.get("/api/tickets?priority=high", headers=h).json()] == [a["id"]]
    assert len(client.get("/api/tickets?q=printer", headers=h).json()) == 1
    assert client.get(f"/api/tickets?q={a['id']}", headers=h).json()[0]["id"] == a["id"]
    assert client.get("/api/tickets?status=closed", headers=h).json() == []
