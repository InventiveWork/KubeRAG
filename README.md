# KubeRAG


<img src="logo.jpeg" alt="Alt Text" style="width:50%; height:auto;">


### A simple helm chart automating deployment of a retrieval augmented generation (RAG) solution on K8s Clusters.


# Architecture 


# Getting started 

Project consist of 2 folder Orchestrator and KubeRag

Orchestator is the main folder for two Application or Agent 

1 - Data Pipeline is responsible for ingestion and embedding the data 

in order to build the image start by running the docker build command 
```shell
docker buildx build . --platform=linux/amd64,linux/arm64 -t <your tag>
```


2 - Second portion is your agent:
you can use one of the sample applications or you can build your own 

you can build the docker image by running the following command 

```shell
docker buildx build . --platform=linux/amd64,linux/arm64 -t <your tag>
```


You can then install your Helm chart 
ensure you have a Kubernetes cluster set up and ready.

run following command to install the helm chart 

```shell
helm install my-release KubeRag-0.0.4 -f myvalues.yaml
```

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
