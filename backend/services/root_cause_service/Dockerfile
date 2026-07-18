FROM python:3.11-slim

WORKDIR /app

COPY backend/services/root_cause_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/shared /app/backend/shared
COPY backend/services/root_cause_service /app/backend/services/root_cause_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.services.root_cause_service.app.main:app", "--host", "0.0.0.0", "--port", "8004"]
