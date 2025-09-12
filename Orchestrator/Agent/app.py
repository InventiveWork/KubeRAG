#!/usr/bin/env python3
"""
KubeRAG Chat Agent Service
FastAPI-based chat service that works with all supported vector stores
"""

import os
import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

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

def initialize_services():
    """Initialize vector store and embedding services"""
    global vector_store, config, embedder, llm_providers
    
    try:
        # Load configuration
        config = Config()
        
        # Initialize vector store using the same factory as data pipeline
        vector_store_config = {
            'dimension': config.vector_store.dimension,
            'collection_name': config.vector_store.collection_name,
            'host': config.vector_store.qdrant_host,
            'port': config.vector_store.qdrant_port,
            'api_key': config.vector_store.qdrant_api_key,
        }
        
        vector_store = get_vector_store(config.vector_store.type, **vector_store_config)
        logger.info(f"Initialized vector store: {config.vector_store.type}")
        
        # Initialize embedder - try to connect to pipeline service for consistency
        try:
            # Use the same embedding model as the pipeline
            from sentence_transformers import SentenceTransformer
            model_path = f"/app/models/{config.embedding.model}"
            embedder = SentenceTransformer(model_path)
            logger.info(f"Initialized local embedding model: {config.embedding.model}")
        except Exception as e:
            logger.warning(f"Failed to load local embedder: {e}")
            embedder = None
        
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
                async with httpx.AsyncClient(timeout=10.0) as client:
                    embed_response = await client.post(
                        "http://kuberag-pipeline-service.kuberag.svc.cluster.local/api/embed/text",
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
        if not context.strip() or not llm_providers:
            return None
        
        # Simple prompt template
        prompt = f"""Based on the following context, please answer the user's question.

Context:
{context}

Question: {query}

Answer:"""
        
        # Try each available LLM provider in order of preference
        provider_order = ['azure_openai', 'openai', 'anthropic', 'gemini', 'ollama']
        
        for provider_name in provider_order:
            if provider_name in llm_providers:
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