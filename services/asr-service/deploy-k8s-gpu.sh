#!/bin/bash

# Kubernetes GPU deployment script for ASR Service
set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
CLUSTER_NAME=${CLUSTER_NAME:-"munshi-cluster"}
ZONE=${ZONE:-"us-central1-a"}
REGION=${REGION:-"us-central1"}
VERSION=$(date +%Y%m%d-%H%M%S)
IMAGE_NAME="gcr.io/${PROJECT_ID}/asr-service-gpu:${VERSION}"
NAMESPACE=${NAMESPACE:-"default"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying ASR Service to Kubernetes with GPU support${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command_exists gcloud; then
    echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    exit 1
fi

if ! command_exists kubectl; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

if ! command_exists docker; then
    echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
    exit 1
fi

# Set project and get credentials
echo -e "${YELLOW}🔧 Setting up GCP project and cluster access...${NC}"
gcloud config set project ${PROJECT_ID}
gcloud container clusters get-credentials ${CLUSTER_NAME} --zone=${ZONE}

# Create namespace if it doesn't exist
echo -e "${YELLOW}📁 Creating namespace: ${NAMESPACE}${NC}"
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Check if GPU node pool exists
echo -e "${YELLOW}🔍 Checking GPU node pool...${NC}"
if ! gcloud container node-pools describe asr-gpu-pool --cluster=${CLUSTER_NAME} --zone=${ZONE} >/dev/null 2>&1; then
    echo -e "${YELLOW}🏗️  Creating GPU node pool...${NC}"
    gcloud container node-pools create asr-gpu-pool \
        --cluster=${CLUSTER_NAME} \
        --zone=${ZONE} \
        --machine-type=n1-standard-4 \
        --accelerator=type=nvidia-tesla-t4,count=1 \
        --num-nodes=0 \
        --min-nodes=0 \
        --max-nodes=3 \
        --enable-autoscaling \
        --enable-autorepair \
        --enable-autoupgrade \
        --disk-size=100GB \
        --disk-type=pd-ssd \
        --image-type=cos_containerd \
        --node-taints=nvidia.com/gpu=:NoSchedule \
        --node-labels=workload=gpu,app=asr-service \
        --metadata=disable-legacy-endpoints=true \
        --scopes=https://www.googleapis.com/auth/cloud-platform
else
    echo -e "${GREEN}✅ GPU node pool already exists${NC}"
fi

# Install NVIDIA GPU drivers
echo -e "${YELLOW}🔧 Installing NVIDIA GPU drivers...${NC}"
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml

# Install KEDA for scale-to-zero
echo -e "${YELLOW}📊 Installing KEDA for scale-to-zero...${NC}"
if ! kubectl get namespace keda-system >/dev/null 2>&1; then
    kubectl apply -f https://github.com/kedacore/keda/releases/download/v2.12.0/keda-2.12.0.yaml
    echo "Waiting for KEDA to be ready..."
    kubectl wait --for=condition=ready pod -l app=keda-operator -n keda-system --timeout=300s
else
    echo -e "${GREEN}✅ KEDA already installed${NC}"
fi

# Install Prometheus for monitoring (optional)
echo -e "${YELLOW}📊 Installing Prometheus monitoring...${NC}"
if ! kubectl get namespace monitoring >/dev/null 2>&1; then
    echo "Installing Prometheus operator..."
    kubectl create namespace monitoring
    kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
else
    echo -e "${GREEN}✅ Prometheus already installed${NC}"
fi

# Create model storage bucket if it doesn't exist
echo -e "${YELLOW}🗄️  Setting up model storage...${NC}"
MODEL_BUCKET="${PROJECT_ID}-munshi-models"
if ! gsutil ls gs://${MODEL_BUCKET} >/dev/null 2>&1; then
    echo "Creating model storage bucket: ${MODEL_BUCKET}"
    gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION} gs://${MODEL_BUCKET}
    gsutil iam ch serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com:objectViewer gs://${MODEL_BUCKET}
    echo -e "${GREEN}✅ Model storage bucket created${NC}"
else
    echo -e "${GREEN}✅ Model storage bucket already exists${NC}"
fi

# Build and push Docker image using lightweight dockerfile
echo -e "${YELLOW}🏗️  Building and pushing Docker image...${NC}"
echo "📦 Using lightweight Dockerfile for faster GPU deployment"
gcloud builds submit --tag ${IMAGE_NAME} --file Dockerfile.lightweight .

# Update deployment manifest with correct image
echo -e "${YELLOW}📝 Updating deployment configuration...${NC}"
sed -i.bak "s|gcr.io/PROJECT_ID/asr-service-gpu:latest|${IMAGE_NAME}|g" k8s-gpu-deployment.yaml

# Deploy the ASR service
echo -e "${YELLOW}🚀 Deploying ASR service...${NC}"
kubectl apply -f k8s-gpu-deployment.yaml -n ${NAMESPACE}

# Deploy KEDA scaler
echo -e "${YELLOW}📊 Deploying KEDA autoscaler...${NC}"
kubectl apply -f keda-scaler.yaml -n ${NAMESPACE}

# Deploy monitoring
echo -e "${YELLOW}📊 Deploying monitoring configuration...${NC}"
kubectl apply -f monitoring.yaml -n ${NAMESPACE}

# Wait for deployment to be ready
echo -e "${YELLOW}⏳ Waiting for deployment to be ready...${NC}"
kubectl wait --for=condition=available deployment/asr-service-gpu -n ${NAMESPACE} --timeout=600s || {
    echo -e "${YELLOW}⚠️  Deployment not ready yet, checking status...${NC}"
    kubectl get pods -l app=asr-service-gpu -n ${NAMESPACE}
    kubectl describe deployment asr-service-gpu -n ${NAMESPACE}
}

# Get service information
echo -e "${YELLOW}📊 Getting service information...${NC}"
SERVICE_IP=$(kubectl get service asr-service-gpu -n ${NAMESPACE} -o jsonpath='{.spec.clusterIP}')
SERVICE_PORT=$(kubectl get service asr-service-gpu -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].port}')

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service available at: http://${SERVICE_IP}:${SERVICE_PORT}${NC}"
echo -e "${GREEN}🔍 Health check: curl http://${SERVICE_IP}:${SERVICE_PORT}/health${NC}"

