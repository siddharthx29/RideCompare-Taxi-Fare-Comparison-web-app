FROM python:3.11-slim

WORKDIR /app

COPY ml/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ml /app/ml

# Pre-train models during image build if not present
RUN python -m ml.training.train_pipeline

EXPOSE 5001

CMD ["python", "ml/server.py"]
