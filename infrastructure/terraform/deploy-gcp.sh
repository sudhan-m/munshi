#!/bin/bash

# Munshi Pronunciation Profiling Platform - GCP Deployment Script
# This script deploys the complete Munshi platform with Thompson Sampling bandits to GCP

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

echo -e "${BLUE}🚀 Deploying Munshi Pronunciation Profiling Platform to GCP${NC}"
echo -e "${BLUE}Project: ${PROJECT_ID}${NC}"
echo -e "${BLUE}Cluster: ${CLUSTER_NAME}${NC}"
echo -e "${BLUE}Region: ${REGION}${NC}"

# Function to print section headers
print_section() {
    echo -e "\n${GREEN}==== $1 ====${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_section "Checking Prerequisites"
    
    # Check if required tools are installed
    for tool in terraform gcloud kubectl helm; do
        if ! command -v $tool &> /dev/null; then
            echo -e "${RED}❌ $tool is not installed${NC}"
            exit 1
        else
            echo -e "${GREEN}✅ $tool is installed${NC}"
        fi
    done
    
    # Check GCP authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo -e "${RED}❌ Not authenticated with GCP${NC}"
        echo -e "${YELLOW}Run: gcloud auth login${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ GCP authentication verified${NC}"
    fi
    
    # Set GCP project
    gcloud config set project $PROJECT_ID
    echo -e "${GREEN}✅ GCP project set to $PROJECT_ID${NC}"
}

