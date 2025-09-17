#!/bin/bash

# KubeRAG Installation Wizard
# Automates Helm chart installation with all supported LLM and Vector Store combinations
# Supports 40 different deployment combinations (5 LLMs x 8 Vector Stores)

set -e

# Color codes for better UX
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Default values
NAMESPACE="kuberag"
RELEASE_NAME="kuberag"
HELM_CHART_PATH="./KubeRag"
VALUES_FILE="generated-values.yaml"
DEPLOYMENT_MODE="standard"

# Supported providers and stores
declare -a LLM_PROVIDERS=("azure_openai" "openai" "anthropic" "gemini" "ollama")
declare -a VECTOR_STORES=("qdrant" "mongodb" "chroma" "faiss" "postgresql" "elasticsearch" "neo4j" "lancedb")

# Function to print colored output
print_header() {
    echo -e "\n${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to display welcome banner
display_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     _  __     _          ____      _    ____                 ║
    ║    | |/ /   _| |__   ___/ __ \    / \  / ___|                ║
    ║    | ' / | | | '_ \ / _ \  / /    / _ \| |  _                 ║
    ║    | . \ |_| | |_) |  __/ |\ \   / ___ \ |_| |                ║
    ║    |_|\_\__,_|_.__/ \___|_| \_\ /_/   \_\____|                ║
    ║                                                               ║
    ║            Kubernetes RAG Deployment Wizard                   ║
    ║                     Version 1.0.0                             ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo -e "${WHITE}Welcome to KubeRAG Installation Wizard!${NC}"
    echo -e "${WHITE}This wizard will help you deploy KubeRAG with your preferred${NC}"
    echo -e "${WHITE}LLM provider and vector store combination.${NC}\n"
    echo -e "${GREEN}Supporting 40 deployment combinations:${NC}"
    echo -e "  • ${CYAN}5 LLM Providers${NC} × ${CYAN}8 Vector Stores${NC}"
    echo
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    local prereqs_met=true

    # Check kubectl
    if command -v kubectl &> /dev/null; then
        print_success "kubectl installed ($(kubectl version --client --short 2>/dev/null | head -1))"
    else
        print_error "kubectl not found. Please install kubectl first."
        prereqs_met=false
    fi

    # Check helm
    if command -v helm &> /dev/null; then
        print_success "helm installed ($(helm version --short))"
    else
        print_error "helm not found. Please install helm first."
        prereqs_met=false
    fi

    # Check kubernetes connection
    if kubectl cluster-info &> /dev/null; then
        print_success "Connected to Kubernetes cluster"
        local context=$(kubectl config current-context)
        print_info "Current context: $context"
    else
        print_error "Cannot connect to Kubernetes cluster"
        prereqs_met=false
    fi

    if [ "$prereqs_met" = false ]; then
        echo
        print_error "Prerequisites not met. Please install missing components."
        exit 1
    fi

    echo
}

# Function to select deployment mode
select_deployment_mode() {
    print_header "Select Deployment Mode"

    echo "Choose your deployment approach:"
    echo
    echo "  1) ${GREEN}Quick Setup${NC} - Use predefined templates"
    echo "  2) ${CYAN}Custom Configuration${NC} - Configure each component"
    echo "  3) ${YELLOW}Advanced${NC} - Full control with custom values"
    echo

    read -p "Select mode [1-3]: " mode_choice

    case $mode_choice in
        1) DEPLOYMENT_MODE="quick";;
        2) DEPLOYMENT_MODE="custom";;
        3) DEPLOYMENT_MODE="advanced";;
        *)
            print_warning "Invalid choice. Using custom mode."
            DEPLOYMENT_MODE="custom"
            ;;
    esac

    print_success "Selected mode: $DEPLOYMENT_MODE"
    echo
}

