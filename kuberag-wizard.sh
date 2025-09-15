#!/bin/bash

# KubeRAG Simple Installation Wizard
# Easy step-by-step installation for KubeRAG

set -e

# Colors for better readability - using printf-compatible format
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
CYAN=$'\033[0;36m'
NC=$'\033[0m' # No Color
BOLD=$'\033[1m'

# Default values
NAMESPACE="kuberag"
RELEASE_NAME="my-kuberag"
VALUES_FILE="my-kuberag-values.yaml"

# Clear screen and show banner
clear
printf "${CYAN}╔════════════════════════════════════════════╗${NC}\n"
printf "${CYAN}║       ${BOLD}KubeRAG Installation Wizard${NC}${CYAN}         ║${NC}\n"
printf "${CYAN}║          Simple • Fast • Easy              ║${NC}\n"
printf "${CYAN}╚════════════════════════════════════════════╝${NC}\n"
echo

# Step counter
STEP=1

show_step() {
    echo
    printf "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    printf "${GREEN}Step $STEP:${NC} ${BOLD}$1${NC}\n"
    printf "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    ((STEP++))
}

# Step 1: Check Prerequisites
show_step "Checking your system"
echo
echo "Let me check if you have everything needed..."
echo

READY=true

# Check kubectl
printf "  Checking kubectl... "
if command -v kubectl &> /dev/null; then
    printf "${GREEN}✓ Found${NC}\n"
else
    printf "${RED}✗ Not found${NC}\n"
    echo "    Please install kubectl first: https://kubernetes.io/docs/tasks/tools/"
    READY=false
fi

# Check helm
printf "  Checking helm... "
if command -v helm &> /dev/null; then
    printf "${GREEN}✓ Found${NC}\n"
else
    printf "${RED}✗ Not found${NC}\n"
    echo "    Please install helm first: https://helm.sh/docs/intro/install/"
    READY=false
fi

# Check kubernetes connection
printf "  Checking Kubernetes connection... "
if kubectl cluster-info &> /dev/null 2>&1; then
    printf "${GREEN}✓ Connected${NC}\n"
else
    printf "${RED}✗ Not connected${NC}\n"
    echo "    Please connect to a Kubernetes cluster first"
    READY=false
fi

if [ "$READY" = false ]; then
    echo
    printf "${RED}Some requirements are missing. Please fix them and run again.${NC}\n"
    exit 1
fi

echo
printf "${GREEN}Great! Your system is ready.${NC}\n"
sleep 1

# Step 2: Basic Settings
show_step "Basic settings"
echo
echo "First, let's set up some basic options."
echo

# Namespace
printf "${CYAN}What namespace should I use?${NC}\n"
echo "  (Press Enter for default: kuberag)"
read -p "  Namespace: " user_namespace
NAMESPACE=${user_namespace:-kuberag}
printf "  ${GREEN}✓${NC} Using namespace: ${BOLD}$NAMESPACE${NC}\n"
echo

# Release name
printf "${CYAN}What should I name this installation?${NC}\n"
echo "  (Press Enter for default: my-kuberag)"
read -p "  Release name: " user_release
RELEASE_NAME=${user_release:-my-kuberag}
printf "  ${GREEN}✓${NC} Release name: ${BOLD}$RELEASE_NAME${NC}\n"

# Step 3: Choose LLM Provider
show_step "Choose your AI provider"
echo
echo "Which AI service would you like to use?"
echo
printf "  ${BOLD}1)${NC} ${CYAN}Azure OpenAI${NC} - Microsoft's enterprise OpenAI\n"
printf "  ${BOLD}2)${NC} ${CYAN}OpenAI${NC} - ChatGPT/GPT-4 directly\n"
printf "  ${BOLD}3)${NC} ${CYAN}Anthropic${NC} - Claude AI\n"
printf "  ${BOLD}4)${NC} ${CYAN}Google Gemini${NC} - Google's AI\n"
printf "  ${BOLD}5)${NC} ${CYAN}Ollama${NC} - Run AI locally (no API needed)\n"
echo

