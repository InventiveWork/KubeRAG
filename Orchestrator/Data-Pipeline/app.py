import logging
import structlog
from flask import Flask, request, jsonify
import load
import load_mongo
import os
import requests
from bs4 import BeautifulSoup

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
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

# Flask constructor takes the name of
# current module (__name__) as argument.
app = Flask(__name__)

from prometheus_flask_exporter import PrometheusMetrics

# Instrument Flask and requests
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
metrics = PrometheusMetrics(app)

UPLOAD_FOLDER = '/data'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'json'}

app.config['DATA'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(filepath, file_extension):
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
    return ""

@app.route('/api/embed_url', methods=['POST'])
def embed_url():
    url = request.get_json().get('url')
    log.info("Received embed URL request", url=url)
    if not url:
        log.error("URL is required")
        return jsonify({"error": "URL is required"}), 400

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.error("Failed to fetch URL", error=e)
        return jsonify({"error": f"Failed to fetch URL: {e}"}), 400

    soup = BeautifulSoup(response.content, 'html.parser')
    # get text and remove leading/trailing whitespace
    text = soup.get_text(separator=' ', strip=True)

    # Save the scraped text to a file
    filename = url.split("/")[-1] + ".txt"
    filepath = os.path.join(app.config['DATA'], filename)
    with open(filepath, 'w') as f:
        f.write(text)
    log.info("Saved scraped text to file", filepath=filepath)

    # Load and index the scraped text
    engineType = os.getenv('VECTOR_STORE', 'mongodb')
    load.load_index(engineType)
    log.info("URL embedded successfully", url=url)
    return jsonify({"message": "URL embedded successfully"}), 200

@app.route('/api/embed', methods=['POST'])
def embed():
    log.info("Received embed file request")
    if 'file' not in request.files:
        log.error("No file part in request")
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        log.error("No selected file")
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['DATA'], filename)
        file.save(filepath)
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
        return jsonify({"message": "File embedded successfully"}), 200
    
@app.route('/api/testMongo', methods=['GET'])
def upload_mongo():
    load_mongo.load_index()


# main driver function
if __name__ == '__main__':

    # run() method of Flask class runs the application 
    # on the local development server.
    app.run()
