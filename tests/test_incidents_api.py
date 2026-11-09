def test_list_incidents_requires_auth(client):
    response = client.get("/api/incidents")
    assert response.status_code == 401


def test_list_incidents_returns_incidents(client, monkeypatch):
    from app.config import settings
    from app.security import create_token
    from tests.test_incident_webhook import alert_payload

    monkeypatch.setattr(settings, "alertmanager_webhook_secret", "test-secret")
    headers = {"Authorization": "Bearer test-secret"}

    # Créer un incident via le webhook
    client.post("/api/webhooks/alertmanager", json=alert_payload(), headers=headers)

    # Récupérer la liste avec un compte utilisateur connecté
    user_token = create_token(1)  # admin / tech
    response = client.get("/api/incidents", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["alert_name"] == "HighErrorRate"
    assert data[0]["status"] == "active"


def test_close_incident_by_staff(client, monkeypatch):
    from app.config import settings
    from app.security import create_token
    from tests.test_incident_webhook import alert_payload

    monkeypatch.setattr(settings, "alertmanager_webhook_secret", "test-secret")
    headers = {"Authorization": "Bearer test-secret"}

    client.post("/api/webhooks/alertmanager", json=alert_payload(fingerprint="fp-close-1"), headers=headers)

    # Token admin (id=1 dans le seed/conftest)
    admin_token = create_token(1)

    # Liste pour trouver l'id
    incidents = client.get("/api/incidents", headers={"Authorization": f"Bearer {admin_token}"}).json()
    target = next(i for i in incidents if i["fingerprint"] == "fp-close-1")

    # Clore l'incident
    close_resp = client.post(f"/api/incidents/{target['id']}/close", headers={"Authorization": f"Bearer {admin_token}"})
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"
    assert close_resp.json()["closed_at"] is not None
