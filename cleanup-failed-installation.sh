#!/bin/bash

# Cleanup script for failed KubeRAG installations
# Handles namespace ownership issues

set -e

NAMESPACE="${1:-kuberag-wizard1}"
RELEASE_NAME="${2:-kuberag-wizard1}"

# Also clean up all kuberag-related namespaces if no specific namespace provided
if [ "$1" = "--all" ]; then
    echo "Cleaning up ALL KubeRAG namespaces..."
    for ns in $(kubectl get namespaces -o name | grep kuberag | cut -d'/' -f2); do
        echo "Cleaning up namespace: $ns"
        helm uninstall $(helm list -n $ns -q) -n $ns 2>/dev/null || true
        kubectl delete namespace $ns --force --grace-period=0
    done
    echo "All KubeRAG namespaces cleaned up!"
    exit 0
fi

echo "Cleaning up failed KubeRAG installation..."
echo "  Namespace: $NAMESPACE"
echo "  Release: $RELEASE_NAME"
echo

# Check if release exists and remove it
if helm list -n $NAMESPACE 2>/dev/null | grep -q "^$RELEASE_NAME"; then
    echo "Removing existing Helm release..."
    helm uninstall $RELEASE_NAME -n $NAMESPACE
    sleep 5
fi

# Check if namespace exists and remove it if not managed by Helm
if kubectl get namespace $NAMESPACE &>/dev/null; then
    MANAGED_BY=$(kubectl get namespace $NAMESPACE -o jsonpath='{.metadata.labels.app\.kubernetes\.io/managed-by}' 2>/dev/null || echo "")

    if [ "$MANAGED_BY" != "Helm" ]; then
        echo "Namespace not managed by Helm. Deleting namespace..."
        kubectl delete namespace $NAMESPACE --ignore-not-found=true

        # Wait for complete deletion
        echo -n "Waiting for namespace deletion"
        while kubectl get namespace $NAMESPACE &>/dev/null; do
            echo -n "."
            sleep 2
        done
        echo " Done!"
    else
        echo "Namespace is properly managed by Helm."
    fi
else
    echo "Namespace does not exist."
fi

echo
echo "✓ Cleanup completed!"
echo
echo "You can now run the installation again:"
echo "  ./kuberag-wizard.sh"
echo "  or"
echo "  ./retry-installation.sh my-kuberag-values.yaml $RELEASE_NAME"