while true; do
    read -p "  Choose [1-5]: " llm_choice
    case $llm_choice in
        1)
            LLM_PROVIDER="azure_openai"
            LLM_NAME="Azure OpenAI"
            break
            ;;
        2)
            LLM_PROVIDER="openai"
            LLM_NAME="OpenAI"
            break
            ;;
        3)
            LLM_PROVIDER="anthropic"
            LLM_NAME="Anthropic Claude"
            break
            ;;
        4)
            LLM_PROVIDER="gemini"
            LLM_NAME="Google Gemini"
            break
            ;;
        5)
            LLM_PROVIDER="ollama"
            LLM_NAME="Ollama (Local)"
            break
            ;;
        *)
            printf "  ${YELLOW}Please choose a number from 1 to 5${NC}\n"
            ;;
    esac
done

printf "  ${GREEN}✓${NC} Selected: ${BOLD}$LLM_NAME${NC}\n"

# Step 4: Configure LLM
show_step "Configure $LLM_NAME"
echo

case $LLM_PROVIDER in
    "azure_openai")
        echo "I need your Azure OpenAI credentials:"
        echo
        read -p "  Azure OpenAI Endpoint (e.g., https://myresource.openai.azure.com/): " AZURE_ENDPOINT
        read -p "  Azure API Key: " -s AZURE_API_KEY
        echo
        echo
        echo "  ${CYAN}Optional settings (press Enter to use defaults):${NC}"
        read -p "  Deployment name (default: gpt-4): " AZURE_DEPLOYMENT
        AZURE_DEPLOYMENT=${AZURE_DEPLOYMENT:-gpt-4}
        ;;
    "openai")
        echo "I need your OpenAI API key:"
        echo
        read -p "  OpenAI API Key: " -s OPENAI_API_KEY
        echo
        echo
        echo "  ${CYAN}Optional settings (press Enter to use defaults):${NC}"
        read -p "  Model (default: gpt-4-turbo): " OPENAI_MODEL
        OPENAI_MODEL=${OPENAI_MODEL:-gpt-4-turbo}
        ;;
    "anthropic")
        echo "I need your Anthropic API key:"
        echo
        read -p "  Anthropic API Key: " -s ANTHROPIC_API_KEY
        echo
        echo
        echo "  ${CYAN}Optional settings (press Enter to use defaults):${NC}"
        read -p "  Model (default: claude-3-opus-20240229): " ANTHROPIC_MODEL
        ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-claude-3-opus-20240229}
        ;;
    "gemini")
        echo "I need your Google API key:"
        echo
        read -p "  Google API Key: " -s GOOGLE_API_KEY
        echo
        echo
        echo "  ${CYAN}Optional settings (press Enter to use defaults):${NC}"
        read -p "  Model (default: gemini-pro): " GEMINI_MODEL
        GEMINI_MODEL=${GEMINI_MODEL:-gemini-pro}
        ;;
    "ollama")
        echo "Ollama will run locally in your cluster."
        echo
        printf "  ${CYAN}Which model would you like to use?${NC}\n"
        echo "  Popular options: llama2, mistral, codellama"
        read -p "  Model (default: llama2): " OLLAMA_MODEL
        OLLAMA_MODEL=${OLLAMA_MODEL:-llama2}
        ;;
esac

printf "  ${GREEN}✓${NC} $LLM_NAME configured\n"

# Step 5: Choose Vector Database
show_step "Choose your vector database"
echo
echo "Where should I store your documents?"
echo
printf "  ${BOLD}1)${NC} ${CYAN}Qdrant${NC} - Fast & reliable (${GREEN}Recommended${NC})\n"
printf "  ${BOLD}2)${NC} ${CYAN}MongoDB${NC} - If you already use MongoDB\n"
printf "  ${BOLD}3)${NC} ${CYAN}ChromaDB${NC} - Simple & lightweight\n"
printf "  ${BOLD}4)${NC} ${CYAN}FAISS${NC} - Facebook's solution\n"
printf "  ${BOLD}5)${NC} ${CYAN}PostgreSQL${NC} - Using your existing PostgreSQL\n"
printf "  ${BOLD}6)${NC} ${CYAN}Elasticsearch${NC} - Full-text search included\n"
printf "  ${BOLD}7)${NC} ${CYAN}Neo4j${NC} - Graph relationships\n"
printf "  ${BOLD}8)${NC} ${CYAN}LanceDB${NC} - Modern & fast\n"
echo

