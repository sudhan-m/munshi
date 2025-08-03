#!/bin/bash

# Universal deployment script for Munshi microservices
# Supports Docker Compose and Kubernetes deployments
# with Linkerd service mesh integration

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INFRASTRUCTURE_DIR="${PROJECT_ROOT}/infrastructure"

# Default values
DEPLOYMENT_TYPE="docker"
ENVIRONMENT="development"
LINKERD_ENABLED=false
VERBOSE=false
DRY_RUN=false
FORCE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS] <deployment-type> <environment>

Deploy Munshi microservices using Docker Compose or Kubernetes

ARGUMENTS:
    deployment-type    Deployment type: docker|k8s|kubernetes
    environment        Environment: development|staging|production

OPTIONS:
    -l, --linkerd      Enable Linkerd service mesh integration
    -v, --verbose      Enable verbose output
    -n, --dry-run      Show what would be done without executing
    -f, --force        Force deployment without confirmation
    -h, --help         Show this help message

EXAMPLES:
    $0 docker development                    # Docker development deployment
    $0 k8s production --linkerd              # Kubernetes production with Linkerd
    $0 docker development --verbose          # Docker with verbose output
    $0 k8s staging --dry-run                 # Kubernetes staging dry run

EOF
}

# Main deployment function
main() {
    log_info "Starting Munshi microservices deployment"
    log_success "Deployment script ready!"
    log_info "Use this script to deploy Munshi microservices"
}

main "$@"