# Function to enable required GCP APIs
enable_apis() {
    print_section "Enabling Required GCP APIs"
    
    apis=(
        "container.googleapis.com"
        "artifactregistry.googleapis.com"
        "cloudsql.googleapis.com"
        "storage.googleapis.com"
        "compute.googleapis.com"
        "iam.googleapis.com"
        "cloudresourcemanager.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        echo "Enabling $api..."
        gcloud services enable $api
    done
    
    echo -e "${GREEN}✅ All required APIs enabled${NC}"
}

# Function to check if terraform.tfvars exists
check_tfvars() {
    print_section "Checking Terraform Configuration"
    
    if [ ! -f "terraform.tfvars" ]; then
        echo -e "${YELLOW}⚠️  terraform.tfvars not found${NC}"
        echo -e "${YELLOW}Copying from terraform-gcp.tfvars.example${NC}"
        cp terraform-gcp.tfvars.example terraform.tfvars
        echo -e "${RED}❌ Please edit terraform.tfvars with your actual values${NC}"
        echo -e "${YELLOW}Required values:${NC}"
        echo -e "  - mongodb_url (MongoDB Atlas connection string)"
        echo -e "  - mongodb_username"
        echo -e "  - mongodb_password"
        echo -e "  - google_api_key (for Gemini LLM service)"
        echo -e "  - jwt_secret"
        echo -e "  - postgres_auth_password"
        echo -e "  - postgres_gateway_password"
        exit 1
    else
        echo -e "${GREEN}✅ terraform.tfvars found${NC}"
    fi
}

# Function to deploy infrastructure with Terraform
deploy_infrastructure() {
    print_section "Deploying Infrastructure with Terraform"
    
    # Initialize Terraform
    echo "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    echo "Planning Terraform deployment..."
    terraform plan -out=tfplan
    
    # Apply deployment
    echo "Applying Terraform deployment..."
    terraform apply tfplan
    
    # Get cluster credentials
    echo "Getting GKE cluster credentials..."
    gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE --project=$PROJECT_ID
    
    echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
}

# Function to build and push container images
build_and_push_images() {
    print_section "Building and Pushing Container Images"
    
    # Get Artifact Registry URL from Terraform output
    REGISTRY_URL=$(terraform output -raw artifact_registry_repository)
    
    # Configure Docker for Artifact Registry
    gcloud auth configure-docker ${REGION}-docker.pkg.dev
    
    # Build and push images
    cd ../../  # Go to project root
    
    services=("auth-service" "ui-service" "audio-service" "asr-service" "llm-service" "pronunciation-evaluator" "conversation-service")
    
    for service in "${services[@]}"; do
        echo "Building and pushing $service..."
        
        # Build image
        docker build -t ${REGISTRY_URL}/munshi-${service}:latest services/${service}/
        
        # Push image
        docker push ${REGISTRY_URL}/munshi-${service}:latest
        
        echo -e "${GREEN}✅ $service image pushed${NC}"
    done
    
    cd infrastructure/terraform/  # Go back to terraform directory
}

# Function to deploy Helm chart
deploy_helm_chart() {
    print_section "Deploying Munshi Platform with Helm"
    
    # Generate Helm values from Terraform template
    echo "Generating Helm values from Terraform outputs..."
    terraform output -json > terraform_outputs.json
    
    # Create values file from template
    # Note: In production, you'd use a proper templating tool
    # For now, we'll use the existing Helm values
    
    # Add Helm repository (if needed)
    # helm repo add munshi-platform ../helm/munshi-platform/
    
    # Deploy with Helm
    echo "Deploying with Helm..."
    helm upgrade --install munshi-platform ../helm/munshi-platform/ \
        --namespace $NAMESPACE \
        --create-namespace \
        --values ../helm/munshi-platform/values-production.yaml \
        --set global.imageRegistry=$(terraform output -raw artifact_registry_repository) \
        --set environment="production" \
        --timeout 10m \
        --wait
    
    echo -e "${GREEN}✅ Munshi platform deployed with Helm${NC}"
}

# Function to verify deployment
verify_deployment() {
    print_section "Verifying Deployment"
    
    # Check if all pods are running
    echo "Checking pod status..."
    kubectl get pods -n $NAMESPACE
    
    # Check services
    echo "Checking services..."
    kubectl get services -n $NAMESPACE
    
    # Check ingress
    echo "Checking ingress..."
    kubectl get ingress -n $NAMESPACE
    
    # Get external IP
    EXTERNAL_IP=$(kubectl get ingress -n $NAMESPACE -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}')
    if [ ! -z "$EXTERNAL_IP" ]; then
        echo -e "${GREEN}✅ External IP: $EXTERNAL_IP${NC}"
    fi
    
    echo -e "${GREEN}✅ Deployment verification complete${NC}"
}

# Function to show post-deployment information
show_info() {
    print_section "Post-Deployment Information"
    
    echo -e "${BLUE}🎯 Pronunciation Profiling Features Deployed:${NC}"
    echo -e "  ✅ Thompson Sampling bandits for adaptive phoneme targeting"
    echo -e "  ✅ Phoneme mappings for English, Tamil, and Malayalam"
    echo -e "  ✅ LLM-driven mood detection and strategy selection"
    echo -e "  ✅ Character-level mispronunciation analysis"
    echo -e "  ✅ Real-time pronunciation profile updates"
    echo -e "  ✅ MongoDB Atlas integration for profile persistence"
    
    echo -e "\n${BLUE}📊 Monitoring and Management:${NC}"
    echo -e "  • Kubernetes Dashboard: kubectl proxy"
    echo -e "  • View logs: kubectl logs -f deployment/conversation-service -n $NAMESPACE"
    echo -e "  • Scale services: kubectl scale deployment conversation-service --replicas=5 -n $NAMESPACE"
    
    echo -e "\n${BLUE}🔗 Useful Commands:${NC}"
    echo -e "  • Get cluster info: kubectl cluster-info"
    echo -e "  • Port forward to test: kubectl port-forward service/conversation-service 8007:8007 -n $NAMESPACE"
    echo -e "  • Update deployment: helm upgrade munshi-platform ../helm/munshi-platform/ -n $NAMESPACE"
    
    echo -e "\n${GREEN}🚀 Munshi Pronunciation Profiling Platform deployed successfully!${NC}"
}

# Main deployment flow
main() {
    check_prerequisites
    enable_apis
    check_tfvars
    deploy_infrastructure
    build_and_push_images
    deploy_helm_chart
    verify_deployment
    show_info
}

# Run main function
main "$@"