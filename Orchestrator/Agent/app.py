import logging
import structlog
from fastapi import FastAPI, Depends
from pydantic import BaseModel
import agent
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
agent_instance = None

@app.on_event("startup")
async def startup_event():
    global agent_instance
    agent_instance = agent.get_agent()

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

class ChatRequest(BaseModel):
    input: str

class ChatResponse(BaseModel):
    output: str

from fastapi import HTTPException

@app.post("/api/chat", response_model=ChatResponse, dependencies=[Depends(get_api_key)])
def chat_endpoint(request: ChatRequest):
    global agent_instance
    log.info("Received chat request", query=request.input)
    try:
        response = agent_instance.chat(request.input)
        log.info("Sending chat response", response=response)
        return ChatResponse(output=response)
    except Exception as e:
        log.error("Error during chat", error=e)
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)