# Function to select LLM provider
select_llm_provider() {
    print_header "Select LLM Provider"

    echo "Available LLM Providers:"
    echo
    echo "  1) ${CYAN}Azure OpenAI${NC} - Enterprise-grade OpenAI models with Azure security"
    echo "  2) ${CYAN}OpenAI${NC} - Direct OpenAI API access"
    echo "  3) ${CYAN}Anthropic${NC} - Claude models for advanced reasoning"
    echo "  4) ${CYAN}Google Gemini${NC} - Google's multimodal AI models"
    echo "  5) ${CYAN}Ollama${NC} - Run local models without external API dependencies"
    echo

    read -p "Select LLM provider [1-5]: " llm_choice

    case $llm_choice in
        1) SELECTED_LLM="azure_openai";;
        2) SELECTED_LLM="openai";;
        3) SELECTED_LLM="anthropic";;
        4) SELECTED_LLM="gemini";;
        5) SELECTED_LLM="ollama";;
        *)
            print_warning "Invalid choice. Using Azure OpenAI."
            SELECTED_LLM="azure_openai"
            ;;
    esac

    print_success "Selected LLM: $SELECTED_LLM"
    echo
}

# Function to configure LLM settings
configure_llm_settings() {
    print_header "Configure $SELECTED_LLM Settings"

    case $SELECTED_LLM in
        "azure_openai")
            read -p "Enter Azure OpenAI Endpoint: " AZURE_ENDPOINT
            read -p "Enter Azure OpenAI API Key: " -s AZURE_API_KEY
            echo
            read -p "Enter Deployment Name (default: gpt-4): " AZURE_DEPLOYMENT
            AZURE_DEPLOYMENT=${AZURE_DEPLOYMENT:-gpt-4}
            read -p "Enter API Version (default: 2024-02-15-preview): " AZURE_API_VERSION
            AZURE_API_VERSION=${AZURE_API_VERSION:-2024-02-15-preview}
            ;;
        "openai")
            read -p "Enter OpenAI API Key: " -s OPENAI_API_KEY
            echo
            read -p "Enter Model Name (default: gpt-4-turbo): " OPENAI_MODEL
            OPENAI_MODEL=${OPENAI_MODEL:-gpt-4-turbo}
            ;;
        "anthropic")
            read -p "Enter Anthropic API Key: " -s ANTHROPIC_API_KEY
            echo
            read -p "Enter Model Name (default: claude-3-opus-20240229): " ANTHROPIC_MODEL
            ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-claude-3-opus-20240229}
            ;;
        "gemini")
            read -p "Enter Google API Key: " -s GOOGLE_API_KEY
            echo
            read -p "Enter Model Name (default: gemini-pro): " GEMINI_MODEL
            GEMINI_MODEL=${GEMINI_MODEL:-gemini-pro}
            ;;
        "ollama")
            read -p "Enter Ollama Host (default: http://ollama:11434): " OLLAMA_HOST
            OLLAMA_HOST=${OLLAMA_HOST:-http://ollama:11434}
            read -p "Enter Model Name (default: llama2): " OLLAMA_MODEL
            OLLAMA_MODEL=${OLLAMA_MODEL:-llama2}
            read -p "Deploy Ollama in cluster? (y/n, default: y): " DEPLOY_OLLAMA
            DEPLOY_OLLAMA=${DEPLOY_OLLAMA:-y}
            ;;
    esac

    print_success "LLM configuration completed"
    echo
}

# Function to select vector store
select_vector_store() {
    print_header "Select Vector Store"

    echo "Available Vector Stores:"
    echo
    echo "  1) ${CYAN}Qdrant${NC} - High-performance dedicated vector database (${GREEN}Recommended${NC})"
    echo "  2) ${CYAN}MongoDB${NC} - Document database with vector search capabilities"
    echo "  3) ${CYAN}ChromaDB${NC} - Open-source embedding database"
    echo "  4) ${CYAN}FAISS${NC} - Facebook's library for efficient similarity search"
    echo "  5) ${CYAN}PostgreSQL${NC} - Traditional database with pgvector extension"
    echo "  6) ${CYAN}Elasticsearch${NC} - Search engine with vector capabilities"
    echo "  7) ${CYAN}Neo4j${NC} - Graph database with vector search"
    echo "  8) ${CYAN}LanceDB${NC} - Modern columnar vector database"
    echo

    read -p "Select vector store [1-8]: " vector_choice

    case $vector_choice in
        1) SELECTED_VECTOR="qdrant";;
        2) SELECTED_VECTOR="mongodb";;
        3) SELECTED_VECTOR="chroma";;
        4) SELECTED_VECTOR="faiss";;
        5) SELECTED_VECTOR="postgresql";;
        6) SELECTED_VECTOR="elasticsearch";;
        7) SELECTED_VECTOR="neo4j";;
        8) SELECTED_VECTOR="lancedb";;
        *)
            print_warning "Invalid choice. Using Qdrant."
            SELECTED_VECTOR="qdrant"
            ;;
    esac

    print_success "Selected Vector Store: $SELECTED_VECTOR"
    echo
}

# Function to configure vector store settings
configure_vector_store_settings() {
    print_header "Configure $SELECTED_VECTOR Settings"

    case $SELECTED_VECTOR in
        "qdrant")
            read -p "Deploy Qdrant in cluster? (y/n, default: y): " DEPLOY_QDRANT
            DEPLOY_QDRANT=${DEPLOY_QDRANT:-y}
            if [ "$DEPLOY_QDRANT" != "y" ]; then
                read -p "Enter Qdrant Host: " QDRANT_HOST
                read -p "Enter Qdrant Port (default: 6333): " QDRANT_PORT
                QDRANT_PORT=${QDRANT_PORT:-6333}
            fi
            read -p "Enter Collection Name (default: documents): " QDRANT_COLLECTION
            QDRANT_COLLECTION=${QDRANT_COLLECTION:-documents}
            ;;
        "mongodb")
            read -p "Enter MongoDB Connection String: " MONGODB_URI
            read -p "Enter Database Name (default: kuberag): " MONGODB_DB
            MONGODB_DB=${MONGODB_DB:-kuberag}
            read -p "Enter Collection Name (default: documents): " MONGODB_COLLECTION
            MONGODB_COLLECTION=${MONGODB_COLLECTION:-documents}
            ;;
        "chroma")
            read -p "Deploy ChromaDB in cluster? (y/n, default: y): " DEPLOY_CHROMA
            DEPLOY_CHROMA=${DEPLOY_CHROMA:-y}
            if [ "$DEPLOY_CHROMA" != "y" ]; then
                read -p "Enter ChromaDB Host: " CHROMA_HOST
                read -p "Enter ChromaDB Port (default: 8000): " CHROMA_PORT
                CHROMA_PORT=${CHROMA_PORT:-8000}
            fi
            ;;
        "faiss")
            read -p "Enter Index Path (default: /data/faiss): " FAISS_PATH
            FAISS_PATH=${FAISS_PATH:-/data/faiss}
            read -p "Enable persistence? (y/n, default: y): " FAISS_PERSISTENCE
            FAISS_PERSISTENCE=${FAISS_PERSISTENCE:-y}
            ;;
        "postgresql")
            read -p "Enter PostgreSQL Host: " PG_HOST
            read -p "Enter PostgreSQL Port (default: 5432): " PG_PORT
            PG_PORT=${PG_PORT:-5432}
            read -p "Enter Database Name: " PG_DB
            read -p "Enter Username: " PG_USER
            read -p "Enter Password: " -s PG_PASSWORD
            echo
            ;;
        "elasticsearch")
            read -p "Enter Elasticsearch URL: " ES_URL
            read -p "Enter Index Name (default: kuberag): " ES_INDEX
            ES_INDEX=${ES_INDEX:-kuberag}
            read -p "Requires authentication? (y/n): " ES_AUTH
            if [ "$ES_AUTH" = "y" ]; then
                read -p "Enter Username: " ES_USER
                read -p "Enter Password: " -s ES_PASSWORD
                echo
            fi
            ;;
        "neo4j")
            read -p "Enter Neo4j URI: " NEO4J_URI
            read -p "Enter Username (default: neo4j): " NEO4J_USER
            NEO4J_USER=${NEO4J_USER:-neo4j}
            read -p "Enter Password: " -s NEO4J_PASSWORD
            echo
            ;;
        "lancedb")
            read -p "Enter LanceDB Path (default: /data/lancedb): " LANCEDB_PATH
            LANCEDB_PATH=${LANCEDB_PATH:-/data/lancedb}
            read -p "Enable persistence? (y/n, default: y): " LANCEDB_PERSISTENCE
            LANCEDB_PERSISTENCE=${LANCEDB_PERSISTENCE:-y}
            ;;
    esac

    print_success "Vector store configuration completed"
    echo
}

