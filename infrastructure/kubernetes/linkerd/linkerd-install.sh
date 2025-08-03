#!/bin/bash

# Linkerd Service Mesh Installation Script for Munshi Microservices
# This script installs and configures Linkerd for automatic mTLS and observability

set -e

echo "🔗 Installing Linkerd Service Mesh for Munshi Microservices..."

# Check if running in Kubernetes environment
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is required but not installed. Installing..."
    # Install kubectl if not present
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    sudo mv kubectl /usr/local/bin/
fi

# Download and install Linkerd CLI
echo "📥 Downloading Linkerd CLI..."
curl -sL https://run.linkerd.io/install | sh
export PATH=$PATH:$HOME/.linkerd2/bin

# Verify Linkerd CLI installation
echo "✅ Verifying Linkerd CLI..."
linkerd version

# Pre-check cluster
echo "🔍 Performing pre-installation checks..."
linkerd check --pre

# Install Linkerd CRDs
echo "📦 Installing Linkerd CRDs..."
linkerd install --crds | kubectl apply -f -

# Install Linkerd control plane
echo "🎛️ Installing Linkerd control plane..."
linkerd install | kubectl apply -f -

# Wait for control plane to be ready
echo "⏳ Waiting for Linkerd control plane to be ready..."
linkerd check

# Install Linkerd Viz extension for observability
echo "📊 Installing Linkerd Viz extension..."
linkerd viz install | kubectl apply -f -

# Wait for viz extension to be ready
echo "⏳ Waiting for Linkerd Viz to be ready..."
linkerd viz check

# Install Linkerd Jaeger extension for distributed tracing
echo "🔍 Installing Linkerd Jaeger extension..."
linkerd jaeger install | kubectl apply -f -

echo "✅ Linkerd installation complete!"
echo ""
echo "🎉 Next steps:"
echo "1. Deploy your services: kubectl apply -f k8s/"
echo "2. Inject Linkerd proxy: kubectl get -n munshi deploy -o yaml | linkerd inject - | kubectl apply -f -"
echo "3. Access dashboard: linkerd viz dashboard"
echo "4. View metrics: linkerd viz stat deploy -n munshi"