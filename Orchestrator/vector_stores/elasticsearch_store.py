import asyncio
from elasticsearch import AsyncElasticsearch, Elasticsearch
from typing import List, Dict, Any, Optional
from .base import BaseVectorStore, VectorSearchResult
import logging

logger = logging.getLogger(__name__)

class ElasticsearchVectorStore(BaseVectorStore):
    """Elasticsearch dense vector implementation"""
    
    def __init__(self, **kwargs):
        self.host = kwargs.get('host', 'localhost')
        self.port = kwargs.get('port', 9200)
        self.index_name = kwargs.get('index_name', 'documents')
        self.dimension = kwargs.get('dimension', 768)
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.api_key = kwargs.get('api_key')
        self.cloud_id = kwargs.get('cloud_id')
        self.use_ssl = kwargs.get('use_ssl', False)
        self.verify_certs = kwargs.get('verify_certs', True)
        
        # Connection configuration
        self.connection_config = {
            'hosts': [f"{self.host}:{self.port}"],
            'use_ssl': self.use_ssl,
            'verify_certs': self.verify_certs
        }
        
        if self.cloud_id:
            self.connection_config['cloud_id'] = self.cloud_id
        elif self.username and self.password:
            self.connection_config['basic_auth'] = (self.username, self.password)
        elif self.api_key:
            self.connection_config['api_key'] = self.api_key
        
        self.es_client = None
        self.async_client = None
        super().__init__(**kwargs)
    
    def initialize(self):
        """Initialize Elasticsearch connection"""
        try:
            # Create sync client for sync operations
            self.es_client = Elasticsearch(**self.connection_config)
            
            # Test connection
            if not self.es_client.ping():
                raise Exception("Cannot connect to Elasticsearch")
            
            # Create index if it doesn't exist
            asyncio.create_task(self._ensure_index_exists())
            
            logger.info("Elasticsearch vector store initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch vector store: {e}")
            raise
    
    async def _get_async_client(self):
        """Get or create async client"""
        if not self.async_client:
            self.async_client = AsyncElasticsearch(**self.connection_config)
        return self.async_client
    
    async def _ensure_index_exists(self):
        """Ensure the vector index exists"""
        client = await self._get_async_client()
        
        if not await client.indices.exists(index=self.index_name):
            # Create index with dense vector mapping
            mapping = {
                "mappings": {
                    "properties": {
                        "vector": {
                            "type": "dense_vector",
                            "dims": self.dimension,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "text": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "metadata": {
                            "type": "object",
                            "enabled": True
                        },
                        "created_at": {
                            "type": "date"
                        }
                    }
                },
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                }
            }
            
            await client.indices.create(index=self.index_name, body=mapping)
            logger.info(f"Created Elasticsearch index: {self.index_name}")
    
    async def _async_add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Async version of add"""
        client = await self._get_async_client()
        
        try:
            document = {
                "vector": vector,
                "text": payload.get('text', ''),
                "metadata": payload,
                "created_at": "now"
            }
            
            await client.index(
                index=self.index_name,
                id=id,
                body=document
            )
            
            logger.debug(f"Added document {id} to Elasticsearch")
        except Exception as e:
            logger.error(f"Failed to add document to Elasticsearch: {e}")
            raise
    
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Add a vector with payload to Elasticsearch"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_add(id, vector, payload))
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            raise
    
    async def _async_search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Async version of search"""
        client = await self._get_async_client()
        
        try:
            # Perform vector similarity search
            search_query = {
                "knn": {
                    "field": "vector",
                    "query_vector": query_vector,
                    "k": limit,
                    "num_candidates": limit * 10  # Number of candidates to consider
                },
                "_source": ["text", "metadata"]
            }
            
            response = await client.search(
                index=self.index_name,
                body=search_query,
                size=limit
            )
            
            results = []
            for hit in response['hits']['hits']:
                results.append(VectorSearchResult(
                    id=hit['_id'],
                    text=hit['_source'].get('text', ''),
                    score=hit['_score'],
                    metadata=hit['_source'].get('metadata', {})
                ))
            
            return results
        except Exception as e:
            logger.error(f"Failed to search in Elasticsearch: {e}")
            return []
    
    def search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Search for similar vectors using cosine similarity"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._async_search(query_vector, limit))
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return []
    
    async def _async_delete(self, id: str):
        """Async version of delete"""
        client = await self._get_async_client()
        
        try:
            await client.delete(index=self.index_name, id=id)
            logger.debug(f"Deleted document {id} from Elasticsearch")
        except Exception as e:
            if "not_found" not in str(e).lower():
                logger.error(f"Failed to delete document from Elasticsearch: {e}")
                raise
    
    def delete(self, id: str):
        """Delete a document by ID"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_delete(id))
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise
    
    async def _async_update(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Async version of update"""
        client = await self._get_async_client()
        
        try:
            document = {
                "vector": vector,
                "text": payload.get('text', ''),
                "metadata": payload,
                "created_at": "now"
            }
            
            await client.update(
                index=self.index_name,
                id=id,
                body={"doc": document, "doc_as_upsert": True}
            )
            
            logger.debug(f"Updated document {id} in Elasticsearch")
        except Exception as e:
            logger.error(f"Failed to update document in Elasticsearch: {e}")
            raise
    
    def update(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Update a vector and its payload"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_update(id, vector, payload))
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            raise
    
    async def _async_count(self) -> int:
        """Async version of count"""
        client = await self._get_async_client()
        
        try:
            response = await client.count(index=self.index_name)
            return response['count']
        except Exception as e:
            logger.error(f"Failed to count documents in Elasticsearch: {e}")
            return 0
    
    def count(self) -> int:
        """Get total number of documents"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._async_count())
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0
    
    def health_check(self) -> bool:
        """Check if Elasticsearch vector store is healthy"""
        try:
            if self.es_client and self.es_client.ping():
                return True
            return False
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return False
    
    async def close(self):
        """Close the async client"""
        if self.async_client:
            await self.async_client.close()
            logger.info("Elasticsearch async client closed")
    
    def batch_add(self, vectors: List[Dict[str, Any]]):
        """Add multiple vectors in batch using bulk API"""
        try:
            actions = []
            for vector_data in vectors:
                action = {
                    "_index": self.index_name,
                    "_id": vector_data['id'],
                    "_source": {
                        "vector": vector_data['vector'],
                        "text": vector_data['payload'].get('text', ''),
                        "metadata": vector_data['payload'],
                        "created_at": "now"
                    }
                }
                actions.append(action)
            
            from elasticsearch.helpers import bulk
            bulk(self.es_client, actions, index=self.index_name)
            
            logger.info(f"Bulk added {len(vectors)} documents to Elasticsearch")
        except Exception as e:
            logger.error(f"Failed to bulk add documents: {e}")
            raise