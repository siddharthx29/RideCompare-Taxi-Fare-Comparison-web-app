FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and ml modules
COPY backend /app/backend
COPY ml /app/ml

# Expose FastAPI backend port
EXPOSE 5000

ENV PORT=5000
ENV ENVIRONMENT=production
ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "5000"]