while true; do
    read -p "  Choose [1-8]: " vector_choice
    case $vector_choice in
        1)
            VECTOR_STORE="qdrant"
            VECTOR_NAME="Qdrant"
            break
            ;;
        2)
            VECTOR_STORE="mongodb"
            VECTOR_NAME="MongoDB"
            break
            ;;
        3)
            VECTOR_STORE="chroma"
            VECTOR_NAME="ChromaDB"
            break
            ;;
        4)
            VECTOR_STORE="faiss"
            VECTOR_NAME="FAISS"
            break
            ;;
        5)
            VECTOR_STORE="postgresql"
            VECTOR_NAME="PostgreSQL"
            break
            ;;
        6)
            VECTOR_STORE="elasticsearch"
            VECTOR_NAME="Elasticsearch"
            break
            ;;
        7)
            VECTOR_STORE="neo4j"
            VECTOR_NAME="Neo4j"
            break
            ;;
        8)
            VECTOR_STORE="lancedb"
            VECTOR_NAME="LanceDB"
            break
            ;;
        *)
            printf "  ${YELLOW}Please choose a number from 1 to 8${NC}\n"
            ;;
    esac
done

printf "  ${GREEN}✓${NC} Selected: ${BOLD}$VECTOR_NAME${NC}\n"

# Step 6: Configure Vector Store
show_step "Configure $VECTOR_NAME"
echo

case $VECTOR_STORE in
    "qdrant")
        echo "Qdrant will be deployed automatically in your cluster."
        echo "No additional configuration needed!"
        DEPLOY_QDRANT="true"
        ;;
    "mongodb")
        echo "I need your MongoDB connection details:"
        echo
        read -p "  MongoDB URI (e.g., mongodb://user:pass@host:27017): " MONGODB_URI
        read -p "  Database name (default: kuberag): " MONGODB_DB
        MONGODB_DB=${MONGODB_DB:-kuberag}
        ;;
    "chroma")
        echo "ChromaDB will be deployed automatically in your cluster."
        echo "No additional configuration needed!"
        DEPLOY_CHROMA="true"
        ;;
    "faiss")
        echo "FAISS will be deployed automatically in your cluster."
        echo "No additional configuration needed!"
        DEPLOY_FAISS="true"
        ;;
    "postgresql")
        echo "I need your PostgreSQL connection details:"
        echo
        read -p "  PostgreSQL host: " PG_HOST
        read -p "  Database name: " PG_DB
        read -p "  Username: " PG_USER
        read -p "  Password: " -s PG_PASSWORD
        echo
        ;;
    "elasticsearch")
        echo "I need your Elasticsearch connection details:"
        echo
        read -p "  Elasticsearch URL (e.g., http://elastic:9200): " ES_URL
        echo "  ${CYAN}Does it need authentication?${NC}"
        read -p "  Need auth? (y/n): " ES_AUTH
        if [ "$ES_AUTH" = "y" ]; then
            read -p "  Username: " ES_USER
            read -p "  Password: " -s ES_PASSWORD
            echo
        fi
        ;;
    "neo4j")
        echo "I need your Neo4j connection details:"
        echo
        read -p "  Neo4j URI (e.g., bolt://localhost:7687): " NEO4J_URI
        read -p "  Username (default: neo4j): " NEO4J_USER
        NEO4J_USER=${NEO4J_USER:-neo4j}
        read -p "  Password: " -s NEO4J_PASSWORD
        echo
        ;;
    "lancedb")
        echo "LanceDB will store data locally in the cluster."
        echo "No additional configuration needed!"
        ;;
esac

printf "  ${GREEN}✓${NC} $VECTOR_NAME configured\n"

# Step 7: Additional Options
show_step "Additional options"
echo
echo "Almost done! Just a few more questions:"
echo

