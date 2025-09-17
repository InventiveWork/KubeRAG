"""
ChromaDB Vector Store Implementation for KubeRag
"""
import os
import uuid
from typing import List, Dict, Any, Optional
from .base import BaseVectorStore, VectorSearchResult
import logging

logger = logging.getLogger(__name__)

class ChromaVectorStore(BaseVectorStore):
    """ChromaDB vector store implementation"""
    
    def initialize(self):
        """Initialize ChromaDB client"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Configuration
            self.collection_name = (
                self.config.get('collection_name')
                or os.getenv('VECTOR_STORE_COLLECTION_NAME')
                or 'kuberag_documents'
            )
            self.persist_directory = self.config.get('persist_directory', '/tmp/chroma_db')
            self.host = self.config.get('host')
            self.port = self.config.get('port', 8000)

            if not self.host:
                release_name = os.getenv('HELM_RELEASE_NAME')
                if release_name:
                    self.host = f"{release_name}-chromadb-service"

            if not self.host:
                self.host = 'localhost'
            
            # Initialize client based on configuration
            logger.info(f"ChromaDB config: host={self.host}, port={self.port}, in_memory={self.config.get('in_memory', False)}, persistent={self.config.get('persistent', True)}")

            if self.config.get('in_memory', False):
                # In-memory database
                logger.info("Using in-memory ChromaDB client")
                self.client = chromadb.Client()
            elif self.host and self.host not in ['localhost', '127.0.0.1'] and self.port:
                # Remote ChromaDB server
                logger.info(f"Connecting to remote ChromaDB at {self.host}:{self.port}")
                self.client = chromadb.HttpClient(host=self.host, port=self.port)
            elif self.config.get('persistent', True):
                # Persistent local database
                logger.info(f"Using persistent ChromaDB client at {self.persist_directory}")
                self.client = chromadb.PersistentClient(path=self.persist_directory)
            else:
                # Remote ChromaDB server
                logger.info(f"Using remote ChromaDB client at {self.host}:{self.port}")
                self.client = chromadb.HttpClient(host=self.host, port=self.port)
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"Using existing Chroma collection: {self.collection_name}")
            except Exception:
                # Collection doesn't exist, create it
                metadata = {"hnsw:space": "cosine"}  # Use cosine distance
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata=metadata
                )
                logger.info(f"Created new Chroma collection: {self.collection_name}")
                
        except ImportError:
            raise ImportError("Please install chromadb: pip install chromadb")
    
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Add vector to ChromaDB"""
        try:
            # ChromaDB requires documents (text), metadatas, and ids
            # The text field is extracted from payload
            document = payload.get('text', '')
            
            # Clean metadata (ChromaDB doesn't accept None values)
            metadata = {k: v for k, v in payload.items() if v is not None}
            
            self.collection.add(
                ids=[str(id)],
                embeddings=[vector],
                documents=[document],
                metadatas=[metadata]
            )
            
        except Exception as e:
            logger.error(f"Error adding vector to ChromaDB: {e}")
            raise
    
    def search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Search for similar vectors in ChromaDB"""
        try:
            # Handle ChromaDB HNSW index error by checking collection size first
            try:
                # Get collection count to ensure it's initialized
                count = self.collection.count()
                if count == 0:
                    logger.warning("ChromaDB collection is empty")
                    return []
            except Exception as e:
                logger.warning(f"ChromaDB collection check failed: {e}")
                return []

            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=min(limit, count) if count > 0 else 1,
                include=['documents', 'metadatas', 'distances']
            )
            
            search_results = []
            if results['ids'] and len(results['ids']) > 0:
                ids = results['ids'][0]
                documents = results['documents'][0] if results['documents'] else []
                metadatas = results['metadatas'][0] if results['metadatas'] else []
                distances = results['distances'][0] if results['distances'] else []
                
                for i, doc_id in enumerate(ids):
                    # Convert distance to similarity score (ChromaDB returns distances)
                    # For cosine distance, similarity = 1 - distance
                    distance = distances[i] if i < len(distances) else 1.0
                    score = max(0, 1 - distance)  # Ensure non-negative score
                    
                    document = documents[i] if i < len(documents) else ''
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    
                    search_results.append(VectorSearchResult(
                        id=str(doc_id),
                        text=document,
                        score=score,
                        metadata=metadata
                    ))
            
            return search_results

        except Exception as e:
            error_msg = str(e)
            # Handle the specific HNSW error
            if "hnsw segment reader" in error_msg.lower() or "nothing found on disk" in error_msg.lower():
                logger.warning(f"ChromaDB HNSW index error, returning empty results: {e}")
                return []
            logger.error(f"Error searching in ChromaDB: {e}")
            raise
    
    def delete(self, id: str):
        """Delete vector from ChromaDB"""
        try:
            self.collection.delete(ids=[str(id)])
        except Exception as e:
            logger.error(f"Error deleting vector from ChromaDB: {e}")
            raise
    
    def update(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Update vector in ChromaDB"""
        try:
            # ChromaDB doesn't have a direct update, so delete and add
            self.delete(id)
            self.add(id, vector, payload)
        except Exception as e:
            logger.error(f"Error updating vector in ChromaDB: {e}")
            raise
    
    def batch_add(self, vectors: List[Dict[str, Any]]):
        """Add multiple vectors in batch to ChromaDB"""
        try:
            if not vectors:
                return
            
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for vector_data in vectors:
                ids.append(str(vector_data['id']))
                embeddings.append(vector_data['vector'])
                
                payload = vector_data['payload']
                documents.append(payload.get('text', ''))
                
                # Clean metadata
                metadata = {k: v for k, v in payload.items() if v is not None}
                metadatas.append(metadata)
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
        except Exception as e:
            logger.error(f"Error batch adding vectors to ChromaDB: {e}")
            raise
    
    def count(self) -> int:
        """Get total number of vectors in ChromaDB collection"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Error getting count from ChromaDB: {e}")
            return 0
    
    def health_check(self) -> bool:
        """Check if ChromaDB is healthy"""
        try:
            # Try to get collection info
            self.collection.count()
            return True
        except Exception:
            return False
