import os
from typing import List, Dict, Any
from .base import BaseVectorStore, VectorSearchResult
import logging

logger = logging.getLogger(__name__)

class MongoDBVectorStore(BaseVectorStore):
    """MongoDB Atlas vector store implementation"""
    
    def initialize(self):
        """Initialize MongoDB connection"""
        try:
            from pymongo import MongoClient
            from pymongo.server_api import ServerApi
            
            self.connection_string = self.config.get('connection_string') or os.getenv('MONGODB_URI')
            self.database_name = self.config.get('database') or os.getenv('MONGODB_DATABASE', 'kuberag')
            self.collection_name = (
                self.config.get('collection_name')
                or os.getenv('VECTOR_STORE_COLLECTION_NAME')
                or 'vectors'
            )
            self.index_name = self.config.get('index_name') or os.getenv('MONGODB_VECTOR_INDEX', 'vector_index')
            
            if not self.connection_string:
                raise ValueError("MongoDB connection string not provided")
            
            # Initialize client
            self.client = MongoClient(self.connection_string, server_api=ServerApi('1'))
            self.database = self.client[self.database_name]
            self.collection = self.database[self.collection_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB Atlas: {self.database_name}.{self.collection_name}")
            
        except ImportError:
            raise ImportError("Please install pymongo: pip install pymongo")
    
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Add vector to MongoDB"""
        try:
            document = {
                '_id': id,
                'vector': vector,
                'text': payload.get('text', ''),
                'metadata': payload,
                'timestamp': payload.get('processed_at')
            }
            
            # Upsert document
            self.collection.replace_one(
                {'_id': id},
                document,
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error adding vector to MongoDB: {e}")
            raise
    
    def search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Search for similar vectors using MongoDB Atlas Vector Search"""
        try:
            # MongoDB Atlas Vector Search aggregation pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.index_name,
                        "path": "vector",
                        "queryVector": query_vector,
                        "numCandidates": limit * 4,  # Oversample for better recall
                        "limit": limit
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "text": 1,
                        "metadata": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]
            
            results = []
            for result in self.collection.aggregate(pipeline):
                results.append(VectorSearchResult(
                    id=str(result['_id']),
                    text=result.get('text', ''),
                    score=result.get('score', 0.0),
                    metadata=result.get('metadata', {})
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching in MongoDB: {e}")
            # Fallback to simple search without vector search
            return self._fallback_search(query_vector, limit)
    
    def _fallback_search(self, query_vector: List[float], limit: int) -> List[VectorSearchResult]:
        """Fallback search without vector search index"""
        try:
            # Simple text-based search as fallback
            results = []
            documents = self.collection.find().limit(limit)
            
            for doc in documents:
                results.append(VectorSearchResult(
                    id=str(doc['_id']),
                    text=doc.get('text', ''),
                    score=0.0,  # No similarity score available
                    metadata=doc.get('metadata', {})
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
            return []
    
    def delete(self, id: str):
        """Delete vector from MongoDB"""
        try:
            self.collection.delete_one({'_id': id})
        except Exception as e:
            logger.error(f"Error deleting vector from MongoDB: {e}")
            raise
    
    def update(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Update vector in MongoDB"""
        # MongoDB update is same as add (upsert)
        self.add(id, vector, payload)
    
    def batch_add(self, vectors: List[Dict[str, Any]]):
        """Add multiple vectors in batch to MongoDB"""
        try:
            documents = []
            for vector_data in vectors:
                document = {
                    '_id': vector_data['id'],
                    'vector': vector_data['vector'],
                    'text': vector_data['payload'].get('text', ''),
                    'metadata': vector_data['payload'],
                    'timestamp': vector_data['payload'].get('processed_at')
                }
                documents.append(document)
            
            # Batch insert with upsert behavior
            operations = []
            from pymongo import ReplaceOne
            
            for doc in documents:
                operations.append(
                    ReplaceOne({'_id': doc['_id']}, doc, upsert=True)
                )
            
            if operations:
                self.collection.bulk_write(operations)
            
        except Exception as e:
            logger.error(f"Error batch adding vectors to MongoDB: {e}")
            raise
    
    def count(self) -> int:
        """Get total number of vectors in MongoDB collection"""
        try:
            return self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Error getting count from MongoDB: {e}")
            return 0
    
    def create_vector_index(self, vector_dimensions: int = 1536):
        """Create vector search index in MongoDB Atlas"""
        try:
            # This would typically be done through Atlas UI or Atlas CLI
            # For programmatic creation, you'd need to use the Atlas Admin API
            index_definition = {
                "fields": [
                    {
                        "path": "vector",
                        "type": "vector",
                        "numDimensions": vector_dimensions,
                        "similarity": "cosine"
                    }
                ]
            }
            
            logger.info(f"Vector index definition created. Apply this in Atlas: {index_definition}")
            
            # Note: Atlas vector search indexes must be created through the Atlas UI or API
            # This is just for reference
            
        except Exception as e:
            logger.error(f"Error creating vector index: {e}")
            raise