# Web UI
printf "  ${CYAN}Would you like a web interface?${NC}\n"
read -p "  Enable Web UI? (Y/n): " enable_ui
ENABLE_UI=${enable_ui:-Y}
if [[ "$ENABLE_UI" =~ ^[Yy]$ ]] || [ -z "$enable_ui" ]; then
    ENABLE_UI="true"
    read -p "  Web UI port (default: 30000): " UI_PORT
    UI_PORT=${UI_PORT:-30000}
    printf "  ${GREEN}✓${NC} Web UI will be available at http://localhost:$UI_PORT\n"
else
    ENABLE_UI="false"
fi

echo

# Embedding model
printf "  ${CYAN}Which embedding model?${NC}\n"
echo "  Options: all-MiniLM-L6-v2 (fast), all-mpnet-base-v2 (accurate)"
read -p "  Model (default: all-MiniLM-L6-v2): " EMBEDDING_MODEL
EMBEDDING_MODEL=${EMBEDDING_MODEL:-all-MiniLM-L6-v2}
printf "  ${GREEN}✓${NC} Using embedding model: $EMBEDDING_MODEL\n"

# Step 8: Generate Configuration
show_step "Creating your configuration"
echo
echo "Generating configuration file..."

# Create the values.yaml file matching the current Helm chart structure
cat > $VALUES_FILE << EOF
# KubeRAG Configuration
# Generated by KubeRAG Wizard
# Date: $(date)

nameOverride: ""
fullnameOverride: ""

# Images
images:
  agent:
    repository: kuberag-agent
    tag: "v1.0.17"
    pullPolicy: IfNotPresent
  pipeline:
    repository: kuberag-pipeline
    tag: "v1.0.10"
    pullPolicy: IfNotPresent

# LLM Configuration
llm:
  provider: "$LLM_PROVIDER"
EOF

# Add all LLM provider configurations (required by Helm templates)
cat >> $VALUES_FILE << EOF
  openai:
    model: "$([ "$LLM_PROVIDER" = "openai" ] && echo "$OPENAI_MODEL" || echo "gpt-3.5-turbo")"
    apiKey: "$([ "$LLM_PROVIDER" = "openai" ] && echo "$OPENAI_API_KEY" || echo "")"
    baseUrl: ""
  azureOpenai:
    deployment: "$([ "$LLM_PROVIDER" = "azure_openai" ] && echo "$AZURE_DEPLOYMENT" || echo "gpt-4o-mini")"
    apiVersion: "2025-01-01-preview"
    endpoint: "$([ "$LLM_PROVIDER" = "azure_openai" ] && echo "$AZURE_ENDPOINT" || echo "https://your-resource.openai.azure.com")"
    apiKey: "$([ "$LLM_PROVIDER" = "azure_openai" ] && echo "$AZURE_API_KEY" || echo "")"
    embedDeployment: "text-embedding-ada-002"
    embedModel: "text-embedding-ada-002"
  anthropic:
    apiKey: "$([ "$LLM_PROVIDER" = "anthropic" ] && echo "$ANTHROPIC_API_KEY" || echo "")"
    model: "$([ "$LLM_PROVIDER" = "anthropic" ] && echo "$ANTHROPIC_MODEL" || echo "claude-3-5-sonnet-20241022")"
  gemini:
    apiKey: "$([ "$LLM_PROVIDER" = "gemini" ] && echo "$GOOGLE_API_KEY" || echo "")"
    model: "$([ "$LLM_PROVIDER" = "gemini" ] && echo "$GEMINI_MODEL" || echo "gemini-1.5-flash")"
  ollama:
    model: "$([ "$LLM_PROVIDER" = "ollama" ] && echo "$OLLAMA_MODEL" || echo "llama2")"
    baseUrl: "http://localhost:11434"
EOF

# Add Vector Store configuration
cat >> $VALUES_FILE << EOF

# Vector Store Configuration
vectorStore:
  type: "$VECTOR_STORE"
  dimension: 384
  collectionName: "documents"
EOF

case $VECTOR_STORE in
    "qdrant")
        cat >> $VALUES_FILE << EOF

  # Qdrant Configuration
  qdrant:
    host: "qdrant-service"
    port: 6333
    grpcPort: 6334
    preferGrpc: false
    https: false
    apiKey: ""
    timeout: 5.0
    deploy: true
