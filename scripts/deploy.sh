#!/bin/bash

# Universal Munshi Deployment Script
# Automatically detects and deploys to current Kubernetes context

set -euo pipefail

# Default configuration
ENVIRONMENT=${ENVIRONMENT:-"auto"}
NAMESPACE=${NAMESPACE:-""}
CHART_PATH="./infrastructure/helm/munshi"
VALUES_FILE=""
BUILD_IMAGES=${BUILD_IMAGES:-"auto"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Display usage information
usage() {
    echo "Usage: $0 [OPTIONS] [COMMAND]"
    echo ""
    echo "Universal deployment script that adapts to current Kubernetes context"
    echo ""
    echo "Environment Variables:"
    echo "  ENVIRONMENT    - Override environment detection (local|dev|staging|prod)"
    echo "  NAMESPACE      - Override namespace (default: munshi-\$ENVIRONMENT)"
    echo "  BUILD_IMAGES   - Force image building (true|false|auto)"
    echo ""
    echo "Commands:"
    echo "  deploy         - Deploy the application (default)"
    echo "  build          - Build images only"
    echo "  upgrade        - Upgrade existing deployment"  
    echo "  status         - Show deployment status"
    echo "  logs           - Show application logs"
    echo "  rollback       - Rollback to previous version"
    echo "  delete         - Remove the deployment"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Auto-detect and deploy"
    echo "  ENVIRONMENT=staging $0                # Force staging environment"
    echo "  BUILD_IMAGES=true $0                  # Force image build"
    echo "  $0 upgrade                            # Upgrade existing deployment"
}

# Detect deployment environment based on Kubernetes context
detect_environment() {
    local context=$(kubectl config current-context)
    local cluster_info=$(kubectl cluster-info)
    
    # Docker Desktop detection
    if [[ "$context" == "docker-desktop" ]] || [[ "$cluster_info" == *"127.0.0.1"* ]] || [[ "$cluster_info" == *"localhost"* ]]; then
        echo "local"
        return
    fi
    
    # Cloud provider detection
    if [[ "$context" == *"prod"* ]] || [[ "$context" == *"production"* ]] || [[ "$cluster_info" == *"prod"* ]]; then
        echo "prod"
    elif [[ "$context" == *"staging"* ]] || [[ "$context" == *"stage"* ]] || [[ "$cluster_info" == *"staging"* ]]; then
        echo "staging"
    elif [[ "$context" == *"dev"* ]] || [[ "$context" == *"development"* ]] || [[ "$cluster_info" == *"dev"* ]]; then
        echo "dev"
    else
        # Default to production for unknown cloud contexts
        echo "prod"
    fi
}

# Determine if we should build images
should_build_images() {
    local env=$1
    
    case "$BUILD_IMAGES" in
        "true") echo "true" ;;
        "false") echo "false" ;;
        "auto")
            if [[ "$env" == "local" ]]; then
                echo "true"
            else
                echo "false"
            fi
            ;;
    esac
}

# Set up environment-specific configuration
setup_environment() {
    local detected_env=$1
    
    # Override with user-provided environment
    if [[ "$ENVIRONMENT" != "auto" ]]; then
        detected_env=$ENVIRONMENT
    fi
    
    # Set namespace (make it global)
    if [[ -z "$NAMESPACE" ]]; then
        NAMESPACE="munshi-${detected_env}"
    fi
    
    # Set values file (make it global)
    case "$detected_env" in
        "local")
            VALUES_FILE="values-local.yaml"
            ;;
        *)
            VALUES_FILE="values.yaml"  # Default production values for all non-local
            ;;
    esac
    
    # Set global environment variable for other functions to use
    FINAL_ENV="$detected_env"
}

