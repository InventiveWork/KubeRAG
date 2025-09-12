# Legacy vector store implementation using LlamaIndex
# This file is kept for backward compatibility with existing workflows
# For new implementations, use the ../vector_stores module

from abc import ABC, abstractmethod
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore as LlamaQdrantStore
from llama_index.vector_stores.mongodb import MongoDBAtlasVectorSearch
from llama_index.core import StorageContext
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import qdrant_client
import os

class VectorStore(ABC):
    @abstractmethod
    def load_index(self, **kwargs):
        pass

class QdrantVectorStore(VectorStore):
    def load_index(self, **kwargs):
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        DATA_PATH = os.path.join(ROOT_DIR, 'data')

        client = qdrant_client.QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        vector_store = LlamaQdrantStore(client=client, collection_name=os.getenv("QDRANT_COLLECTION_NAME"))
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        if os.path.exists(DATA_PATH):
            for filename in os.listdir(DATA_PATH):
                if os.path.isfile(os.path.join(DATA_PATH, filename)):
                    documents = SimpleDirectoryReader(input_files=[os.path.join(DATA_PATH, filename)]).load_data()
                    for doc in documents:
                        doc.doc_id = filename
                    VectorStoreIndex.from_documents(documents, storage_context=storage_context)

        return True

class MongoDBVectorStore(VectorStore):
    def load_index(self, **kwargs):
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        DATA_PATH = os.path.join(ROOT_DIR, 'data')

        client = MongoClient(os.getenv("MONGODB_URI"), server_api=ServerApi('1'))

        store = MongoDBAtlasVectorSearch(
            client,
            db_name=os.getenv('MONGODB_DATABASE'),
            collection_name=os.getenv('MONGODB_VECTORS'),
            index_name=os.getenv('MONGODB_VECTOR_INDEX')
        )
        storage_context = StorageContext.from_defaults(vector_store=store)

        if os.path.exists(DATA_PATH):
            for filename in os.listdir(DATA_PATH):
                if os.path.isfile(os.path.join(DATA_PATH, filename)):
                    documents = SimpleDirectoryReader(input_files=[os.path.join(DATA_PATH, filename)]).load_data()
                    for doc in documents:
                        doc.doc_id = filename
                    VectorStoreIndex.from_documents(
                        documents, storage_context=storage_context,
                        show_progress=True,
                    )
        return True

def get_vector_store(name):
    """Legacy factory function - use ../vector_stores module for new code"""
    if name == "qdrant":
        return QdrantVectorStore()
    elif name == "mongodb":
        return MongoDBVectorStore()
    else:
        raise ValueError(f"Unknown vector store: {name}")
