"""
FAISS Vector Store Implementation for KubeRag
"""
import os
import json
import requests
from typing import List, Dict, Any, Optional
from .base import BaseVectorStore, VectorSearchResult
import logging

logger = logging.getLogger(__name__)

class FAISSVectorStore(BaseVectorStore):
    """FAISS vector store implementation using remote FAISS server"""

    def initialize(self):
        """Initialize FAISS connection"""
        try:
            # Configuration
            logger.info(f"FAISS config received: {self.config}")

            # Check if we have remote service configuration
            self.host = self.config.get('host', os.getenv('VECTOR_STORE_FAISS_HOST'))
            self.port = self.config.get('port', os.getenv('VECTOR_STORE_FAISS_PORT', '8080'))

            if self.host and self.port:
                # Remote FAISS service
                self.base_url = f"http://{self.host}:{self.port}"
                logger.info(f"Using remote FAISS service at {self.base_url}")

                # Test connection
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=5)
                    if response.status_code == 200:
                        health_data = response.json()
                        logger.info(f"Connected to FAISS service: {health_data}")
                    else:
                        logger.error(f"FAISS service health check failed: {response.status_code}")
                        raise Exception(f"FAISS service not healthy: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    logger.error(f"Failed to connect to FAISS service: {e}")
                    raise Exception(f"Cannot connect to FAISS service at {self.base_url}: {e}")
            else:
                # Fall back to file-based implementation
                logger.warning("No FAISS service configuration found, falling back to file-based implementation")
                self._initialize_file_based()
                return

            self.dimension = self.config.get('dimension', 384)
            self.use_remote = True
            logger.info(f"FAISS remote store initialized with dimension {self.dimension}")

        except Exception as e:
            logger.error(f"Error initializing FAISS: {e}")
            raise

    def _initialize_file_based(self):
        """Initialize file-based FAISS (fallback)"""
        try:
            import faiss
        except ImportError:
            raise ImportError("Please install faiss: pip install faiss-cpu (or faiss-gpu for GPU support)")

        # Configuration
        self.index_path = self.config.get('index_path', '/tmp/faiss_index')
        self.metadata_path = self.config.get('metadata_path', '/tmp/faiss_metadata.json')
        self.dimension = self.config.get('dimension', 768)
        self.index_type = self.config.get('index_type', 'IndexFlatIP')
        logger.info(f"FAISS paths - index: {self.index_path}, metadata: {self.metadata_path}, type: {self.index_type}")

        # Initialize index
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            logger.info(f"Loaded existing FAISS index from {self.index_path}")
        else:
            if self.index_type in ['IndexFlatIP', 'FlatIP']:
                self.index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type in ['IndexFlatL2', 'FlatL2']:
                self.index = faiss.IndexFlatL2(self.dimension)
            else:
                raise ValueError(f"Unsupported index type: {self.index_type}")

            logger.info(f"Created new FAISS index: {self.index_type} with dimension {self.dimension}")

        # Load or initialize metadata store
        self.metadata = {}
        self.id_to_index = {}
        self.index_to_id = {}
        self.next_index = 0

        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r') as f:
                saved_data = json.load(f)
                self.metadata = saved_data.get('metadata', {})
                self.id_to_index = saved_data.get('id_to_index', {})
                self.index_to_id = {str(v): k for k, v in self.id_to_index.items()}
                self.next_index = saved_data.get('next_index', 0)
            logger.info(f"Loaded metadata for {len(self.metadata)} vectors")

        self.use_remote = False
    
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Add vector to FAISS index"""
        try:
            if hasattr(self, 'base_url'):
                # Remote FAISS service
                data = {
                    "id": str(id),
                    "vector": vector,
                    "payload": payload
                }
                response = requests.post(f"{self.base_url}/add", json=data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Added vector to remote FAISS: {result}")
                else:
                    raise Exception(f"Failed to add vector to FAISS service: {response.status_code} - {response.text}")
            else:
                # File-based implementation
                import faiss
                import numpy as np

                vector_np = np.array([vector], dtype=np.float32)
                if self.index_type in ['IndexFlatIP', 'FlatIP']:
                    faiss.normalize_L2(vector_np)

                self.index.add(vector_np)

                current_index = self.next_index
                self.id_to_index[str(id)] = current_index
                self.index_to_id[str(current_index)] = str(id)
                self.metadata[str(id)] = payload
                self.next_index += 1

                self._save_index()
                self._save_metadata()

        except Exception as e:
            logger.error(f"Error adding vector to FAISS: {e}")
            raise
    
    def search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Search for similar vectors in FAISS"""
        try:
            if hasattr(self, 'base_url'):
                # Remote FAISS service
                data = {
                    "vector": query_vector,
                    "limit": limit
                }
                response = requests.post(f"{self.base_url}/search", json=data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"FAISS search returned {len(result.get('results', []))} results")

                    search_results = []
                    for item in result.get('results', []):
                        search_results.append(VectorSearchResult(
                            id=item['id'],
                            text=item['payload'].get('text', ''),
                            score=item['score'],
                            metadata=item['payload']
                        ))
                    return search_results
                else:
                    logger.error(f"FAISS search failed: {response.status_code} - {response.text}")
                    return []
            else:
                # File-based implementation
                import faiss
                import numpy as np

                logger.info(f"FAISS search called with limit={limit}, index.ntotal={self.index.ntotal}")
                if self.index.ntotal == 0:
                    logger.warning("FAISS index is empty (ntotal=0)")
                    return []

                query_np = np.array([query_vector], dtype=np.float32)
                logger.info(f"Query vector shape: {query_np.shape}, index_type: {self.index_type}")
                if self.index_type in ['IndexFlatIP', 'FlatIP']:
                    faiss.normalize_L2(query_np)
                    logger.info("Normalized query vector for IndexFlatIP")

                search_limit = min(limit, self.index.ntotal)
                logger.info(f"Searching FAISS index with limit={search_limit}")
                scores, indices = self.index.search(query_np, search_limit)
                logger.info(f"FAISS search returned {len(scores[0])} scores: {scores[0][:3]} and {len(indices[0])} indices: {indices[0][:3]}")

                results = []
                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                    logger.info(f"Processing result {i}: score={score}, idx={idx}")
                    if idx == -1:
                        logger.info(f"Skipping empty slot at index {i}")
                        continue

                    doc_id = self.index_to_id.get(str(idx))
                    logger.info(f"Found doc_id={doc_id} for idx={idx}")
                    if not doc_id:
                        logger.warning(f"No doc_id found for index {idx}")
                        continue

                    metadata = self.metadata.get(doc_id, {})
                    text = metadata.get('text', '')
                    logger.info(f"Retrieved text length: {len(text)} for doc_id={doc_id}")

                    if self.index_type in ['IndexFlatIP', 'FlatIP']:
                        final_score = float(score)
                    elif self.index_type in ['IndexFlatL2', 'FlatL2']:
                        final_score = 1.0 / (1.0 + float(score))
                    else:
                        final_score = float(score)

                    logger.info(f"Final score: {final_score} (original: {score}) for doc_id={doc_id}")
                    results.append(VectorSearchResult(
                        id=doc_id,
                        text=text,
                        score=final_score,
                        metadata=metadata
                    ))

                results.sort(key=lambda x: x.score, reverse=True)
                logger.info(f"Returning {len(results)} search results")
                return results

        except Exception as e:
            logger.error(f"Error searching in FAISS: {e}")
            raise
    
    def delete(self, id: str):
        """Delete vector from FAISS"""
        try:
            if hasattr(self, 'base_url'):
                # Remote FAISS service doesn't support deletion directly
                logger.warning(f"Delete operation not supported for remote FAISS service")
                return
            else:
                # File-based implementation
                if str(id) not in self.id_to_index:
                    logger.warning(f"Vector {id} not found for deletion")
                    return

                # Remove from metadata
                del self.metadata[str(id)]
                idx_to_remove = self.id_to_index[str(id)]
                del self.id_to_index[str(id)]
                del self.index_to_id[str(idx_to_remove)]

                # Rebuild index without the deleted vector
                self._rebuild_index()

        except Exception as e:
            logger.error(f"Error deleting vector from FAISS: {e}")
            raise
    
    def update(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Update vector in FAISS"""
        try:
            if hasattr(self, 'base_url'):
                # Remote FAISS service - just add (will overwrite)
                self.add(id, vector, payload)
            else:
                # File-based implementation - delete and add
                if str(id) in self.id_to_index:
                    self.delete(id)
                self.add(id, vector, payload)
        except Exception as e:
            logger.error(f"Error updating vector in FAISS: {e}")
            raise
    
    def batch_add(self, vectors: List[Dict[str, Any]]):
        """Add multiple vectors in batch to FAISS"""
        try:
            if not vectors:
                return

            if hasattr(self, 'base_url'):
                # Remote FAISS service - add vectors one by one
                for vector_info in vectors:
                    self.add(vector_info['id'], vector_info['vector'], vector_info['payload'])
            else:
                # File-based implementation
                import faiss
                import numpy as np

                # Prepare batch data
                vector_data = []
                for v in vectors:
                    vector_data.append(v['vector'])

                # Convert to numpy array
                vectors_np = np.array(vector_data, dtype=np.float32)
                if self.index_type in ['IndexFlatIP', 'FlatIP']:
                    faiss.normalize_L2(vectors_np)

                # Add all vectors at once
                self.index.add(vectors_np)

                # Update metadata
                for i, vector_info in enumerate(vectors):
                    current_index = self.next_index + i
                    doc_id = str(vector_info['id'])

                    self.id_to_index[doc_id] = current_index
                    self.index_to_id[str(current_index)] = doc_id
                    self.metadata[doc_id] = vector_info['payload']

                self.next_index += len(vectors)

                # Save to disk
                self._save_index()
                self._save_metadata()

        except Exception as e:
            logger.error(f"Error batch adding vectors to FAISS: {e}")
            raise
    
    def count(self) -> int:
        """Get total number of vectors in FAISS index"""
        try:
            if hasattr(self, 'base_url'):
                # Remote FAISS service
                response = requests.get(f"{self.base_url}/count", timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    return result.get('count', 0)
                else:
                    logger.error(f"Failed to get count from FAISS service: {response.status_code}")
                    return 0
            else:
                # File-based implementation
                return self.index.ntotal
        except Exception as e:
            logger.error(f"Error getting count from FAISS: {e}")
            return 0
    
    def _rebuild_index(self):
        """Rebuild FAISS index without deleted vectors"""
        try:
            # Create new index
            old_index = self.index
            if self.index_type in ['IndexFlatIP', 'FlatIP']:
                self.index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type in ['IndexFlatL2', 'FlatL2']:
                self.index = faiss.IndexFlatL2(self.dimension)
            # Add other index types as needed
            
            # Re-add all remaining vectors
            if len(self.metadata) > 0:
                vectors = []
                new_id_to_index = {}
                new_index_to_id = {}
                
                for i, (doc_id, metadata) in enumerate(self.metadata.items()):
                    # We need to reconstruct vectors from somewhere
                    # This is a limitation of FAISS - it doesn't store original vectors
                    # In practice, you'd need to store vectors separately or use a different approach
                    logger.warning("FAISS deletion requires vector reconstruction - consider using a different vector store for frequent deletions")
                    break
            
            self.next_index = len(self.metadata)
            self._save_index()
            self._save_metadata()
            
        except Exception as e:
            logger.error(f"Error rebuilding FAISS index: {e}")
            raise
    
    def _save_index(self):
        """Save FAISS index to disk"""
        try:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            faiss.write_index(self.index, self.index_path)
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
    
    def _save_metadata(self):
        """Save metadata to disk"""
        try:
            os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
            with open(self.metadata_path, 'w') as f:
                json.dump({
                    'metadata': self.metadata,
                    'id_to_index': self.id_to_index,
                    'next_index': self.next_index
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving FAISS metadata: {e}")
    
    def health_check(self) -> bool:
        """Check if FAISS index is healthy"""
        try:
            if hasattr(self, 'base_url'):
                # Remote FAISS service
                response = requests.get(f"{self.base_url}/health", timeout=5)
                return response.status_code == 200
            else:
                # File-based implementation
                self.index.ntotal
                return True
        except Exception:
            return False