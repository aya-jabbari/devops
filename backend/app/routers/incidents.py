import secrets

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import STAFF, current_user, require_roles
from ..incident_service import process_alerts
from ..models import Incident, User
from ..schemas import AlertmanagerPayload, IncidentOut, IncidentWebhookResult

router = APIRouter(prefix="/api", tags=["incidents"])


def verify_alertmanager_secret(authorization: str | None) -> None:
    scheme, _, token = (authorization or "").partition(" ")
    configured_secret = settings.alertmanager_webhook_secret
    if (
        scheme.lower() != "bearer"
        or not token
        or not configured_secret
        or not secrets.compare_digest(token, configured_secret)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook credentials",
        )


@router.post(
    "/webhooks/alertmanager",
    response_model=IncidentWebhookResult,
    status_code=status.HTTP_202_ACCEPTED,
)
def alertmanager_webhook(
    payload: AlertmanagerPayload,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> IncidentWebhookResult:
    verify_alertmanager_secret(authorization)
    result = process_alerts(db, payload.alerts)
    return IncidentWebhookResult(
        processed=len(payload.alerts),
        created=result.created,
        updated=result.updated,
        recovered=result.recovered,
    )


@router.get(
    "/incidents",
    response_model=list[IncidentOut],
)
def list_incidents(
    status: str | None = Query(default=None, description="Filtre par statut: active, recovered, closed"),
    severity: str | None = Query(default=None, description="Filtre par sévérité"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[Incident]:
    query = select(Incident).order_by(Incident.detected_at.desc())
    if status:
        query = query.where(Incident.status == status)
    if severity:
        query = query.where(Incident.severity == severity)
    return list(db.scalars(query).all())


@router.post(
    "/incidents/{incident_id}/close",
    response_model=IncidentOut,
)
def close_incident(
    incident_id: int,
    user: User = Depends(require_roles(*STAFF)),
    db: Session = Depends(get_db),
) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident introuvable")

    incident.status = "closed"
    incident.closed_at = datetime.now(timezone.utc)
    incident.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(incident)
    return incident

