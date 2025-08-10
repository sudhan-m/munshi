# Munshi Helm Deployment

This directory contains Helm charts for deploying the Munshi microservices platform with integrated Linkerd service mesh.

## Prerequisites

- Kubernetes cluster (1.21+)
- Helm 3.8+
- kubectl configured for your cluster

## Quick Start

### Local Development (Docker Desktop)
```bash
# Deploy to Docker Desktop with auto image builds and port forwarding
./scripts/deploy-local.sh

# Just build images
./scripts/deploy-local.sh build

# Check status
./scripts/deploy-local.sh status
```

### Cloud Deployment (AWS/GCP/Azure)
```bash
# Deploy to production
./scripts/deploy-cloud.sh

# Deploy to staging
ENVIRONMENT=dev ./scripts/deploy-cloud.sh

# Deploy to development
ENVIRONMENT=staging ./scripts/deploy-cloud.sh

# Upgrade existing deployment
./scripts/deploy-cloud.sh upgrade
```

## Configuration Files

| File | Purpose |
|------|---------|
| `values.yaml` | Default production values |
| `values-local.yaml` | Local development overrides |
| `values-dev.yaml` | Development/staging environment |
| `values-prod.yaml` | Production-specific overrides |

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
  --values ./infrastructure/helm/munshi/values-prod.yaml
```

### Upgrade
```bash
helm upgrade munshi ./infrastructure/helm/munshi \
  --namespace munshi-prod \
  --values ./infrastructure/helm/munshi/values-prod.yaml
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

For local development with hot reloading:

1. Build and tag images locally
2. Use `values-local.yaml` with `imagePullPolicy: Never`
3. Deploy with local configuration

```bash
# Build images
docker build -t munshi/api-gateway:latest ./services/api-gateway/
docker build -t munshi/auth-service:latest ./services/auth-service/

# Deploy locally
ENVIRONMENT=local ./scripts/deploy.sh
```