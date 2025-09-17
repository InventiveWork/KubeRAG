FROM python:3.9-slim as builder

WORKDIR /app

COPY Orchestrator/Agent/requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

ARG EMBEDDING_MODEL=all-MiniLM-L6-v2
ENV EMBEDDING_MODEL=${EMBEDDING_MODEL}
ENV MODEL_CACHE_DIR=/app/models
RUN python - <<'PY'
import os
from sentence_transformers import SentenceTransformer

model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
cache_dir = os.getenv('MODEL_CACHE_DIR', '/app/models')
save_dir = os.path.join(cache_dir, model_name.replace('/', '_'))
os.makedirs(cache_dir, exist_ok=True)
os.makedirs(save_dir, exist_ok=True)
model = SentenceTransformer(model_name, cache_folder=cache_dir)
model.save(save_dir)
PY

FROM python:3.9-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder --chown=nonroot:nonroot /app/models /app/models

COPY Orchestrator/Agent/app.py .
COPY Orchestrator/Agent/llm_providers.py .
COPY Orchestrator/config/ ./config/
COPY Orchestrator/vector_stores/ ./vector_stores/

ENV PYTHONPATH=/app

EXPOSE 8082

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8082"]
