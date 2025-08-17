# Munshi Platform - Complete Deployment Guide

This guide provides instructions for deploying the Munshi pronunciation profiling platform from scratch on Google Cloud Platform.

## Prerequisites

### Required Tools
- **Google Cloud SDK**: `gcloud` CLI authenticated with your GCP account
- **Docker**: For building container images (with `buildx` support recommended)
- **Terraform**: Infrastructure as Code tool
- **kubectl**: Kubernetes CLI
- **Helm**: Kubernetes package manager

### Required Accounts/Services
- **Google Cloud Project** with billing enabled
- **Google API Key** for Gemini LLM service

## Quick Start

### 1. Authentication and Setup

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set your project
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID
```

### 2. Configuration

```bash
# Set environment variables (recommended)
export GOOGLE_API_KEY="your-google-gemini-api-key"
export JWT_SECRET="your-super-secret-jwt-key-min-32-chars"  # Optional - will auto-generate if not set

# Navigate to infrastructure directory
cd infrastructure/terraform

# Update project configuration
vim terraform.tfvars
```

**Required in `terraform.tfvars`:**
```hcl
project_id = "your-gcp-project-id"
```

**Secrets (choose one method):**
- **Environment variables** (recommended):
  ```bash
  export GOOGLE_API_KEY="AIza..."
  export JWT_SECRET="your-secret"
  ```
- **Or in terraform.tfvars**:
  ```hcl
  google_api_key = "AIza..."
  jwt_secret = "your-secret"
  ```

### 3. Deploy Everything

```bash
# Make deployment script executable
chmod +x deploy-gcp.sh

# Deploy the entire platform
./deploy-gcp.sh
```

## What Gets Deployed

### Infrastructure Components
- **GKE Cluster** with multiple node pools:
  - General nodes (e2-medium) for core services
  - Memory-intensive nodes (e2-highmem-4) for LLM services
  - GPU nodes (n1-standard-4 + T4) for ASR service (auto-scaling to 0)
  - Database nodes (e2-standard-4) for persistent storage
- **Artifact Registry** for container images
- **Cloud Storage Bucket** for ML model storage
- **Service Accounts** with appropriate IAM permissions

### Application Services
- **UI Service** (React frontend) - Port 8002
- **Auth Service** (Authentication) - Port 8001
- **Audio Service** (Audio processing) - Port 8003
- **ASR Service** (Speech recognition with GPU) - Port 8004
- **LLM Service** (Language model with Gemini) - Port 8005
- **Pronunciation Evaluator** - Port 8006
- **Conversation Service** - Port 8007

### Data Stores
- **PostgreSQL** for authentication and user data
- **MongoDB** for conversation and application data
- **Redis** for caching and session storage

## Architecture Details

### Node Pool Configuration

1. **General Pool** (`e2-medium`):
   - Runs UI, Audio, and Pronunciation services
   - Auto-scales 1-10 nodes (2-10 in production)
   - Uses spot instances for cost optimization

2. **Memory-Intensive Pool** (`e2-highmem-4`):
   - Runs LLM service
   - Auto-scales 0-3 nodes
   - Tainted to prevent other workloads

3. **GPU Pool** (`n1-standard-4` + T4 GPU):
   - Runs ASR service exclusively
   - Auto-scales 0-2 nodes (scales to 0 when idle)
   - Automatically tainted for GPU workloads

4. **Database Pool** (`e2-standard-4`):
   - Runs PostgreSQL, MongoDB, Redis
   - Always-on for data persistence
   - No spot instances for reliability

### Database Initialization

The deployment automatically:
1. Creates PostgreSQL database `munshi_auth`
2. Creates user `munshi_user` with proper permissions
3. Grants schema permissions for table creation
4. Configures connection strings in services

### Image Building

All services are built for `linux/amd64` architecture using:
- Docker Buildx for multi-platform builds
- Automatic push to Artifact Registry
- Version tagging with timestamp + latest

## Verification Steps

After deployment, verify the system:

```bash
# Check all pods are running
kubectl get pods -n munshi-prod

# Check services
kubectl get services -n munshi-prod

# Monitor deployments
kubectl get pods -n munshi-prod -w

# Check ASR service can access GPU nodes
kubectl describe nodes | grep -A 5 "nvidia"

# Test database connectivity
kubectl exec -it deployment/auth-service -n munshi-prod -- \
  psql postgresql://munshi_user:munshi_password@munshi-platform-postgresql:5432/munshi_auth -c "SELECT 1;"
```

## Accessing the Application

### Port Forwarding (Development)
```bash
# Forward UI service
kubectl port-forward service/ui-service 8002:8002 -n munshi-prod

# Access at http://localhost:8002
```

### Load Balancer (Production)
```bash
# Get external IP (if ingress configured)
kubectl get ingress -n munshi-prod
```

## Troubleshooting

### Common Issues

1. **ASR Service Pending**: GPU nodes may take 3-5 minutes to provision
2. **Auth Service CrashLoop**: Database initialization may still be running
3. **Image Pull Errors**: Check Artifact Registry permissions
4. **Node Scheduling**: Services have specific node selectors and tolerations

### Useful Commands

```bash
# Check pod logs
kubectl logs -f deployment/auth-service -n munshi-prod

# Check node pool status
kubectl get nodes -o wide

# Check database initialization
kubectl logs job/database-init-* -n munshi-prod

# Restart a deployment
kubectl rollout restart deployment/auth-service -n munshi-prod
```

## Cleanup

To destroy everything:

```bash
# Delete Helm releases
helm uninstall munshi-platform -n munshi-prod

# Delete infrastructure
terraform destroy -auto-approve

# Delete container images (optional)
gcloud artifacts repositories delete munshi-containers --location=us-central1
```

## Cost Optimization

The deployment is optimized for cost:
- **Spot instances** for non-critical workloads (70% savings)
- **Auto-scaling to 0** for GPU nodes when idle
- **Regional persistent disks** instead of zonal
- **Minimal resource requests** with appropriate limits

**Estimated monthly cost for light usage**: $50-150 USD
**Estimated cost for production usage**: $200-500 USD

## Security Features

- **Private cluster** with authorized networks
- **Workload Identity** for secure GCP access
- **Node taints** to isolate workloads
- **Network policies** enabled
- **Secrets management** for sensitive data
- **Service accounts** with minimal permissions

## Next Steps

1. **Set up monitoring**: Add Prometheus/Grafana for observability
2. **Configure ingress**: Set up NGINX ingress for external access
3. **Add TLS certificates**: Enable cert-manager for HTTPS
4. **Set up CI/CD**: Automate deployments with GitHub Actions
5. **Configure backups**: Set up automated database backups