# Python is pinned: the unpinned chainguard "latest" moved to 3.15, which SQLAlchemy does not support yet.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /app/venv \
    && /app/venv/bin/pip install --no-cache-dir -r requirements.txt \
    && find /app/venv -type d -name 'setuptools*' -prune -exec rm -rf {} +

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/venv/bin:${PATH}"

WORKDIR /app

COPY --from=builder /app/venv /app/venv
COPY app ./app

USER 65532

EXPOSE 8000

# Always run the venv's python (the one that has uvicorn/celery installed).
ENTRYPOINT ["/app/venv/bin/python"]
CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]