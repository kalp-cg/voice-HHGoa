FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend backend
COPY frontend frontend
COPY ingestion ingestion
COPY retrieval retrieval
COPY scripts scripts
COPY data/samples data/samples

RUN chmod +x scripts/deploy_start.sh

EXPOSE 7860
CMD ["./scripts/deploy_start.sh"]
