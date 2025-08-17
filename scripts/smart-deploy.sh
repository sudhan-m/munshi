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

echo -e "${BLUE}🔍 Detecting services that need rebuilding...${NC}"

# Function to get current deployed image tag for a service
get_current_deployed_tag() {
    local service=$1
    
    # Convert service name to camelCase for Helm values (e.g., "llm-service" -> "llmService")
    local service_camel_case=$(echo "$service" | sed 's/-\([a-z]\)/\U\1/g')
    
    # Try to get from Helm values first
    local helm_tag=$(helm get values munshi-platform -n munshi-prod -o json 2>/dev/null | \
        jq -r ".services.${service_camel_case}.image.tag // empty" 2>/dev/null)
    
    if [ -n "$helm_tag" ] && [ "$helm_tag" != "null" ] && [ "$helm_tag" != "empty" ]; then
        echo "$helm_tag"
        return 0
    fi
    
    # Try to get from running pods using correct label selector
    local pod_image=$(kubectl get pods -n munshi-prod -l "app.kubernetes.io/component=${service}" \
        -o jsonpath='{.items[0].spec.containers[0].image}' 2>/dev/null)
    
    if [ -n "$pod_image" ]; then
        echo "$pod_image" | cut -d':' -f2
        return 0
    fi
    
    # If no deployment found, return empty (will force rebuild)
    echo ""
}

# Function to get service last modified timestamp  
get_service_modified_time() {
    local service=$1
    local service_dir="services/${service}"
    
    if [ ! -d "$service_dir" ]; then
        echo "0"
        return
    fi
    
    # Get the latest modification time of any file in the service directory
    find "$service_dir" -type f -exec stat -f "%m" {} \; 2>/dev/null | sort -n | tail -1
}

# Function to convert image tag to timestamp
tag_to_timestamp() {
    local tag=$1
    
    # Handle timestamp format YYYYMMDD-HHMMSS
    if [[ $tag =~ ^[0-9]{8}-[0-9]{6}$ ]]; then
        local date_part=${tag%-*}
        local time_part=${tag#*-}
        
        # Convert to format YYYY-MM-DD HH:MM:SS
        local formatted_date="${date_part:0:4}-${date_part:4:2}-${date_part:6:2}"
        local formatted_time="${time_part:0:2}:${time_part:2:2}:${time_part:4:2}"
        
        # Convert to epoch timestamp
        date -j -f "%Y-%m-%d %H:%M:%S" "$formatted_date $formatted_time" +%s 2>/dev/null || echo "0"
    else
        # For non-timestamp tags (like "latest"), return 0 to force rebuild
        echo "0"
    fi
}

# Function to get image tag from timestamp
get_image_tag() {
    date +%Y%m%d-%H%M%S
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
    
    # Standard production build configuration
    BUILD_ARGS="--platform linux/amd64"
    DOCKERFILE="Dockerfile"
    
    # Build image
    docker build $BUILD_ARGS -f $DOCKERFILE \
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
    echo -e "${BLUE}Checking ${service}...${NC}"
    
    # Get current deployed tag and service modification time
    current_tag=$(get_current_deployed_tag "$service")
    service_mod_time=$(get_service_modified_time "$service")
    
    if [ -z "$current_tag" ]; then
        # No current deployment, force build
        CHANGED_SERVICES+=("$service")
        echo -e "${YELLOW}🔄 ${service}: no current deployment, will build${NC}"
        continue
    fi
    
    # Convert current tag to timestamp
    current_tag_timestamp=$(tag_to_timestamp "$current_tag")
    
    if [ "$current_tag_timestamp" -eq 0 ]; then
        # Non-timestamp tag or conversion failed, force build
        CHANGED_SERVICES+=("$service")
        echo -e "${YELLOW}🔄 ${service}: non-timestamp tag '${current_tag}', will build${NC}"
        continue
    fi
    
    # Compare timestamps
    if [ "$service_mod_time" -gt "$current_tag_timestamp" ]; then
        # Service is newer than deployed image
        CHANGED_SERVICES+=("$service")
        echo -e "${YELLOW}📝 ${service}: modified since deployment (current: ${current_tag}), will build${NC}"
    else
        # Service is older than or same as deployed image
        UNCHANGED_SERVICES+=("$service")
        echo -e "${GREEN}✓ ${service}: up-to-date (current: ${current_tag})${NC}"
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

# Generate Helm set commands for updated services
echo -e "${BLUE}📋 Generating Helm deployment configuration...${NC}"
HELM_SET_ARGS=""
for service in "${SERVICES[@]}"; do
    # Convert service name to camelCase (e.g., "llm-service" -> "llmService")
    service_name_camel=$(echo "${service}" | sed 's/-\([a-z]\)/\U\1/g')
    
    if [[ " ${CHANGED_SERVICES[@]} " =~ " ${service} " ]]; then
        # Use new tag for changed services
        HELM_SET_ARGS+=" --set services.${service_name_camel}.image.tag=${IMAGE_TAG}"
    else
        # Keep existing tag for unchanged services  
        current_tag=$(get_current_deployed_tag "$service")
        if [ -n "$current_tag" ]; then
            HELM_SET_ARGS+=" --set services.${service_name_camel}.image.tag=${current_tag}"
        fi
    fi
done

# Write the helm set arguments to a file for the Makefile to use
echo "$HELM_SET_ARGS" > /tmp/munshi-helm-set-args