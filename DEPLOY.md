# Munshi Platform - Simple Deployment Guide

## Quick Start (3 minutes)

### 1. Initialize Configuration
```bash
# Create terraform.tfvars file
make init
```

### 2. Edit Configuration
```bash
# Edit infrastructure/terraform/terraform.tfvars with your values:
# - project_id: Your GCP project ID  
# - jwt_secret: Random 32-character string
# - google_api_key: Your Google Gemini API key
```

### 3. Create Infrastructure
```bash
# Create GCP cluster and node pools (one-time setup)
make env-init
```

### 4. Deploy Application
```bash
# Build, push, and deploy all services
make deploy
```

The deployment process:
- ✅ **env-init**: Creates GKE cluster with optimized node pools, Artifact Registry, and APIs (54% cost savings with spot instances)
- ✅ **deploy**: Builds images, pushes to registry, and deploys all services with Helm

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

# Rebuild infrastructure (destroy + recreate)
make destroy && make env-init
```

### Hassle-Free Infrastructure Management

The updated commands handle common issues automatically:

**`make env-init`**:
- ✅ Detects existing clusters and imports them into Terraform state
- ✅ Creates missing node pools and infrastructure
- ✅ Handles state synchronization automatically

**`make destroy`**:
- ✅ Imports existing clusters before destroying (prevents state issues)
- ✅ Automatically disables deletion protection
- ✅ Falls back to manual cleanup if Terraform fails
- ✅ Ensures complete infrastructure removal

## Advanced Configuration

### Environment Variables
Set these before deployment to override defaults:
```bash
export PROJECT_ID="my-project"
export CLUSTER_NAME="my-cluster"  
export REGION="us-west1"
export NAMESPACE="munshi-staging"
```

### Update Application Code
Rebuild and redeploy after code changes:
```bash
make redeploy
```

### Individual Commands
```bash
make build    # Build all images
make push     # Push to registry  
make deploy   # Deploy to GCP
```

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