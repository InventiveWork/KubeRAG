# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask, request, jsonify
import load
import load_mongo
import os
import requests
from bs4 import BeautifulSoup

# Flask constructor takes the name of 
# current module (__name__) as argument.
app = Flask(__name__)

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
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to fetch URL: {e}"}), 400

    soup = BeautifulSoup(response.content, 'html.parser')
    # get text and remove leading/trailing whitespace
    text = soup.get_text(separator=' ', strip=True)

    # Save the scraped text to a file
    filename = url.split("/")[-1] + ".txt"
    with open(os.path.join(app.config['DATA'], filename), 'w') as f:
        f.write(text)

    # Load and index the scraped text
    engineType = os.getenv('VECTOR_STORE', 'mongodb')
    load.load_index(engineType)
    return jsonify({"message": "URL embedded successfully"}), 200

@app.route('/api/embed', methods=['POST'])
def embed():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['DATA'], filename)
        file.save(filepath)

        file_extension = filename.rsplit('.', 1)[1].lower()
        text = extract_text_from_file(filepath, file_extension)

        # Save the extracted text to a file
        with open(filepath, 'w') as f:
            f.write(text)

        # Load and index after upload
        engineType = os.getenv('VECTOR_STORE', 'mongodb')
        load.load_index(engineType)
        return jsonify({"message": "File embedded successfully"}), 200
    
@app.route('/api/testMongo', methods=['GET'])
def upload_mongo():
    load_mongo.load_index()


# main driver function
if __name__ == '__main__':

    # run() method of Flask class runs the application 
    # on the local development server.
    app.run()
