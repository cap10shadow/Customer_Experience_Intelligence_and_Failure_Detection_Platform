FROM python:3.11-slim

WORKDIR /app

COPY backend/services/gateway_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Phase 13 Batch 1 (AD-1): gateway_service now owns identity migrations,
# the same reason ingestion_service's Dockerfile already copies this.
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
COPY backend/services/gateway_service /app/backend/services/gateway_service
# `backend/migrations/env.py` imports every service's ORM models (not
# just this one) to build the single shared Alembic chain's metadata
# (ARCH-001/002: one shared Postgres instance, one linear migration
# history) -- also previously masked by the development bind mount.
# Only these three (plus gateway_service's own, already copied above)
# are actually imported by env.py; every other service's migrations
# apply through the same shared chain without needing their model code
# present here.
COPY backend/services/ingestion_service /app/backend/services/ingestion_service
COPY backend/services/nlp_service /app/backend/services/nlp_service
COPY backend/services/copilot_service /app/backend/services/copilot_service

ENV PYTHONPATH=/app

# Phase 13 Batch 9 (AD-2, §20): non-root execution, applied where
# feasible. Affects both configurations (one Dockerfile) -- the
# production-like configuration's lack of any source bind mount avoids
# any UID/permission concern entirely; verified compatible with the
# development configuration's bind-mount + --reload workflow too.
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "backend.services.gateway_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
