# Stage 1: Build the application
FROM python:3.12.8-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
COPY Orchestrator/data_pipeline/requirements.txt requirements.txt
RUN pip3 install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Download the model during the build
COPY Orchestrator/data_pipeline/download_model.py .
RUN python download_model.py

# Stage 2: Create the final image
FROM python:3.12.8-slim
WORKDIR /app
RUN groupadd --system nonroot && useradd --system --create-home --gid nonroot nonroot
RUN mkdir -p /data && chown nonroot:nonroot /data
USER nonroot
# Copy the pre-downloaded model from the builder stage
COPY --from=builder /app/models /app/models
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY Orchestrator/data_pipeline/ .
COPY Orchestrator/vector_stores/ ./vector_stores/
COPY Orchestrator/config/ ./config/
CMD [ "python", "-m", "uvicorn", "universal_pipeline:app", "--host", "0.0.0.0", "--port", "8001" ]