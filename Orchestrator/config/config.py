"""
Centralized configuration management for KubeRAG
"""
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class LLMConfig:
    """LLM provider configuration"""
    provider: str = "azure_openai"
    
    # OpenAI Config
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    
    # Azure OpenAI Config
    azure_api_key: Optional[str] = None
    azure_endpoint: Optional[str] = None
    azure_deployment: str = "gpt-4o-mini"
    azure_api_version: str = "2025-01-01-preview"
    azure_embed_deployment: str = "text-embedding-ada-002"
    azure_embed_model: str = "text-embedding-ada-002"

@dataclass
class VectorStoreConfig:
    """Vector store configuration"""
    type: str = "qdrant"
    dimension: int = 768
    collection_name: str = "documents"
    
    # Qdrant specific
    qdrant_host: str = "qdrant-service"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: Optional[str] = None
    qdrant_prefer_grpc: bool = False
    qdrant_https: bool = False
    qdrant_timeout: float = 5.0

@dataclass
class EmbeddingConfig:
    """Embedding configuration"""
    model: str = "all-MiniLM-L6-v2"
    dimension: int = 384

@dataclass
class TextProcessingConfig:
    """Text processing configuration"""
    chunk_size: int = 500
    chunk_overlap: int = 50
    method: str = "words"

class Config:
    """Centralized configuration manager"""
    
    def __init__(self):
        self.llm = self._load_llm_config()
        self.vector_store = self._load_vector_store_config()
        self.embedding = self._load_embedding_config()
        self.text_processing = self._load_text_processing_config()
    
    def _load_llm_config(self) -> LLMConfig:
        """Load LLM configuration from environment"""
        return LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "azure_openai"),
            
            # OpenAI
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            
            # Azure OpenAI
            azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            azure_api_version=os.getenv("AZURE_API_VERSION", "2025-01-01-preview"),
            azure_embed_deployment=os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-ada-002"),
            azure_embed_model=os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-ada-002")
        )
    
    def _load_vector_store_config(self) -> VectorStoreConfig:
        """Load vector store configuration from environment"""
        return VectorStoreConfig(
            type=os.getenv("VECTOR_STORE_TYPE", "qdrant"),
            dimension=int(os.getenv("VECTOR_STORE_DIMENSION", "768")),
            collection_name=os.getenv("VECTOR_STORE_COLLECTION", "documents"),
            
            # Qdrant
            qdrant_host=os.getenv("QDRANT_HOST", "qdrant-service"),
            qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
            qdrant_grpc_port=int(os.getenv("QDRANT_GRPC_PORT", "6334")),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            qdrant_prefer_grpc=os.getenv("QDRANT_PREFER_GRPC", "false").lower() == "true",
            qdrant_https=os.getenv("QDRANT_HTTPS", "false").lower() == "true",
            qdrant_timeout=float(os.getenv("QDRANT_TIMEOUT", "5.0"))
        )
    
    def _load_embedding_config(self) -> EmbeddingConfig:
        """Load embedding configuration from environment"""
        model = os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")
        # Set dimension based on model
        dimension = 384 if "MiniLM" in model else 768
        return EmbeddingConfig(
            model=model,
            dimension=dimension
        )
    
    def _load_text_processing_config(self) -> TextProcessingConfig:
        """Load text processing configuration from environment"""
        return TextProcessingConfig(
            chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
            method=os.getenv("CHUNK_METHOD", "words")
        )
    
    def validate(self) -> Dict[str, str]:
        """Validate configuration and return errors"""
        errors = {}
        
        # Validate LLM config
        if self.llm.provider == "azure_openai":
            if not self.llm.azure_api_key:
                errors["azure_api_key"] = "Azure OpenAI API key is required"
            if not self.llm.azure_endpoint:
                errors["azure_endpoint"] = "Azure OpenAI endpoint is required"
        elif self.llm.provider == "openai":
            if not self.llm.openai_api_key:
                errors["openai_api_key"] = "OpenAI API key is required"
        
        # Validate vector store config
        if self.vector_store.type == "qdrant":
            if not self.vector_store.qdrant_host:
                errors["qdrant_host"] = "Qdrant host is required"
        
        return errors
    
    def to_env_dict(self) -> Dict[str, str]:
        """Convert config to environment variable dictionary"""
        env_vars = {}
        
        # LLM Config
        env_vars["LLM_PROVIDER"] = self.llm.provider
        if self.llm.openai_api_key:
            env_vars["OPENAI_API_KEY"] = self.llm.openai_api_key
        if self.llm.openai_base_url:
            env_vars["OPENAI_BASE_URL"] = self.llm.openai_base_url
        env_vars["OPENAI_MODEL"] = self.llm.openai_model
        
        if self.llm.azure_api_key:
            env_vars["AZURE_OPENAI_API_KEY"] = self.llm.azure_api_key
        if self.llm.azure_endpoint:
            env_vars["AZURE_OPENAI_ENDPOINT"] = self.llm.azure_endpoint
        env_vars["AZURE_OPENAI_DEPLOYMENT"] = self.llm.azure_deployment
        env_vars["AZURE_API_VERSION"] = self.llm.azure_api_version
        env_vars["AZURE_OPENAI_EMBED_DEPLOYMENT"] = self.llm.azure_embed_deployment
        env_vars["AZURE_OPENAI_EMBED_MODEL"] = self.llm.azure_embed_model
        
        # Vector Store Config
        env_vars["VECTOR_STORE_TYPE"] = self.vector_store.type
        env_vars["VECTOR_STORE_DIMENSION"] = str(self.vector_store.dimension)
        env_vars["VECTOR_STORE_COLLECTION"] = self.vector_store.collection_name
        env_vars["QDRANT_HOST"] = self.vector_store.qdrant_host
        env_vars["QDRANT_PORT"] = str(self.vector_store.qdrant_port)
        env_vars["QDRANT_GRPC_PORT"] = str(self.vector_store.qdrant_grpc_port)
        if self.vector_store.qdrant_api_key:
            env_vars["QDRANT_API_KEY"] = self.vector_store.qdrant_api_key
        env_vars["QDRANT_PREFER_GRPC"] = str(self.vector_store.qdrant_prefer_grpc).lower()
        env_vars["QDRANT_HTTPS"] = str(self.vector_store.qdrant_https).lower()
        env_vars["QDRANT_TIMEOUT"] = str(self.vector_store.qdrant_timeout)
        
        # Embedding Config
        env_vars["EMBEDDING_MODEL"] = self.embedding.model
        
        # Text Processing Config
        env_vars["CHUNK_SIZE"] = str(self.text_processing.chunk_size)
        env_vars["CHUNK_OVERLAP"] = str(self.text_processing.chunk_overlap)
        env_vars["CHUNK_METHOD"] = self.text_processing.method
        
        return env_vars

# Global config instance
config = Config()