# Munshi Pronunciation Profiling Platform - GCP Deployment

This directory contains Terraform configurations for deploying the Munshi pronunciation profiling platform with Thompson Sampling bandits on Google Cloud Platform (GCP).

## 🎯 Features Deployed

### Pronunciation Profiling System
- **Thompson Sampling Bandits**: Adaptive phoneme targeting for personalized learning
- **Vector Space Modeling**: Phoneme-level tracking for English, Tamil, and Malayalam
- **LLM-Driven Strategy**: Mood detection and adaptive difficulty adjustment
- **Character-Level Analysis**: Precise mispronunciation detection and feedback
- **Real-time Profiling**: Live pronunciation profile updates during practice
- **MongoDB Integration**: Persistent storage for user pronunciation profiles

### Infrastructure Architecture
- **GKE Cluster**: Multi-node pool setup optimized for ML workloads
- **Artifact Registry**: Container image storage and management
- **Cloud Storage**: Audio files and ML model storage
- **Workload Identity**: Secure service-to-service authentication
- **Network Policies**: Enhanced security and traffic isolation

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   General Pool  │    │Memory Intensive │    │  Storage Layer  │
│                 │    │     Pool        │    │                 │
│ • UI Service    │    │ • LLM Service   │    │ • MongoDB Atlas │
│ • Auth Service  │    │ • ASR Service   │    │ • Cloud Storage │
│ • Audio Service │    │ • Pronunciation │    │ • Artifact Reg  │
│ • Conversation  │    │   Evaluator     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Prerequisites

1. **Google Cloud CLI**: Install and authenticate
   ```bash
   gcloud auth login
   gcloud config set project central-list-469110-f1
   ```

2. **Required Tools**:
   ```bash
   # Install via homebrew (macOS)
   brew install terraform kubectl helm docker
   ```

3. **MongoDB Atlas Account**: For pronunciation profile storage
   - Create cluster at [MongoDB Atlas](https://cloud.mongodb.com)
   - Note connection string, username, and password

4. **Google API Key**: For Gemini LLM service
   - Enable Gemini API in Google Cloud Console
   - Create API key for LLM service

## 🚀 Quick Deployment

### Option 1: Automated Deployment Script
```bash
# Make script executable
chmod +x deploy-gcp.sh

# Run complete deployment
./deploy-gcp.sh
```

### Option 2: Manual Step-by-Step

1. **Enable Required APIs**:
   ```bash
   gcloud services enable container.googleapis.com \
     artifactregistry.googleapis.com \
     storage.googleapis.com \
     iam.googleapis.com \
     compute.googleapis.com
   ```

2. **Configure Variables**:
   ```bash
   cp terraform-gcp.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Set Sensitive Variables**:
   ```bash
   export TF_VAR_mongodb_url="mongodb+srv://user:pass@cluster.mongodb.net/"
   export TF_VAR_mongodb_username="munshi_user"
   export TF_VAR_mongodb_password="your-secure-password"
   export TF_VAR_google_api_key="your-gemini-api-key"
   export TF_VAR_jwt_secret="your-256-bit-jwt-secret"
   export TF_VAR_postgres_auth_password="auth-password"
   export TF_VAR_postgres_gateway_password="gateway-password"
   ```

4. **Deploy Infrastructure**:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

5. **Get Cluster Access**:
   ```bash
   gcloud container clusters get-credentials munshi-cluster \
     --zone=us-central1-a --project=central-list-469110-f1
   ```

## 🔧 Configuration Details

### Cluster Configuration
- **General Node Pool**: `e2-standard-4` for general services
- **Memory-Intensive Pool**: `e2-highmem-4` for LLM/ASR services
- **Autoscaling**: 2-10 nodes (production), 1-5 nodes (development)
- **Security**: Private cluster with Workload Identity enabled

### Resource Allocation
```yaml
LLM Service:        1-2 GB RAM, 0.5-1 CPU
ASR Service:        2-4 GB RAM, 1-2 CPU  
Conversation:       512MB-1GB RAM, 200-500m CPU
Pronunciation:      256-512MB RAM, 200-500m CPU
```

### Storage Setup
- **Audio Storage**: Cloud Storage bucket with lifecycle policies
- **Model Storage**: Separate bucket for Whisper models
- **Database**: MongoDB Atlas for pronunciation profiles
- **Container Images**: Artifact Registry with cleanup policies

## 📊 Pronunciation Profiling APIs

After deployment, these endpoints are available:

### Core APIs
```bash
# Get pronunciation profile insights
GET /user/{user_id}/pronunciation-profile/{language}

# Generate practice sentences with target phonemes
POST /user/{user_id}/generate-sentence

# Evaluate pronunciation with profiling updates
POST /evaluate-pronunciation

# LLM strategy analysis for bandit selection
POST /analyze-strategy
```

### Example Response
```json
{
  "user_id": "user123",
  "language": "Tamil",
  "overall_accuracy": 0.78,
  "recommended_phonemes": ["க", "ச", "ர"],
  "weakest_phonemes": [
    {"phoneme": "ழ", "confidence": 0.23}
  ],
  "strongest_phonemes": [
    {"phoneme": "அ", "confidence": 0.91}
  ]
}
```

## 🏷️ Container Images

All services are built and pushed to Artifact Registry:
```
us-central1-docker.pkg.dev/central-list-469110-f1/munshi-containers/
├── munshi-conversation-service:latest
├── munshi-llm-service:latest
├── munshi-asr-service:latest
├── munshi-pronunciation-evaluator:latest
├── munshi-audio-service:latest
├── munshi-ui-service:latest
└── munshi-auth-service:latest
```

## 📈 Monitoring and Scaling

### View Deployment Status
```bash
# Check all pods
kubectl get pods -n munshi-prod

# Check services
kubectl get services -n munshi-prod

# View pronunciation profiling logs
kubectl logs -f deployment/conversation-service -n munshi-prod
```

### Test Pronunciation Profiling
```bash
# Port forward conversation service
kubectl port-forward service/conversation-service 8007:8007 -n munshi-prod

# Test profile endpoint
curl http://localhost:8007/user/test123/pronunciation-profile/Tamil
```

### Scale ML Services
```bash
# Scale LLM service for higher load
kubectl scale deployment llm-service --replicas=5 -n munshi-prod

# Scale ASR service for more concurrent requests  
kubectl scale deployment asr-service --replicas=3 -n munshi-prod
```

## 🔐 Security Features

### Network Security
- **Private GKE cluster** with authorized networks
- **Network policies** for pod-to-pod communication
- **Workload Identity** for secure GCP service access

### Data Security
- **MongoDB Atlas** with authentication and encryption
- **Kubernetes secrets** for sensitive configuration
- **Binary authorization** for container image security

### API Security
- **JWT authentication** for user sessions
- **Rate limiting** via Kubernetes ingress
- **HTTPS enforcement** with automatic SSL certificates

## 🎛️ Cost Optimization

### Development Environment
- **Spot instances**: 60-70% cost savings
- **Smaller resources**: Reduced memory/CPU allocation
- **Auto-shutdown**: Unused resource cleanup

### Production Environment  
- **Committed use discounts**: For predictable workloads
- **Autoscaling**: Dynamic resource adjustment
- **Storage lifecycle**: Automatic data archival

### Monitoring Costs
```bash
# Check current spending
gcloud billing accounts list
gcloud billing budgets list --billing-account=ACCOUNT_ID

# Monitor resource usage
kubectl top nodes
kubectl top pods -n munshi-prod
```

## 🧪 Testing Pronunciation Features

### Test Thompson Sampling Bandits
```bash
# Get user's current pronunciation profile
curl -X GET "http://localhost:8007/user/test123/pronunciation-profile/Tamil"

# Generate sentence with target phonemes  
curl -X POST "http://localhost:8007/user/test123/generate-sentence" \
  -H "Content-Type: application/json" \
  -d '{"language": "Tamil", "difficulty": "beginner"}'

# Simulate pronunciation evaluation
curl -X POST "http://localhost:8007/evaluate-pronunciation" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test123",
    "audio_file_id": "audio123", 
    "intended_text": "வணக்கம்",
    "language": "Tamil"
  }'
