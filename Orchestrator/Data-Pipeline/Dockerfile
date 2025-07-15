# Stage 1: Build the application
FROM python:3.10.15-slim-bookworm as builder
WORKDIR /Data-Pipeline
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Stage 2: Create the final image
FROM python:3.10.15-slim-bookworm
WORKDIR /Data-Pipeline
RUN addgroup -S nonroot && adduser -S nonroot -G nonroot
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY . .
USER nonroot
CMD [ "gunicorn", "--bind", "0.0.0.0:5000", "app:app" ]