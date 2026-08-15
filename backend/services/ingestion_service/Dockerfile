FROM python:3.11-slim

WORKDIR /app

COPY backend/services/ingestion_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini /app/alembic.ini
# Phase 13 Batch 9 (AD-2, §20): alembic.ini's own `script_location`
# points at `backend/migrations` -- previously masked entirely by the
# development configuration's `./backend:/app/backend` bind mount
# (which supplies this directory even though the image itself never
# did). The production-like configuration has no such bind mount, so
# `alembic upgrade head` inside this container needs the real migration
# scripts baked into the image -- discovered during this batch's own
# production-like migration verification.
COPY backend/migrations /app/backend/migrations
COPY backend/shared /app/backend/shared
COPY backend/services/ingestion_service /app/backend/services/ingestion_service
# `backend/migrations/env.py` imports every service's ORM models (not
# just this one) to build the single shared Alembic chain's metadata
# (ARCH-001/002) -- see gateway_service/Dockerfile's identical comment
# for the full rationale. Only these three (plus ingestion_service's
# own, already copied above) are actually imported by env.py.
COPY backend/services/gateway_service /app/backend/services/gateway_service
COPY backend/services/nlp_service /app/backend/services/nlp_service
COPY backend/services/copilot_service /app/backend/services/copilot_service

ENV PYTHONPATH=/app

# Phase 13 Batch 9 (AD-2, §20): non-root execution, applied where
# feasible -- verified compatible with both the development (bind-mount
# + --reload) and production-like configurations.
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "backend.services.ingestion_service.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
