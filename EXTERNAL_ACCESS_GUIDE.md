# KubeRAG External Access Troubleshooting Guide

## Problem: Curl works inside cluster but not from external UI

This guide provides multiple solutions based on your Kubernetes setup.

## Quick Diagnosis Commands

```bash
# Check services
kubectl get services -n <your-namespace>

# Check ingress
kubectl get ingress -n <your-namespace>

# Check pods
kubectl get pods -n <your-namespace>

# Check service endpoints
kubectl get endpoints -n <your-namespace>
```

## Solution 1: Using LoadBalancer (Recommended for Cloud)

### Configuration
Set in your values.yaml:
```yaml
SERVICE_TYPE: LoadBalancer
```

### Deploy and Get External IP
```bash
helm upgrade --install kuberag ./KubeRag --values ./KubeRag/values.yaml

# Wait for external IP
kubectl get services -n <namespace> --watch

# Access via external IP
curl http://<EXTERNAL-IP>/agent/health
curl http://<EXTERNAL-IP>/data/health
```

## Solution 2: Using NodePort (For Local/Development)

### Configuration
Set in your values.yaml:
```yaml
SERVICE_TYPE: NodePort
AGENT_NODE_PORT: 30080
DATA_NODE_PORT: 30081
```

### Deploy and Access
```bash
helm upgrade --install kuberag ./KubeRag --values ./KubeRag/values.yaml

# Get node IP
kubectl get nodes -o wide

# Access via node IP and port
curl http://<NODE-IP>:30080/health  # Agent service
curl http://<NODE-IP>:30081/health  # Data service
```

## Solution 3: Using Ingress (For Production with Domain)

### Prerequisites
- Ingress controller installed (nginx, traefik, etc.)
- Domain name configured

### Configuration
Set in your values.yaml:
```yaml
SERVICE_TYPE: ClusterIP
INGRESS_HOST: "kuberag.yourdomain.com"
INGRESS_CLASS_NAME: "nginx"
```

### Deploy and Access
```bash
helm upgrade --install kuberag ./KubeRag --values ./KubeRag/values.yaml

# Access via domain
curl https://kuberag.yourdomain.com/agent/health
curl https://kuberag.yourdomain.com/data/health
```

## Solution 4: Port Forwarding (For Testing)

```bash
# Forward agent service
kubectl port-forward service/kuberag-agent-service 8080:80 -n <namespace>

# Forward data service
kubectl port-forward service/kuberag-data-pipeline-service 8081:80 -n <namespace>

# Test locally
curl http://localhost:8080/health
curl http://localhost:8081/health
```

## Common Issues and Fixes

### Issue 1: Service Not Found
```bash
# Check service exists
kubectl get services -n <namespace>

# Check labels match
kubectl describe service <service-name> -n <namespace>
kubectl get pods -l app=<release-name> -n <namespace>
```

### Issue 2: No External IP (LoadBalancer Pending)
```bash
# Check LoadBalancer support
kubectl get services -n <namespace>

# If EXTERNAL-IP shows <pending>, use NodePort instead
```

### Issue 3: Ingress Not Working
```bash
# Check ingress controller is installed
kubectl get pods -n ingress-nginx

# Check ingress configuration
kubectl describe ingress -n <namespace>

# Check DNS resolution
nslookup <your-domain>
```

### Issue 4: Connection Refused
```bash
# Check pod is running
kubectl get pods -n <namespace>

# Check pod logs
kubectl logs <pod-name> -n <namespace>

# Check service endpoints
kubectl get endpoints -n <namespace>
```

## Debugging Steps

1. **Verify pod is running and healthy**
   ```bash
   kubectl get pods -n <namespace>
   kubectl logs <pod-name> -n <namespace>
   ```

2. **Test service connectivity from within cluster**
   ```bash
   kubectl run test-pod --rm -i --tty --image=busybox -- /bin/sh
   # Inside the pod:
   wget -qO- http://<service-name>.<namespace>.svc.cluster.local/health
   ```

3. **Check service configuration**
   ```bash
   kubectl describe service <service-name> -n <namespace>
   ```

4. **Verify network policies (if any)**
   ```bash
   kubectl get networkpolicy -n <namespace>
   ```

## Final Verification

Once configured, test external access:

```bash
# For LoadBalancer
curl http://<EXTERNAL-IP>/agent/health

# For NodePort
curl http://<NODE-IP>:<NODE-PORT>/health

# For Ingress
curl https://<DOMAIN>/agent/health
```

## UI Configuration

Update your UI configuration to point to the correct external endpoint:
- LoadBalancer: `http://<EXTERNAL-IP>`
- NodePort: `http://<NODE-IP>:<NODE-PORT>`
- Ingress: `https://<DOMAIN>`