FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY Orchestrator/Agent/requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Copy the application code
COPY Orchestrator/Agent/app.py .
COPY Orchestrator/Agent/llm_providers.py .

# Copy shared modules
COPY Orchestrator/config/ ./config/
COPY Orchestrator/vector_stores/ ./vector_stores/

# Create models directory
RUN mkdir -p /app/models

# Set environment variables
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8082

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8082"]