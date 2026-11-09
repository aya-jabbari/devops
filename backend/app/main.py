from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text
from starlette.requests import Request
from starlette.responses import Response

from .db import Base, SessionLocal, engine
from . import models_notification  # noqa: F401  (registers the notifications table)
from .routers import auth, dashboard, incidents, tickets


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Week 1 only: tables created at startup. Replace with Alembic migrations (team decision).
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="SupportOps API", lifespan=lifespan)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ("service", "status"),
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("service",),
)


@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        REQUEST_COUNT.labels(service="api", status="500").inc()
        REQUEST_DURATION.labels(service="api").observe(perf_counter() - started)
        raise

    REQUEST_COUNT.labels(service="api", status=str(response.status_code)).inc()
    REQUEST_DURATION.labels(service="api").observe(perf_counter() - started)
    return response


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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