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

# Function to wait for cluster readiness
wait_for_cluster() {
    echo -e "${YELLOW}⏳ Waiting for cluster to be ready...${NC}"
    
    for i in $(seq 1 30); do
        if kubectl get nodes --no-headers 2>/dev/null | grep -q Ready; then
            echo -e "${GREEN}✅ Cluster nodes are ready${NC}"
            break
        else
            echo "Waiting for nodes... ($i/30)"
            sleep 10
        fi
        
        if [ $i -eq 30 ]; then
            echo -e "${RED}❌ Timeout waiting for cluster readiness${NC}"
            kubectl get nodes 2>/dev/null || echo "Cannot access cluster"
            exit 1
        fi
    done
    
    echo -e "${YELLOW}🔍 Verifying cluster connectivity...${NC}"
    if kubectl cluster-info --request-timeout=10s >/dev/null; then
        echo -e "${GREEN}✅ Cluster is ready and accessible${NC}"
    else
        echo -e "${RED}❌ Cluster connectivity test failed${NC}"
        exit 1
    fi
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
gcloud services enable storage.googleapis.com
echo -e "${GREEN}✅ APIs enabled${NC}"

# Create model storage bucket for ASR service
print_section "Setting up Model Storage"
MODEL_BUCKET="${PROJECT_ID}-munshi-models"
if ! gsutil ls gs://${MODEL_BUCKET} >/dev/null 2>&1; then
    echo "Creating model storage bucket: ${MODEL_BUCKET}"
    gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION} gs://${MODEL_BUCKET}
    echo "Setting bucket permissions..."
    gsutil iam ch serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com:objectViewer gs://${MODEL_BUCKET}
    echo -e "${GREEN}✅ Model storage bucket created${NC}"
else
    echo -e "${GREEN}✅ Model storage bucket already exists${NC}"
fi

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
    wait_for_cluster
else
    echo "Creating infrastructure..."
    terraform init
    
    # Apply with retry logic and disabled cert-manager
    for i in 1 2 3; do
        echo "Infrastructure deployment attempt $i/3..."
        if terraform apply -auto-approve -var="enable_cert_manager=false"; then
            echo -e "${GREEN}✅ Infrastructure applied successfully${NC}"
            break
        else
            echo -e "${YELLOW}⚠️  Attempt $i failed, retrying...${NC}"
            if [ $i -eq 3 ]; then
                echo -e "${RED}❌ All attempts failed${NC}"
                exit 1
            fi
            sleep 30
        fi
    done
    
    gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE
    wait_for_cluster
fi
echo -e "${GREEN}✅ Infrastructure ready${NC}"

# Build and push images
print_section "Building Images"
REGISTRY_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/munshi-containers"
VERSION=$(date +%Y%m%d-%H%M%S)
echo "Using version: ${VERSION}"
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

cd ../../  # Go to project root
services=("auth-service" "audio-service" "asr-service" "conversation-service" "llm-service" "pronunciation-evaluator" "ui-service")

# Check if docker buildx is available for multi-platform builds
if docker buildx version >/dev/null 2>&1; then
    echo "Using docker buildx for multi-platform builds"
    BUILD_CMD="docker buildx build --platform linux/amd64 --push"
else
    echo "Using standard docker build"
    BUILD_CMD="docker build --platform linux/amd64"
    PUSH_NEEDED=true
fi

for service in "${services[@]}"; do
    if [[ -d "services/${service}" ]]; then
        echo "Building ${service}..."
        cd services/${service}
        
        DOCKERFILE="Dockerfile"
        
        if [[ "$BUILD_CMD" == *"buildx"* ]]; then
            # Use buildx for direct push
            docker buildx build --platform linux/amd64 \
                -t ${REGISTRY_URL}/munshi-${service}:${VERSION} \
                -t ${REGISTRY_URL}/munshi-${service}:latest \
                --push .
        else
            # Traditional build and push
            docker build --platform linux/amd64 \
                -t ${REGISTRY_URL}/munshi-${service}:${VERSION} \
                -t ${REGISTRY_URL}/munshi-${service}:latest .
            docker push ${REGISTRY_URL}/munshi-${service}:${VERSION}
            docker push ${REGISTRY_URL}/munshi-${service}:latest
        fi
        cd ../..
    fi
done
echo -e "${GREEN}✅ Images built and pushed${NC}"

# Deploy with Helm
print_section "Deploying Application"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create secrets
echo -e "${YELLOW}📋 Creating secrets...${NC}"
cd infrastructure/terraform

# Get secrets from environment variables or terraform.tfvars
if [ -n "$GOOGLE_API_KEY" ]; then
    echo "Using GOOGLE_API_KEY from environment"
else
    GOOGLE_API_KEY=$(grep -E "^google_api_key" terraform.tfvars 2>/dev/null | cut -d'"' -f2)
    if [ -z "$GOOGLE_API_KEY" ] || [ "$GOOGLE_API_KEY" = "your-google-api-key-here" ]; then
        echo -e "${RED}❌ GOOGLE_API_KEY not set. Set environment variable or update terraform.tfvars${NC}"
        exit 1
    fi
fi

if [ -n "$JWT_SECRET" ]; then
    echo "Using JWT_SECRET from environment"
