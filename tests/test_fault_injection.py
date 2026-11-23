from app.config import settings


def test_no_fault_by_default(client):
    assert client.get("/api/auth/me").status_code != 500


def test_fault_rate_fails_api_routes_but_not_probes_or_metrics(client, monkeypatch):
    monkeypatch.setattr(settings, "fault_rate", 1.0)
    assert client.get("/api/auth/me").status_code == 500
    assert client.get("/healthz").status_code == 200
    assert client.get("/metrics").status_code == 200


def test_injected_faults_are_counted_as_5xx_in_metrics(client, monkeypatch):
    monkeypatch.setattr(settings, "fault_rate", 1.0)
    client.get("/api/auth/me")
    assert 'http_requests_total{service="api",status="500"}' in client.get("/metrics").text
