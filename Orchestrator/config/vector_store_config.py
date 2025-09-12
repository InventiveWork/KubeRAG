from typing import Dict, Any, Optional
import os
import json
from dataclasses import dataclass, field
from enum import Enum

class VectorStoreType(Enum):
    QDRANT = "qdrant"
    MONGODB = "mongodb"
    CHROMA = "chroma"
    FAISS = "faiss"
    POSTGRESQL = "postgresql"
    PGVECTOR = "pgvector"
    ELASTICSEARCH = "elasticsearch"
    ELASTIC = "elastic"
    NEO4J = "neo4j"
    LANCEDB = "lancedb"
    LANCE = "lance"

@dataclass
class BaseVectorStoreConfig:
    """Base configuration for all vector stores"""
    store_type: str
    dimension: int = 768
    collection_name: str = "documents"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'store_type': self.store_type,
            'dimension': self.dimension,
            'collection_name': self.collection_name
        }

@dataclass
class QdrantConfig(BaseVectorStoreConfig):
    """Qdrant configuration"""
    host: str = "localhost"
    port: int = 6333
    grpc_port: int = 6334
    prefer_grpc: bool = False
    https: bool = False
    api_key: Optional[str] = None
    prefix: Optional[str] = None
    timeout: float = 5.0
    
    def __post_init__(self):
        self.store_type = "qdrant"
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'host': self.host,
            'port': self.port,
            'grpc_port': self.grpc_port,
            'prefer_grpc': self.prefer_grpc,
            'https': self.https,
            'api_key': self.api_key,
            'prefix': self.prefix,
            'timeout': self.timeout
        })
        return base

@dataclass
class MongoDBConfig(BaseVectorStoreConfig):
    """MongoDB Atlas configuration"""
    connection_string: Optional[str] = None
    host: str = "localhost"
    port: int = 27017
    database: str = "vectordb"
    username: Optional[str] = None
    password: Optional[str] = None
    index_name: str = "vector_index"
    
    def __post_init__(self):
        self.store_type = "mongodb"
        if not self.connection_string and self.username and self.password:
            self.connection_string = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'connection_string': self.connection_string,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'password': self.password,
            'index_name': self.index_name
        })
        return base

@dataclass
class ChromaConfig(BaseVectorStoreConfig):
    """ChromaDB configuration"""
    persist_directory: str = "./chroma_db"
    host: Optional[str] = None
    port: Optional[int] = None
    
    def __post_init__(self):
        self.store_type = "chroma"
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'persist_directory': self.persist_directory,
            'host': self.host,
            'port': self.port
        })
        return base

@dataclass
class FAISSConfig(BaseVectorStoreConfig):
    """FAISS configuration"""
    index_path: str = "./faiss_index"
    metadata_path: str = "./faiss_metadata.pkl"
    index_type: str = "FlatL2"  # FlatL2, FlatIP, IVFFlat, HNSW
    nlist: int = 100  # For IVF indices
    M: int = 16  # For HNSW
    efConstruction: int = 200  # For HNSW
    
    def __post_init__(self):
        self.store_type = "faiss"
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'index_path': self.index_path,
            'metadata_path': self.metadata_path,
            'index_type': self.index_type,
            'nlist': self.nlist,
            'M': self.M,
            'efConstruction': self.efConstruction
        })
        return base

@dataclass
class PostgreSQLConfig(BaseVectorStoreConfig):
    """PostgreSQL + pgvector configuration"""
    connection_string: Optional[str] = None
    host: str = "localhost"
    port: int = 5432
    database: str = "vectordb"
    username: str = "postgres"
    password: str = "password"
    table_name: str = "documents"
    
    def __post_init__(self):
        self.store_type = "postgresql"
        if not self.connection_string:
            self.connection_string = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'connection_string': self.connection_string,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.username,
            'password': self.password,
            'table_name': self.table_name
        })
        return base

