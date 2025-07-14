# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask, request, jsonify
import load
import load_mongo
import os

# Flask constructor takes the name of 
# current module (__name__) as argument.
app = Flask(__name__)

UPLOAD_FOLDER = '/data'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'json'}

app.config['DATA'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return False
    
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        return False
    
    if file and allowed_file(file.filename):
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Load and index after upload
        engineType = os.getenv('VECTOR_STORE', 'mongodb')
        load.load_index(engineType)
        return True
    
@app.route('/api/testMongo', methods=['GET'])
def upload_mongo():
    load_mongo.load_index()


# main driver function
if __name__ == '__main__':

    # run() method of Flask class runs the application 
    # on the local development server.
    app.run()