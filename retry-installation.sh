#!/bin/bash

# KubeRAG Installation Retry Script
# Use this to retry a failed installation with the generated values

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

VALUES_FILE="${1:-my-kuberag-values.yaml}"
RELEASE_NAME="${2:-my-kuberag}"

if [ ! -f "$VALUES_FILE" ]; then
    echo -e "${YELLOW}Values file not found: $VALUES_FILE${NC}"
    echo "Usage: $0 [values-file] [release-name]"
    echo "Example: $0 my-kuberag-values.yaml my-kuberag"
    exit 1
fi

# Extract namespace and release name from values file
NAMESPACE=$(grep "^namespace:" "$VALUES_FILE" | cut -d'"' -f2 | cut -d"'" -f2 | awk '{print $2}')
NAMESPACE=${NAMESPACE:-kuberag}

echo -e "${BLUE}KubeRAG Installation Retry${NC}"
echo -e "${BLUE}=========================${NC}"
echo
echo "  Values file: $VALUES_FILE"
echo "  Release name: $RELEASE_NAME"
echo "  Namespace: $NAMESPACE"
echo

# Check if release already exists and needs to be cleaned up
if helm list -n $NAMESPACE | grep -q "^$RELEASE_NAME"; then
    echo -e "${YELLOW}Release $RELEASE_NAME already exists. Cleaning up first...${NC}"
    helm uninstall $RELEASE_NAME -n $NAMESPACE
    echo "Waiting for cleanup to complete..."
    sleep 10
fi

# Let Helm manage the namespace creation

echo "Installing KubeRAG..."
echo

if helm install $RELEASE_NAME ./KubeRag -f $VALUES_FILE -n $NAMESPACE --create-namespace --wait --timeout 10m; then
    echo
    echo -e "${GREEN}✓ Installation successful!${NC}"
    echo
    echo "Check status:"
    echo "  kubectl get pods -n $NAMESPACE"
    echo
    echo "Run tests:"
    echo "  ./test-kuberag-services.sh"
else
    echo
    echo -e "${YELLOW}Installation failed again.${NC}"
    echo
    echo "Common troubleshooting steps:"
    echo "1. Check cluster resources: kubectl describe nodes"
    echo "2. Check namespace events: kubectl get events -n $NAMESPACE"
    echo "3. Check pod logs: kubectl logs -n $NAMESPACE -l app=agent"
    echo "4. Verify API credentials in: $VALUES_FILE"
fi