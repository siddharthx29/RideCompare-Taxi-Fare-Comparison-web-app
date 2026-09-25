FROM python:3.11-slim

WORKDIR /app

RUN useradd --system --no-create-home --shell /usr/sbin/nologin appuser

# Copy requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and ml modules
COPY --chown=appuser:appuser backend /app/backend
COPY --chown=appuser:appuser ml /app/ml

USER appuser

# Expose FastAPI backend port
EXPOSE 5000

ENV PORT=5000
ENV ENVIRONMENT=production
ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "5000"]
