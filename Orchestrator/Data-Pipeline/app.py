import logging
import structlog
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel
import load
import load_mongo
import os
import requests
from bs4 import BeautifulSoup
import uvicorn
from .security import get_api_key

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Configure OpenTelemetry
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)
tracer = trace.get_tracer(__name__)

# Configure structured logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
log = structlog.get_logger()

app = FastAPI()

# Instrument FastAPI and requests
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

UPLOAD_FOLDER = '/data'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'json'}

class EmbedUrlRequest(BaseModel):
    url: str

class EmbedResponse(BaseModel):
    message: str

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(filepath, file_extension):
    try:
        if file_extension == 'txt':
            with open(filepath, 'r') as f:
                return f.read()
        elif file_extension == 'pdf':
            import pypdf
            text = ""
            with open(filepath, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text()
            return text
        elif file_extension == 'docx':
            import docx2txt
            return docx2txt.process(filepath)
        elif file_extension == 'json':
            import json
            with open(filepath, 'r') as f:
                data = json.load(f)
                return json.dumps(data)
    except Exception as e:
        log.error("Error extracting text from file", error=e)
        raise HTTPException(status_code=400, detail=f"Error extracting text from file: {e}")
    return ""

import re

@app.post("/api/embed_url", response_model=EmbedResponse, dependencies=[Depends(get_api_key)])
def embed_url(request: EmbedUrlRequest):
    log.info("Received embed URL request", url=request.url)
    if not request.url:
        log.error("URL is required")
        raise HTTPException(status_code=400, detail="URL is required")

    # URL validation
    if not re.match(r'^https?://', request.url):
        log.error("Invalid URL scheme", url=request.url)
        raise HTTPException(status_code=400, detail="Invalid URL scheme. Only HTTP and HTTPS are allowed.")

    try:
        response = requests.get(request.url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.error("Failed to fetch URL", error=e)
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    soup = BeautifulSoup(response.content, 'html.parser')
    # get text and remove leading/trailing whitespace
    text = soup.get_text(separator=' ', strip=True)

    # Save the scraped text to a file
    filename = request.url.split("/")[-1] + ".txt"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'w') as f:
        f.write(text)
    log.info("Saved scraped text to file", filepath=filepath)

    # Load and index the scraped text
    engineType = os.getenv('VECTOR_STORE', 'mongodb')
    load.load_index(engineType)
    log.info("URL embedded successfully", url=request.url)
    return EmbedResponse(message="URL embedded successfully")

@app.post("/api/embed", response_model=EmbedResponse, dependencies=[Depends(get_api_key)])
def embed(file: UploadFile = File(...)):
    log.info("Received embed file request")
    if not file:
        log.error("No file part in request")
        raise HTTPException(status_code=400, detail="No file part in request")
    
    if file.filename == '':
        log.error("No selected file")
        raise HTTPException(status_code=400, detail="No selected file")
    
    if allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, "wb") as buffer:
            buffer.write(file.file.read())
        log.info("Saved uploaded file", filepath=filepath)

        file_extension = filename.rsplit('.', 1)[1].lower()
        text = extract_text_from_file(filepath, file_extension)

        # Save the extracted text to a file
        with open(filepath, 'w') as f:
            f.write(text)
        log.info("Saved extracted text to file", filepath=filepath)

        # Load and index after upload
        engineType = os.getenv('VECTOR_STORE', 'mongodb')
        load.load_index(engineType)
        log.info("File embedded successfully", filename=filename)
        return EmbedResponse(message="File embedded successfully")
    else:
        log.error("File type not allowed", filename=file.filename)
        raise HTTPException(status_code=400, detail="File type not allowed")

@app.get('/api/testMongo')
def upload_mongo_endpoint():
    load_mongo.load_index()
    return {"message": "Mongo test complete"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
