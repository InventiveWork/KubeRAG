from neo4j import AsyncGraphDatabase, GraphDatabase
from typing import List, Dict, Any, Optional
from .base import BaseVectorStore, VectorSearchResult
import logging
import asyncio

logger = logging.getLogger(__name__)

class Neo4jVectorStore(BaseVectorStore):
    """Neo4j graph + vector hybrid implementation"""
    
    def __init__(self, **kwargs):
        self.uri = kwargs.get('uri', 'bolt://localhost:7687')
        self.username = kwargs.get('username', 'neo4j')
        self.password = kwargs.get('password', 'password')
        self.database = kwargs.get('database', 'neo4j')
        self.dimension = kwargs.get('dimension', 768)
        self.index_name = kwargs.get('index_name', 'document_embeddings')
        
        self.driver = None
        self.async_driver = None
        super().__init__(**kwargs)
    
    def initialize(self):
        """Initialize Neo4j connection"""
        try:
            # Create sync driver for sync operations
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            
            # Test connection
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            
            # Create vector index
            asyncio.create_task(self._ensure_vector_index())
            
            logger.info("Neo4j vector store initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j vector store: {e}")
            raise
    
    async def _get_async_driver(self):
        """Get or create async driver"""
        if not self.async_driver:
            self.async_driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
        return self.async_driver
    
    async def _ensure_vector_index(self):
        """Ensure vector index exists"""
        driver = await self._get_async_driver()
        
        try:
            async with driver.session(database=self.database) as session:
                # Create vector index for similarity search
                create_index_query = f"""
                CREATE VECTOR INDEX {self.index_name} IF NOT EXISTS
                FOR (d:Document) ON (d.embedding)
                OPTIONS {{
                    indexConfig: {{
                        `vector.dimensions`: {self.dimension},
                        `vector.similarity_function`: 'cosine'
                    }}
                }}
                """
                await session.run(create_index_query)
                
                # Create text index for full-text search
                await session.run("""
                    CREATE FULLTEXT INDEX document_text IF NOT EXISTS
                    FOR (d:Document) ON EACH [d.text]
                """)
                
                logger.info(f"Created Neo4j vector index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to create Neo4j vector index: {e}")
            raise
    
    async def _async_add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Async version of add"""
        driver = await self._get_async_driver()
        
        try:
            async with driver.session(database=self.database) as session:
                # Create or update document node with vector
                query = """
                MERGE (d:Document {id: $id})
                SET d.embedding = $vector,
                    d.text = $text,
                    d.metadata = $metadata,
                    d.created_at = datetime()
                """
                
                await session.run(query, {
                    'id': id,
                    'vector': vector,
                    'text': payload.get('text', ''),
                    'metadata': payload
                })
                
                # Create relationships based on metadata
                await self._create_relationships(session, id, payload)
                
                logger.debug(f"Added document {id} to Neo4j")
        except Exception as e:
            logger.error(f"Failed to add document to Neo4j: {e}")
            raise
    
    async def _create_relationships(self, session, document_id: str, metadata: Dict[str, Any]):
        """Create relationships based on metadata"""
        try:
            # Create category relationships
            if 'category' in metadata:
                category = metadata['category']
                await session.run("""
                    MATCH (d:Document {id: $doc_id})
                    MERGE (c:Category {name: $category})
                    MERGE (d)-[:BELONGS_TO]->(c)
                """, {'doc_id': document_id, 'category': category})
            
            # Create source relationships
            if 'source' in metadata:
                source = metadata['source']
                await session.run("""
                    MATCH (d:Document {id: $doc_id})
                    MERGE (s:Source {name: $source})
                    MERGE (d)-[:FROM_SOURCE]->(s)
                """, {'doc_id': document_id, 'source': source})
            
            # Create author relationships
            if 'author' in metadata:
                author = metadata['author']
                await session.run("""
                    MATCH (d:Document {id: $doc_id})
                    MERGE (a:Author {name: $author})
                    MERGE (d)-[:AUTHORED_BY]->(a)
                """, {'doc_id': document_id, 'author': author})
                
        except Exception as e:
            logger.warning(f"Failed to create relationships for document {document_id}: {e}")
    
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        """Add a vector with payload to Neo4j"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_add(id, vector, payload))
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            raise
    
    async def _async_search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        """Async version of search"""
        driver = await self._get_async_driver()
        
        try:
            async with driver.session(database=self.database) as session:
                # Perform vector similarity search
                query = f"""
                CALL db.index.vector.queryNodes('{self.index_name}', $limit, $query_vector)
                YIELD node, score
                RETURN node.id as id, node.text as text, node.metadata as metadata, score
                ORDER BY score DESC
                """
                
                result = await session.run(query, {
                    'query_vector': query_vector,
                    'limit': limit
                })
                
                results = []
                async for record in result:
                    results.append(VectorSearchResult(
                        id=record['id'],
                        text=record['text'] or '',
                        score=float(record['score']),
                        metadata=record['metadata'] or {}
                    ))
                
                return results
        except Exception as e:
            logger.error(f"Failed to search in Neo4j: {e}")
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
        driver = await self._get_async_driver()
        
        try:
            async with driver.session(database=self.database) as session:
                # Delete document and its relationships
                await session.run("""
                    MATCH (d:Document {id: $id})
                    DETACH DELETE d
                """, {'id': id})
                
                logger.debug(f"Deleted document {id} from Neo4j")
        except Exception as e:
            logger.error(f"Failed to delete document from Neo4j: {e}")
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
        # Update is the same as add with merge logic
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
        driver = await self._get_async_driver()
        
        try:
            async with driver.session(database=self.database) as session:
                result = await session.run("MATCH (d:Document) RETURN count(d) as count")
                record = await result.single()
                return record['count'] if record else 0
        except Exception as e:
            logger.error(f"Failed to count documents in Neo4j: {e}")
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
        """Check if Neo4j vector store is healthy"""
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1")
                result.single()
                return True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False
    
    async def close(self):
        """Close the drivers"""
        if self.async_driver:
            await self.async_driver.close()
        if self.driver:
            self.driver.close()
        logger.info("Neo4j drivers closed")
    
    def search_by_graph(self, query_params: Dict[str, Any], limit: int = 5) -> List[VectorSearchResult]:
        """Search using graph relationships"""
        try:
            with self.driver.session(database=self.database) as session:
                # Build graph query based on parameters
                conditions = []
                params = {}
                
                if 'category' in query_params:
                    conditions.append("(d)-[:BELONGS_TO]->(c:Category {name: $category})")
                    params['category'] = query_params['category']
                
                if 'source' in query_params:
                    conditions.append("(d)-[:FROM_SOURCE]->(s:Source {name: $source})")
                    params['source'] = query_params['source']
                
                if 'author' in query_params:
                    conditions.append("(d)-[:AUTHORED_BY]->(a:Author {name: $author})")
                    params['author'] = query_params['author']
                
                where_clause = " AND ".join(conditions) if conditions else ""
                
                query = f"""
                MATCH (d:Document)
                {f"WHERE {where_clause}" if where_clause else ""}
                RETURN d.id as id, d.text as text, d.metadata as metadata, 1.0 as score
                LIMIT $limit
                """
                
                params['limit'] = limit
                result = session.run(query, params)
                
                results = []
                for record in result:
                    results.append(VectorSearchResult(
                        id=record['id'],
                        text=record['text'] or '',
                        score=float(record['score']),
                        metadata=record['metadata'] or {}
                    ))
                
                return results
        except Exception as e:
            logger.error(f"Failed to search by graph in Neo4j: {e}")
            return []