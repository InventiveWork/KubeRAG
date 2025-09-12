import asyncio
import asyncpg
import json
import numpy as np
from typing import List, Dict, Any, Optional
from .base import BaseVectorStore, VectorSearchResult
import logging

logger = logging.getLogger(__name__)

class PostgreSQLVectorStore(BaseVectorStore):
    """PostgreSQL + pgvector implementation"""
    
    def __init__(self, **kwargs):
        self.connection_string = kwargs.get('connection_string')
        self.host = kwargs.get('host', 'localhost')
        self.port = kwargs.get('port', 5432)
        self.database = kwargs.get('database', 'vectordb')
        self.user = kwargs.get('user', 'postgres')
        self.password = kwargs.get('password', 'password')
        self.table_name = kwargs.get('table_name', 'documents')
        self.dimension = kwargs.get('dimension', 768)
        self.pool = None
        super().__init__(**kwargs)
    
    def initialize(self):
        """Initialize PostgreSQL connection pool"""
        try:
            if not self.connection_string:
                self.connection_string = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            
            # Create connection pool in async context
            asyncio.create_task(self._create_pool())
            logger.info("PostgreSQL vector store initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL vector store: {e}")
            raise
    
    async def _create_pool(self):
        """Create async connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10
            )
            await self._ensure_table_exists()
            logger.info("PostgreSQL connection pool created")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL pool: {e}")
            raise
    
    async def _ensure_table_exists(self):
        """Ensure the vector table exists with pgvector extension"""
        async with self.pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create table with vector column
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id VARCHAR PRIMARY KEY,
                vector vector({self.dimension}),
                text TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
            await conn.execute(create_table_sql)
            
            # Create vector index for faster similarity search
            index_sql = f"""
            CREATE INDEX IF NOT EXISTS {self.table_name}_vector_idx 
            ON {self.table_name} 
            USING ivfflat (vector vector_cosine_ops) 
            WITH (lists = 100);
            """
            await conn.execute(index_sql)
    
    async def _async_add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Async version of add"""
        if not self.pool:
            await self._create_pool()
        
        try:
            async with self.pool.acquire() as conn:
                # Convert vector to PostgreSQL vector format
                vector_str = '[' + ','.join(map(str, vector)) + ']'
                
                # Insert or update document
                await conn.execute(
                    f"""
                    INSERT INTO {self.table_name} (id, vector, text, metadata)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO UPDATE SET
                        vector = EXCLUDED.vector,
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        created_at = NOW()
                    """,
                    id, vector_str, payload.get('text', ''), json.dumps(payload)
                )
                logger.debug(f"Added document {id} to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to add document to PostgreSQL: {e}")
            raise
    
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Add a vector with payload to PostgreSQL"""
        try:
            # Run async operation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_add(id, vector, payload))
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            raise
    
    async def _async_search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Async version of search"""
        if not self.pool:
            await self._create_pool()
        
        try:
            async with self.pool.acquire() as conn:
                # Convert query vector to PostgreSQL format
                vector_str = '[' + ','.join(map(str, query_vector)) + ']'
                
                # Perform similarity search using cosine distance
                rows = await conn.fetch(
                    f"""
                    SELECT id, text, metadata, 1 - (vector <=> $1::vector) as score
                    FROM {self.table_name}
                    ORDER BY vector <=> $1::vector
                    LIMIT $2
                    """,
                    vector_str, limit
                )
                
                results = []
                for row in rows:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    results.append(VectorSearchResult(
                        id=row['id'],
                        text=row['text'],
                        score=float(row['score']),
                        metadata=metadata
                    ))
                
                return results
        except Exception as e:
            logger.error(f"Failed to search in PostgreSQL: {e}")
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
        if not self.pool:
            await self._create_pool()
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"DELETE FROM {self.table_name} WHERE id = $1", id)
                logger.debug(f"Deleted document {id} from PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to delete document from PostgreSQL: {e}")
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
        # Update is the same as add with conflict resolution
        await self._async_add(id, vector, payload)
    
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
        if not self.pool:
            await self._create_pool()
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(f"SELECT COUNT(*) FROM {self.table_name}")
                return result
        except Exception as e:
            logger.error(f"Failed to count documents in PostgreSQL: {e}")
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
        """Check if PostgreSQL vector store is healthy"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            count = loop.run_until_complete(self._async_count())
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False
    
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")