#!/bin/bash

# Cloud Run deployment script for ASR Service
set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="asr-service"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying ASR Service to Cloud Run${NC}"

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
    exit 1
fi

# Verify project
echo -e "${YELLOW}🔍 Verifying project: ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build image using Cloud Build (recommended for Cloud Run)
echo -e "${YELLOW}🏗️  Building image with Cloud Build...${NC}"
gcloud builds submit --tag ${IMAGE_NAME} --file Dockerfile.cloudrun .

# Alternative: Build locally and push
# echo -e "${YELLOW}🏗️  Building image locally...${NC}"
# docker build -f Dockerfile.cloudrun -t ${IMAGE_NAME} .
# docker push ${IMAGE_NAME}

# Create service account if it doesn't exist
echo -e "${YELLOW}👤 Setting up service account...${NC}"
SERVICE_ACCOUNT_EMAIL="asr-service-sa@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} &> /dev/null; then
    echo "Creating service account..."
    gcloud iam service-accounts create asr-service-sa \
        --display-name="ASR Service Account" \
        --description="Service account for ASR Cloud Run service"
fi

# Grant necessary permissions
echo -e "${YELLOW}🔑 Granting permissions...${NC}"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.objectViewer"

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run...${NC}"

gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT_EMAIL} \
    --memory 4Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 10 \
    --min-instances 0 \
    --concurrency 1 \
    --no-cpu-throttling \
    --port 8080 \
    --set-env-vars="CLOUD_RUN_MODE=true,FALLBACK_MODE=true,GPU_SUPPORT=cpu,MODEL_CACHE_SIZE=1" \
    --allow-unauthenticated

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}🔍 Health check: ${SERVICE_URL}/health${NC}"

# Test the deployment
echo -e "${YELLOW}🧪 Testing deployment...${NC}"
if curl -f "${SERVICE_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Service is healthy!${NC}"
else
    echo -e "${YELLOW}⚠️  Service might still be starting up. Check logs with:${NC}"
    echo "gcloud run logs read ${SERVICE_NAME} --region=${REGION}"
fi

# Show useful commands
echo -e "${YELLOW}📝 Useful commands:${NC}"
echo "  View logs: gcloud run logs read ${SERVICE_NAME} --region=${REGION}"
echo "  Update service: gcloud run services replace cloudrun-deploy.yaml --region=${REGION}"
echo "  Delete service: gcloud run services delete ${SERVICE_NAME} --region=${REGION}"
echo "  Monitor: gcloud run services describe ${SERVICE_NAME} --region=${REGION}"

echo -e "${GREEN}🎉 ASR Service is now running on Cloud Run!${NC}"