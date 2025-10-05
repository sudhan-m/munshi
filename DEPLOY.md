# Munshi Platform - Deployment Guide

## Prerequisites

### Required Tools
- **Google Cloud SDK**: `gcloud` CLI authenticated with your GCP account
- **Docker**: For building container images
- **Terraform**: Infrastructure as Code tool (v1.0+)
- **kubectl**: Kubernetes CLI
- **Helm**: Kubernetes package manager (v3+)

### Get a Google Gemini API Key
1. Visit: https://aistudio.google.com/apikey
2. Create a new API key (starts with "AIza")
3. Save it for configuration below

## Quick Start

### 1. Initialize Configuration
```bash
# Create terraform.tfvars from template
make init
```

### 2. Edit Configuration
Edit `infrastructure/terraform/terraform.tfvars` with your values:

```hcl
project_id      = "your-gcp-project-id"
google_api_key  = "AIzaSy..."  # From Google AI Studio
jwt_secret      = "your-random-32-char-secret"  # Optional - auto-generated if not set
```

**Important**:
- Your Gemini API key must start with `AIza` (get from https://aistudio.google.com/apikey)
- JWT secret will be auto-generated if not provided

### 3. Create Infrastructure
```bash
# Create GKE cluster and node pools (one-time setup, ~5-10 minutes)
make env-init
```

This command:
- ✅ Creates GKE cluster with 4 specialized node pools
- ✅ Sets up Artifact Registry for Docker images
- ✅ Configures Cloud Storage for ML models
- ✅ Enables required GCP APIs
- ✅ Uses spot instances for 54% cost savings
- ✅ **Idempotent**: Safe to run multiple times (skips existing resources)

### 4. Deploy Application
```bash
# Build, push, and deploy all services
make deploy
```

This command:
- ✅ Smart builds only changed services (saves time!)
- ✅ Pushes images to Artifact Registry
- ✅ Creates Kubernetes secrets
- ✅ Deploys with Helm (databases + 7 microservices)
- ✅ Sets up LoadBalancer for external access
- ✅ **Idempotent**: Safe to run after code changes

## Deployment Workflow

**For fresh deployment:**
```bash
make init        # 1. Create config file
# Edit terraform.tfvars
make env-init    # 2. Create infrastructure (one-time)
make deploy      # 3. Deploy application
```

**For code updates:**
```bash
# Just redeploy - smart-deploy only builds changed services
make deploy
```

**The two-step workflow (`make env-init` + `make deploy`) is the recommended approach.**

## What Gets Deployed

### Infrastructure
- **GKE Cluster**: Auto-scaling with 4 specialized node pools
- **Application Nodes**: Spot instances (54% cost savings)
- **GPU Nodes**: NVIDIA T4 for ASR service
- **Database Nodes**: On-demand for reliability
- **Artifact Registry**: Docker repository for container images

### Services
- **UI Service**: React frontend (port 8002)
- **Auth Service**: JWT authentication (port 8001)  
- **Audio Service**: File processing (port 8003)
- **ASR Service**: GPU speech recognition (port 8004)
- **LLM Service**: Gemini integration (port 8005)
- **Pronunciation Evaluator**: Analysis engine (port 8006)
- **Conversation Service**: Business logic (port 8007)

### Databases
- **PostgreSQL**: Auth and audio data
- **MongoDB**: User profiles and conversations
- **Redis**: Session cache

## Access Your Application

```bash
# Check deployment status
kubectl get pods -n munshi-prod

# Port forward to access locally
kubectl port-forward service/ui-service 8002:8002 -n munshi-prod

# View logs
kubectl logs -f deployment/ui-service -n munshi-prod
```

## Cost Optimization

The deployment uses **spot instances** by default for 54% cost savings:

- **Monthly cost**: ~$410 (down from $900)
- **Idle cost**: ~$20 (only databases running)
- **Interruption rate**: ~5% per month
- **Recovery time**: 30-60 seconds

To disable spot instances:
```bash
# Edit terraform.tfvars
use_spot_instances = false
```

## Troubleshooting

### Common Issues

**Images fail to build:**
```bash
# Check Docker is running
docker ps

# Retry build manually
cd services/ui-service
docker build -t test .
```

**Terraform fails:**
```bash
# Check GCP authentication
gcloud auth list

# Verify project ID
gcloud config get-value project
```

**Pods stuck pending:**
```bash
# Check node pools
kubectl get nodes

# Check resource requests
kubectl describe pod <pod-name> -n munshi-prod
```

### Cleanup

```bash
# Remove just the application (keep cluster)
make takedown

# Destroy everything (WARNING: Deletes all infrastructure)
make destroy
```

### Hassle-Free Infrastructure Management

The deployment commands handle common issues automatically:

**`make env-init`**:
- ✅ Detects existing clusters and imports them into Terraform state
- ✅ Creates missing node pools and infrastructure
- ✅ Handles state synchronization automatically
- ✅ Skips infrastructure creation if cluster already exists

**`make deploy`**:
- ✅ Smart-deploy only builds changed services (git diff)
- ✅ Handles existing namespaces and secrets gracefully
- ✅ Retries failed operations automatically
- ✅ Cleans up problematic pods before deployment

**`make destroy`**:
- ✅ Imports existing clusters before destroying (prevents state issues)
- ✅ Automatically disables deletion protection
- ✅ Falls back to manual cleanup if Terraform fails
- ✅ Ensures complete infrastructure removal

## Advanced Usage

### Update Secrets

**Update Gemini API Key:**
```bash
kubectl create secret generic google-api-keys \
  --from-literal=api-key="AIzaSyNEW_KEY_HERE" \
  -n munshi-prod --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deployment/llm-service -n munshi-prod
```

**Update JWT Secret:**
```bash
kubectl create secret generic jwt-secret \
  --from-literal=secret="$(openssl rand -base64 32)" \
  -n munshi-prod --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deployment/auth-service -n munshi-prod
```

### Individual Build Commands
```bash
make build       # Build all images (rebuilds everything - slow)
make push        # Push all images to registry
make deploy      # Deploy to GCP (uses smart-deploy by default)
make rebuild-all # Force rebuild all services (build + push)
```

**Notes**:
- `make deploy` uses smart-deploy automatically (only builds changed services)
- Use `make rebuild-all && make deploy` to force rebuild everything

### Scaling
```bash
# Scale replicas
kubectl scale deployment ui-service --replicas=5 -n munshi-prod

# Scale nodes
kubectl scale deployment cluster-autoscaler --replicas=2 -n kube-system
```

## Support

- **Issues**: Check logs with `kubectl logs`
- **Performance**: Monitor with `kubectl top nodes`
- **Costs**: Check GCP billing console
- **Updates**: Run `make gcp-deploy` again

The deployment is designed to be **simple**, **cost-effective**, and **production-ready** out of the box.