# Validate environment and dependencies
validate_environment() {
    log "Validating environment..."
    
    local context=$(kubectl config current-context)
    local detected_env=$(detect_environment)
    
    # Call setup_environment to set globals
    setup_environment "$detected_env"
    
    info "Kubernetes context: $context"
    info "Detected environment: $detected_env"
    info "Final environment: $FINAL_ENV"
    info "Namespace: $NAMESPACE"
    info "Values file: $VALUES_FILE"
    
    # Check dependencies
    if ! command -v helm &> /dev/null; then
        error "Helm is not installed. Please install Helm 3.8+ first."
    fi
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed. Please install kubectl first."
    fi
    
    if [[ "$FINAL_ENV" == "local" ]] && ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker Desktop first."
    fi
    
    # Check if we can connect to the cluster
    if ! kubectl cluster-info > /dev/null 2>&1; then
        error "Cannot connect to Kubernetes cluster. Check your kubectl configuration."
    fi
    
    # Check if values file exists
    cd "$(dirname "$0")/.."
    if [[ ! -f "$CHART_PATH/$VALUES_FILE" ]]; then
        error "Values file not found: $CHART_PATH/$VALUES_FILE"
    fi
    
    log "Environment validation completed ✓"
}

# Build Docker images (for local development)
build_images() {
    log "Building Docker images..."
    
    cd "$(dirname "$0")/.."
    
    # Build API Gateway
    if [[ -f "services/api-gateway/Dockerfile" ]]; then
        log "Building API Gateway image..."
        docker build -t munshi/api-gateway:latest -f services/api-gateway/Dockerfile ./services/
    else
        warn "API Gateway Dockerfile not found, skipping build"
    fi
    
    # Build Auth Service  
    if [[ -f "services/auth-service/Dockerfile" ]]; then
        log "Building Auth Service image..."
        docker build -t munshi/auth-service:latest -f services/auth-service/Dockerfile ./services/
    else
        warn "Auth Service Dockerfile not found, skipping build"
    fi
    
    log "Image builds completed ✓"
}

# Add Helm repositories
add_helm_repos() {
    log "Adding Helm repositories..."
    
    helm repo add linkerd https://helm.linkerd.io/stable
    
    # Add additional repos for production environments
    local env=$1
    if [[ "$env" != "local" ]]; then
        helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 2>/dev/null || true
        helm repo add cert-manager https://charts.jetstack.io 2>/dev/null || true
    fi
    
    helm repo update
    log "Helm repositories updated ✓"
}

# Update Helm dependencies
update_dependencies() {
    log "Updating Helm dependencies..."
    cd "$(dirname "$0")/.."
    helm dependency update "$CHART_PATH"
    log "Helm dependencies updated ✓"
}


# Setup port forwarding for local environments
setup_port_forwarding() {
    local env=$1
    
    if [[ "$env" != "local" ]]; then
        return  # Only for local environments
    fi
    
    log "Setting up port forwarding for local access..."
    
    # Kill any existing port forwards
    pkill -f "kubectl port-forward.*munshi" || true
    pkill -f "kubectl port-forward.*linkerd" || true
    
    # Wait a moment for processes to terminate
    sleep 2
    
    # Port forward API Gateway
    log "Forwarding API Gateway (localhost:8000)..."
    kubectl port-forward -n "$NAMESPACE" svc/api-gateway 8000:8000 > /dev/null 2>&1 &
    
    # Port forward Linkerd dashboard if enabled
    if helm get values munshi -n "$NAMESPACE" 2>/dev/null | grep -q "linkerd.*enabled.*true"; then
        log "Forwarding Linkerd dashboard (localhost:50750)..."
        kubectl port-forward -n linkerd-viz svc/web 50750:8084 > /dev/null 2>&1 &
    fi
    
    log "Port forwarding setup completed ✓"
}

# Deploy the application
deploy() {
    local env=$1
    
    log "Deploying Munshi to Kubernetes..."
    log "Environment: $env"
    log "Namespace: $NAMESPACE"
    log "Values: $VALUES_FILE"
    
    cd "$(dirname "$0")/.."
    
    # Build images if needed
    if [[ "$(should_build_images "$env")" == "true" ]]; then
        build_images
    fi
    
    add_helm_repos "$env"
    update_dependencies
    
    # Let Helm create and manage the namespace
    
    # Deploy with Helm
    local timeout="10m"
    if [[ "$env" == "local" ]]; then
        timeout="5m"  # Shorter timeout for local
    fi
    
    helm upgrade --install munshi "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        --create-namespace \
        --values "$CHART_PATH/$VALUES_FILE" \
        --wait \
        --timeout "$timeout" \
        --atomic \
        --history-max 10
    
    log "Deployment completed ✓"
}

