#!/bin/bash

# KubeRAG Batch Configuration Generator
# Generates Helm values for all 40 supported combinations

set -e

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Output directory
OUTPUT_DIR="kuberag-configurations"

# Arrays of providers and stores
declare -a LLM_PROVIDERS=("azure_openai" "openai" "anthropic" "gemini" "ollama")
declare -a VECTOR_STORES=("qdrant" "mongodb" "chroma" "faiss" "postgresql" "elasticsearch" "neo4j" "lancedb")

# Create output directory
mkdir -p $OUTPUT_DIR

echo -e "${CYAN}KubeRAG Batch Configuration Generator${NC}"
echo -e "${CYAN}=====================================  =${NC}\n"
echo -e "Generating configurations for all 40 combinations...\n"

# Function to generate configuration for a specific combination
generate_combination() {
    local llm=$1
    local vector=$2
    local index=$3
    local filename="${OUTPUT_DIR}/kuberag-${llm}-${vector}.yaml"

    cat > $filename << EOF
# KubeRAG Configuration #$index
# LLM Provider: $llm
# Vector Store: $vector
# Generated: $(date)

namespace: kuberag

global:
  embeddings:
    model: "all-MiniLM-L6-v2"
    dimension: 384
  chunking:
    size: 500
    overlap: 50

# LLM Provider Configuration
llm:
  provider: "$llm"
EOF

    # Add LLM specific defaults
    case $llm in
        "azure_openai")
            cat >> $filename << EOF
  azure_openai:
    enabled: true
    endpoint: "\${AZURE_OPENAI_ENDPOINT}"
    apiKey: "\${AZURE_OPENAI_API_KEY}"
    deploymentName: "gpt-4"
    apiVersion: "2024-02-15-preview"
EOF
            ;;
        "openai")
            cat >> $filename << EOF
  openai:
    enabled: true
    apiKey: "\${OPENAI_API_KEY}"
    model: "gpt-4-turbo"
EOF
            ;;
        "anthropic")
            cat >> $filename << EOF
  anthropic:
    enabled: true
    apiKey: "\${ANTHROPIC_API_KEY}"
    model: "claude-3-opus-20240229"
EOF
            ;;
        "gemini")
            cat >> $filename << EOF
  gemini:
    enabled: true
    apiKey: "\${GOOGLE_API_KEY}"
    model: "gemini-pro"
EOF
            ;;
        "ollama")
            cat >> $filename << EOF
  ollama:
    enabled: true
    host: "http://ollama:11434"
    model: "llama2"
    deployInCluster: true
EOF
            ;;
    esac

    # Add Vector Store configuration
    cat >> $filename << EOF

# Vector Store Configuration
vectorStore:
  type: "$vector"
EOF

    case $vector in
        "qdrant")
            cat >> $filename << EOF
  qdrant:
    enabled: true
    deployInCluster: true
    persistence:
      enabled: true
      size: 10Gi
    service:
      type: NodePort
      nodePort: 30333
    collection: "documents"
EOF
            ;;
        "mongodb")
            cat >> $filename << EOF
  mongodb:
    enabled: true
    uri: "\${MONGODB_URI}"
    database: "kuberag"
    collection: "documents"
EOF
            ;;
        "chroma")
            cat >> $filename << EOF
  chroma:
    enabled: true
    deployInCluster: true
    persistence:
      enabled: true
      size: 10Gi
EOF
            ;;
        "faiss")
            cat >> $filename << EOF
  faiss:
    enabled: true
    indexPath: "/data/faiss"
    persistence:
      enabled: true
      size: 10Gi
EOF
            ;;
        "postgresql")
            cat >> $filename << EOF
  postgresql:
    enabled: true
    host: "\${PG_HOST}"
    port: 5432
    database: "\${PG_DATABASE}"
    username: "\${PG_USERNAME}"
    password: "\${PG_PASSWORD}"
    pgvector:
      enabled: true
EOF
            ;;
        "elasticsearch")
            cat >> $filename << EOF
  elasticsearch:
    enabled: true
    url: "\${ELASTICSEARCH_URL}"
    index: "kuberag"
    auth:
      enabled: false
EOF
            ;;
        "neo4j")
            cat >> $filename << EOF
  neo4j:
    enabled: true
    uri: "\${NEO4J_URI}"
    username: "\${NEO4J_USERNAME}"
    password: "\${NEO4J_PASSWORD}"
EOF
            ;;
        "lancedb")
            cat >> $filename << EOF
  lancedb:
    enabled: true
    path: "/data/lancedb"
    persistence:
      enabled: true
      size: 10Gi
EOF
            ;;
    esac

    # Add common service configuration
    cat >> $filename << EOF

# Service Configuration
service:
  agent:
    type: NodePort
    nodePort: 31390
  pipeline:
    type: NodePort
    nodePort: 31095
  ui:
    enabled: true
    type: NodePort
    nodePort: 30000

# Resource Configuration
resources:
  agent:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
  pipeline:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "2000m"

# Replica Configuration
replicaCount:
  agent: 2
  pipeline: 1

# Monitoring
monitoring:
  enabled: false
  prometheus:
    enabled: false
  grafana:
    enabled: false
EOF

    echo -e "${GREEN}✓${NC} Generated config #$index: ${BLUE}$llm${NC} + ${CYAN}$vector${NC}"
}

# Generate all combinations
index=1
for llm in "${LLM_PROVIDERS[@]}"; do
    for vector in "${VECTOR_STORES[@]}"; do
        generate_combination $llm $vector $index
        ((index++))
    done
done

