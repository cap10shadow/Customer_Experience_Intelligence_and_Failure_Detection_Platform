FROM python:3.11-slim

WORKDIR /app

COPY backend/services/recommendation_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/shared /app/backend/shared
COPY backend/services/recommendation_service /app/backend/services/recommendation_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.services.recommendation_service.app.main:app", "--host", "0.0.0.0", "--port", "8006"]
