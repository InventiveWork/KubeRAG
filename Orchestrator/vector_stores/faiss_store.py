"""
FAISS Vector Store Implementation for KubeRag
"""
import os
import json
import pickle
from typing import List, Dict, Any, Optional
from .base import BaseVectorStore, VectorSearchResult
import logging
import numpy as np

logger = logging.getLogger(__name__)

class FAISSVectorStore(BaseVectorStore):
    """FAISS vector store implementation"""
    
    def initialize(self):
        """Initialize FAISS index"""
        try:
            import faiss
            
            # Configuration
            self.index_path = self.config.get('index_path', '/tmp/faiss_index')
            self.metadata_path = self.config.get('metadata_path', '/tmp/faiss_metadata.json')
            self.dimension = self.config.get('dimension', 768)
            self.index_type = self.config.get('index_type', 'IndexFlatIP')  # Inner Product (cosine for normalized vectors)
            
            # Initialize index
            if os.path.exists(self.index_path):
                # Load existing index
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Loaded existing FAISS index from {self.index_path}")
            else:
                # Create new index
                if self.index_type == 'IndexFlatIP':
                    self.index = faiss.IndexFlatIP(self.dimension)
                elif self.index_type == 'IndexFlatL2':
                    self.index = faiss.IndexFlatL2(self.dimension)
                elif self.index_type == 'IndexIVFFlat':
                    # For larger datasets, use IVF (Inverted File Index)
                    nlist = self.config.get('nlist', 100)  # Number of clusters
                    quantizer = faiss.IndexFlatL2(self.dimension)
                    self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
                elif self.index_type == 'IndexHNSW':
                    # Hierarchical Navigable Small World graphs
                    M = self.config.get('M', 64)  # Number of connections
                    self.index = faiss.IndexHNSWFlat(self.dimension, M)
                else:
                    raise ValueError(f"Unsupported index type: {self.index_type}")
                
                logger.info(f"Created new FAISS index: {self.index_type} with dimension {self.dimension}")
            
            # Load or initialize metadata store
            self.metadata = {}
            self.id_to_index = {}  # Map document IDs to FAISS index positions
            self.index_to_id = {}  # Map FAISS index positions to document IDs
            self.next_index = 0
            
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'r') as f:
                    saved_data = json.load(f)
                    self.metadata = saved_data.get('metadata', {})
                    self.id_to_index = saved_data.get('id_to_index', {})
                    self.index_to_id = {str(v): k for k, v in self.id_to_index.items()}
                    self.next_index = saved_data.get('next_index', 0)
                logger.info(f"Loaded metadata for {len(self.metadata)} vectors")
            
            # Train index if needed (for IVF indices)
            if hasattr(self.index, 'is_trained') and not self.index.is_trained and self.index.ntotal > 0:
                logger.info("Training FAISS index...")
                # For IVF indices, we need training data
                # This should be done when we have enough vectors
                pass
                
        except ImportError:
            raise ImportError("Please install faiss: pip install faiss-cpu (or faiss-gpu for GPU support)")
    
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Add vector to FAISS index"""
        try:
            # Convert to numpy array and normalize if using IndexFlatIP
            vector_np = np.array([vector], dtype=np.float32)
            if self.index_type == 'IndexFlatIP':
                # Normalize for cosine similarity
                faiss.normalize_L2(vector_np)
            
            # Add to index
            self.index.add(vector_np)
            
            # Store metadata
            current_index = self.next_index
            self.id_to_index[str(id)] = current_index
            self.index_to_id[str(current_index)] = str(id)
            self.metadata[str(id)] = payload
            self.next_index += 1
            
            # Save to disk
            self._save_index()
            self._save_metadata()
            
        except Exception as e:
            logger.error(f"Error adding vector to FAISS: {e}")
            raise
    
    def search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Search for similar vectors in FAISS"""
        try:
            if self.index.ntotal == 0:
                return []
            
            # Convert query to numpy array and normalize if needed
            query_np = np.array([query_vector], dtype=np.float32)
            if self.index_type == 'IndexFlatIP':
                faiss.normalize_L2(query_np)
            
            # Search
            scores, indices = self.index.search(query_np, min(limit, self.index.ntotal))
            
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue
                
                doc_id = self.index_to_id.get(str(idx))
                if not doc_id:
                    continue
                
                metadata = self.metadata.get(doc_id, {})
                text = metadata.get('text', '')
                
                # Convert score based on index type
                if self.index_type == 'IndexFlatIP':
                    # Inner product score (higher is better)
                    final_score = float(score)
                elif self.index_type == 'IndexFlatL2':
                    # L2 distance (lower is better), convert to similarity
                    final_score = 1.0 / (1.0 + float(score))
                else:
                    final_score = float(score)
                
                results.append(VectorSearchResult(
                    id=doc_id,
                    text=text,
                    score=final_score,
                    metadata=metadata
                ))
            
            # Sort by score (descending)
            results.sort(key=lambda x: x.score, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error searching in FAISS: {e}")
            raise
    
    def delete(self, id: str):
        """Delete vector from FAISS"""
        try:
            # FAISS doesn't support deletion directly
            # We need to rebuild the index without the deleted vector
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
            # FAISS doesn't support updates directly, so delete and add
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
            
            # Prepare batch data
            vector_data = []
            for v in vectors:
                vector_data.append(v['vector'])
            
            # Convert to numpy array
            vectors_np = np.array(vector_data, dtype=np.float32)
            if self.index_type == 'IndexFlatIP':
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
            return self.index.ntotal
        except Exception as e:
            logger.error(f"Error getting count from FAISS: {e}")
            return 0
    
    def _rebuild_index(self):
        """Rebuild FAISS index without deleted vectors"""
        try:
            # Create new index
            old_index = self.index
            if self.index_type == 'IndexFlatIP':
                self.index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == 'IndexFlatL2':
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
            # Try to get the count
            self.index.ntotal
            return True
        except Exception:
            return False