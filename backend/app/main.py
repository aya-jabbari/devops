from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from .db import Base, SessionLocal, engine
from . import models_notification  # noqa: F401  (registers the notifications table)
from .routers import auth, tickets
from .routers import auth, incidents, tickets
from .routers import auth, dashboard, tickets


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Week 1 only: tables created at startup. Replace with Alembic migrations (team decision).
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="SupportOps API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(incidents.router)
app.include_router(tickets.router)
app.include_router(dashboard.router)


@app.get("/health")  # kept from the backend skeleton
def health():
    return {"status": "ok"}


@app.get("/healthz")  # liveness probe
def healthz():
    return {"status": "ok"}


@app.get("/readyz")  # readiness probe: checks the database
def readyz():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready"}