```

## 🛠️ Troubleshooting

### Common Issues

1. **Pod Scheduling on Memory-Intensive Pool**:
   ```bash
   kubectl describe pod <llm-service-pod> -n munshi-prod
   # Check if tolerations and nodeSelector are correct
   ```

2. **MongoDB Connection Issues**:
   ```bash
   kubectl logs deployment/conversation-service -n munshi-prod
   # Verify MongoDB Atlas connection string and credentials
   ```

3. **LLM Service API Key Issues**:
   ```bash
   kubectl get secret google-api-keys -n munshi-prod -o yaml
   # Verify Google API key is correctly configured
   ```

### Debug Pronunciation Profiling
```bash
# Check conversation service logs for bandit decisions
kubectl logs -f deployment/conversation-service -n munshi-prod | grep "bandit"

# Monitor pronunciation profile updates
kubectl logs -f deployment/conversation-service -n munshi-prod | grep "profile"

# Check LLM service for strategy analysis
kubectl logs -f deployment/llm-service -n munshi-prod | grep "strategy"
```

## 🧹 Cleanup

To remove all resources:
```bash
# Delete Kubernetes resources
helm uninstall munshi-platform -n munshi-prod

# Destroy GCP infrastructure
terraform destroy

# Clean up container images
gcloud artifacts repositories delete munshi-containers \
  --location=us-central1 --project=central-list-469110-f1
```

## 📞 Support

### Documentation
- **Terraform**: [terraform.io/docs](https://terraform.io/docs)
- **GKE**: [cloud.google.com/kubernetes-engine/docs](https://cloud.google.com/kubernetes-engine/docs)
- **MongoDB Atlas**: [docs.atlas.mongodb.com](https://docs.atlas.mongodb.com)

### Monitoring
- **Kubernetes Dashboard**: `kubectl proxy`
- **GCP Console**: [console.cloud.google.com](https://console.cloud.google.com)
- **Application Logs**: `kubectl logs -f deployment/<service> -n munshi-prod`

The Munshi pronunciation profiling platform is now ready to provide personalized, AI-driven language learning with Thompson Sampling optimization! 🎉