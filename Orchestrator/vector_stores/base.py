from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class VectorSearchResult:
    """Represents a vector search result"""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = None

class BaseVectorStore(ABC):
    """Base class for all vector store implementations"""
    
    def __init__(self, **kwargs):
        self.config = kwargs
        self.initialize()
    
    @abstractmethod
    def initialize(self):
        """Initialize the vector store connection"""
        pass
    
    @abstractmethod
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Add a vector with payload to the store"""
        pass
    
    @abstractmethod
    def search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    def delete(self, id: str):
        """Delete a vector by ID"""
        pass
    
    @abstractmethod
    def update(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Update a vector and its payload"""
        pass
    
    def batch_add(self, vectors: List[Dict[str, Any]]):
        """Add multiple vectors in batch"""
        for vector_data in vectors:
            self.add(
                id=vector_data['id'],
                vector=vector_data['vector'],
                payload=vector_data['payload']
            )
    
    def count(self) -> int:
        """Get total number of vectors"""
        raise NotImplementedError("Count method not implemented")
    
    def health_check(self) -> bool:
        """Check if vector store is healthy"""
        try:
            try:
                count = self.count()
                if isinstance(count, int):
                    return True
            except NotImplementedError:
                pass

            dimension = self.config.get('dimension', 384)
            self.search([0.0] * dimension, limit=1)
            return True
        except Exception:
            return False
