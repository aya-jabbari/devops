from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import AlertmanagerPayload


def valid_alert_payload() -> dict:
    return {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighErrorRate",
                    "service": "backend",
                    "severity": "critical",
                },
                "annotations": {
                    "summary": "Le taux d'erreur du backend est élevé",
                    "grafana_url": "https://grafana.example.com/d/backend",
                },
                "startsAt": "2026-10-25T17:00:00Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": "http://prometheus:9090/graph",
                "fingerprint": "abc123",
            }
        ],
    }


def test_valid_payload_is_parsed():
    payload = AlertmanagerPayload.model_validate(valid_alert_payload())
    alert = payload.alerts[0]

    assert payload.status == "firing"
    assert alert.labels.service == "backend"
    assert alert.fingerprint == "abc123"
    assert alert.starts_at == datetime(2026, 10, 25, 17, 0, tzinfo=timezone.utc)


def test_resolved_payload_is_accepted():
    data = valid_alert_payload()
    data["status"] = "resolved"
    data["alerts"][0]["status"] = "resolved"

    payload = AlertmanagerPayload.model_validate(data)

    assert payload.status == "resolved"
    assert payload.alerts[0].status == "resolved"


def test_empty_alerts_are_rejected():
    data = valid_alert_payload()
    data["alerts"] = []

    with pytest.raises(ValidationError):
        AlertmanagerPayload.model_validate(data)


def test_unknown_status_is_rejected():
    data = valid_alert_payload()
    data["alerts"][0]["status"] = "pending"

    with pytest.raises(ValidationError):
        AlertmanagerPayload.model_validate(data)


def test_missing_fingerprint_is_rejected():
    data = valid_alert_payload()
    del data["alerts"][0]["fingerprint"]

    with pytest.raises(ValidationError):
        AlertmanagerPayload.model_validate(data)


def test_blank_fingerprint_is_rejected():
    data = valid_alert_payload()
    data["alerts"][0]["fingerprint"] = "   "

    with pytest.raises(ValidationError):
        AlertmanagerPayload.model_validate(data)


def test_missing_required_label_is_rejected():
    data = valid_alert_payload()
    del data["alerts"][0]["labels"]["service"]

    with pytest.raises(ValidationError):
        AlertmanagerPayload.model_validate(data)


def test_blank_summary_is_rejected():
    data = valid_alert_payload()
    data["alerts"][0]["annotations"]["summary"] = " "

    with pytest.raises(ValidationError):
        AlertmanagerPayload.model_validate(data)


def test_invalid_start_time_is_rejected():
    data = valid_alert_payload()
    data["alerts"][0]["startsAt"] = "not-a-date"

    with pytest.raises(ValidationError):
        AlertmanagerPayload.model_validate(data)