# Function to configure general settings
configure_general_settings() {
    print_header "General Configuration"

    read -p "Enter namespace (default: kuberag): " user_namespace
    NAMESPACE=${user_namespace:-kuberag}

    read -p "Enter release name (default: kuberag): " user_release
    RELEASE_NAME=${user_release:-kuberag}

    read -p "Enter embedding model (default: all-MiniLM-L6-v2): " EMBEDDING_MODEL
    EMBEDDING_MODEL=${EMBEDDING_MODEL:-all-MiniLM-L6-v2}

    read -p "Enter chunk size (default: 500): " CHUNK_SIZE
    CHUNK_SIZE=${CHUNK_SIZE:-500}

    read -p "Enter chunk overlap (default: 50): " CHUNK_OVERLAP
    CHUNK_OVERLAP=${CHUNK_OVERLAP:-50}

    read -p "Enable UI? (y/n, default: y): " ENABLE_UI
    ENABLE_UI=${ENABLE_UI:-y}

    if [ "$ENABLE_UI" = "y" ]; then
        read -p "UI NodePort (default: 30000): " UI_PORT
        UI_PORT=${UI_PORT:-30000}
    fi

    read -p "Enable monitoring? (y/n, default: n): " ENABLE_MONITORING
    ENABLE_MONITORING=${ENABLE_MONITORING:-n}

    print_success "General configuration completed"
    echo
}

# Function to generate values.yaml
generate_values_yaml() {
    print_header "Generating Helm Values"

    cat > $VALUES_FILE << EOF
# Generated by KubeRAG Installation Wizard
# Timestamp: $(date)
# Configuration: $SELECTED_LLM + $SELECTED_VECTOR

# Namespace configuration
namespace: $NAMESPACE

# Global configuration
global:
  embeddings:
    model: "$EMBEDDING_MODEL"
    dimension: 384
  chunking:
    size: $CHUNK_SIZE
    overlap: $CHUNK_OVERLAP

# LLM Provider Configuration
llm:
  provider: "$SELECTED_LLM"
EOF

    # Add LLM specific configuration
    case $SELECTED_LLM in
        "azure_openai")
            cat >> $VALUES_FILE << EOF
  azure_openai:
    enabled: true
    endpoint: "$AZURE_ENDPOINT"
    apiKey: "$AZURE_API_KEY"
    deploymentName: "$AZURE_DEPLOYMENT"
    apiVersion: "$AZURE_API_VERSION"
EOF
            ;;
        "openai")
            cat >> $VALUES_FILE << EOF
  openai:
    enabled: true
    apiKey: "$OPENAI_API_KEY"
    model: "$OPENAI_MODEL"
EOF
            ;;
        "anthropic")
            cat >> $VALUES_FILE << EOF
  anthropic:
    enabled: true
    apiKey: "$ANTHROPIC_API_KEY"
    model: "$ANTHROPIC_MODEL"
EOF
            ;;
        "gemini")
            cat >> $VALUES_FILE << EOF
  gemini:
    enabled: true
    apiKey: "$GOOGLE_API_KEY"
    model: "$GEMINI_MODEL"
EOF
            ;;
        "ollama")
            cat >> $VALUES_FILE << EOF
  ollama:
    enabled: true
    host: "$OLLAMA_HOST"
    model: "$OLLAMA_MODEL"
    deployInCluster: $([ "$DEPLOY_OLLAMA" = "y" ] && echo "true" || echo "false")
EOF
            ;;
    esac

    # Add Vector Store configuration
    cat >> $VALUES_FILE << EOF

# Vector Store Configuration
vectorStore:
  type: "$SELECTED_VECTOR"
EOF

    case $SELECTED_VECTOR in
        "qdrant")
            cat >> $VALUES_FILE << EOF
  qdrant:
    enabled: true
    deployInCluster: $([ "$DEPLOY_QDRANT" = "y" ] && echo "true" || echo "false")
EOF
            if [ "$DEPLOY_QDRANT" != "y" ]; then
                cat >> $VALUES_FILE << EOF
    host: "$QDRANT_HOST"
    port: $QDRANT_PORT
