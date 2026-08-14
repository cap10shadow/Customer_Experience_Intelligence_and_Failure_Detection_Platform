FROM python:3.11-slim

WORKDIR /app

COPY backend/services/gateway_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Phase 13 Batch 1 (AD-1): gateway_service now owns identity migrations,
# the same reason ingestion_service's Dockerfile already copies this.
COPY alembic.ini /app/alembic.ini
COPY backend/shared /app/backend/shared
COPY backend/services/gateway_service /app/backend/services/gateway_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.services.gateway_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
