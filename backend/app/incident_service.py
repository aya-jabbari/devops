from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Incident
from .schemas import AlertmanagerAlert
from .tasks import notify_incident


@dataclass
class IncidentProcessingResult:
    created: int = 0
    updated: int = 0
    recovered: int = 0
    created_incidents: list[Incident] = None

    def __post_init__(self):
        if self.created_incidents is None:
            self.created_incidents = []


def process_alerts(db: Session, alerts: list[AlertmanagerAlert]) -> IncidentProcessingResult:
    result = IncidentProcessingResult()

    for alert in alerts:
        if alert.status == "firing":
            _process_firing(db, alert, result)
        else:
            _process_resolved(db, alert, result)

    db.commit()

    # Déclencher la tâche Celery asynchrone pour chaque nouvel incident créé
    for incident in result.created_incidents:
        try:
            notify_incident.delay(
                incident.id,
                incident.alert_name,
                incident.severity,
                incident.summary,
                incident.grafana_url,
            )
        except Exception:
            # Ne bloque pas la transaction si Redis/Celery est temporairement injoignable
            pass

    return result


def _process_firing(
    db: Session,
    alert: AlertmanagerAlert,
    result: IncidentProcessingResult,
) -> None:
    incident = _find_active_incident(db, alert.fingerprint)
    if incident is None:
        incident = Incident(
            fingerprint=alert.fingerprint,
            service=alert.labels.service,
            severity=alert.labels.severity,
            alert_name=alert.labels.alertname,
            status="active",
            summary=alert.annotations.summary,
            grafana_url=alert.annotations.grafana_url,
            detected_at=alert.starts_at,
        )
        db.add(incident)
        db.flush()
        result.created_incidents.append(incident)
        result.created += 1
        return

    incident.service = alert.labels.service
    incident.severity = alert.labels.severity
    incident.alert_name = alert.labels.alertname
    incident.summary = alert.annotations.summary
    incident.grafana_url = alert.annotations.grafana_url
    incident.updated_at = datetime.now(timezone.utc)
    result.updated += 1


def _process_resolved(
    db: Session,
    alert: AlertmanagerAlert,
    result: IncidentProcessingResult,
) -> None:
    incident = _find_active_incident(db, alert.fingerprint)
    if incident is None:
        return

    incident.status = "recovered"
    incident.recovered_at = alert.ends_at or datetime.now(timezone.utc)
    incident.updated_at = datetime.now(timezone.utc)
    result.recovered += 1


def _find_active_incident(db: Session, fingerprint: str) -> Incident | None:
    return db.scalar(
        select(Incident).where(
            Incident.fingerprint == fingerprint,
            Incident.status == "active",
        )
    )