EOF
            else
                cat >> $VALUES_FILE << EOF
    persistence:
      enabled: true
      size: 10Gi
    service:
      type: NodePort
      nodePort: 30333
EOF
            fi
            cat >> $VALUES_FILE << EOF
    collection: "$QDRANT_COLLECTION"
EOF
            ;;
        "mongodb")
            cat >> $VALUES_FILE << EOF
  mongodb:
    enabled: true
    uri: "$MONGODB_URI"
    database: "$MONGODB_DB"
    collection: "$MONGODB_COLLECTION"
EOF
            ;;
        "chroma")
            cat >> $VALUES_FILE << EOF
  chroma:
    enabled: true
    deployInCluster: $([ "$DEPLOY_CHROMA" = "y" ] && echo "true" || echo "false")
EOF
            if [ "$DEPLOY_CHROMA" != "y" ]; then
                cat >> $VALUES_FILE << EOF
    host: "$CHROMA_HOST"
    port: $CHROMA_PORT
EOF
            else
                cat >> $VALUES_FILE << EOF
    persistence:
      enabled: true
      size: 10Gi
EOF
            fi
            ;;
        "faiss")
            cat >> $VALUES_FILE << EOF
  faiss:
    enabled: true
    indexPath: "$FAISS_PATH"
    persistence:
      enabled: $([ "$FAISS_PERSISTENCE" = "y" ] && echo "true" || echo "false")
      size: 10Gi
EOF
            ;;
        "postgresql")
            cat >> $VALUES_FILE << EOF
  postgresql:
    enabled: true
    host: "$PG_HOST"
    port: $PG_PORT
    database: "$PG_DB"
    username: "$PG_USER"
    password: "$PG_PASSWORD"
    pgvector:
      enabled: true
EOF
            ;;
        "elasticsearch")
            cat >> $VALUES_FILE << EOF
  elasticsearch:
    enabled: true
    url: "$ES_URL"
    index: "$ES_INDEX"
EOF
            if [ "$ES_AUTH" = "y" ]; then
                cat >> $VALUES_FILE << EOF
    auth:
      enabled: true
      username: "$ES_USER"
      password: "$ES_PASSWORD"
EOF
            fi
            ;;
        "neo4j")
            cat >> $VALUES_FILE << EOF
  neo4j:
    enabled: true
    uri: "$NEO4J_URI"
    username: "$NEO4J_USER"
    password: "$NEO4J_PASSWORD"
EOF
            ;;
        "lancedb")
            cat >> $VALUES_FILE << EOF
  lancedb:
    enabled: true
    path: "$LANCEDB_PATH"
    persistence:
      enabled: $([ "$LANCEDB_PERSISTENCE" = "y" ] && echo "true" || echo "false")
      size: 10Gi
EOF
            ;;
    esac

    # Add service configuration
    cat >> $VALUES_FILE << EOF

# Service Configuration
service:
  agent:
    type: NodePort
    nodePort: 31390
  pipeline:
    type: NodePort
    nodePort: 31095
EOF

    if [ "$ENABLE_UI" = "y" ]; then
        cat >> $VALUES_FILE << EOF
  ui:
    enabled: true
    type: NodePort
    nodePort: $UI_PORT
EOF
    fi

    # Add monitoring if enabled
    if [ "$ENABLE_MONITORING" = "y" ]; then
        cat >> $VALUES_FILE << EOF

# Monitoring Configuration
monitoring:
  enabled: true
  prometheus:
    enabled: true
  grafana:
    enabled: true
    service:
      type: NodePort
      nodePort: 30300
EOF
    fi

    # Add resource limits
    cat >> $VALUES_FILE << EOF

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
EOF

    print_success "Generated values file: $VALUES_FILE"
    echo
}