EOF
        ;;
    "mongodb")
        cat >> $VALUES_FILE << EOF

  # MongoDB Configuration
  mongodb:
    host: "mongodb-service"
    port: 27017
    database: "$MONGODB_DB"
    username: "kuberag"
    password: ""
    connectionString: "$MONGODB_URI"
    indexName: "vector_index"
    deploy: false

  # Qdrant Configuration (disabled when using MongoDB)
  qdrant:
    host: "qdrant-service"
    port: 6333
    grpcPort: 6334
    preferGrpc: false
    https: false
    apiKey: ""
    timeout: 5.0
    deploy: false
EOF
        ;;
    "chroma")
        cat >> $VALUES_FILE << EOF

  # ChromaDB Configuration
  chroma:
    host: "chromadb-service"
    port: 8000
    deploy: true

  # Qdrant Configuration (disabled when using ChromaDB)
  qdrant:
    host: "qdrant-service"
    port: 6333
    grpcPort: 6334
    preferGrpc: false
    https: false
    apiKey: ""
    timeout: 5.0
    deploy: false
EOF
        ;;
    "faiss")
        cat >> $VALUES_FILE << EOF

  # FAISS Configuration
  faiss:
    host: "faiss-service"
    port: 8080
    indexPath: "/data/faiss_index"
    metadataPath: "/data/faiss_metadata.pkl"
    indexType: "FlatL2"
    deploy: true

  # Qdrant Configuration (disabled when using FAISS)
  qdrant:
    host: "qdrant-service"
    port: 6333
    grpcPort: 6334
    preferGrpc: false
    https: false
    apiKey: ""
    timeout: 5.0
    deploy: false
EOF
        ;;
    "postgresql")
        cat >> $VALUES_FILE << EOF

  # PostgreSQL Configuration
  postgresql:
    host: "$PG_HOST"
    port: 5432
    database: "$PG_DB"
    username: "$PG_USER"
    password: "$PG_PASSWORD"
    tableName: "documents"

  # Qdrant Configuration (disabled when using PostgreSQL)
  qdrant:
    host: "qdrant-service"
    port: 6333
    grpcPort: 6334
    preferGrpc: false
    https: false
    apiKey: ""
    timeout: 5.0
    deploy: false
EOF
        ;;
    "elasticsearch")
        cat >> $VALUES_FILE << EOF

  # Elasticsearch Configuration
  elasticsearch:
    host: "$ES_HOST"
    port: 9200
    indexName: "documents"
    username: "$ES_USER"
    password: "$ES_PASSWORD"
    useSSL: false
    verifyCerts: false

  # Qdrant Configuration (disabled when using Elasticsearch)
  qdrant:
    host: "qdrant-service"
    port: 6333
    grpcPort: 6334
    preferGrpc: false
    https: false
    apiKey: ""
    timeout: 5.0
    deploy: false
EOF
        ;;
    "neo4j")
        cat >> $VALUES_FILE << EOF

  # Neo4j Configuration
  neo4j:
    uri: "$NEO4J_URI"
    username: "$NEO4J_USER"
    password: "$NEO4J_PASSWORD"
    database: "neo4j"
    indexName: "document_embeddings"

  # Qdrant Configuration (disabled when using Neo4j)
  qdrant:
    host: "qdrant-service"
    port: 6333
    grpcPort: 6334
    preferGrpc: false
    https: false
    apiKey: ""
    timeout: 5.0
    deploy: false
EOF
        ;;
    "lancedb")
        cat >> $VALUES_FILE << EOF

  # LanceDB Configuration
  lancedb:
    uri: "/data/lancedb"
    tableName: "documents"
    metric: "cosine"

  # Qdrant Configuration (disabled when using LanceDB)
  qdrant:
    host: "qdrant-service"
    port: 6333
    grpcPort: 6334
    preferGrpc: false
    https: false
    apiKey: ""
    timeout: 5.0
    deploy: false
EOF
        ;;
esac

# Add remaining configuration to match Helm chart structure
cat >> $VALUES_FILE << EOF

# Embedding Configuration
embedding:
  model: "$EMBEDDING_MODEL"

# Text Processing Configuration
textProcessing:
  chunkSize: 500
  chunkOverlap: 50
  method: "words"

