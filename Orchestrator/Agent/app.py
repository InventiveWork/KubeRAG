#!/usr/bin/env python3
"""
KubeRAG Chat Agent Service
FastAPI-based chat service that works with all supported vector stores
"""

import os
import logging
import time
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from pathlib import Path

# Import our config system
import sys
sys.path.append('/app')
from config import Config
from vector_stores import get_vector_store
from llm_providers import LLMProviderFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="KubeRAG Chat Agent Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    session_id: Optional[str] = None
    total_results: int = 0

# Global variables
vector_store = None
config = None
embedder = None
llm_providers = {}
pipeline_service_url = None  # Cache the discovered pipeline service URL

def initialize_services():
    """Initialize vector store and embedding services"""
    global vector_store, config, embedder, llm_providers, pipeline_service_url

    logger.info("STARTING initialize_services() function")
    try:
        # Load configuration
        config = Config()
        logger.info(f"Config loaded - vector store type: '{config.vector_store.type}'")
        logger.info(f"Config vector store object: {config.vector_store}")
        logger.info(f"Config vector store attributes: {dir(config.vector_store)}")
        
        # Initialize vector store using the same factory as data pipeline
        # Build configuration based on vector store type
        vector_store_config = {
            'dimension': config.vector_store.dimension,
        }

        # Add vector store specific configuration
        logger.info(f"Vector store type: '{config.vector_store.type}', all config attributes: {dir(config.vector_store)}")
        if config.vector_store.type in ['qdrant']:
            vector_store_config.update({
                'collection_name': config.vector_store.collection_name,
                'host': config.vector_store.qdrant_host,
                'port': config.vector_store.qdrant_port,
                'api_key': config.vector_store.qdrant_api_key,
            })
        elif config.vector_store.type in ['faiss']:
            # FAISS needs shared storage paths for index sharing
            # Access FAISS config directly from environment variables since config object doesn't have these attributes
            faiss_config = {
                'index_path': os.getenv('VECTOR_STORE_FAISS_INDEX_PATH', '/data/faiss_index'),
                'metadata_path': os.getenv('VECTOR_STORE_FAISS_METADATA_PATH', '/data/faiss_metadata.pkl'),
                'index_type': os.getenv('VECTOR_STORE_FAISS_INDEX_TYPE', 'FlatL2'),
            }
            logger.info(f"FAISS configuration: {faiss_config}")
            vector_store_config.update(faiss_config)
        elif config.vector_store.type in ['mongodb']:
            vector_store_config.update({
                'collection_name': config.vector_store.collection_name,
                'host': getattr(config.vector_store, 'mongodb_host', 'localhost'),
                'port': getattr(config.vector_store, 'mongodb_port', 27017),
                'database': getattr(config.vector_store, 'mongodb_database', 'kuberag'),
                'username': getattr(config.vector_store, 'mongodb_username', None),
                'password': getattr(config.vector_store, 'mongodb_password', None),
            })
        elif config.vector_store.type in ['chroma']:
            vector_store_config.update({
                'collection_name': config.vector_store.collection_name,
                'host': os.getenv('VECTOR_STORE_CHROMA_HOST', 'localhost'),
                'port': int(os.getenv('VECTOR_STORE_CHROMA_PORT', '8000')),
            })
        elif config.vector_store.type in ['postgresql', 'pgvector']:
            vector_store_config.update({
                'host': getattr(config.vector_store, 'postgres_host', 'localhost'),
                'port': getattr(config.vector_store, 'postgres_port', 5432),
                'database': getattr(config.vector_store, 'postgres_database', 'kuberag'),
                'username': getattr(config.vector_store, 'postgres_username', 'postgres'),
                'password': getattr(config.vector_store, 'postgres_password', ''),
                'table_name': getattr(config.vector_store, 'postgres_table', 'vectors'),
            })
        elif config.vector_store.type in ['elasticsearch', 'elastic']:
            vector_store_config.update({
                'host': getattr(config.vector_store, 'elasticsearch_host', 'localhost'),
                'port': getattr(config.vector_store, 'elasticsearch_port', 9200),
                'index_name': getattr(config.vector_store, 'elasticsearch_index', 'kuberag-vectors'),
                'username': getattr(config.vector_store, 'elasticsearch_username', None),
                'password': getattr(config.vector_store, 'elasticsearch_password', None),
            })
        elif config.vector_store.type in ['neo4j']:
            vector_store_config.update({
                'uri': getattr(config.vector_store, 'neo4j_uri', 'bolt://localhost:7687'),
                'username': getattr(config.vector_store, 'neo4j_username', 'neo4j'),
                'password': getattr(config.vector_store, 'neo4j_password', 'password'),
                'index_name': getattr(config.vector_store, 'neo4j_index', 'vector-index'),
            })
        elif config.vector_store.type in ['lancedb', 'lance']:
            vector_store_config.update({
                'uri': getattr(config.vector_store, 'lancedb_uri', '/app/data/lancedb'),
                'table_name': getattr(config.vector_store, 'lancedb_table', 'vectors'),
                'host': getattr(config.vector_store, 'lancedb_host', None),
                'port': getattr(config.vector_store, 'lancedb_port', 8080),
                'metric': getattr(config.vector_store, 'lancedb_metric', 'cosine'),
            })

        connect_attempts = int(os.getenv("VECTOR_STORE_CONNECT_RETRIES", "5"))
        connect_backoff = float(os.getenv("VECTOR_STORE_CONNECT_BACKOFF", "2.0"))

        for attempt in range(1, connect_attempts + 1):
            try:
                logger.info(
                    "Initializing vector store (attempt %s/%s)...",
                    attempt,
                    connect_attempts,
                )
                vector_store = get_vector_store(config.vector_store.type, **vector_store_config)
                logger.info(f"Initialized vector store: {config.vector_store.type}")
                break
            except Exception as exc:
                logger.error("Vector store initialization failed: %s", exc)
                if attempt == connect_attempts:
                    raise
                sleep_seconds = connect_backoff * attempt
                logger.warning(
                    "Retrying vector store initialization in %.1f seconds...",
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
        
        # Initialize embedder - try to connect to pipeline service for consistency
        try:
            # Use the same embedding model as the pipeline
            from sentence_transformers import SentenceTransformer

            model_name = config.embedding.model
            packaged_model_path = Path('/app/models') / model_name.replace('/', '_')
            cache_root = Path(os.getenv('TRANSFORMERS_CACHE', '/home/nonroot/.cache/huggingface'))
            cache_root.mkdir(parents=True, exist_ok=True)

            if packaged_model_path.exists():
                embedder = SentenceTransformer(str(packaged_model_path))
            else:
                embedder = SentenceTransformer(model_name, cache_folder=str(cache_root))

            logger.info(f"Initialized embedding model: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to load local embedder: {e}")
            embedder = None

        # Discover pipeline service URL at startup
        pipeline_service_url = os.getenv('PIPELINE_SERVICE_URL')
        if not pipeline_service_url:
            logger.info("Discovering pipeline service...")
            import requests
            # Try common service name patterns
            possible_names = [
                'pipeline-service',
                'data-pipeline-service'
            ]

            # Also try with release name prefix if available
            release_name = os.getenv('HELM_RELEASE_NAME')
            if release_name:
                possible_names.insert(0, f'{release_name}-pipeline-service')

            for service_name in possible_names:
                try:
                    test_url = f'http://{service_name}/health'
                    response = requests.get(test_url, timeout=2)
                    if response.status_code == 200:
                        pipeline_service_url = f'http://{service_name}/api/embed/text'
                        logger.info(f"Discovered pipeline service at: {service_name}")
                        break
                except:
                    continue

            if pipeline_service_url:
                logger.info(f"Pipeline service URL discovered: {pipeline_service_url}")
            else:
                logger.warning("Pipeline service could not be discovered, will retry per request")

        # Initialize LLM providers
        try:
            llm_configs = {
                'azure_openai': {
                    'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
                    'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
                    'deployment': os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o-mini'),
                    'api_version': os.getenv('AZURE_API_VERSION', '2025-01-01-preview')
                },
                'openai': {
                    'api_key': os.getenv('OPENAI_API_KEY'),
                    'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                    'base_url': os.getenv('OPENAI_BASE_URL')
                },
                'anthropic': {
                    'api_key': os.getenv('ANTHROPIC_API_KEY'),
                    'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
                },
                'gemini': {
                    'api_key': os.getenv('GOOGLE_API_KEY'),
                    'model': os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
                },
                'ollama': {
                    'base_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                    'model': os.getenv('OLLAMA_MODEL', 'llama2')
                }
            }
            
            llm_providers = LLMProviderFactory.get_available_providers(llm_configs)
            logger.info(f"Initialized {len(llm_providers)} LLM providers: {list(llm_providers.keys())}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize LLM providers: {e}")
            llm_providers = {}
            
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    initialize_services()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "service": "kuberag-chat-agent",
        "vector_store_initialized": vector_store is not None,
        "embedding_model_initialized": embedder is not None,
        "llm_providers_available": list(llm_providers.keys()) if llm_providers else []
    }
    
    if vector_store:
        try:
            status["vector_store_healthy"] = vector_store.health_check()
        except:
            status["vector_store_healthy"] = False
    
    return status

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint with RAG functionality"""
    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="Vector store not initialized")
        
        message = request.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Generate embedding for the query
        query_embedding = None
        if embedder:
            # Use local embedder
            query_embedding = embedder.encode(message).tolist()
        else:
            # Fallback 1: use pipeline service for embedding
            try:
                # Use cached pipeline service URL or get from environment
                pipeline_url = pipeline_service_url or os.getenv('PIPELINE_SERVICE_URL')

                if not pipeline_url:
                    # If not set, try to use local service discovery
                    # The service should be in the same namespace
                    logger.warning("PIPELINE_SERVICE_URL not set, attempting local service discovery")
                    # Try common patterns - this will work within the same namespace
                    possible_names = [
                        'pipeline-service',
                        'kuberag-pipeline-service',
                        'data-pipeline-service'
                    ]

                    # Try each possible service name
                    for service_name in possible_names:
                        try:
                            test_url = f'http://{service_name}/health'
                            async with httpx.AsyncClient(timeout=2.0) as test_client:
                                test_response = await test_client.get(test_url)
                                if test_response.status_code == 200:
                                    pipeline_url = f'http://{service_name}/api/embed/text'
                                    logger.info(f"Found pipeline service at: {service_name}")
                                    break
                        except:
                            continue

                    if not pipeline_url:
                        # Last resort: construct from environment if possible
                        logger.warning("Could not discover pipeline service")
                        raise Exception("Pipeline service URL not configured and could not be discovered")

                logger.info(f"Using pipeline URL: {pipeline_url}")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    embed_response = await client.post(
                        pipeline_url,
                        json={"text": message}
                    )
                    if embed_response.status_code == 200:
                        embed_data = embed_response.json()
                        query_embedding = embed_data.get("embedding")
            except Exception as e:
                logger.warning(f"Failed to get embedding from pipeline: {e}")
        
        # Fallback 2: try downloading local embedding model on demand
        if not query_embedding:
            try:
                from sentence_transformers import SentenceTransformer
                embedding_model = config.embedding.model if config and config.embedding else 'all-MiniLM-L6-v2'
                
                # Download model to cache directory (same as HuggingFace cache)
                local_embedder = SentenceTransformer(embedding_model, cache_folder='/home/nonroot/.cache/huggingface')
                query_embedding = local_embedder.encode(message).tolist()
                logger.info(f"Generated embedding using local model: {embedding_model}")
            except Exception as e:
                logger.warning(f"Failed to download/load local embedding model: {e}")
        
        # Fallback 3: use Azure OpenAI for embeddings if available
        if not query_embedding and 'azure_openai' in llm_providers:
            try:
                azure_provider = llm_providers['azure_openai']
                if hasattr(azure_provider, 'client'):
                    response = await azure_provider.client.embeddings.create(
                        model="text-embedding-ada-002",
                        input=message
                    )
                    query_embedding = response.data[0].embedding
                    logger.info("Generated embedding using Azure OpenAI")
            except Exception as e:
                logger.warning(f"Failed to get embedding from Azure OpenAI: {e}")
        
        if not query_embedding:
            raise HTTPException(status_code=503, detail="Embedding service not available")
        
        # Search for relevant documents
        search_results = vector_store.search(query_embedding, limit=5)
        
        # Format sources
        sources = []
        context_text = ""
        for result in search_results:
            source = {
                "id": result.id,
                "text": result.text[:300] + "..." if len(result.text) > 300 else result.text,
                "score": result.score,
                "metadata": result.metadata or {}
            }
            sources.append(source)
            context_text += f"{result.text}\n\n"
        
        # Generate response using available LLM or provide search-based response
        response_text = await generate_response(message, context_text, sources)
        
        return ChatResponse(
            response=response_text,
            sources=sources,
            session_id=request.session_id,
            total_results=len(sources)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_response(query: str, context: str, sources: List[Dict]) -> str:
    """Generate a response using available LLM or fallback to search-based response"""
    try:
        # Try to use configured LLM if available
        if config and config.llm:
            response_text = await generate_llm_response(query, context)
            if response_text:
                return response_text
    except Exception as e:
        logger.warning(f"LLM generation failed: {e}")
    
    # Fallback to search-based response
    if sources:
        response_text = f"Based on your query '{query}', I found {len(sources)} relevant documents in the knowledge base:\n\n"
        for i, source in enumerate(sources[:3], 1):
            response_text += f"{i}. {source['text']}\n\n"
        response_text += "This is a search-based response. For full conversational AI capabilities, please configure an LLM provider."
    else:
        response_text = f"I couldn't find any relevant documents for your query '{query}'. The knowledge base might be empty or your query doesn't match the indexed content."
    
    return response_text

async def generate_llm_response(query: str, context: str) -> Optional[str]:
    """Generate response using configured LLM"""
    try:
        if not llm_providers:
            return None
        
        # Create prompt based on whether we have context or not
        if context.strip():
            # RAG prompt with context
            prompt = f"""Based on the following context, please answer the user's question.

