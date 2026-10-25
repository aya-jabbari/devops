from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal["open", "in_progress", "resolved", "closed"]
Priority = Literal["low", "medium", "high", "critical"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(ORM):
    id: int
    username: str
    full_name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    category: str = "general"
    priority: Priority = "medium"
    due_at: datetime | None = None


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    category: str | None = None
    priority: Priority | None = None
    due_at: datetime | None = None


class StatusIn(BaseModel):
    status: Status


class AssignIn(BaseModel):
    technician_id: int | None


class CommentIn(BaseModel):
    body: str = Field(min_length=1)


class CommentOut(ORM):
    id: int
    author: UserOut | None
    body: str
    created_at: datetime


class EventOut(ORM):
    id: int
    actor: UserOut | None
    type: str
    field: str | None
    old_value: str | None
    new_value: str | None
    created_at: datetime


class TicketOut(ORM):
    id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    source: str
    creator: UserOut | None
    technician: UserOut | None
    created_at: datetime
    updated_at: datetime
    due_at: datetime | None
    resolved_at: datetime | None


class TicketDetail(TicketOut):
    comments: list[CommentOut]
    events: list[EventOut]


AlertStatus = Literal["firing", "resolved"]


class AlertLabels(BaseModel):
    alertname: str = Field(min_length=1)
    service: str = Field(min_length=1)
    severity: str = Field(min_length=1)

    @field_validator("alertname", "service", "severity")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Cette valeur ne peut pas être vide")
        return value


class AlertAnnotations(BaseModel):
    summary: str = Field(min_length=1)
    grafana_url: str | None = None

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Le résumé ne peut pas être vide")
        return value


class AlertmanagerAlert(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: AlertStatus
    labels: AlertLabels
    annotations: AlertAnnotations
    starts_at: datetime = Field(alias="startsAt")
    ends_at: datetime | None = Field(default=None, alias="endsAt")
    generator_url: str | None = Field(default=None, alias="generatorURL")
    fingerprint: str = Field(min_length=1)

    @field_validator("fingerprint")
    @classmethod
    def validate_fingerprint(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La fingerprint ne peut pas être vide")
        return value


class AlertmanagerPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: AlertStatus
    alerts: list[AlertmanagerAlert] = Field(min_length=1)
    version: str | None = None
    receiver: str | None = None
    group_labels: dict[str, str] = Field(
        default_factory=dict,
        alias="groupLabels",
    )
    common_labels: dict[str, str] = Field(
        default_factory=dict,
        alias="commonLabels",
    )
    common_annotations: dict[str, str] = Field(
        default_factory=dict,
        alias="commonAnnotations",
    )