# Deployment Configuration
deployment:
  agent:
    replicas: 2
    resources:
      requests:
        memory: "512Mi"
        cpu: "250m"
      limits:
        memory: "2Gi"
        cpu: "1000m"
  pipeline:
    replicas: 1
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"
      limits:
        memory: "4Gi"
        cpu: "2000m"

# Service Configuration
service:
  type: "NodePort"
  agent:
    port: 80
    targetPort: 8082
    nodePort: 31390
  pipeline:
    port: 80
    targetPort: 8001
    nodePort: 31095

# Ingress Configuration
ingress:
  enabled: false
  className: "nginx"
  host: "kuberag.local"
  annotations: {}
  tls:
    enabled: false
    secretName: "kuberag-tls"

# Persistence Configuration
persistence:
  enabled: true
  storageClass: "standard"
  accessMode: "ReadWriteOnce"
  size: "10Gi"

# Security Configuration
security:
  podSecurityContext:
    fsGroup: 2000
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000

# Auto-scaling Configuration
autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

# Secrets Configuration
secrets: {}
EOF

printf "${GREEN}✓${NC} Configuration saved to: ${BOLD}$VALUES_FILE${NC}\n"

# Step 9: Review and Install
show_step "Ready to install!"
echo
printf "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "${BOLD}Your KubeRAG Configuration:${NC}\n"
printf "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
printf "  ${CYAN}Namespace:${NC}      $NAMESPACE\n"
printf "  ${CYAN}Release:${NC}        $RELEASE_NAME\n"
printf "  ${CYAN}AI Provider:${NC}    $LLM_NAME\n"
printf "  ${CYAN}Vector DB:${NC}      $VECTOR_NAME\n"
printf "  ${CYAN}Web UI:${NC}         $([ "$ENABLE_UI" = "true" ] && echo "Yes (port $UI_PORT)" || echo "No")\n"
printf "  ${CYAN}Config File:${NC}    $VALUES_FILE\n"
printf "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
echo

printf "${YELLOW}Do you want to install KubeRAG now?${NC}\n"
read -p "Install? (Y/n): " do_install

if [[ "$do_install" =~ ^[Nn]$ ]]; then
    echo
    printf "${YELLOW}Installation skipped.${NC}\n"
    echo
    echo "To install later, run:"
    printf "${CYAN}helm install $RELEASE_NAME ./KubeRag -f $VALUES_FILE  \n"
    echo
    exit 0
fi

# Helper function for basic health checks
basic_health_checks() {
    printf "${BLUE}Running basic health checks...${NC}\\n"
    echo

    # Check pod status
    printf "  Checking pod status... "
    if kubectl get pods -n $NAMESPACE | grep -q "Running"; then
        printf "${GREEN}✓${NC}\\n"
    else
        printf "${YELLOW}Some pods may still be starting${NC}\\n"
    fi

    # Check services
    printf "  Checking services... "
    local svc_count=$(kubectl get svc -n $NAMESPACE --no-headers | wc -l)
    if [ $svc_count -gt 0 ]; then
        printf "${GREEN}✓ ($svc_count services)${NC}\\n"
    else
        printf "${RED}✗ No services found${NC}\\n"
    fi

    # Simple connectivity test
    printf "  Testing basic connectivity... "
    if kubectl port-forward -n $NAMESPACE service/kuberag-agent-service 8082:80 --address=0.0.0.0 &>/dev/null &
    then
        local pf_pid=$!
        sleep 3
        if curl -s --max-time 5 http://localhost:8082/health &>/dev/null; then
            printf "${GREEN}✓${NC}\\n"
        else
            printf "${YELLOW}Services may still be initializing${NC}\\n"
        fi
        kill $pf_pid &>/dev/null || true
    else
        printf "${YELLOW}Could not test connectivity${NC}\\n"
    fi
}

