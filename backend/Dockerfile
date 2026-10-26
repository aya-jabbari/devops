FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip uninstall -y setuptools wheel urllib3 jaraco.context || true \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir jaraco.context==6.1.0

COPY app ./app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]