# Verify deployment
verify_deployment() {
    local env=$1
    
    log "Verifying deployment..."
    
    # Wait for pods to be ready
    log "Waiting for pods to be ready..."
    local timeout="300s"
    if [[ "$env" == "local" ]]; then
        timeout="120s"
    fi
    
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=munshi -n "$NAMESPACE" --timeout="$timeout"
    
    # Check deployment status
    kubectl get pods,svc -n "$NAMESPACE"
    
    # Setup port forwarding for local
    if [[ "$env" == "local" ]]; then
        setup_port_forwarding "$env"
    fi
    
    log "Verification completed ✓"
}

# Show deployment information
show_info() {
    local env=$1
    
    log "🎉 Deployment Information:"
    
    if [[ "$env" == "local" ]]; then
        info "🏠 Local Development Environment"
        info "  Application: http://localhost:8000"
        info "  Linkerd Dashboard: http://localhost:50750"
        info "  Health Check: http://localhost:8000/health"
    else
        info "☁️  Cloud Environment: $env"
        
        # Get ingress information
        local ingress_ip=""
        local ingress_host=""
        
        if kubectl get ingress -n "$NAMESPACE" > /dev/null 2>&1; then
            ingress_ip=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
            ingress_host=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null || echo "")
        fi
        
        if [[ -n "$ingress_host" ]]; then
            info "  Application URL: https://$ingress_host"
        elif [[ -n "$ingress_ip" ]]; then
            info "  Application IP: $ingress_ip"
        else
            info "  Port Forward: kubectl port-forward -n $NAMESPACE svc/api-gateway 8080:8000"
        fi
        
        info "  Linkerd Dashboard: kubectl port-forward -n linkerd-viz svc/web 50750:8084"
    fi
    
    info ""
    info "🔧 Useful Commands:"
    info "  Status: $0 status"
    info "  Logs: $0 logs"
    info "  Upgrade: $0 upgrade"
    info "  Delete: $0 delete"
}

# Main execution
main() {
    log "🚀 Starting Munshi deployment..."
    
    validate_environment
    
    deploy "$FINAL_ENV"
    verify_deployment "$FINAL_ENV"
    show_info "$FINAL_ENV"
    
    log "🎉 Deployment successful!"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy"|"install")
        main
        ;;
    "build")
        validate_environment
        if [[ "$FINAL_ENV" == "local" ]]; then
            build_images
            log "Image builds completed! Run '$0' to deploy."
        else
            error "Image building only supported for local environments. Use CI/CD for cloud deployments."
        fi
        ;;
    "upgrade")
        log "Upgrading existing deployment..."
        validate_environment
        deploy "$FINAL_ENV"
        verify_deployment "$FINAL_ENV"
        show_info "$FINAL_ENV"
        ;;
    "status")
        validate_environment
        helm status munshi -n "$NAMESPACE"
        kubectl get all -n "$NAMESPACE"
        ;;
    "logs")
        validate_environment
        kubectl logs -n "$NAMESPACE" -l app.kubernetes.io/name=munshi --tail=100 -f
        ;;
    "rollback")
        validate_environment
        log "Rolling back deployment..."
        helm rollback munshi -n "$NAMESPACE"
        kubectl rollout status deployment -n "$NAMESPACE"
        ;;
    "delete"|"uninstall")
        validate_environment
        log "Removing deployment..."
        helm uninstall munshi -n "$NAMESPACE" || true
        
        if [[ "$FINAL_ENV" == "local" ]]; then
            # Stop port forwarding for local
            pkill -f "kubectl port-forward.*munshi" || true
            pkill -f "kubectl port-forward.*linkerd" || true
        fi
        
        read -p "Delete namespace $NAMESPACE? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kubectl delete namespace "$NAMESPACE" || true
        fi
        
        log "Deployment removed ✓"
        ;;
    "stop")
        # Stop port forwarding (local only)
        log "Stopping port forwarding..."
        pkill -f "kubectl port-forward.*munshi" || true
        pkill -f "kubectl port-forward.*linkerd" || true
        log "Port forwarding stopped ✓"
        ;;
    "help"|"-h"|"--help")
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac