import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        for u, role in [("admin", "admin"), ("tech1", "technician"), ("tech2", "technician"),
                        ("user1", "user"), ("user2", "user")]:
            db.add(User(username=u, full_name=u.title(), role=role, password_hash=hash_password(u + "123")))
        db.commit()

    def override():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override
    app.router.lifespan_context = None  # skip create_all on the real DB
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def login(client):
    def _login(username):
        r = client.post("/api/auth/login", json={"username": username, "password": username + "123"})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _login
