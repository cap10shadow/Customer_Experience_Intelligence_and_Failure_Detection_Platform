FROM python:3.11-slim

WORKDIR /app

COPY backend/services/copilot_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/shared /app/backend/shared
COPY backend/services/copilot_service /app/backend/services/copilot_service

ENV PYTHONPATH=/app

# Phase 13 Batch 9 (AD-2, §20): non-root execution, applied where
# feasible -- verified compatible with both the development (bind-mount
# + --reload) and production-like configurations.
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "backend.services.copilot_service.app.main:app", "--host", "0.0.0.0", "--port", "8007"]
