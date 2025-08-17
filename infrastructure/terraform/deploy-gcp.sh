#!/bin/bash

# Munshi Platform - Simplified GCP Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${PROJECT_ID:-central-list-469110-f1}"
CLUSTER_NAME="${CLUSTER_NAME:-munshi-cluster}"
REGION="${REGION:-us-central1}"
ZONE="${ZONE:-us-central1-a}"
NAMESPACE="${NAMESPACE:-munshi-prod}"

echo -e "${BLUE}🚀 Deploying Munshi Platform to GCP${NC}"
echo -e "${BLUE}Project: ${PROJECT_ID}${NC}"
echo -e "${BLUE}Cluster: ${CLUSTER_NAME}${NC}"

# Function to print section headers
print_section() {
    echo -e "\n${GREEN}==== $1 ====${NC}"
}

# Check prerequisites
print_section "Checking Prerequisites"
for tool in terraform gcloud kubectl helm; do
    if ! command -v $tool &> /dev/null; then
        echo -e "${RED}❌ $tool is not installed${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All tools available${NC}"

# Check GCP authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Not authenticated with GCP${NC}"
    echo -e "${YELLOW}Run: gcloud auth login${NC}"
    exit 1
fi
gcloud config set project $PROJECT_ID

# Enable required APIs
print_section "Enabling GCP APIs"
gcloud services enable container.googleapis.com
gcloud services enable artifactregistry.googleapis.com
echo -e "${GREEN}✅ APIs enabled${NC}"

# Check terraform.tfvars
print_section "Checking Configuration"
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}⚠️  Creating terraform.tfvars from example${NC}"
    cp terraform-gcp.tfvars.example terraform.tfvars
    echo -e "${RED}❌ Please edit terraform.tfvars with your values:${NC}"
    echo -e "  - project_id"
    echo -e "  - jwt_secret"
    echo -e "  - google_api_key"
    exit 1
fi
echo -e "${GREEN}✅ Configuration ready${NC}"

# Deploy infrastructure
print_section "Deploying Infrastructure"
if gcloud container clusters describe $CLUSTER_NAME --zone=$ZONE &>/dev/null; then
    echo -e "${YELLOW}⚠️  Cluster exists, getting credentials${NC}"
    gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE
else
    echo "Creating infrastructure..."
    terraform init
    terraform plan -out=tfplan
    terraform apply tfplan
    gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE
fi
echo -e "${GREEN}✅ Infrastructure ready${NC}"

# Build and push images
print_section "Building Images"
REGISTRY_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/munshi-containers"
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

cd ../../  # Go to project root
services=("auth-service" "audio-service" "asr-service" "conversation-service" "llm-service" "pronunciation-evaluator" "ui-service")

for service in "${services[@]}"; do
    if [[ -d "services/${service}" ]]; then
        echo "Building ${service}..."
        cd services/${service}
        
        BUILD_ARGS="--platform linux/amd64"
        if [[ "$service" == "asr-service" ]]; then
            BUILD_ARGS="${BUILD_ARGS} --build-arg GPU_SUPPORT=gpu"
        fi
        
        docker build ${BUILD_ARGS} -t ${REGISTRY_URL}/munshi-${service}:latest .
        docker push ${REGISTRY_URL}/munshi-${service}:latest
        cd ../..
    fi
done
echo -e "${GREEN}✅ Images built and pushed${NC}"

# Deploy with Helm
print_section "Deploying Application"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create secrets
GOOGLE_API_KEY=$(grep -E "^google_api_key" terraform.tfvars | cut -d'"' -f2)
JWT_SECRET=$(grep -E "^jwt_secret" terraform.tfvars | cut -d'"' -f2)

kubectl create secret generic google-api-keys \
    --from-literal=api-key="$GOOGLE_API_KEY" \
    -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic jwt-secret \
    --from-literal=secret="$JWT_SECRET" \
    -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic database-credentials \
    --from-literal=mongodb_url="mongodb://munshi:munshi123@munshi-platform-mongodb:27017/munshi" \
    --from-literal=auth-db-url="postgresql://munshi_user:munshi_password@munshi-platform-postgresql:5432/munshi_auth" \
    --from-literal=audio-db-url="postgresql://munshi_user:munshi_password@munshi-platform-postgresql:5432/munshi_audio" \
    -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Deploy Helm chart
cd infrastructure/helm/munshi-platform/
helm repo add bitnami https://charts.bitnami.com/bitnami --force-update
helm repo update
helm dependency update

helm upgrade --install munshi-platform . \
    --namespace $NAMESPACE \
    --values values-gcp.yaml \
    --set global.imageRegistry="${REGISTRY_URL}" \
    --wait --timeout=600s

echo -e "${GREEN}✅ Application deployed${NC}"

# Show status
print_section "Deployment Status"
kubectl get pods -n $NAMESPACE
kubectl get services -n $NAMESPACE

echo -e "\n${GREEN}🎉 Munshi Platform deployed successfully!${NC}"
echo -e "${BLUE}💡 Next steps:${NC}"
echo -e "  • Monitor pods: kubectl get pods -n $NAMESPACE -w"
echo -e "  • View logs: kubectl logs -f deployment/ui-service -n $NAMESPACE"
echo -e "  • Port forward: kubectl port-forward service/ui-service 8002:8002 -n $NAMESPACE"