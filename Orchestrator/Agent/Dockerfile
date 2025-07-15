# Stage 1: Build the application
FROM python:3.12.8-slim as builder
WORKDIR /Agent
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Stage 2: Create the final image
FROM python:3.12.8-slim
WORKDIR /Agent
RUN addgroup -S nonroot && adduser -S nonroot -G nonroot
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY . .
USER nonroot
CMD [ "gunicorn", "--bind", "0.0.0.0:5000", "app:app" ]