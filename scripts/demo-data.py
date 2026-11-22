"""Add realistic demo data through the real API: comments and a monitoring incident.

Runs INSIDE the api pod, so it needs nothing but the standard library:
    kubectl -n supportops exec -i deploy/api -c api -- python - < scripts/demo-data.py

- Comments: tech1 and user1 comment on tickets they can see (ticket_events and notifications follow).
- Incident: one firing Alertmanager alert sent to the authenticated webhook (creates one incident).
  The fingerprint is unique per run, so each run adds one incident.
Demo accounts come from `python -m app.seed` (password = <username>123).
"""

import json
import os
import time
import urllib.request
from datetime import datetime, timezone

API = os.environ.get("DEMO_API", "http://127.0.0.1:8000")


def call(method, path, body=None, token=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data, timeout=10) as resp:
        return json.loads(resp.read() or "null")


def login(username):
    return call("POST", "/api/auth/login", {"username": username, "password": f"{username}123"})["access_token"]


def tickets_of(token):
    data = call("GET", "/api/tickets", token=token)
    items = data["items"] if isinstance(data, dict) and "items" in data else data
    return [t for t in items if t.get("status") != "closed"]


comments = 0
for user in ("tech1", "user1"):
    token = login(user)
    for ticket in tickets_of(token)[:3]:
        call("POST", f"/api/tickets/{ticket['id']}/comments",
             {"body": f"Act 5 demo comment by {user} on ticket {ticket['id']}"}, token=token)
        comments += 1

secret = os.environ["ALERTMANAGER_WEBHOOK_SECRET"]
now = datetime.now(timezone.utc).isoformat()
alert = {
    "status": "firing",
    "labels": {"alertname": "DemoAct5HighErrorRate", "service": "api", "severity": "critical"},
    "annotations": {"summary": "Act 5 demo incident (restore proof)", "grafana_url": None},
    "startsAt": now,
    "fingerprint": f"act5-demo-{int(time.time())}",
}
result = call("POST", "/api/webhooks/alertmanager",
              {"status": "firing", "alerts": [alert], "version": "4"}, token=secret)

print(f"comments added: {comments}, incidents created: {result.get('created')}")