# Function to save deployment information
save_deployment_info() {
    local info_file="kuberag-deployment-info.json"

    cat > $info_file << EOF
{
  "deployment": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "namespace": "$NAMESPACE",
    "release_name": "$RELEASE_NAME",
    "llm_provider": "$LLM_PROVIDER",
    "vector_store": "$VECTOR_STORE",
    "embedding_model": "$EMBEDDING_MODEL",
    "web_ui_enabled": "$ENABLE_UI"
  },
  "access": {
    "agent_api": "http://localhost:${AGENT_PORT:-31390}",
    "pipeline_api": "http://localhost:${PIPELINE_PORT:-31095}",
    "web_ui": $([ "$ENABLE_UI" = "true" ] && echo "\"http://localhost:${UI_ACTUAL_PORT:-$UI_PORT}\"" || echo "null"),
    "qdrant_ui": $([ "$VECTOR_STORE" = "qdrant" ] && echo "\"http://localhost:${QDRANT_PORT:-30333}\"" || echo "null")
  },
  "commands": {
    "check_status": "kubectl get pods -n $NAMESPACE",
    "view_logs": "kubectl logs -n $NAMESPACE -l app=agent",
    "run_tests": "./test-kuberag-services.sh",
    "uninstall": "helm uninstall $RELEASE_NAME -n $NAMESPACE"
  }
}
EOF

    printf "${GREEN}✓${NC} Deployment info saved to: ${BOLD}$info_file${NC}\\n"
}

# Step 10: Install
show_step "Installing KubeRAG"
echo

# Clean up any existing failed installations
if helm list -n $NAMESPACE 2>/dev/null | grep -q "^$RELEASE_NAME"; then
    printf "${YELLOW}Found existing release. Cleaning up first...${NC}\\n"
    helm uninstall $RELEASE_NAME -n $NAMESPACE
    sleep 5
fi

# If namespace exists but not managed by Helm, delete it
if kubectl get namespace $NAMESPACE &>/dev/null; then
    MANAGED_BY=$(kubectl get namespace $NAMESPACE -o jsonpath='{.metadata.labels.app\.kubernetes\.io/managed-by}' 2>/dev/null || echo "")
    if [ "$MANAGED_BY" != "Helm" ]; then
        printf "${YELLOW}Namespace exists but not managed by Helm. Recreating...${NC}\\n"
        kubectl delete namespace $NAMESPACE --ignore-not-found=true
        # Wait for namespace to be fully deleted
        while kubectl get namespace $NAMESPACE &>/dev/null; do
            printf "."
            sleep 2
        done
        echo
    fi
fi

# Check if helm chart exists
if [ ! -d "./KubeRag" ]; then
    printf "${YELLOW}Warning: KubeRag helm chart not found in current directory${NC}\n"
    echo "Please ensure the KubeRag helm chart is in ./KubeRag"
    echo
    echo "To install manually, run:"
    printf "${CYAN}helm install $RELEASE_NAME ./KubeRag -f $VALUES_FILE -n $NAMESPACE${NC}\n"
    exit 1
fi

