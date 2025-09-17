# KubeRAG


<img src="logo.jpeg" alt="KubeRAG Logo" style="width:50%; height:auto;">


### Enterprise-grade Kubernetes-native Retrieval Augmented Generation (RAG) platform for deploying scalable AI solutions on K8s clusters.

KubeRAG provides a comprehensive, production-ready solution for deploying RAG applications on Kubernetes with support for multiple LLM providers and vector databases. It features automatic scaling, monitoring, and seamless integration with existing Kubernetes infrastructure.

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Core Components](#core-components)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Deployment Options](#deployment-options)
- [Advanced Usage](#advanced-usage)
- [Contributing](#contributing)
- [License](#license)

## Features

### 🚀 Core Capabilities
- **Multi-LLM Support**: Seamlessly integrate with Azure OpenAI, OpenAI, Anthropic, Google Gemini, and Ollama
- **Vector Store Flexibility**: Choose from 8 different vector databases including Qdrant, MongoDB, ChromaDB, FAISS, PostgreSQL, Elasticsearch, Neo4j, and LanceDB
- **Production Ready**: Built for enterprise deployments with high availability, auto-scaling, and comprehensive monitoring
- **Document Processing**: Support for PDF, DOCX, Markdown, CSV, and plain text with intelligent chunking
- **Kubernetes Native**: Designed specifically for K8s with proper resource management and service discovery
- **RESTful APIs**: Well-documented REST endpoints for easy integration
- **Embedding Models**: Flexible embedding model support with automatic model downloading

### 🔧 Technical Features
- Horizontal pod autoscaling
- Persistent volume support
- ConfigMap and Secret management
- Ingress controller support
- Health checks and readiness probes
- Service mesh compatibility
- Multi-replica deployments
- Resource quotas and limits

## Architecture

KubeRAG follows a microservices architecture with three main components:

```
┌─────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐    ┌──────────────┐ │
│  │   Ingress    │────▶│  Agent       │───▶│  Pipeline    │ │
│  │  Controller  │     │  Service     │    │  Service     │ │
│  └──────────────┘     └──────────────┘    └──────────────┘ │
│                              │                    │         │
│                              ▼                    ▼         │
│                       ┌──────────────┐    ┌──────────────┐ │
│                       │  LLM         │    │  Embedding   │ │
│                       │  Providers   │    │  Models      │ │
│                       └──────────────┘    └──────────────┘ │
│                              │                    │         │
│                              ▼                    ▼         │
│                       ┌────────────────────────────┐       │
│                       │    Vector Store            │       │
│                       │  (Qdrant/MongoDB/etc)      │       │
│                       └────────────────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Component Overview

1. **Agent Service**: Handles chat interactions, query processing, and response generation
2. **Pipeline Service**: Manages document ingestion, text extraction, chunking, and embedding
3. **Vector Store**: Stores and retrieves document embeddings for similarity search

## Prerequisites

- Kubernetes cluster (v1.19+)
- Helm 3.x
- kubectl configured
- Docker (for building custom images)
- Minimum 4GB RAM per node
- Storage class for persistent volumes (if using FAISS/LanceDB)

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/kuberag.git
cd kuberag
```

### 2. Build Docker Images
```bash
# Build Pipeline Service
cd orchestrator/data_pipeline
docker buildx build . --platform=linux/amd64,linux/arm64 -t your-registry/kuberag-pipeline:v1.0.0
docker push your-registry/kuberag-pipeline:v1.0.0

# Build Agent Service
cd ../Agent
docker buildx build . --platform=linux/amd64,linux/arm64 -t your-registry/kuberag-agent:v1.0.0
docker push your-registry/kuberag-agent:v1.0.0
```

### 3. Configure Values
Create a custom `values.yaml` file:
```yaml
images:
  agent:
    repository: your-registry/kuberag-agent
    tag: v1.0.0
  pipeline:
    repository: your-registry/kuberag-pipeline
    tag: v1.0.0

llm:
  provider: "openai"
  openai:
    apiKey: "your-api-key"

vectorStore:
  type: "qdrant"
  qdrant:
    deploy: true
```

### 4. Deploy with Helm
```bash
helm install kuberag ./KubeRag -f values.yaml
```

### 5. Verify Deployment
```bash
kubectl get pods -l app.kubernetes.io/instance=kuberag
kubectl get svc -l app.kubernetes.io/instance=kuberag
```

## Project Structure

```
KubeRag/
├── orchestrator/
│   ├── Agent/
│   │   ├── app.py              # FastAPI chat service
│   │   ├── agent.py            # Core RAG logic
│   │   ├── llm_providers.py    # LLM integrations
│   │   └── Dockerfile
│   ├── data_pipeline/
│   │   ├── universal_pipeline.py  # Document processing
│   │   ├── vector_store.py       # Vector store interface
│   │   ├── download_model.py     # Embedding model manager
│   │   └── Dockerfile
│   ├── vector_stores/
│   │   ├── base.py             # Abstract base class
│   │   ├── qdrant_store.py     # Qdrant implementation
│   │   ├── mongodb_store.py    # MongoDB implementation
│   │   ├── chroma_store.py     # ChromaDB implementation
│   │   ├── faiss_store.py      # FAISS implementation
│   │   └── ...                 # Other implementations
│   └── config/
│       ├── config.py           # Configuration management
│       └── vector_store_config.py
├── KubeRag/                    # Helm chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── agent-deployment.yaml
│       ├── agent-service.yaml
│       ├── data-pipeline-deployment.yaml
│       ├── configmap.yaml
│       ├── secret.yaml
│       └── ...
└── tests/
    ├── test_e2e.py
    └── conftest.py
```

## Core Components

### Agent Service (orchestrator/Agent/)
The Agent service provides the chat interface and RAG functionality:

- **FastAPI-based REST API** for chat interactions
- **Multi-LLM support** with automatic failover
- **Context-aware response generation** using retrieved documents
- **Session management** for conversation history
- **Health checks** and monitoring endpoints

Key files:
- `app.py`: FastAPI application with chat endpoints
- `agent.py`: Core RAG logic and document retrieval
- `llm_providers.py`: LLM provider factory and integrations

### Pipeline Service (orchestrator/data_pipeline/)
The Pipeline service handles document processing and embedding:

- **Multi-format document support** (PDF, DOCX, MD, CSV, TXT)
- **Intelligent text chunking** with configurable strategies
- **Batch processing** for large document sets
- **Embedding generation** using sentence transformers
- **Vector store management** and indexing

Key files:
- `universal_pipeline.py`: Main pipeline service
- `vector_store.py`: Vector store abstraction layer
- `download_model.py`: Embedding model downloader

### Vector Stores (orchestrator/vector_stores/)
Abstracted vector store implementations supporting:

- **Qdrant**: High-performance vector search
- **MongoDB**: Document store with vector capabilities
- **ChromaDB**: Open-source embedding database
- **FAISS**: Facebook's similarity search library
- **PostgreSQL**: With pgvector extension
- **Elasticsearch**: Full-text and vector search
- **Neo4j**: Graph database with vectors
- **LanceDB**: Modern columnar database

## API Documentation

### Agent Service Endpoints

#### POST /chat
Send a message and receive an AI-generated response with sources.

**Request:**
```json
{
  "message": "What is KubeRAG?",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "response": "KubeRAG is a Kubernetes-native RAG platform...",
  "sources": [
    {
      "id": "doc-123",
      "text": "Relevant document excerpt...",
      "score": 0.95,
      "metadata": {}
    }
  ],
  "session_id": "session-123",
  "total_results": 5
}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "kuberag-chat-agent",
  "vector_store_initialized": true,
  "embedding_model_initialized": true,
  "llm_providers_available": ["azure_openai", "openai"]
}
```

### Pipeline Service Endpoints

#### POST /api/embed
Upload and process a document file.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body:
  - file: Document file (PDF, DOCX, etc.)
  - metadata: JSON string with metadata
  - chunk: Boolean for chunking (default: true)
  - chunk_config: JSON configuration for chunking

**Response:**
```json
{
  "status": "success",
  "message": "File document.pdf processed and indexed",
  "documents_processed": 1,
  "chunks_created": 15,
  "index_size": 1250,
  "vector_store_used": "qdrant"
}
```

#### POST /ingest/text
Process raw text input.

**Request:**
```json
{
  "text": "Your document text here...",
  "metadata": {
    "source": "manual",
    "category": "documentation"
  },
  "chunk": true,
  "id": "optional-document-id"
}
```

#### POST /ingest/batch
Process multiple documents in batch.

**Request:**
```json
{
  "documents": [
    {
      "text": "First document...",
      "metadata": {},
      "chunk": true
    },
    {
      "text": "Second document...",
      "metadata": {},
      "chunk": true
    }
  ]
}
```

#### GET /stats
Get pipeline statistics.

**Response:**
```json
{
  "service": "KubeRAG Universal Data Pipeline",
  "vector_store_type": "qdrant",
  "embedding_model": "all-MiniLM-L12-v2",
  "embedding_dimension": 384,
  "chunk_size": 500,
  "chunk_overlap": 50,
  "index_size": 1250
}
```

## Configuration

### Helm Values Configuration

The `values.yaml` file provides comprehensive configuration options:

```yaml
# LLM Configuration
llm:
  provider: "azure_openai"  # Options: openai, azure_openai, anthropic, gemini, ollama
  azureOpenai:
    deployment: "gpt-4o-mini"
    endpoint: "https://your-endpoint.openai.azure.com"
    apiKey: ""  # Set via secret

# Vector Store Configuration
vectorStore:
  type: "qdrant"  # Options: qdrant, mongodb, chroma, faiss, postgresql, elasticsearch, neo4j, lancedb
  dimension: 384
  collectionName: "documents"

  qdrant:
    host: "qdrant-service"
    port: 6333
    deploy: true  # Deploy Qdrant with the chart

# Embedding Configuration
embedding:
  model: "all-MiniLM-L12-v2"  # Any HuggingFace sentence transformer

# Text Processing
textProcessing:
  chunkSize: 500
  chunkOverlap: 50
  method: "words"  # Options: words, sentences, characters

# Deployment Settings
deployment:
  agent:
    replicas: 2
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"
      limits:
        memory: "2Gi"
        cpu: "1000m"

# Ingress Configuration
ingress:
  enabled: true
  className: "nginx"
  host: "kuberag.example.com"
  tls:
    enabled: true
    secretName: "kuberag-tls"

# Auto-scaling
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

### Environment Variables

Key environment variables for services:

```bash
# Vector Store
VECTOR_STORE_TYPE=qdrant
VECTOR_STORE_DIMENSION=384
VECTOR_STORE_COLLECTION_NAME=documents

# LLM Provider
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com

# Embedding Model
EMBEDDING_MODEL=all-MiniLM-L12-v2

# Text Processing
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

## Deployment Options

### Production Deployment

For production environments:

1. **Use External Secrets**: Store API keys in Kubernetes secrets or external secret managers
2. **Enable TLS**: Configure ingress with TLS certificates
3. **Set Resource Limits**: Define appropriate resource requests and limits
4. **Enable Auto-scaling**: Configure HPA for dynamic scaling
5. **Use Persistent Storage**: For FAISS and LanceDB deployments

Example production values:
```yaml
ingress:
  enabled: true
  className: "nginx"
  host: "rag.yourdomain.com"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  tls:
    enabled: true
    secretName: "kuberag-tls"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20

deployment:
  agent:
    replicas: 3
    resources:
      requests:
        memory: "2Gi"
        cpu: "1000m"
      limits:
        memory: "4Gi"
        cpu: "2000m"

persistence:
  enabled: true
  storageClass: "fast-ssd"
  size: "50Gi"
```

### Development Deployment

For development/testing:

```yaml
service:
  type: "NodePort"

deployment:
  agent:
    replicas: 1
    resources:
      requests:
        memory: "512Mi"
        cpu: "250m"

vectorStore:
  type: "faiss"  # Local vector store
  faiss:
    deploy: true
```

## Advanced Usage

### Custom Embedding Models

To use custom embedding models:

1. Update the embedding model in values.yaml:
```yaml
embedding:
  model: "sentence-transformers/all-mpnet-base-v2"
```

2. The model will be automatically downloaded on first use

### Adding Custom Vector Stores

To add a new vector store:

1. Create a new store class in `orchestrator/vector_stores/`
2. Inherit from `VectorStoreBase`
3. Implement required methods
4. Register in the factory

Example:
```python
class CustomVectorStore(VectorStoreBase):
    def initialize(self):
        # Initialize connection
        pass

    def add(self, id, vector, payload):
        # Add vector
        pass

    def search(self, vector, limit=5):
        # Search vectors
        pass
```

### Monitoring and Observability

KubeRAG supports integration with:
- Prometheus for metrics
- Grafana for visualization
- ELK stack for logging
- Jaeger for distributed tracing

### Scaling Strategies

1. **Horizontal Scaling**: Use HPA for automatic pod scaling
2. **Vertical Scaling**: Adjust resource limits based on load
3. **Vector Store Scaling**: Use distributed vector stores like Qdrant cluster mode
4. **Caching**: Implement Redis for response caching

# Deployment Combinations

KubeRAG supports multiple LLM providers and vector stores. Here are all possible deployment combinations:

## Supported Combinations Matrix

| LLM Provider    | Qdrant | MongoDB | ChromaDB | FAISS | PostgreSQL | Elasticsearch | Neo4j | LanceDB | Total |
|-----------------|--------|---------|----------|-------|------------|---------------|-------|---------|-------|
| Azure OpenAI    | ✅     | ✅      | ✅       | ✅    | ✅         | ✅            | ✅    | ✅      | 8     |
| OpenAI          | ✅     | ✅      | ✅       | ✅    | ✅         | ✅            | ✅    | ✅      | 8     |
| Anthropic       | ✅     | ✅      | ✅       | ✅    | ✅         | ✅            | ✅    | ✅      | 8     |
| Google Gemini   | ✅     | ✅      | ✅       | ✅    | ✅         | ✅            | ✅    | ✅      | 8     |
| Ollama (Local)  | ✅     | ✅      | ✅       | ✅    | ✅         | ✅            | ✅    | ✅      | 8     |
| **Total**       | **5**  | **5**   | **5**    | **5** | **5**      | **5**         | **5** | **5**   | **40** |

## Vector Store Characteristics

- **Qdrant**: High-performance dedicated vector database (Recommended for production)
- **MongoDB**: Document database with vector search capabilities
- **ChromaDB**: Open-source embedding database
- **FAISS**: Facebook's library for efficient similarity search
- **PostgreSQL**: Traditional database with pgvector extension
- **Elasticsearch**: Search engine with vector capabilities
- **Neo4j**: Graph database with vector search
- **LanceDB**: Modern columnar vector database

## LLM Provider Features

- **Azure OpenAI**: Enterprise-grade OpenAI models with Azure security
- **OpenAI**: Direct OpenAI API access
- **Anthropic**: Claude models for advanced reasoning
- **Google Gemini**: Google's multimodal AI models
- **Ollama**: Run local models without external API dependencies

All 40 combinations are fully supported and can be deployed using the KubeRAG Helm chart with appropriate configuration.
