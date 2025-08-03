#!/bin/bash

# Deployment script for Munshi Microservices with Linkerd Service Mesh
# Supports both Kubernetes and Docker Compose deployments

set -e

DEPLOYMENT_TYPE=${1:-"help"}
ENVIRONMENT=${2:-"development"}

echo "🚀 Munshi Microservices Deployment Script"
echo "============================================"

case $DEPLOYMENT_TYPE in
    "k8s"|"kubernetes")
        echo "📦 Deploying to Kubernetes with Linkerd..."
        
        # Check if kubectl is available
        if ! command -v kubectl &> /dev/null; then
            echo "❌ kubectl is required for Kubernetes deployment"
            exit 1
        fi
        
        # Check if Linkerd is installed
        if ! command -v linkerd &> /dev/null; then
            echo "📥 Installing Linkerd..."
            ./linkerd/linkerd-install.sh
        fi
        
        # Verify Linkerd is running
        echo "🔍 Checking Linkerd status..."
        linkerd check
        
        # Create namespace with Linkerd injection
        echo "🏗️ Creating munshi namespace..."
        kubectl apply -f k8s/namespace.yaml
        
        # Deploy databases and Redis
        echo "🗄️ Deploying databases and Redis..."
        kubectl apply -f k8s/postgres-auth.yaml
        kubectl apply -f k8s/postgres-gateway.yaml
        kubectl apply -f k8s/redis-auth.yaml
        kubectl apply -f k8s/redis-gateway.yaml
        
        # Wait for databases to be ready
        echo "⏳ Waiting for databases to be ready..."
        kubectl wait --for=condition=available --timeout=300s deployment/postgres-auth -n munshi
        kubectl wait --for=condition=available --timeout=300s deployment/postgres-gateway -n munshi
        kubectl wait --for=condition=available --timeout=300s deployment/redis-auth -n munshi
        kubectl wait --for=condition=available --timeout=300s deployment/redis-gateway -n munshi
        
        # Deploy services
        echo "🔐 Deploying authentication service..."
        kubectl apply -f k8s/auth-service.yaml
        
        echo "🌐 Deploying API gateway..."
        kubectl apply -f k8s/api-gateway.yaml
        
        echo "🔄 Deploying Caddy ingress..."
        kubectl apply -f k8s/caddy-ingress.yaml
        
        # Apply Linkerd service profiles
        echo "📊 Applying Linkerd service profiles..."
        kubectl apply -f k8s/linkerd-service-profiles.yaml
        
        # Apply monitoring configuration
        echo "📈 Setting up monitoring..."
        kubectl apply -f k8s/monitoring.yaml
        
        # Wait for services to be ready
        echo "⏳ Waiting for services to be ready..."
        kubectl wait --for=condition=available --timeout=300s deployment/auth-service -n munshi
        kubectl wait --for=condition=available --timeout=300s deployment/api-gateway -n munshi
        kubectl wait --for=condition=available --timeout=300s deployment/caddy-ingress -n munshi
        
        # Get service status
        echo "✅ Deployment complete! Service status:"
        kubectl get pods -n munshi
        kubectl get services -n munshi
        
        echo ""
        echo "🎉 Access your services:"
        echo "📊 Linkerd Dashboard: linkerd viz dashboard"
        echo "🔍 Jaeger Tracing: linkerd jaeger dashboard"
        echo "📈 Grafana: kubectl port-forward -n linkerd-viz svc/grafana 3000"
        echo "🌐 Application: kubectl port-forward -n munshi svc/caddy-ingress 8443:443"
        
        ;;
        
    "docker"|"compose")
        echo "🐳 Deploying with Docker Compose (Linkerd-compatible)..."
        
        if [ "$ENVIRONMENT" = "production" ]; then
            echo "⚠️  Docker Compose is not recommended for production with Linkerd"
            echo "    Consider using Kubernetes deployment instead"
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
        
        # Build images
        echo "🔨 Building Docker images..."
        docker-compose -f docker-compose.linkerd.yml build
        
        # Start services
        echo "🚀 Starting services..."
        docker-compose -f docker-compose.linkerd.yml up -d
        
        # Wait for services to be healthy
        echo "⏳ Waiting for services to be healthy..."
        sleep 30
        
        # Check service health
        echo "🔍 Checking service health..."
        docker-compose -f docker-compose.linkerd.yml ps
        
        echo ""
        echo "✅ Deployment complete!"
        echo "🎉 Access your services:"
        echo "🌐 Application: https://localhost"
        echo "📊 Caddy Admin: http://localhost:2019"
        echo "🔍 Jaeger UI: http://localhost:16686"
        echo "📈 Linkerd Viz: http://localhost:8080"
        
        ;;
        
    "clean")
        echo "🧹 Cleaning up deployments..."
        
        if [ -f "k8s/namespace.yaml" ]; then
            echo "🗑️ Cleaning Kubernetes resources..."
            kubectl delete namespace munshi --ignore-not-found=true
        fi
        
        if [ -f "docker-compose.linkerd.yml" ]; then
            echo "🗑️ Cleaning Docker Compose resources..."
            docker-compose -f docker-compose.linkerd.yml down -v
            docker system prune -f
        fi
        
        echo "✅ Cleanup complete!"
        ;;
        
    "status")
        echo "📊 Checking deployment status..."
        
        if command -v kubectl &> /dev/null; then
            echo ""
            echo "📦 Kubernetes Status:"
            kubectl get pods -n munshi 2>/dev/null || echo "No Kubernetes deployment found"
            
            if command -v linkerd &> /dev/null; then
                echo ""
                echo "🔗 Linkerd Status:"
                linkerd stat deploy -n munshi 2>/dev/null || echo "Linkerd not found or no deployments"
            fi
        fi
        
        if [ -f "docker-compose.linkerd.yml" ]; then
            echo ""
            echo "🐳 Docker Compose Status:"
            docker-compose -f docker-compose.linkerd.yml ps 2>/dev/null || echo "No Docker Compose deployment found"
        fi
        ;;
        
    "help"|*)
        echo "Usage: $0 <deployment-type> [environment]"
        echo ""
        echo "Deployment Types:"
        echo "  k8s, kubernetes  - Deploy to Kubernetes with Linkerd (recommended)"
        echo "  docker, compose  - Deploy with Docker Compose (development only)"
        echo "  clean            - Clean up all deployments"
        echo "  status           - Check deployment status"
        echo "  help             - Show this help message"
        echo ""
        echo "Environments:"
        echo "  development      - Development environment (default)"
        echo "  production       - Production environment"
        echo ""
        echo "Examples:"
        echo "  $0 k8s production          # Deploy to Kubernetes for production"
        echo "  $0 docker development      # Deploy with Docker Compose for development"
        echo "  $0 status                  # Check current deployment status"
        echo "  $0 clean                   # Clean up all deployments"
        ;;
esac