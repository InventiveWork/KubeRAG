import lancedb
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from .base import BaseVectorStore, VectorSearchResult
import logging
import os
import tempfile
import uuid

logger = logging.getLogger(__name__)

class LanceDBVectorStore(BaseVectorStore):
    """LanceDB implementation"""
    
    def __init__(self, **kwargs):
        self.uri = kwargs.get('uri', tempfile.mkdtemp())  # Default to temp directory
        self.table_name = kwargs.get('table_name', 'documents')
        self.dimension = kwargs.get('dimension', 768)
        self.metric = kwargs.get('metric', 'cosine')
        
        self.db = None
        self.table = None
        super().__init__(**kwargs)
    
    def initialize(self):
        """Initialize LanceDB connection"""
        try:
            # Connect to LanceDB
            self.db = lancedb.connect(self.uri)
            
            # Try to open existing table or create new one
            try:
                self.table = self.db.open_table(self.table_name)
                logger.info(f"Opened existing LanceDB table: {self.table_name}")
            except Exception:
                # Create new table with schema
                self._create_table()
                logger.info(f"Created new LanceDB table: {self.table_name}")
            
            logger.info("LanceDB vector store initialized")
        except Exception as e:
            logger.error(f"Failed to initialize LanceDB vector store: {e}")
            raise
    
    def _create_table(self):
        """Create a new table with proper schema"""
        # Create initial data with proper schema
        initial_data = pd.DataFrame({
            'id': [str(uuid.uuid4())],
            'vector': [np.zeros(self.dimension).tolist()],
            'text': [''],
            'metadata': ['{}']
        })
        
        self.table = self.db.create_table(self.table_name, initial_data, mode="overwrite")
        
        # Create vector index for efficient similarity search
        self.table.create_index(
            "vector",
            index_type="ivf_pq",
            metric=self.metric,
            num_partitions=1,  # Start with 1 partition for small datasets
            num_sub_vectors=4
        )
        
        # Remove the initial dummy record
        self.table.delete("id = '" + initial_data['id'].iloc[0] + "'")
    
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Add a vector with payload to LanceDB"""
        try:
            # Prepare data
            data = pd.DataFrame({
                'id': [id],
                'vector': [vector],
                'text': [payload.get('text', '')],
                'metadata': [str(payload)]  # Store as string for simplicity
            })
            
            # Check if document already exists
            try:
                existing = self.table.search().where(f"id = '{id}'").limit(1).to_pandas()
                if len(existing) > 0:
                    # Update existing document
                    self.table.delete(f"id = '{id}'")
            except Exception:
                pass  # Document doesn't exist, which is fine
            
            # Add the document
            self.table.add(data)
            
            logger.debug(f"Added document {id} to LanceDB")
        except Exception as e:
            logger.error(f"Failed to add document to LanceDB: {e}")
            raise
    
    def search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Search for similar vectors"""
        try:
            if not self.table:
                return []
            
            # Perform vector similarity search
            results = (self.table
                      .search(query_vector)
                      .metric(self.metric)
                      .limit(limit)
                      .to_pandas())
            
            search_results = []
            for _, row in results.iterrows():
                try:
                    # Parse metadata (stored as string)
                    metadata = eval(row['metadata']) if row['metadata'] else {}
                except Exception:
                    metadata = {}
                
                search_results.append(VectorSearchResult(
                    id=row['id'],
                    text=row['text'],
                    score=1.0 - row['_distance'],  # Convert distance to similarity score
                    metadata=metadata
                ))
            
            return search_results
        except Exception as e:
            logger.error(f"Failed to search in LanceDB: {e}")
            return []
    
    def delete(self, id: str):
        """Delete a document by ID"""
        try:
            self.table.delete(f"id = '{id}'")
            logger.debug(f"Deleted document {id} from LanceDB")
        except Exception as e:
            logger.error(f"Failed to delete document from LanceDB: {e}")
            raise
    
    def update(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Update a vector and its payload"""
        try:
            # Delete existing and add new (LanceDB doesn't have direct update)
            self.delete(id)
            self.add(id, vector, payload)
            logger.debug(f"Updated document {id} in LanceDB")
        except Exception as e:
            logger.error(f"Failed to update document in LanceDB: {e}")
            raise
    
    def count(self) -> int:
        """Get total number of documents"""
        try:
            if not self.table:
                return 0
            
            # Count all rows
            result = self.table.search().limit(1000000).to_pandas()  # Large limit to get all
            return len(result)
        except Exception as e:
            logger.error(f"Failed to count documents in LanceDB: {e}")
            return 0
    
    def health_check(self) -> bool:
        """Check if LanceDB vector store is healthy"""
        try:
            if not self.table:
                return False
            
            # Try a simple search operation
            self.table.search(np.zeros(self.dimension).tolist()).limit(1).to_pandas()
            return True
        except Exception as e:
            logger.error(f"LanceDB health check failed: {e}")
            return False
    
    def batch_add(self, vectors: List[Dict[str, Any]]):
        """Add multiple vectors in batch"""
        try:
            if not vectors:
                return
            
            # Prepare batch data
            data = []
            for vector_data in vectors:
                data.append({
                    'id': vector_data['id'],
                    'vector': vector_data['vector'],
                    'text': vector_data['payload'].get('text', ''),
                    'metadata': str(vector_data['payload'])
                })
            
            df = pd.DataFrame(data)
            
            # Remove existing documents with same IDs
            for vector_data in vectors:
                try:
                    self.table.delete(f"id = '{vector_data['id']}'")
                except Exception:
                    pass  # Document doesn't exist
            
            # Add all documents
            self.table.add(df)
            
            logger.info(f"Batch added {len(vectors)} documents to LanceDB")
        except Exception as e:
            logger.error(f"Failed to batch add documents to LanceDB: {e}")
            raise
    
    def optimize(self):
        """Optimize the table (compact and rebuild indexes)"""
        try:
            # Compact the table
            self.table.compact_files()
            
            # Rebuild vector index if needed
            if self.count() > 100:  # Only rebuild index if we have enough data
                self.table.create_index(
                    "vector",
                    index_type="ivf_pq",
                    metric=self.metric,
                    num_partitions=max(1, self.count() // 1000),
                    num_sub_vectors=min(64, self.dimension // 8),
                    replace=True
                )
            
            logger.info("LanceDB table optimized")
        except Exception as e:
            logger.warning(f"Failed to optimize LanceDB table: {e}")
    
    def list_tables(self) -> List[str]:
        """List all tables in the database"""
        try:
            return self.db.table_names()
        except Exception as e:
            logger.error(f"Failed to list tables in LanceDB: {e}")
            return []
    
    def drop_table(self):
        """Drop the current table"""
        try:
            self.db.drop_table(self.table_name)
            self.table = None
            logger.info(f"Dropped LanceDB table: {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to drop LanceDB table: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get table statistics"""
        try:
            return {
                'table_name': self.table_name,
                'count': self.count(),
                'dimension': self.dimension,
                'metric': self.metric,
                'uri': self.uri,
                'size_mb': os.path.getsize(self.uri) / (1024 * 1024) if os.path.exists(self.uri) else 0
            }
        except Exception as e:
            logger.error(f"Failed to get LanceDB stats: {e}")
            return {}
    
    def close(self):
        """Close the database connection"""
        try:
            # LanceDB doesn't require explicit closing
            self.db = None
            self.table = None
            logger.info("LanceDB connection closed")
        except Exception as e:
            logger.warning(f"Error closing LanceDB: {e}")
            pass