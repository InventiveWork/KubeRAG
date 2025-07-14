from dotenv import load_dotenv
from enum import Enum
from pydantic import BaseModel
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from llama_index.vector_stores.mongodb import MongoDBAtlasVectorSearch
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from llama_index.core import VectorStoreIndex
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import json
from bson.objectid import ObjectId
from bson.json_util import dumps
import time

load_dotenv()


llm = AzureOpenAI(
    model=os.getenv("AZURE_LLM_MODEL"),
    deployment_name=os.getenv("AZURE_LLM_MODEL_DEPLOYMENT"),
    api_key=os.getenv("AZURE_API_KEY"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
    api_version=os.getenv("AZURE_API_VERSION"),
)

# You need to deploy your own embedding model as well as your own chat completion model
# You need to deploy your own embedding model as well as your own chat completion model
embed_model = HuggingFaceEmbedding(
    model_name="jinaai/jina-embeddings-v2-small-en"
)


Settings.llm = llm
Settings.embed_model = embed_model
Settings.chunk_size = 512
Settings.chunk_overlap = 50

mongo_connection_string = "mongodb+srv://{mongousername}:{mongopass}@{mongoserver}"
mongo_connection_string = mongo_connection_string.format(mongousername = os.getenv("MONGO_USERNAME"))
mongo_connection_string = mongo_connection_string.format(mongopass = os.getenv("MONGO_PASSWORD"))
mongo_connection_string = mongo_connection_string.format(mongoserver = os.getenv("MONGO_SERVER"))

database_engine = os.getenv("DATABASE_ENGINE")

if database_engine == "mongodb":
    # Create a new client and connect to the server
    client = MongoClient(mongo_connection_string, server_api=ServerApi('1'))



    # connect to Atlas as a vector store
    store = MongoDBAtlasVectorSearch(
        client,
        db_name=os.getenv("MONGODB_NAME"), # this is the database where you stored your embeddings
        collection_name=os.getenv("MONGODB_COLLECTION"), # this is where your embeddings were stored in 2_load_and_index.py
        vector_index_name=os.getenv("MONGODB_VECTOR_INDEX") # this is the name of the index you created after loading your data
    )

    index = VectorStoreIndex.from_vector_store(store)
elif database_engine == "qdrant":
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    vector_store = QdrantVectorStore(client=client, collection_name=os.getenv("QDRANT_COLLECTION_NAME"))
    index = VectorStoreIndex.from_vector_store(vector_store)

# You are a sales agent capable of generating legal IT Software contract and statement of work based on Scotiabank Contract P65432.

def chat(query):

    if query is not None:
        # query your data!
        query_engine = index.as_query_engine(llm=llm, similarity_top_k=10)
        response = query_engine.query(query)
        return str(response)
    else:
        return ""
 

# while True:
#     user_input = input("Enter your input (or 'quit' to exit): ")
#     if user_input.lower() == "quit":
#         break
#     else:
#         chat(user_input)