@dataclass
class ElasticsearchConfig(BaseVectorStoreConfig):
    """Elasticsearch configuration"""
    host: str = "localhost"
    port: int = 9200
    index_name: str = "documents"
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    cloud_id: Optional[str] = None
    use_ssl: bool = False
    verify_certs: bool = True
    
    def __post_init__(self):
        self.store_type = "elasticsearch"
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'host': self.host,
            'port': self.port,
            'index_name': self.index_name,
            'username': self.username,
            'password': self.password,
            'api_key': self.api_key,
            'cloud_id': self.cloud_id,
            'use_ssl': self.use_ssl,
            'verify_certs': self.verify_certs
        })
        return base

@dataclass
class Neo4jConfig(BaseVectorStoreConfig):
    """Neo4j configuration"""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    index_name: str = "document_embeddings"
    
    def __post_init__(self):
        self.store_type = "neo4j"
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'uri': self.uri,
            'username': self.username,
            'password': self.password,
            'database': self.database,
            'index_name': self.index_name
        })
        return base

@dataclass
class LanceDBConfig(BaseVectorStoreConfig):
    """LanceDB configuration"""
    uri: str = "./lancedb"
    table_name: str = "documents"
    metric: str = "cosine"  # cosine, l2, dot
    
    def __post_init__(self):
        self.store_type = "lancedb"
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'uri': self.uri,
            'table_name': self.table_name,
            'metric': self.metric
        })
        return base

