import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..incident_service import process_alerts
from ..schemas import AlertmanagerPayload, IncidentWebhookResult

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


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
    "/alertmanager",
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
