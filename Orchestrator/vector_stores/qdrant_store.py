import os
import uuid
from typing import List, Dict, Any
from .base import BaseVectorStore, VectorSearchResult
import logging

logger = logging.getLogger(__name__)

class QdrantVectorStore(BaseVectorStore):
    """Qdrant vector store implementation"""
    
    def initialize(self):
        """Initialize Qdrant client"""
        try:
            import qdrant_client
            from qdrant_client.models import VectorParams, Distance
            
            # Use centralized config with fallbacks
            qdrant_host = self.config.get('host') or os.getenv('QDRANT_HOST', 'localhost')
            qdrant_port = self.config.get('port') or int(os.getenv('QDRANT_PORT', '6333'))
            
            self.url = self.config.get('url') or f'http://{qdrant_host}:{qdrant_port}'
            self.api_key = self.config.get('api_key') or os.getenv('QDRANT_API_KEY')
            self.collection_name = self.config.get('collection') or os.getenv('VECTOR_STORE_COLLECTION', 'documents')
            
            # Initialize client
            logger.info(f"Connecting to Qdrant at {self.url} with collection {self.collection_name}")
            if self.api_key:
                self.client = qdrant_client.QdrantClient(url=self.url, api_key=self.api_key)
                logger.info("Using Qdrant with API key authentication")
            else:
                self.client = qdrant_client.QdrantClient(url=self.url)
                logger.info("Using Qdrant without authentication")
                
            # Test connection
            try:
                collections = self.client.get_collections()
                logger.info(f"Successfully connected to Qdrant. Available collections: {[c.name for c in collections.collections]}")
            except Exception as e:
                logger.error(f"Failed to connect to Qdrant at {self.url}: {e}")
                raise
            
            # Create collection if it doesn't exist
            try:
                self.client.get_collection(self.collection_name)
                logger.info(f"Using existing Qdrant collection: {self.collection_name}")
            except Exception:
                # Collection doesn't exist, create it
                vector_size = self.config.get('dimension', self.config.get('vector_size', 384))  # Check both keys
                distance = self.config.get('distance', 'Cosine')
                
                distance_map = {
                    'Cosine': Distance.COSINE,
                    'Euclidean': Distance.EUCLID,
                    'Dot': Distance.DOT
                }
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=distance_map.get(distance, Distance.COSINE)
                    )
                )
                logger.info(f"Created new Qdrant collection: {self.collection_name}")
                
        except ImportError:
            raise ImportError("Please install qdrant-client: pip install qdrant-client")
    
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Add vector to Qdrant"""
        try:
            from qdrant_client.models import PointStruct
            
            # Convert string ID to UUID for Qdrant compatibility
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, id))
            
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
        except Exception as e:
            logger.error(f"Error adding vector to Qdrant: {e}")
            raise
    
    def search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Search for similar vectors in Qdrant"""
        try:
            from qdrant_client.models import SearchRequest
            
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True
            )
            
            results = []
            for result in search_results:
                results.append(VectorSearchResult(
                    id=str(result.id),
                    text=result.payload.get('text', ''),
                    score=result.score,
                    metadata=result.payload
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching in Qdrant: {e}")
            raise
    
    def delete(self, id: str):
        """Delete vector from Qdrant"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[id]
            )
        except Exception as e:
            logger.error(f"Error deleting vector from Qdrant: {e}")
            raise
    
    def update(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Update vector in Qdrant"""
        # Qdrant doesn't have separate update, use upsert
        self.add(id, vector, payload)
    
    def batch_add(self, vectors: List[Dict[str, Any]]):
        """Add multiple vectors in batch to Qdrant"""
        try:
            from qdrant_client.models import PointStruct
            
            points = []
            for vector_data in vectors:
                # Convert string ID to UUID for Qdrant compatibility
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, vector_data['id']))
                
                point = PointStruct(
                    id=point_id,
                    vector=vector_data['vector'],
                    payload=vector_data['payload']
                )
                points.append(point)
            
            # Batch upsert
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
        except Exception as e:
            logger.error(f"Error batch adding vectors to Qdrant: {e}")
            raise
    
    def count(self) -> int:
        """Get total number of vectors in Qdrant collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Error getting count from Qdrant: {e}")
            return 0