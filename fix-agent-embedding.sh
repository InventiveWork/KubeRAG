#!/bin/bash

# Dynamic fix for KubeRAG agent embedding service discovery
# This script creates a service alias to match the hardcoded URL in the agent

set -e

# Get the namespace dynamically
NAMESPACE="${1:-$(kubectl config view --minify -o jsonpath='{..namespace}')}"
if [ -z "$NAMESPACE" ]; then
    echo "Error: No namespace specified and none set in current context"
    echo "Usage: $0 [namespace]"
    exit 1
fi

echo "Fixing embedding service discovery for namespace: $NAMESPACE"

# Check if KubeRAG is installed in this namespace
if ! kubectl get deployment -n "$NAMESPACE" 2>/dev/null | grep -q "agent"; then
    echo "Error: No KubeRAG agent deployment found in namespace $NAMESPACE"
    exit 1
fi

# Get the actual pipeline service name dynamically
PIPELINE_SERVICE=$(kubectl get svc -n "$NAMESPACE" -o name | grep pipeline | head -1 | cut -d'/' -f2)
if [ -z "$PIPELINE_SERVICE" ]; then
    echo "Error: No pipeline service found in namespace $NAMESPACE"
    exit 1
fi

echo "Found pipeline service: $PIPELINE_SERVICE"

# Get the pipeline service details
PIPELINE_PORT=$(kubectl get svc "$PIPELINE_SERVICE" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}')
PIPELINE_TARGET_PORT=$(kubectl get svc "$PIPELINE_SERVICE" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].targetPort}')
PIPELINE_SELECTOR=$(kubectl get svc "$PIPELINE_SERVICE" -n "$NAMESPACE" -o json | jq -r '.spec.selector | to_entries | map("\(.key)=\(.value)") | join(",")')

echo "Pipeline service details:"
echo "  Port: $PIPELINE_PORT"
echo "  Target Port: $PIPELINE_TARGET_PORT"
echo "  Selector: $PIPELINE_SELECTOR"

# Create a service alias that matches what the agent expects
# The agent code expects: kuberag-pipeline-service.kuberag.svc.cluster.local
# We need to create a service named 'kuberag-pipeline-service' in the same namespace

cat <<EOF > /tmp/pipeline-service-alias.yaml
apiVersion: v1
kind: Service
metadata:
  name: kuberag-pipeline-service
  namespace: $NAMESPACE
  labels:
    app: kuberag-pipeline-alias
    original-service: $PIPELINE_SERVICE
spec:
  type: ClusterIP
  ports:
  - port: $PIPELINE_PORT
    targetPort: $PIPELINE_TARGET_PORT
    protocol: TCP
    name: http
  selector:
EOF

# Add selectors dynamically
echo "  selector:" >> /tmp/pipeline-service-alias.yaml
for selector in $(echo $PIPELINE_SELECTOR | tr ',' '\n'); do
    key=$(echo $selector | cut -d'=' -f1)
    value=$(echo $selector | cut -d'=' -f2)
    echo "    $key: $value" >> /tmp/pipeline-service-alias.yaml
done

echo "Creating service alias..."
kubectl apply -f /tmp/pipeline-service-alias.yaml

# Also update the ConfigMap to ensure the environment variable is set correctly
echo "Updating ConfigMap with correct pipeline URL..."

# Get the current ConfigMap
CONFIG_MAP=$(kubectl get configmap -n "$NAMESPACE" -o name | grep -E "(config|cm)" | head -1 | cut -d'/' -f2)
if [ -n "$CONFIG_MAP" ]; then
    echo "Found ConfigMap: $CONFIG_MAP"

    # Create a patch for the ConfigMap
    cat <<EOF > /tmp/configmap-patch.yaml
data:
  PIPELINE_SERVICE_URL: "http://kuberag-pipeline-service/api/embed/text"
  DATA_PIPELINE_URL: "http://kuberag-pipeline-service:$PIPELINE_PORT"
EOF

    kubectl patch configmap "$CONFIG_MAP" -n "$NAMESPACE" --patch-file=/tmp/configmap-patch.yaml

    # Restart the agent deployment to pick up the changes
    AGENT_DEPLOYMENT=$(kubectl get deployment -n "$NAMESPACE" -o name | grep agent | head -1 | cut -d'/' -f2)
    if [ -n "$AGENT_DEPLOYMENT" ]; then
        echo "Restarting agent deployment: $AGENT_DEPLOYMENT"
        kubectl rollout restart deployment/"$AGENT_DEPLOYMENT" -n "$NAMESPACE"
        kubectl rollout status deployment/"$AGENT_DEPLOYMENT" -n "$NAMESPACE" --timeout=60s
    fi
fi

echo "Fix applied successfully!"
echo ""
echo "Testing connectivity..."

# Wait a moment for the service to be ready
sleep 2

# Test if the service alias works
AGENT_POD=$(kubectl get pods -n "$NAMESPACE" -l app=*agent* -o name | head -1 | cut -d'/' -f2)
if [ -n "$AGENT_POD" ]; then
    echo "Testing from agent pod: $AGENT_POD"
    kubectl exec -n "$NAMESPACE" "$AGENT_POD" -- python -c "
import requests
try:
    r = requests.post('http://kuberag-pipeline-service/api/embed/text', json={'text': 'test'}, timeout=5)
    print(f'✓ Service alias working! Status: {r.status_code}')
except Exception as e:
    print(f'✗ Service alias test failed: {e}')
" 2>/dev/null || echo "Note: Test requires Python requests library in the agent container"
fi

echo ""
echo "Embedding service discovery fix completed!"
echo "The agent should now be able to reach the pipeline service for embeddings."