echo -e "\n${GREEN}Successfully generated all 40 configurations!${NC}"
echo -e "Configuration files saved in: ${YELLOW}$OUTPUT_DIR/${NC}\n"

# Generate summary file
cat > "${OUTPUT_DIR}/README.md" << EOF
# KubeRAG Configuration Files

This directory contains pre-generated Helm values files for all 40 supported combinations of KubeRAG.

## Supported Combinations

### LLM Providers (5)
- Azure OpenAI
- OpenAI
- Anthropic (Claude)
- Google Gemini
- Ollama (Local)

### Vector Stores (8)
- Qdrant
- MongoDB
- ChromaDB
- FAISS
- PostgreSQL (with pgvector)
- Elasticsearch
- Neo4j
- LanceDB

## Usage

1. Choose your desired combination file (e.g., \`kuberag-openai-qdrant.yaml\`)
2. Set required environment variables (noted with \${VARIABLE_NAME} in the files)
3. Install using:
   \`\`\`bash
   helm install kuberag ./KubeRag -f kuberag-configurations/kuberag-<llm>-<vector>.yaml
   \`\`\`

## Configuration Matrix

| File | LLM Provider | Vector Store |
|------|-------------|--------------|
EOF

# Generate matrix table
index=1
for llm in "${LLM_PROVIDERS[@]}"; do
    for vector in "${VECTOR_STORES[@]}"; do
        echo "| kuberag-${llm}-${vector}.yaml | $llm | $vector |" >> "${OUTPUT_DIR}/README.md"
        ((index++))
    done
done

cat >> "${OUTPUT_DIR}/README.md" << EOF

## Environment Variables Required

### Azure OpenAI
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_KEY

### OpenAI
- OPENAI_API_KEY

### Anthropic
- ANTHROPIC_API_KEY

### Google Gemini
- GOOGLE_API_KEY

### MongoDB
- MONGODB_URI

### PostgreSQL
- PG_HOST
- PG_DATABASE
- PG_USERNAME
- PG_PASSWORD

### Elasticsearch
- ELASTICSEARCH_URL

### Neo4j
- NEO4J_URI
- NEO4J_USERNAME
- NEO4J_PASSWORD

## Quick Installation Examples

### Production Setup (Azure OpenAI + Qdrant)
\`\`\`bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-api-key"
helm install kuberag ./KubeRag -f kuberag-configurations/kuberag-azure_openai-qdrant.yaml
\`\`\`

### Development Setup (Ollama + FAISS)
\`\`\`bash
helm install kuberag ./KubeRag -f kuberag-configurations/kuberag-ollama-faiss.yaml
\`\`\`

### Enterprise Setup (OpenAI + MongoDB)
\`\`\`bash
export OPENAI_API_KEY="your-api-key"
export MONGODB_URI="mongodb://username:password@host:port"
helm install kuberag ./KubeRag -f kuberag-configurations/kuberag-openai-mongodb.yaml
\`\`\`
EOF

echo -e "Generated documentation: ${YELLOW}${OUTPUT_DIR}/README.md${NC}\n"

# Create installation helper script
cat > "${OUTPUT_DIR}/install.sh" << 'INSTALL_EOF'
#!/bin/bash

# KubeRAG Installation Helper
# Simplifies installation of specific combinations

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <llm_provider> <vector_store>"
    echo ""
    echo "LLM Providers: azure_openai, openai, anthropic, gemini, ollama"
    echo "Vector Stores: qdrant, mongodb, chroma, faiss, postgresql, elasticsearch, neo4j, lancedb"
    echo ""
    echo "Example: $0 openai qdrant"
    exit 1
fi

LLM=$1
VECTOR=$2
VALUES_FILE="kuberag-${LLM}-${VECTOR}.yaml"

if [ ! -f "$VALUES_FILE" ]; then
    echo "Error: Configuration file not found: $VALUES_FILE"
    echo "Please ensure you selected a valid combination."
    exit 1
fi

echo "Installing KubeRAG with:"
echo "  LLM Provider: $LLM"
echo "  Vector Store: $VECTOR"
echo "  Values File: $VALUES_FILE"
echo ""

# Check for required environment variables
case $LLM in
    "azure_openai")
        if [ -z "$AZURE_OPENAI_ENDPOINT" ] || [ -z "$AZURE_OPENAI_API_KEY" ]; then
            echo "Error: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set"
            exit 1
        fi
        ;;
    "openai")
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "Error: OPENAI_API_KEY must be set"
            exit 1
        fi
        ;;
    "anthropic")
        if [ -z "$ANTHROPIC_API_KEY" ]; then
            echo "Error: ANTHROPIC_API_KEY must be set"
            exit 1
        fi
        ;;
    "gemini")
        if [ -z "$GOOGLE_API_KEY" ]; then
            echo "Error: GOOGLE_API_KEY must be set"
            exit 1
        fi
        ;;
esac

# Substitute environment variables and install
envsubst < "$VALUES_FILE" | helm install kuberag ../KubeRag -f - --create-namespace --namespace kuberag

echo ""
echo "Installation complete! Check status with:"
echo "  kubectl get pods -n kuberag"
INSTALL_EOF

chmod +x "${OUTPUT_DIR}/install.sh"

echo -e "Created installation helper: ${YELLOW}${OUTPUT_DIR}/install.sh${NC}"
echo -e "\nTo install a specific combination:"
echo -e "  ${CYAN}cd ${OUTPUT_DIR}${NC}"
echo -e "  ${CYAN}./install.sh <llm_provider> <vector_store>${NC}"
echo -e "\nExample:"
echo -e "  ${CYAN}./install.sh openai qdrant${NC}"