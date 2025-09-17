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

    # LanceDB specific
    lancedb_uri: str = "/data/lancedb"
    lancedb_host: Optional[str] = None
    lancedb_port: int = 8080
    lancedb_metric: str = "cosine"
    lancedb_table: str = "documents"

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

def _infer_embedding_dimension(model_name: Optional[str]) -> int:
    """Best-effort dimension inference for sentence-transformer style models."""
    if not model_name:
        return 768

    name = model_name.lower()

    # Common small sentence-transformer families ship 384-d embeddings.
    if "minilm" in name or "e5-small" in name or "mpnet-base-v2" not in name and name.endswith("-v2"):
        return 384

    # Fall back to the standard 768-d size used by most base models.
    return 768


class Config:
    """Centralized configuration manager"""
    
    def __init__(self):
        self.embedding = self._load_embedding_config()
        self.vector_store = self._load_vector_store_config()
        self.llm = self._load_llm_config()
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
        configured_dimension = os.getenv("VECTOR_STORE_DIMENSION")
        inferred_dimension = _infer_embedding_dimension(os.getenv("EMBEDDING_MODEL"))

        if configured_dimension and int(configured_dimension) != inferred_dimension:
            logger.warning(
                "VECTOR_STORE_DIMENSION=%s does not match embedding dimension %s. "
                "Overriding to embedding dimension.",
                configured_dimension,
                inferred_dimension,
            )

        dimension = inferred_dimension if not configured_dimension else int(configured_dimension)
        if dimension != inferred_dimension:
            dimension = inferred_dimension

        collection = os.getenv("VECTOR_STORE_COLLECTION_NAME") or "documents"

        release_name = os.getenv("HELM_RELEASE_NAME")
        default_qdrant_host = (
            os.getenv("QDRANT_HOST")
            or (f"{release_name}-qdrant-service" if release_name else "qdrant-service")
        )
        default_lancedb_host = (
            os.getenv("VECTOR_STORE_LANCEDB_HOST")
            or (f"{release_name}-lancedb-service" if release_name else None)
        )

        return VectorStoreConfig(
            type=os.getenv("VECTOR_STORE_TYPE", "qdrant"),
            dimension=dimension,
            collection_name=collection,
            
            # Qdrant
            qdrant_host=default_qdrant_host,
            qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
            qdrant_grpc_port=int(os.getenv("QDRANT_GRPC_PORT", "6334")),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            qdrant_prefer_grpc=os.getenv("QDRANT_PREFER_GRPC", "false").lower() == "true",
            qdrant_https=os.getenv("QDRANT_HTTPS", "false").lower() == "true",
            qdrant_timeout=float(os.getenv("QDRANT_TIMEOUT", "5.0")),
            lancedb_uri=os.getenv("VECTOR_STORE_LANCEDB_URI", "/data/lancedb"),
            lancedb_host=default_lancedb_host,
            lancedb_port=int(os.getenv("VECTOR_STORE_LANCEDB_PORT", "8080")),
            lancedb_metric=os.getenv("VECTOR_STORE_LANCEDB_METRIC", "cosine"),
            lancedb_table=os.getenv("VECTOR_STORE_LANCEDB_TABLE_NAME", "documents"),
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
        env_vars["VECTOR_STORE_LANCEDB_URI"] = self.vector_store.lancedb_uri
        if self.vector_store.lancedb_host:
            env_vars["VECTOR_STORE_LANCEDB_HOST"] = self.vector_store.lancedb_host
        env_vars["VECTOR_STORE_LANCEDB_PORT"] = str(self.vector_store.lancedb_port)
        env_vars["VECTOR_STORE_LANCEDB_METRIC"] = self.vector_store.lancedb_metric
        env_vars["VECTOR_STORE_LANCEDB_TABLE_NAME"] = self.vector_store.lancedb_table

        # Embedding Config
        env_vars["EMBEDDING_MODEL"] = self.embedding.model

        # Text Processing Config
        env_vars["CHUNK_SIZE"] = str(self.text_processing.chunk_size)
        env_vars["CHUNK_OVERLAP"] = str(self.text_processing.chunk_overlap)
        env_vars["CHUNK_METHOD"] = self.text_processing.method
        
        return env_vars

# Global config instance
config = Config()