class VectorStoreConfigFactory:
    """Factory for creating vector store configurations"""
    
    CONFIG_CLASSES = {
        'qdrant': QdrantConfig,
        'mongodb': MongoDBConfig,
        'chroma': ChromaConfig,
        'faiss': FAISSConfig,
        'postgresql': PostgreSQLConfig,
        'pgvector': PostgreSQLConfig,
        'elasticsearch': ElasticsearchConfig,
        'elastic': ElasticsearchConfig,
        'neo4j': Neo4jConfig,
        'lancedb': LanceDBConfig,
        'lance': LanceDBConfig
    }
    
    @classmethod
    def create_config(cls, store_type: str, **kwargs) -> BaseVectorStoreConfig:
        """Create a configuration instance for the given store type"""
        if store_type not in cls.CONFIG_CLASSES:
            raise ValueError(f"Unknown store type: {store_type}")
        
        config_class = cls.CONFIG_CLASSES[store_type]
        return config_class(store_type=store_type, **kwargs)
    
    @classmethod
    def from_env(cls, store_type: str, prefix: str = "VECTOR_STORE_") -> BaseVectorStoreConfig:
        """Create configuration from environment variables"""
        kwargs = {}
        
        # Common environment variables
        kwargs['dimension'] = int(os.getenv(f"{prefix}DIMENSION", "768"))
        kwargs['collection_name'] = os.getenv(f"{prefix}COLLECTION_NAME", "documents")
        
        # Store-specific environment variables
        if store_type == 'qdrant':
            kwargs.update({
                'host': os.getenv("QDRANT_HOST", "localhost"),
                'port': int(os.getenv("QDRANT_PORT", "6333")),
                'grpc_port': int(os.getenv("QDRANT_GRPC_PORT", "6334")),
                'prefer_grpc': os.getenv("QDRANT_PREFER_GRPC", "false").lower() == "true",
                'api_key': os.getenv("QDRANT_API_KEY"),
                'https': os.getenv("QDRANT_HTTPS", "false").lower() == "true",
                'timeout': float(os.getenv("QDRANT_TIMEOUT", "5.0"))
            })
        elif store_type == 'mongodb':
            kwargs.update({
                'connection_string': os.getenv(f"{prefix}MONGODB_CONNECTION_STRING"),
                'host': os.getenv(f"{prefix}MONGODB_HOST", "localhost"),
                'port': int(os.getenv(f"{prefix}MONGODB_PORT", "27017")),
                'database': os.getenv(f"{prefix}MONGODB_DATABASE", "vectordb"),
                'username': os.getenv(f"{prefix}MONGODB_USERNAME"),
                'password': os.getenv(f"{prefix}MONGODB_PASSWORD")
            })
        elif store_type == 'postgresql':
            kwargs.update({
                'connection_string': os.getenv(f"{prefix}POSTGRESQL_CONNECTION_STRING"),
                'host': os.getenv(f"{prefix}POSTGRESQL_HOST", "localhost"),
                'port': int(os.getenv(f"{prefix}POSTGRESQL_PORT", "5432")),
                'database': os.getenv(f"{prefix}POSTGRESQL_DATABASE", "vectordb"),
                'username': os.getenv(f"{prefix}POSTGRESQL_USERNAME", "postgres"),
                'password': os.getenv(f"{prefix}POSTGRESQL_PASSWORD", "password")
            })
        elif store_type == 'elasticsearch':
            kwargs.update({
                'host': os.getenv(f"{prefix}ELASTICSEARCH_HOST", "localhost"),
                'port': int(os.getenv(f"{prefix}ELASTICSEARCH_PORT", "9200")),
                'username': os.getenv(f"{prefix}ELASTICSEARCH_USERNAME"),
                'password': os.getenv(f"{prefix}ELASTICSEARCH_PASSWORD"),
                'cloud_id': os.getenv(f"{prefix}ELASTICSEARCH_CLOUD_ID"),
                'api_key': os.getenv(f"{prefix}ELASTICSEARCH_API_KEY")
            })
        elif store_type == 'neo4j':
            kwargs.update({
                'uri': os.getenv(f"{prefix}NEO4J_URI", "bolt://localhost:7687"),
                'username': os.getenv(f"{prefix}NEO4J_USERNAME", "neo4j"),
                'password': os.getenv(f"{prefix}NEO4J_PASSWORD", "password"),
                'database': os.getenv(f"{prefix}NEO4J_DATABASE", "neo4j")
            })
        elif store_type in ['faiss']:
            kwargs.update({
                'index_path': os.getenv(f"{prefix}FAISS_INDEX_PATH", "./faiss_index"),
                'metadata_path': os.getenv(f"{prefix}FAISS_METADATA_PATH", "./faiss_metadata.pkl")
            })
        elif store_type == 'chroma':
            kwargs.update({
                'persist_directory': os.getenv(f"{prefix}CHROMA_PERSIST_DIR", "./chroma_db"),
                'host': os.getenv(f"{prefix}CHROMA_HOST"),
                'port': int(os.getenv(f"{prefix}CHROMA_PORT", "8000")) if os.getenv(f"{prefix}CHROMA_PORT") else None
            })
        elif store_type == 'lancedb':
            kwargs.update({
                'uri': os.getenv(f"{prefix}LANCEDB_URI", "./lancedb"),
                'metric': os.getenv(f"{prefix}LANCEDB_METRIC", "cosine")
            })
        
        return cls.create_config(store_type, **kwargs)
    
    @classmethod
    def from_file(cls, config_file: str) -> BaseVectorStoreConfig:
        """Create configuration from JSON file"""
        with open(config_file, 'r') as f:
            config_dict = json.load(f)
        
        store_type = config_dict.pop('store_type')
        return cls.create_config(store_type, **config_dict)
    
    @classmethod
    def get_sample_configs(cls) -> Dict[str, Dict[str, Any]]:
        """Get sample configurations for all supported stores"""
        samples = {}
        for store_type, config_class in cls.CONFIG_CLASSES.items():
            if store_type in ['pgvector', 'elastic', 'lance']:  # Skip aliases
                continue
            try:
                sample_config = config_class()
                samples[store_type] = sample_config.to_dict()
            except Exception as e:
                samples[store_type] = f"Error creating sample: {e}"
        
        return samples