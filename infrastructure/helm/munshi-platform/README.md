# Munshi Platform Helm Chart

This Helm chart deploys the complete Munshi Language Learning Platform on Kubernetes.

## Overview

The Munshi platform consists of multiple microservices:

- **Auth Service** - User authentication and authorization
- **Audio Service** - Audio file processing and storage
- **ASR Service** - Automatic Speech Recognition using Whisper
- **Conversation Service** - Conversation management
- **LLM Service** - Large Language Model integration (Gemini/OpenAI)
- **Pronunciation Evaluator** - Speech pronunciation analysis
- **UI Service** - React-based frontend application

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure
- NGINX Ingress Controller (required for HTTPS ingress)
- cert-manager (required for automatic TLS certificate management)

## Installing the Chart

### Development Environment

```bash
# Install cert-manager first (if not already installed)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.1/cert-manager.yaml

# Add required repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install dependencies
helm dependency update

# Install the chart for development with HTTPS
helm install munshi-dev . -f values-development.yaml --namespace munshi-dev --create-namespace
```

### Staging Environment

```bash
# Install for staging
helm install munshi-staging . -f values-staging.yaml --namespace munshi-staging --create-namespace
```

### Production Environment

```bash
# Set production secrets first (see Security section below)
kubectl create namespace munshi-prod

# Create external secrets (example)
kubectl create secret generic database-credentials \
  --from-literal=auth-db-url="postgresql://user:pass@db-host:5432/munshi_auth" \
  --from-literal=audio-db-url="postgresql://user:pass@db-host:5432/munshi_audio" \
  --from-literal=conversation-db-url="postgresql://user:pass@db-host:5432/munshi_conversation" \
  --namespace munshi-prod

# Install for production
helm install munshi-prod . -f values-production.yaml --namespace munshi-prod
```

## Configuration

### Values Files

- `values.yaml` - Default configuration
- `values-development.yaml` - Development overrides
- `values-staging.yaml` - Staging overrides  
- `values-production.yaml` - Production overrides

### Key Configuration Options

#### Service Configuration

Each service can be configured with:

```yaml
services:
  serviceName:
    enabled: true/false
    replicas: 2
    image:
      repository: munshi/service-name
      tag: latest
    resources:
      limits:
        cpu: 500m
        memory: 512Mi
      requests:
        cpu: 100m
        memory: 128Mi
    env:
      - name: ENV_VAR
        value: "value"
```

#### Database Configuration

```yaml
postgresql:
  enabled: true  # Set to false for external database
  auth:
    postgresPassword: "password"
    database: "munshi"
```

#### Redis Configuration

```yaml
redis:
  enabled: true  # Set to false for external Redis
  auth:
    enabled: true
    password: "password"
```

#### Ingress Configuration

```yaml
ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: munshi.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: munshi-tls
      hosts:
        - munshi.example.com
```

## HTTPS Configuration

The platform is configured with HTTPS enabled by default across all environments:

### Development
- Uses self-signed certificates via cert-manager
- Automatic certificate generation for `munshi.local`
- HTTPS redirects enabled

### Staging
- Uses Let's Encrypt staging certificates
- Automatic certificate generation for `staging.munshi.app`
- Full HTTPS security headers

### Production
- Uses Let's Encrypt production certificates
- Automatic certificate generation for `api.munshi.app`
- Full security headers including HSTS

### TLS Certificate Management

The chart automatically creates TLS certificates using cert-manager:

```yaml
certManager:
  enabled: true
  email: admin@example.com  # Required for Let's Encrypt
```

### Security Headers

All HTTPS endpoints include security headers:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` (production)

## Security

### Secrets Management

For production deployments, manage secrets externally:

1. **Database Credentials**
   ```bash
   kubectl create secret generic database-credentials \
     --from-literal=auth-db-url="postgresql://..." \
     --from-literal=audio-db-url="postgresql://..." \
     --from-literal=conversation-db-url="postgresql://..."
   ```

2. **Authentication Secrets**
   ```bash
   kubectl create secret generic auth-secrets \
     --from-literal=jwt-secret="your-strong-jwt-secret"
   ```

3. **LLM API Keys**
   ```bash
   kubectl create secret generic llm-secrets \
     --from-literal=google-api-key="your-google-api-key" \
     --from-literal=openai-api-key="your-openai-api-key"
   ```

### Network Policies

Enable network policies in production:

```yaml
networkPolicy:
  enabled: true
```

## Monitoring

Enable monitoring with Prometheus:

```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    labels:
      release: prometheus
```

## Scaling

### Horizontal Pod Autoscaler

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

### Pod Disruption Budget

```yaml
podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

## Upgrades

```bash
# Upgrade the deployment
helm upgrade munshi-dev . -f values-development.yaml

# Rollback if needed
helm rollback munshi-dev 1
```

## Uninstalling

```bash
# Uninstall the chart
helm uninstall munshi-dev --namespace munshi-dev

# Clean up namespace
kubectl delete namespace munshi-dev
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n munshi-dev
kubectl describe pod <pod-name> -n munshi-dev
kubectl logs <pod-name> -n munshi-dev
```

### Check Services
```bash
kubectl get svc -n munshi-dev
kubectl describe svc <service-name> -n munshi-dev
```

### Check Ingress
```bash
kubectl get ingress -n munshi-dev
kubectl describe ingress <ingress-name> -n munshi-dev
```

### Common Issues

1. **Database Connection Issues**
   - Check database credentials in secrets
   - Verify database service is running
   - Check network connectivity

2. **Image Pull Issues**
   - Verify image names and tags
   - Check image registry credentials
   - Ensure images exist in registry

3. **Resource Issues**
   - Check node resources
   - Verify resource requests/limits
   - Scale down if needed

## Development

### Local Development with Kind

```bash
# Create kind cluster
kind create cluster --name munshi

# Load local images (if building locally)
kind load docker-image munshi/auth-service:latest --name munshi
kind load docker-image munshi/ui-service:latest --name munshi

# Install NGINX Ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Install the chart
helm install munshi-dev . -f values-development.yaml
```

## Contributing

1. Make changes to templates or values
2. Test with different environments
3. Update documentation
4. Submit pull request

## License

[Your License Here]