# Function to display configuration summary
display_summary() {
    print_header "Configuration Summary"

    echo -e "${WHITE}Deployment Configuration:${NC}"
    echo -e "  ${CYAN}Namespace:${NC}        $NAMESPACE"
    echo -e "  ${CYAN}Release Name:${NC}     $RELEASE_NAME"
    echo -e "  ${CYAN}LLM Provider:${NC}     $SELECTED_LLM"
    echo -e "  ${CYAN}Vector Store:${NC}     $SELECTED_VECTOR"
    echo -e "  ${CYAN}Embedding Model:${NC}  $EMBEDDING_MODEL"
    echo -e "  ${CYAN}Chunk Size:${NC}       $CHUNK_SIZE"
    echo -e "  ${CYAN}Chunk Overlap:${NC}    $CHUNK_OVERLAP"
    echo -e "  ${CYAN}UI Enabled:${NC}       $ENABLE_UI"
    echo -e "  ${CYAN}Monitoring:${NC}       $ENABLE_MONITORING"
    echo

    # Display combination info
    local llm_index=$(printf '%s\n' "${LLM_PROVIDERS[@]}" | grep -n "^$SELECTED_LLM$" | cut -d: -f1)
    local vector_index=$(printf '%s\n' "${VECTOR_STORES[@]}" | grep -n "^$SELECTED_VECTOR$" | cut -d: -f1)
    local combination_number=$(( (llm_index - 1) * 8 + vector_index ))

    echo -e "${GREEN}This is combination #$combination_number out of 40 supported combinations${NC}"
    echo
}

# Function to perform installation
perform_installation() {
    print_header "Installation"

    echo "Ready to install KubeRAG with the following configuration:"
    echo
    display_summary

    read -p "Proceed with installation? (y/n): " confirm

    if [ "$confirm" != "y" ]; then
        print_warning "Installation cancelled"
        exit 0
    fi

    # Create namespace if it doesn't exist
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        print_info "Creating namespace $NAMESPACE..."
        kubectl create namespace $NAMESPACE
        print_success "Namespace created"
    fi

    # Check if helm chart exists
    if [ ! -d "$HELM_CHART_PATH" ]; then
        print_error "Helm chart not found at $HELM_CHART_PATH"
        print_info "Please ensure the KubeRAG helm chart is in the current directory"
        exit 1
    fi

    # Install or upgrade the release
    print_info "Installing KubeRAG..."
    echo

    if helm list -n $NAMESPACE | grep -q "^$RELEASE_NAME"; then
        print_info "Release exists. Upgrading..."
        helm upgrade $RELEASE_NAME $HELM_CHART_PATH \
            --namespace $NAMESPACE \
            --values $VALUES_FILE \
            --wait \
            --timeout 10m
    else
        helm install $RELEASE_NAME $HELM_CHART_PATH \
            --namespace $NAMESPACE \
            --values $VALUES_FILE \
            --create-namespace \
            --wait \
            --timeout 10m
    fi

    if [ $? -eq 0 ]; then
        print_success "KubeRAG installed successfully!"
        echo
        display_post_install_info
    else
        print_error "Installation failed. Please check the logs."
        exit 1
    fi
}

# Function to display post-installation information
display_post_install_info() {
    print_header "Installation Complete!"

    echo -e "${GREEN}KubeRAG has been successfully deployed!${NC}"
    echo
    echo -e "${WHITE}Access Information:${NC}"
    echo

    # Get service endpoints
    local services=$(kubectl get svc -n $NAMESPACE -o wide)

    # Agent service
    local agent_port=$(kubectl get svc -n $NAMESPACE -l app=agent -o jsonpath='{.items[0].spec.ports[0].nodePort}' 2>/dev/null)
    if [ ! -z "$agent_port" ]; then
        echo -e "  ${CYAN}Agent API:${NC}      http://localhost:$agent_port"
    fi

    # Pipeline service
    local pipeline_port=$(kubectl get svc -n $NAMESPACE -l app=pipeline -o jsonpath='{.items[0].spec.ports[0].nodePort}' 2>/dev/null)
    if [ ! -z "$pipeline_port" ]; then
        echo -e "  ${CYAN}Pipeline API:${NC}   http://localhost:$pipeline_port"
    fi

    # UI service
    if [ "$ENABLE_UI" = "y" ]; then
        echo -e "  ${CYAN}Web UI:${NC}         http://localhost:$UI_PORT"
    fi

    # Vector store service
    case $SELECTED_VECTOR in
        "qdrant")
            if [ "$DEPLOY_QDRANT" = "y" ]; then
                echo -e "  ${CYAN}Qdrant UI:${NC}      http://localhost:30333"
            fi
            ;;
    esac

    # Monitoring
    if [ "$ENABLE_MONITORING" = "y" ]; then
        echo -e "  ${CYAN}Grafana:${NC}        http://localhost:30300"
    fi

    echo
    echo -e "${WHITE}Useful Commands:${NC}"
    echo
    echo -e "  ${CYAN}Check pods:${NC}       kubectl get pods -n $NAMESPACE"
    echo -e "  ${CYAN}Check services:${NC}   kubectl get svc -n $NAMESPACE"
    echo -e "  ${CYAN}View logs:${NC}        kubectl logs -n $NAMESPACE -l app=agent"
    echo -e "  ${CYAN}Test services:${NC}    ./test-kuberag-services.sh"
    echo
    echo -e "${WHITE}Configuration saved to:${NC} $VALUES_FILE"
    echo
    echo -e "${GREEN}Thank you for using KubeRAG!${NC}"
}

