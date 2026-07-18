FROM python:3.11-slim

WORKDIR /app

COPY backend/services/ingestion_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini /app/alembic.ini
COPY backend/shared /app/backend/shared
COPY backend/services/ingestion_service /app/backend/services/ingestion_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.services.ingestion_service.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