# Port forwarding for testing
echo -e "${YELLOW}🔗 Setting up port forwarding for testing...${NC}"
echo "Run the following command to access the service locally:"
echo -e "${BLUE}kubectl port-forward service/asr-service-gpu 8004:8004 -n ${NAMESPACE}${NC}"

# Show useful commands
echo -e "${YELLOW}📝 Useful commands:${NC}"
echo "  View logs: kubectl logs -l app=asr-service-gpu -n ${NAMESPACE} -f"
echo "  Check GPU usage: kubectl top nodes"
echo "  Check pod status: kubectl get pods -l app=asr-service-gpu -n ${NAMESPACE}"
echo "  Check KEDA scaling: kubectl get scaledobject -n ${NAMESPACE}"
echo "  Check GPU metrics: kubectl get --raw /api/v1/nodes/\$(kubectl get nodes -l accelerator=nvidia-tesla-t4 -o name | head -1 | cut -d/ -f2)/proxy/metrics/cadvisor"
echo "  Scale manually: kubectl scale deployment asr-service-gpu --replicas=1 -n ${NAMESPACE}"
echo "  Delete deployment: kubectl delete -f k8s-gpu-deployment.yaml -n ${NAMESPACE}"

# Test the deployment
echo -e "${YELLOW}🧪 Testing deployment...${NC}"
if kubectl get pods -l app=asr-service-gpu -n ${NAMESPACE} | grep -q "Running"; then
    echo -e "${GREEN}✅ Service pods are running!${NC}"
    
    # Test health endpoint
    POD_NAME=$(kubectl get pods -l app=asr-service-gpu -n ${NAMESPACE} -o jsonpath='{.items[0].metadata.name}')
    if [ ! -z "$POD_NAME" ]; then
        echo "Testing health endpoint..."
        kubectl exec ${POD_NAME} -n ${NAMESPACE} -- curl -f http://localhost:8004/health >/dev/null 2>&1 && {
            echo -e "${GREEN}✅ Health check passed!${NC}"
        } || {
            echo -e "${YELLOW}⚠️  Health check failed, service might still be starting up${NC}"
        }
    fi
else
    echo -e "${YELLOW}⚠️  Service pods are not running yet. Check logs with:${NC}"
    echo "kubectl logs -l app=asr-service-gpu -n ${NAMESPACE}"
fi

echo -e "${GREEN}🎉 ASR GPU service is now deployed on Kubernetes with scale-to-zero!${NC}"
echo -e "${GREEN}💰 The service will automatically scale to 0 when not in use to save costs.${NC}"

# Restore original deployment file
mv k8s-gpu-deployment.yaml.bak k8s-gpu-deployment.yaml 2>/dev/null || true