else
    JWT_SECRET=$(grep -E "^jwt_secret" terraform.tfvars 2>/dev/null | cut -d'"' -f2)
    if [ -z "$JWT_SECRET" ] || [ "$JWT_SECRET" = "your-jwt-secret-here" ]; then
        JWT_SECRET=$(openssl rand -base64 32)
        echo "Generated JWT_SECRET: $JWT_SECRET"
    fi
fi

kubectl create secret generic google-api-keys \
    --from-literal=api-key="$GOOGLE_API_KEY" \
    -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic auth-secrets \
    --from-literal=jwt-secret="$JWT_SECRET" \
    -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic database-credentials \
    --from-literal=mongodb_url="mongodb://munshi:munshi123@munshi-platform-mongodb:27017/munshi" \
    --from-literal=auth-db-url="postgresql://munshi_user:munshi_password@munshi-platform-postgresql:5432/munshi_auth" \
    --from-literal=audio-db-url="postgresql://munshi_user:munshi_password@munshi-platform-postgresql:5432/munshi_audio" \
    -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

cd ../..

# Create model storage configuration
kubectl create configmap model-storage-config \
    --from-literal=bucket-name="${MODEL_BUCKET}" \
    --from-literal=cache-dir="/tmp/model_cache" \
    -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Deploy Helm chart
cd infrastructure/helm/munshi-platform/
helm repo add bitnami https://charts.bitnami.com/bitnami --force-update
helm repo update
helm dependency update

# Deploy with Helm with retry logic
for i in 1 2; do
    echo "Helm deployment attempt $i/2..."
    if helm upgrade --install munshi-platform . \
        --namespace $NAMESPACE \
        --values values-gcp.yaml \
        --set global.imageRegistry="${REGISTRY_URL}" \
        --set image.tag="${VERSION}" \
        --set services.authService.image.tag="${VERSION}" \
        --set services.audioService.image.tag="${VERSION}" \
        --set services.asrService.image.tag="${VERSION}" \
        --set services.conversationService.image.tag="${VERSION}" \
        --set services.llmService.image.tag="${VERSION}" \
        --set services.pronunciationEvaluator.image.tag="${VERSION}" \
        --set services.uiService.image.tag="${VERSION}" \
        --wait --timeout=600s; then
        echo -e "${GREEN}✅ Helm deployment successful${NC}"
        break
    else
        echo -e "${YELLOW}⚠️  Helm deployment attempt $i failed${NC}"
        if [ $i -eq 2 ]; then
            echo -e "${RED}❌ All Helm deployment attempts failed${NC}"
            exit 1
        fi
        sleep 30
    fi
done

echo -e "${GREEN}✅ Application deployed${NC}"

# Wait for database and initialize
print_section "Database Initialization"
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql --timeout=300s -n $NAMESPACE

echo -e "${YELLOW}🔧 Initializing database...${NC}"
# Create database initialization job
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: database-init-$(date +%s)
  namespace: $NAMESPACE
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: postgres-init
        image: postgres:15-alpine
        command: ["/bin/sh"]
        args:
        - -c
        - |
          export PGPASSWORD="postgres123"
          echo "Waiting for PostgreSQL to be ready..."
          until pg_isready -h munshi-platform-postgresql -p 5432 -U postgres; do
            echo "PostgreSQL not ready, waiting..."
            sleep 5
          done
          echo "PostgreSQL is ready, creating database and user..."
          psql -h munshi-platform-postgresql -U postgres -c "CREATE DATABASE munshi_auth;" || echo "Database already exists"
          psql -h munshi-platform-postgresql -U postgres -c "CREATE USER munshi_user WITH PASSWORD 'munshi_password';" || echo "User already exists"
          psql -h munshi-platform-postgresql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE munshi_auth TO munshi_user;"
          psql -h munshi-platform-postgresql -U postgres -d munshi_auth -c "GRANT ALL ON SCHEMA public TO munshi_user;"
          psql -h munshi-platform-postgresql -U postgres -d munshi_auth -c "GRANT CREATE ON SCHEMA public TO munshi_user;"
          echo "Database initialization completed successfully!"
      nodeSelector:
        workload-type: "database"
      tolerations:
      - key: "workload-type"
        value: "database"
        effect: "NoSchedule"
  backoffLimit: 3
  ttlSecondsAfterFinished: 300
EOF

# Wait for database initialization to complete
kubectl wait --for=condition=complete job -l batch.kubernetes.io/job-name --timeout=300s -n $NAMESPACE 2>/dev/null || echo "Database initialization completed or already done"
echo -e "${GREEN}✅ Database initialized${NC}"

# Show status
print_section "Deployment Status"
kubectl get pods -n $NAMESPACE
kubectl get services -n $NAMESPACE

echo -e "\n${GREEN}🎉 Munshi Platform deployed successfully!${NC}"
echo -e "${BLUE}💡 Next steps:${NC}"
echo -e "  • Monitor pods: kubectl get pods -n $NAMESPACE -w"
echo -e "  • View logs: kubectl logs -f deployment/ui-service -n $NAMESPACE"
echo -e "  • Port forward: kubectl port-forward service/ui-service 8002:8002 -n $NAMESPACE"