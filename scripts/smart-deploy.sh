#!/bin/bash

# Smart deployment script that only builds/pushes changed services
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PROJECT_ID="central-list-469110-f1"
REGION="us-central1"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/munshi-containers"
SERVICES=(auth-service audio-service asr-service conversation-service llm-service pronunciation-evaluator ui-service)

# Get the comparison base (default to origin/main)
BASE_REF="${1:-origin/main}"

echo -e "${BLUE}🔍 Detecting changed services since ${BASE_REF}...${NC}"

# Function to check if service changed
service_changed() {
    local service=$1
    local service_dir="services/${service}"
    
    if [ ! -d "$service_dir" ]; then
        return 1
    fi
    
    # Check if any files in the service directory changed
    if git diff --quiet "${BASE_REF}" HEAD -- "${service_dir}/"; then
        return 1  # No changes
    else
        return 0  # Has changes
    fi
}

# Function to get image tag from current commit
get_image_tag() {
    git describe --tags --always --dirty 2>/dev/null || echo "dev"
}

# Function to check if image exists in registry
image_exists() {
    local service=$1
    local tag=$2
    
    gcloud artifacts docker images list "${REGISTRY}" \
        --filter="package~munshi-${service} AND version~${tag}" \
        --format="value(package)" 2>/dev/null | grep -q "munshi-${service}"
}

# Function to build and push service
build_and_push_service() {
    local service=$1
    local tag=$2
    
    echo -e "${BLUE}🏗️  Building ${service}...${NC}"
    cd "services/${service}"
    
    # Build arguments
    BUILD_ARGS="--platform linux/amd64"
    if [ "$service" = "asr-service" ]; then
        BUILD_ARGS="$BUILD_ARGS --build-arg GPU_SUPPORT=gpu"
    fi
    
    # Build image
    docker build $BUILD_ARGS \
        -t "${REGISTRY}/munshi-${service}:${tag}" \
        -t "${REGISTRY}/munshi-${service}:latest" .
    
    echo -e "${BLUE}📤 Pushing ${service}...${NC}"
    docker push "${REGISTRY}/munshi-${service}:${tag}"
    docker push "${REGISTRY}/munshi-${service}:latest"
    
    cd ../..
}

# Main logic
CHANGED_SERVICES=()
UNCHANGED_SERVICES=()
IMAGE_TAG=$(get_image_tag)

echo -e "${BLUE}Using image tag: ${IMAGE_TAG}${NC}"

# Configure docker auth
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Check each service
for service in "${SERVICES[@]}"; do
    if service_changed "$service"; then
        CHANGED_SERVICES+=("$service")
        echo -e "${YELLOW}📝 ${service}: CHANGED${NC}"
    else
        # Check if image exists for unchanged services
        if image_exists "$service" "$IMAGE_TAG"; then
            UNCHANGED_SERVICES+=("$service")
            echo -e "${GREEN}✓ ${service}: unchanged (image exists)${NC}"
        else
            # Force build if image doesn't exist
            CHANGED_SERVICES+=("$service")
            echo -e "${YELLOW}🔄 ${service}: unchanged but missing image, will build${NC}"
        fi
    fi
done

# Build and push changed services
if [ ${#CHANGED_SERVICES[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ No services need rebuilding${NC}"
else
    echo -e "${BLUE}🏗️  Building ${#CHANGED_SERVICES[@]} changed services...${NC}"
    for service in "${CHANGED_SERVICES[@]}"; do
        build_and_push_service "$service" "$IMAGE_TAG"
    done
    echo -e "${GREEN}✓ All changed services built and pushed${NC}"
fi

echo -e "${BLUE}📊 Summary:${NC}"
echo -e "  Changed services: ${#CHANGED_SERVICES[@]}"
echo -e "  Unchanged services: ${#UNCHANGED_SERVICES[@]}"

if [ ${#CHANGED_SERVICES[@]} -gt 0 ]; then
    echo -e "${YELLOW}Changed services:${NC}"
    printf '  - %s\n' "${CHANGED_SERVICES[@]}"
fi

if [ ${#UNCHANGED_SERVICES[@]} -gt 0 ]; then
    echo -e "${GREEN}Unchanged services:${NC}"
    printf '  - %s\n' "${UNCHANGED_SERVICES[@]}"
fi