# Install with progress monitoring
printf "Installing KubeRAG (this may take a few minutes)...\n"
if helm install $RELEASE_NAME ./KubeRag -f $VALUES_FILE -n $NAMESPACE --create-namespace --wait --timeout 10m; then
    echo
    printf "${GREEN}╔════════════════════════════════════════════╗${NC}\\n"
    printf "${GREEN}║     ${BOLD}🎉 KubeRAG Installed Successfully!${NC}${GREEN}     ║${NC}\\n"
    printf "${GREEN}╚════════════════════════════════════════════╝${NC}\\n"
    echo

    # Wait for pods to be ready
    printf "${BLUE}Waiting for all pods to be ready...${NC}\\n"
    kubectl wait --for=condition=ready pod --all -n $NAMESPACE --timeout=300s

    # Get dynamic service information
    printf "${BLUE}Detecting service endpoints...${NC}\\n"

    # Get actual service ports dynamically
    AGENT_PORT=$(kubectl get svc -n $NAMESPACE -o jsonpath='{.items[?(@.metadata.labels.app=="agent")].spec.ports[0].nodePort}' 2>/dev/null || echo "31390")
    PIPELINE_PORT=$(kubectl get svc -n $NAMESPACE -o jsonpath='{.items[?(@.metadata.labels.app=="pipeline")].spec.ports[0].nodePort}' 2>/dev/null || echo "31095")

    if [ "$ENABLE_UI" = "true" ]; then
        UI_ACTUAL_PORT=$(kubectl get svc -n $NAMESPACE -o jsonpath='{.items[?(@.metadata.labels.app=="ui")].spec.ports[0].nodePort}' 2>/dev/null || echo "$UI_PORT")
    fi

    if [ "$VECTOR_STORE" = "qdrant" ]; then
        QDRANT_PORT=$(kubectl get svc -n $NAMESPACE -o jsonpath='{.items[?(@.metadata.labels.app=="qdrant")].spec.ports[0].nodePort}' 2>/dev/null || echo "30333")
    fi

    printf "${BOLD}Access your services:${NC}\\n"
    echo
    printf "  ${CYAN}Agent API:${NC}      http://localhost:${AGENT_PORT}\\n"
    printf "  ${CYAN}Pipeline API:${NC}   http://localhost:${PIPELINE_PORT}\\n"
    if [ "$ENABLE_UI" = "true" ]; then
        printf "  ${CYAN}Web UI:${NC}         http://localhost:${UI_ACTUAL_PORT}\\n"
    fi
    if [ "$VECTOR_STORE" = "qdrant" ]; then
        printf "  ${CYAN}Qdrant UI:${NC}      http://localhost:${QDRANT_PORT}\\n"
    fi
    echo

    # Automatically run integration tests
    show_step "Running Integration Tests"
    echo
    printf "${BLUE}Automatically testing your KubeRAG deployment...${NC}\\n"
    echo

    # Check if test script exists
    TEST_SCRIPT="./test-kuberag-services.sh"
    if [ -f "$TEST_SCRIPT" ]; then
        printf "${GREEN}Running comprehensive integration tests...${NC}\\n"
        echo

        # Run the test script with the correct namespace
        if KUBERAG_INSTALLER=1 NAMESPACE=$NAMESPACE $TEST_SCRIPT; then
            echo
            printf "${GREEN}╔════════════════════════════════════════════╗${NC}\\n"
            printf "${GREEN}║   ${BOLD}✅ All Tests Passed! System Ready!${NC}${GREEN}      ║${NC}\\n"
            printf "${GREEN}╚════════════════════════════════════════════╝${NC}\\n"
            echo
            printf "${BOLD}${GREEN}Your KubeRAG system is fully operational!${NC}\\n"
            echo
        else
            echo
            printf "${YELLOW}╔════════════════════════════════════════════╗${NC}\\n"
            printf "${YELLOW}║     ${BOLD}⚠️  Some Tests Failed${NC}${YELLOW}               ║${NC}\\n"
            printf "${YELLOW}╚════════════════════════════════════════════╝${NC}\\n"
            echo
            printf "${YELLOW}Installation completed but some tests failed.${NC}\\n"
            printf "${YELLOW}This might be due to services still starting up.${NC}\\n"
            echo
            printf "You can re-run tests later with: ${CYAN}$TEST_SCRIPT${NC}\\n"
        fi
    else
        printf "${YELLOW}Test script not found. Running basic health checks...${NC}\\n"

        # Basic health checks without the test script
        basic_health_checks
    fi

    echo
    printf "${BOLD}Useful commands:${NC}\\n"
    printf "  Check status:  ${CYAN}kubectl get pods -n $NAMESPACE${NC}\\n"
    printf "  View logs:     ${CYAN}kubectl logs -n $NAMESPACE -l app=agent${NC}\\n"
    printf "  Run tests:     ${CYAN}$TEST_SCRIPT${NC}\\n"
    printf "  Uninstall:     ${CYAN}helm uninstall $RELEASE_NAME -n $NAMESPACE${NC}\\n"
    echo

    # Save deployment info
    save_deployment_info

else
    echo
    printf "${RED}Installation failed!${NC}\\n"
    echo "Please check the error messages above."
    echo
    echo "Common issues:"
    echo "  - Insufficient cluster resources"
    echo "  - Invalid API credentials"
    echo "  - Network connectivity problems"
    echo
    echo "To retry, run:"
    printf "${CYAN}helm install $RELEASE_NAME ./KubeRag -f $VALUES_FILE -n $NAMESPACE --create-namespace${NC}\\n"
fi