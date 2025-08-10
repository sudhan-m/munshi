# Munshi Helm Deployment

This directory contains Helm charts for deploying the Munshi microservices platform with integrated Linkerd service mesh.

## Prerequisites

- Kubernetes cluster (1.21+)
- Helm 3.8+
- kubectl configured for your cluster

## Quick Start

The universal deployment script automatically detects your environment and deploys accordingly:

```bash
# Universal deployment - auto-detects environment and deploys
./scripts/deploy.sh

# Build images only (local environments)
./scripts/deploy.sh build

# Check deployment status
./scripts/deploy.sh status

# View application logs
./scripts/deploy.sh logs

# Upgrade existing deployment
./scripts/deploy.sh upgrade
```

### Environment Override
```bash
# Force specific environment (overrides auto-detection)
ENVIRONMENT=staging ./scripts/deploy.sh

# Force image building
BUILD_IMAGES=true ./scripts/deploy.sh

# Custom namespace
NAMESPACE=my-munshi ./scripts/deploy.sh
```

## Environment Detection

The deployment script automatically detects your environment:

- **Local**: Docker Desktop context (`docker-desktop`) or localhost clusters
- **Cloud**: Production, staging, or development based on context/cluster names
- **Fallback**: Unknown cloud environments default to production settings

## Configuration Files

| File | Purpose |
|------|---------|
| `values.yaml` | Production defaults (used for all cloud environments) |
| `values-local.yaml` | Local development overrides (Docker Desktop) |

## Key Features

### Linkerd Service Mesh Integration

The chart automatically installs and configures:
- Linkerd control plane
- Linkerd-viz (observability dashboard)
- Service mesh injection for all workloads
- mTLS encryption between services
- Traffic policies and load balancing

### Environment-Specific Configuration

Each environment has tailored:
- Resource limits and requests
- Replica counts
- Debug settings
- Service mesh proxy configurations
- Monitoring and observability settings

### Security Features

- Non-root containers
- Read-only root filesystems
- Dropped capabilities
- Pod Security Standards compliance
- mTLS encryption via Linkerd

## Manual Helm Commands

If you prefer manual deployment:

### Install
```bash
helm install munshi ./infrastructure/helm/munshi \
  --namespace munshi-prod \
  --create-namespace \
  --values ./infrastructure/helm/munshi/values.yaml
```

### Upgrade
```bash
helm upgrade munshi ./infrastructure/helm/munshi \
  --namespace munshi-prod \
  --values ./infrastructure/helm/munshi/values.yaml
```

### Uninstall
```bash
helm uninstall munshi --namespace munshi-prod
kubectl delete namespace munshi-prod
```

## Monitoring and Observability

When Linkerd is enabled, access the service mesh dashboard:

```bash
# Forward port to Linkerd dashboard
kubectl port-forward -n linkerd-viz svc/web 8080:8084

# Open browser to http://localhost:8080
```

View application logs:
```bash
# API Gateway logs
kubectl logs -n munshi-prod -l app=api-gateway -f

# Auth Service logs  
kubectl logs -n munshi-prod -l app=auth-service -f

# All application logs
kubectl logs -n munshi-prod -l app.kubernetes.io/name=munshi -f
```

## Customization

### Override Values

Create your own values file:
```bash
helm install munshi ./infrastructure/helm/munshi \
  --values ./infrastructure/helm/munshi/values.yaml \
  --values ./my-custom-values.yaml
```

### Disable Linkerd

Set `linkerd.enabled: false` in your values file:
```yaml
linkerd:
  enabled: false
```

### Resource Scaling

Adjust replica counts and resources in your values file:
```yaml
replicaCount:
  apiGateway: 5
  authService: 3

resources:
  apiGateway:
    requests:
      memory: "512Mi"
      cpu: "200m"
    limits:
      memory: "1Gi"
      cpu: "500m"
```

## Troubleshooting

### Check Deployment Status
```bash
./scripts/deploy.sh status
```

### Verify Linkerd Installation
```bash
linkerd check
```

### Debug Pod Issues
```bash
kubectl describe pod -n munshi-prod <pod-name>
kubectl logs -n munshi-prod <pod-name> -c <container-name>
```

### Check Service Mesh Status
```bash
linkerd stat -n munshi-prod
linkerd edges -n munshi-prod
```

## Development

The universal deployment script handles local development automatically:

```bash
# Automatically builds images and deploys with port forwarding
./scripts/deploy.sh

# Access your application
open http://localhost:8000

# Access Linkerd dashboard (if enabled)  
open http://localhost:50750
```

For manual image building:
```bash
./scripts/deploy.sh build
```