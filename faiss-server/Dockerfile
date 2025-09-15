FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY faiss_server.py .

# Expose port
EXPOSE 8080

# Run the server
CMD ["python", "faiss_server.py"]