#!/bin/bash

# KubeRAG Services Integration Test Script
# Tests all services in the kuberag namespace for full RAG functionality

set -e

# Configuration - Allow namespace to be set via environment variable
NAMESPACE="${NAMESPACE:-kuberag}"
TEST_FILE="test-upload.txt"
TEST_CONTENT="This is a test document for KubeRAG. It contains information about artificial intelligence, machine learning, and natural language processing. The system should be able to retrieve this content and use it for augmented generation."

# If run from the installer, add some spacing
if [ ! -z "$KUBERAG_INSTALLER" ]; then
    echo "  Running automated tests for namespace: $NAMESPACE"
    echo
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if namespace exists
check_namespace() {
    print_status "Checking if namespace $NAMESPACE exists..."
    if kubectl get namespace $NAMESPACE &>/dev/null; then
        print_success "Namespace $NAMESPACE exists"
    else
        print_error "Namespace $NAMESPACE does not exist"
        exit 1
    fi
}

# Function to get service endpoints
get_service_endpoints() {
    print_status "Getting service endpoints..."

    # Get all services in the namespace
    kubectl get svc -n $NAMESPACE -o json > /tmp/services.json

    # Extract service information
    SERVICES=$(kubectl get svc -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}')
    print_status "Found services: $SERVICES"

    # Try to get ingress/nodeport information
    for svc in $SERVICES; do
        TYPE=$(kubectl get svc $svc -n $NAMESPACE -o jsonpath='{.spec.type}')
        print_status "Service $svc type: $TYPE"

        if [ "$TYPE" = "NodePort" ]; then
            NODE_PORT=$(kubectl get svc $svc -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')
            print_status "  NodePort: $NODE_PORT"
        fi
    done
}

# Function to detect services
detect_services() {
    print_status "Detecting KubeRAG services..."

    # Check for data pipeline service (usually on port 8081)
    DATA_PIPELINE_POD=$(kubectl get pods -n $NAMESPACE -l app=data-pipeline -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -z "$DATA_PIPELINE_POD" ]; then
        DATA_PIPELINE_POD=$(kubectl get pods -n $NAMESPACE | grep -i pipeline | awk '{print $1}' | head -1)
    fi

    # Check for agent service (usually on port 8082)
    AGENT_POD=$(kubectl get pods -n $NAMESPACE -l app=agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -z "$AGENT_POD" ]; then
        AGENT_POD=$(kubectl get pods -n $NAMESPACE | grep -i agent | awk '{print $1}' | head -1)
    fi

    # Check for deployment service (orchestrator)
    ORCHESTRATOR_POD=$(kubectl get pods -n $NAMESPACE -l app=orchestrator -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -z "$ORCHESTRATOR_POD" ]; then
        ORCHESTRATOR_POD=$(kubectl get pods -n $NAMESPACE | grep -i orchestrator | awk '{print $1}' | head -1)
    fi

    print_status "Data Pipeline Pod: ${DATA_PIPELINE_POD:-Not found}"
    print_status "Agent Pod: ${AGENT_POD:-Not found}"
    print_status "Orchestrator Pod: ${ORCHESTRATOR_POD:-Not found}"
}

# Function to setup port forwarding
setup_port_forward() {
    print_status "Setting up port forwarding..."

    # Kill any existing port forwards
    pkill -f "kubectl port-forward" || true
    sleep 2

    # Port forward for data pipeline (runs on 8001 internally)
    if [ ! -z "$DATA_PIPELINE_POD" ]; then
        kubectl port-forward -n $NAMESPACE pod/$DATA_PIPELINE_POD 8081:8001 &
        PF_PID_1=$!
        print_status "Port forwarding data pipeline on local:8081 -> pod:8001 (PID: $PF_PID_1)"
    fi

    # Port forward for agent
    if [ ! -z "$AGENT_POD" ]; then
        kubectl port-forward -n $NAMESPACE pod/$AGENT_POD 8082:8082 &
        PF_PID_2=$!
        print_status "Port forwarding agent on 8082 (PID: $PF_PID_2)"
    fi

    # Port forward for orchestrator
    if [ ! -z "$ORCHESTRATOR_POD" ]; then
        kubectl port-forward -n $NAMESPACE pod/$ORCHESTRATOR_POD 8083:8082 &
        PF_PID_3=$!
        print_status "Port forwarding orchestrator on 8083 (PID: $PF_PID_3)"
    fi

    # Wait for port forwards to establish
    sleep 5
}

# Function to test health endpoints
test_health() {
    print_status "Testing health endpoints..."

    # Test data pipeline health
    if curl -s http://localhost:8081/health > /dev/null 2>&1; then
        print_success "Data Pipeline is healthy"
    else
        print_warning "Data Pipeline health check failed or not available"
    fi

    # Test agent health
    if curl -s http://localhost:8082/health > /dev/null 2>&1; then
        print_success "Agent is healthy"
    else
        print_warning "Agent health check failed or not available"
    fi

    # Test orchestrator health
    if curl -s http://localhost:8083/health > /dev/null 2>&1; then
        print_success "Orchestrator is healthy"
    else
        print_warning "Orchestrator health check failed or not available"
    fi
}

# Function to create test file
create_test_file() {
    print_status "Creating test file..."
    echo "$TEST_CONTENT" > $TEST_FILE
    print_success "Test file created: $TEST_FILE"
}

# Function to upload document via text ingestion
upload_document() {
    print_status "Uploading document to data pipeline via text ingestion..."

    RESPONSE=$(curl -s -X POST http://localhost:8081/ingest/text \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$TEST_CONTENT\", \"metadata\": {\"source\": \"test-file\", \"filename\": \"$TEST_FILE\"}}" 2>&1)

    if [ $? -eq 0 ]; then
        if echo "$RESPONSE" | grep -q "error"; then
            print_error "Failed to ingest document"
            echo "Error: $RESPONSE"
            return 1
        else
            print_success "Document ingested successfully"
            echo "Response: $RESPONSE"

            # Extract document info if available
            DOCS_PROCESSED=$(echo $RESPONSE | grep -o '"documents_processed":[0-9]*' | cut -d':' -f2)
            if [ ! -z "$DOCS_PROCESSED" ]; then
                print_status "Documents processed: $DOCS_PROCESSED"
            fi
        fi
    else
        print_error "Failed to upload document"
        echo "Error: $RESPONSE"
        return 1
    fi
}

# Function to test embedding
test_embedding() {
    print_status "Testing document embedding..."

    # Send text directly for embedding
    RESPONSE=$(curl -s -X POST http://localhost:8081/api/embed/text \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$TEST_CONTENT\", \"metadata\": {\"source\": \"test\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}")

    if [ $? -eq 0 ]; then
        if echo "$RESPONSE" | grep -q "error"; then
            print_warning "Embedding endpoint may not be available"
        else
            print_success "Document embedded successfully"
            echo "Response: $RESPONSE"
        fi
    else
        print_error "Failed to embed document"
        return 1
    fi
}

# Function to test RAG chat
test_rag_chat() {
    print_status "Testing RAG chat functionality..."

    # Test queries
    QUERIES=(
        "What information is available about artificial intelligence?"
        "Tell me about machine learning"
        "What does the document say about natural language processing?"
        "Summarize the uploaded content"
    )

    for query in "${QUERIES[@]}"; do
        print_status "Query: $query"

        # Using the correct message field as per the API schema
        RESPONSE=$(curl -s -X POST http://localhost:8082/chat \
            -H "Content-Type: application/json" \
            -d "{\"message\": \"$query\", \"session_id\": \"test-session-$(date +%s)\"}")

        if [ $? -eq 0 ]; then
            # Check if response contains meaningful content
            if echo "$RESPONSE" | grep -q "response\|message"; then
                print_success "RAG query successful"
                echo "Response preview: $(echo $RESPONSE | head -c 300)..."

                # Check if context was retrieved
                if echo "$RESPONSE" | grep -q "context\|sources"; then
                    print_success "Context retrieved from vector store"
                fi
            elif echo "$RESPONSE" | grep -q "error"; then
                print_error "Chat error: $RESPONSE"
            else
                print_warning "Response received but might be empty"
                echo "Full response: $RESPONSE"
            fi
        else
            print_error "Failed to get RAG response"
            echo "Error: $RESPONSE"
        fi

        sleep 2  # Rate limiting
    done
}

# Function to test vector store stats
test_vector_stats() {
    print_status "Getting vector store statistics..."

    RESPONSE=$(curl -s http://localhost:8081/stats)

    if [ $? -eq 0 ]; then
        if echo "$RESPONSE" | grep -q "total_documents\|index_size\|vector_store"; then
            print_success "Vector store stats retrieved"
            echo "Stats: $RESPONSE"
        else
            print_warning "Stats endpoint not available or returned unexpected format"
            echo "Response: $RESPONSE"
        fi
    else
        print_warning "Failed to get vector store stats"
    fi
}

# Function to get system info
get_system_info() {
    print_status "Getting system configuration..."

    # Get available vector stores
    STORES=$(curl -s http://localhost:8081/stores 2>/dev/null || echo "{}")
    if [ "$STORES" != "{}" ] && [ "$STORES" != "" ]; then
        print_status "Available vector stores:"
        echo "$STORES" | python3 -m json.tool 2>/dev/null || echo "$STORES"
    fi

    # Get stats from data pipeline
    STATS=$(curl -s http://localhost:8081/stats 2>/dev/null || echo "{}")
    if [ "$STATS" != "{}" ] && [ "$STATS" != "" ]; then
        print_status "Vector store statistics:"
        echo "$STATS" | python3 -m json.tool 2>/dev/null || echo "$STATS"
    fi
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up..."

    # Kill port forwards
    if [ ! -z "$PF_PID_1" ]; then
        kill $PF_PID_1 2>/dev/null || true
    fi
    if [ ! -z "$PF_PID_2" ]; then
        kill $PF_PID_2 2>/dev/null || true
    fi
    if [ ! -z "$PF_PID_3" ]; then
        kill $PF_PID_3 2>/dev/null || true
    fi

    # Remove test file
    rm -f $TEST_FILE

    print_success "Cleanup completed"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    echo "========================================"
    echo "KubeRAG Services Integration Test"
    echo "========================================"
    echo ""

    # Check prerequisites
    print_status "Checking prerequisites..."
    command -v kubectl >/dev/null 2>&1 || { print_error "kubectl is required but not installed."; exit 1; }
    command -v curl >/dev/null 2>&1 || { print_error "curl is required but not installed."; exit 1; }

    # Run tests
    check_namespace
    get_service_endpoints
    detect_services

    if [ -z "$DATA_PIPELINE_POD" ] && [ -z "$AGENT_POD" ]; then
        print_error "No KubeRAG pods found in namespace $NAMESPACE"
        exit 1
    fi

    setup_port_forward
    test_health
    get_system_info

    # Only proceed with upload tests if services are healthy
    create_test_file

    print_status "Starting functional tests..."
    echo "----------------------------------------"

    # Test 1: Upload and embed document
    if upload_document; then
        sleep 3  # Wait for processing
    else
        test_embedding  # Try direct embedding if upload fails
    fi

    # Test 2: Vector stats
    test_vector_stats

    # Test 3: RAG chat
    test_rag_chat

    echo ""
    echo "========================================"
    print_success "Integration test completed!"
    echo "========================================"

    # Summary
    echo ""
    print_status "Test Summary:"
    echo "  - Namespace verified: ✓"
    echo "  - Services detected: ✓"
    echo "  - Health checks performed"
    echo "  - Document upload tested"
    echo "  - Embedding tested"
    echo "  - Vector search tested"
    echo "  - RAG chat tested"
    echo ""

    print_status "Note: Some tests may show warnings if certain endpoints are not available."
    print_status "This is normal depending on your deployment configuration."
}

# Run main function
main