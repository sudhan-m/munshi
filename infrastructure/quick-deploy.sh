#!/bin/bash

# Munshi Platform - Quick Deployment Script
# This script provides a one-command deployment experience

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Munshi Platform Quick Deployment${NC}"

# Check if we're in the right directory
if [[ ! -f "infrastructure/terraform/deploy-gcp.sh" ]]; then
    echo -e "${RED}❌ Please run this script from the munshi project root directory${NC}"
    exit 1
fi

# Check if terraform.tfvars exists
if [[ ! -f "infrastructure/terraform/terraform.tfvars" ]]; then
    echo -e "${YELLOW}⚠️  terraform.tfvars not found. Creating from example...${NC}"
    cp infrastructure/terraform/terraform-gcp.tfvars.example infrastructure/terraform/terraform.tfvars
    
    echo -e "${RED}❌ Please edit infrastructure/terraform/terraform.tfvars with your values:${NC}"
    echo -e "  • project_id: Your GCP project ID"
    echo -e "  • jwt_secret: A secure random string (32+ characters)"
    echo -e "  • google_api_key: Your Google Gemini API key"
    echo -e ""
    echo -e "${BLUE}Then run this script again.${NC}"
    exit 1
fi

# Check if required values are set
PROJECT_ID=$(grep -E "^project_id" infrastructure/terraform/terraform.tfvars | cut -d'"' -f2)
JWT_SECRET=$(grep -E "^jwt_secret" infrastructure/terraform/terraform.tfvars | cut -d'"' -f2)
GOOGLE_API_KEY=$(grep -E "^google_api_key" infrastructure/terraform/terraform.tfvars | cut -d'"' -f2)

if [[ "$PROJECT_ID" == "your-gcp-project-id" ]] || [[ -z "$PROJECT_ID" ]]; then
    echo -e "${RED}❌ Please set your project_id in terraform.tfvars${NC}"
    exit 1
fi

if [[ "$JWT_SECRET" == "your-jwt-secret-key-here" ]] || [[ -z "$JWT_SECRET" ]]; then
    echo -e "${RED}❌ Please set your jwt_secret in terraform.tfvars${NC}"
    exit 1
fi

if [[ "$GOOGLE_API_KEY" == "your-google-gemini-api-key" ]] || [[ -z "$GOOGLE_API_KEY" ]]; then
    echo -e "${RED}❌ Please set your google_api_key in terraform.tfvars${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Configuration looks good!${NC}"
echo -e "${BLUE}Project ID: ${PROJECT_ID}${NC}"

# Run the deployment
echo -e "${YELLOW}🚀 Starting deployment...${NC}"
cd infrastructure/terraform
chmod +x deploy-gcp.sh
./deploy-gcp.sh

echo -e "\n${GREEN}🎉 Deployment completed!${NC}"
echo -e "${BLUE}💡 To access your application:${NC}"
echo -e "  kubectl port-forward service/ui-service 8002:8002 -n munshi-prod"
echo -e "  Then open: http://localhost:8002"