# Function for quick setup templates
quick_setup() {
    print_header "Quick Setup Templates"

    echo "Select a pre-configured template:"
    echo
    echo "  1) ${GREEN}Production Ready${NC} - Azure OpenAI + Qdrant"
    echo "  2) ${CYAN}Enterprise${NC} - OpenAI + MongoDB"
    echo "  3) ${YELLOW}Development${NC} - Ollama + FAISS"
    echo "  4) ${MAGENTA}Research${NC} - Anthropic + ChromaDB"
    echo "  5) ${BLUE}Analytics${NC} - Gemini + Elasticsearch"
    echo

    read -p "Select template [1-5]: " template_choice

    case $template_choice in
        1)
            SELECTED_LLM="azure_openai"
            SELECTED_VECTOR="qdrant"
            print_info "Using Production template: Azure OpenAI + Qdrant"
            ;;
        2)
            SELECTED_LLM="openai"
            SELECTED_VECTOR="mongodb"
            print_info "Using Enterprise template: OpenAI + MongoDB"
            ;;
        3)
            SELECTED_LLM="ollama"
            SELECTED_VECTOR="faiss"
            print_info "Using Development template: Ollama + FAISS"
            ;;
        4)
            SELECTED_LLM="anthropic"
            SELECTED_VECTOR="chroma"
            print_info "Using Research template: Anthropic + ChromaDB"
            ;;
        5)
            SELECTED_LLM="gemini"
            SELECTED_VECTOR="elasticsearch"
            print_info "Using Analytics template: Gemini + Elasticsearch"
            ;;
        *)
            print_warning "Invalid choice. Using Production template."
            SELECTED_LLM="azure_openai"
            SELECTED_VECTOR="qdrant"
            ;;
    esac

    echo
}

# Function to load existing configuration
load_configuration() {
    if [ -f "$1" ]; then
        print_info "Loading configuration from $1"
        cp "$1" $VALUES_FILE
        print_success "Configuration loaded"
        return 0
    else
        print_error "Configuration file not found: $1"
        return 1
    fi
}

# Main execution flow
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config|-c)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --namespace|-n)
                NAMESPACE="$2"
                shift 2
                ;;
            --release|-r)
                RELEASE_NAME="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  -c, --config FILE    Load configuration from file"
                echo "  -n, --namespace NS   Set Kubernetes namespace"
                echo "  -r, --release NAME   Set Helm release name"
                echo "  -h, --help          Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Display banner
    display_banner

    # Check prerequisites
    check_prerequisites

    # If config file provided, load it and install
    if [ ! -z "$CONFIG_FILE" ]; then
        if load_configuration "$CONFIG_FILE"; then
            perform_installation
        fi
        exit $?
    fi

    # Interactive mode
    select_deployment_mode

    case $DEPLOYMENT_MODE in
        "quick")
            quick_setup
            configure_llm_settings
            configure_vector_store_settings
            configure_general_settings
            ;;
        "custom")
            select_llm_provider
            configure_llm_settings
            select_vector_store
            configure_vector_store_settings
            configure_general_settings
            ;;
        "advanced")
            print_info "Advanced mode: Please edit the generated values.yaml file manually"
            select_llm_provider
            select_vector_store
            configure_general_settings
            ;;
    esac

    # Generate values.yaml
    generate_values_yaml

    # Perform installation
    perform_installation
}

# Run main function
main "$@"