Context:
{context}

Question: {query}

Answer:"""
        else:
            # General conversation prompt without context
            prompt = f"""You are a helpful AI assistant. Please answer the user's question.

Question: {query}

Answer:"""
        
        # Try each available LLM provider - prioritize the ones that are actually configured
        # Define preferred order, but only use providers that are actually available
        preferred_order = ['azure_openai', 'openai', 'anthropic', 'gemini', 'ollama']
        available_providers = list(llm_providers.keys())
        
        # Sort available providers by preferred order
        sorted_providers = []
        for provider in preferred_order:
            if provider in available_providers:
                sorted_providers.append(provider)
        
        # Add any other available providers that aren't in the preferred list
        for provider in available_providers:
            if provider not in sorted_providers:
                sorted_providers.append(provider)
        
        logger.info(f"Trying LLM providers in order: {sorted_providers}")
        
        for provider_name in sorted_providers:
            try:
                provider = llm_providers[provider_name]
                response = await provider.generate_response(prompt)
                if response:
                    logger.info(f"Generated response using {provider_name}")
                    return response
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        # If all providers fail
        logger.warning("All LLM providers failed or unavailable")
        return None
        
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return None

@app.get("/api/chat/health")
async def chat_health():
    """Specific health check for chat functionality"""
    try:
        health_status = {
            "chat_service": "operational",
            "vector_store": "connected" if vector_store and vector_store.health_check() else "disconnected",
            "embedding_service": "available" if embedder else "unavailable",
            "llm_providers": list(llm_providers.keys()) if llm_providers else [],
            "supported_vector_stores": ["qdrant", "mongodb", "chroma", "faiss", "postgresql", "elasticsearch", "neo4j", "lancedb"],
            "supported_llm_providers": ["azure_openai", "openai", "anthropic", "gemini", "ollama"]
        }
        
        # Test a simple search if possible
        if vector_store and embedder:
            try:
                test_embedding = embedder.encode("test").tolist()
                test_results = vector_store.search(test_embedding, limit=1)
                health_status["search_test"] = "passed"
            except:
                health_status["search_test"] = "failed"
        
        return health_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
