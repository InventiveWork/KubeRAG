FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY lancedb_server.py ./

ENV LANCEDB_PATH=/data/lancedb \
    LANCEDB_TABLE=documents \
    LANCEDB_DIMENSION=768 \
    LANCEDB_METRIC=cosine

EXPOSE 8080

CMD ["uvicorn", "lancedb_server:app", "--host", "0.0.0.0", "--port", "8080"]
