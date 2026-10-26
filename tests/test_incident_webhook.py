def alert_payload(status="firing", fingerprint="abc123"):
    return {
        "status": status,
        "alerts": [
            {
                "status": status,
                "labels": {
                    "alertname": "HighErrorRate",
                    "service": "backend",
                    "severity": "critical",
                },
                "annotations": {
                    "summary": "Le taux d'erreur est élevé",
                    "grafana_url": "https://grafana.example.com/d/backend",
                },
                "startsAt": "2026-10-26T15:00:00Z",
                "endsAt": (
                    "2026-10-26T15:05:00Z"
                    if status == "resolved"
                    else "0001-01-01T00:00:00Z"
                ),
                "fingerprint": fingerprint,
            }
        ],
    }


def test_webhook_requires_authentication(client):
    response = client.post("/api/webhooks/alertmanager", json=alert_payload())

    assert response.status_code == 401


def test_webhook_rejects_invalid_token(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "alertmanager_webhook_secret", "test-secret")

    response = client.post(
        "/api/webhooks/alertmanager",
        json=alert_payload(),
        headers={"Authorization": "Bearer wrong-secret"},
    )

    assert response.status_code == 401


def test_webhook_creates_and_deduplicates_incident(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "alertmanager_webhook_secret", "test-secret")
    headers = {"Authorization": "Bearer test-secret"}

    created = client.post(
        "/api/webhooks/alertmanager",
        json=alert_payload(),
        headers=headers,
    )
    repeated = client.post(
        "/api/webhooks/alertmanager",
        json=alert_payload(),
        headers=headers,
    )

    assert created.status_code == 202
    assert created.json() == {
        "processed": 1,
        "created": 1,
        "updated": 0,
        "recovered": 0,
    }
    assert repeated.status_code == 202
    assert repeated.json() == {
        "processed": 1,
        "created": 0,
        "updated": 1,
        "recovered": 0,
    }


def test_webhook_recovers_active_incident(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "alertmanager_webhook_secret", "test-secret")
    headers = {"Authorization": "Bearer test-secret"}

    client.post(
        "/api/webhooks/alertmanager",
        json=alert_payload(),
        headers=headers,
    )
    recovered = client.post(
        "/api/webhooks/alertmanager",
        json=alert_payload(status="resolved"),
        headers=headers,
    )

    assert recovered.status_code == 202
    assert recovered.json() == {
        "processed": 1,
        "created": 0,
        "updated": 0,
        "recovered": 1,
    }


def test_webhook_rejects_invalid_payload(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "alertmanager_webhook_secret", "test-secret")

    response = client.post(
        "/api/webhooks/alertmanager",
        json={"status": "firing", "alerts": []},
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 422
