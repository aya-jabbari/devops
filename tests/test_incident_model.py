from sqlalchemy import create_engine, inspect

from app.db import Base
from app.models import Incident


def test_incident_model_has_expected_table():
    assert Incident.__tablename__ == "incidents"


def test_incident_model_has_expected_columns():
    columns = set(Incident.__table__.columns.keys())

    assert {
        "id",
        "ticket_id",
        "fingerprint",
        "service",
        "severity",
        "alert_name",
        "status",
        "summary",
        "grafana_url",
        "detected_at",
        "recovered_at",
        "closed_at",
        "created_at",
        "updated_at",
    } <= columns


def test_incident_table_is_created_with_expected_index():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    table_names = inspect(engine).get_table_names()
    index_names = {
        index["name"] for index in inspect(engine).get_indexes("incidents")
    }

    assert "incidents" in table_names
    assert "ix_incidents_fingerprint_status" in index_names
