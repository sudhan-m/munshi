# Munshi Microservices - Helm Deployment

.PHONY: help install dev build test lint format clean deploy status logs
.DEFAULT_GOAL := help

# Variables
PYTHON_VERSION := 3.11
POETRY := ~/.local/bin/poetry
GITHUB_USERNAME ?= your-username
PROJECT_NAME := munshi
TAG ?= latest

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
RED := \033[31m
YELLOW := \033[33m
NC := \033[0m

help: ## Show this help message
	@echo "$(BLUE)Munshi Microservices - Helm Deployment$(NC)"
	@echo "Available commands:"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-25s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# DEVELOPMENT SETUP
# =============================================================================

install: ## Install project dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(POETRY) install --with dev,test
	@echo "$(GREEN)Dependencies installed successfully$(NC)"

install-dev: ## Install development dependencies with pre-commit
	@echo "$(BLUE)Installing development environment...$(NC)"
	$(POETRY) install --with dev,test
	$(POETRY) run pre-commit install
	@echo "$(GREEN)Development environment ready$(NC)"

init: ## Initialize project for first-time setup
	@echo "$(BLUE)Initializing project...$(NC)"
	@make install-dev
	@echo "$(GREEN)Project initialized successfully$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Run 'make deploy' to deploy to current Kubernetes context"
	@echo "  2. Run 'make status' to check deployment status"

# =============================================================================
# UNIVERSAL DEPLOYMENT
# =============================================================================

deploy: ## Deploy to current Kubernetes context (auto-detects environment)
	@echo "$(BLUE)🚀 Deploying to current Kubernetes context...$(NC)"
	@./scripts/deploy.sh

deploy-local: ## Force local environment deployment
	@echo "$(BLUE)🏠 Deploying to local environment...$(NC)"
	@ENVIRONMENT=local ./scripts/deploy.sh

deploy-dev: ## Force development environment deployment
	@echo "$(BLUE)🔧 Deploying to development environment...$(NC)"
	@ENVIRONMENT=dev ./scripts/deploy.sh

deploy-staging: ## Force staging environment deployment
	@echo "$(BLUE)🎭 Deploying to staging environment...$(NC)"
	@ENVIRONMENT=staging ./scripts/deploy.sh

deploy-prod: ## Force production environment deployment
	@echo "$(BLUE)🏭 Deploying to production environment...$(NC)"
	@ENVIRONMENT=prod ./scripts/deploy.sh

build: ## Build images (local only)
	@echo "$(BLUE)🔨 Building images...$(NC)"
	@./scripts/deploy.sh build

upgrade: ## Upgrade existing deployment
	@echo "$(BLUE)⬆️  Upgrading deployment...$(NC)"
	@./scripts/deploy.sh upgrade

rollback: ## Rollback deployment
	@echo "$(BLUE)⏪ Rolling back deployment...$(NC)"
	@./scripts/deploy.sh rollback

stop: ## Stop port forwarding (local only)
	@echo "$(BLUE)⏹️  Stopping port forwarding...$(NC)"
	@./scripts/deploy.sh stop

clean: ## Remove deployment
	@echo "$(BLUE)🧹 Removing deployment...$(NC)"
	@./scripts/deploy.sh delete

# =============================================================================
# IMAGE MANAGEMENT
# =============================================================================

build-cloud: ## Build images for cloud deployment
	@echo "$(BLUE)🔨 Building cloud images...$(NC)"
	@if [ "$(GITHUB_USERNAME)" = "your-username" ]; then \
		echo "$(RED)❌ Please set GITHUB_USERNAME: make build-cloud GITHUB_USERNAME=your-github-username$(NC)"; \
		exit 1; \
	fi
	@docker build -t ghcr.io/$(GITHUB_USERNAME)/$(PROJECT_NAME)/api-gateway:$(TAG) services/api-gateway/
	@docker build -t ghcr.io/$(GITHUB_USERNAME)/$(PROJECT_NAME)/auth-service:$(TAG) services/auth-service/
	@echo "$(GREEN)Cloud images built$(NC)"

push-cloud: build-cloud ## Build and push images to GitHub Container Registry
	@echo "$(BLUE)📤 Pushing images to GitHub Container Registry...$(NC)"
	@docker push ghcr.io/$(GITHUB_USERNAME)/$(PROJECT_NAME)/api-gateway:$(TAG)
	@docker push ghcr.io/$(GITHUB_USERNAME)/$(PROJECT_NAME)/auth-service:$(TAG)
	@echo "$(GREEN)Images pushed to GitHub Container Registry$(NC)"

clean-images: ## Clean up local Docker images
	@echo "$(BLUE)🧹 Cleaning local images...$(NC)"
	@docker rmi $(PROJECT_NAME)/api-gateway:latest 2>/dev/null || true
	@docker rmi $(PROJECT_NAME)/auth-service:latest 2>/dev/null || true
	@docker rmi ghcr.io/$(GITHUB_USERNAME)/$(PROJECT_NAME)/api-gateway:$(TAG) 2>/dev/null || true
	@docker rmi ghcr.io/$(GITHUB_USERNAME)/$(PROJECT_NAME)/auth-service:$(TAG) 2>/dev/null || true
	@echo "$(GREEN)Images cleaned$(NC)"

# =============================================================================
# TESTING
# =============================================================================

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(POETRY) run pytest tests/ -v --cov=services --cov-report=term-missing
	@echo "$(GREEN)Tests completed$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(POETRY) run pytest tests/ -m "unit" -v
	@echo "$(GREEN)Unit tests completed$(NC)"

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(POETRY) run pytest tests/ -m "integration" -v
	@echo "$(GREEN)Integration tests completed$(NC)"

test-e2e: ## Run end-to-end tests
	@echo "$(BLUE)Running end-to-end tests...$(NC)"
	$(POETRY) run pytest tests/ -m "e2e" -v
	@echo "$(GREEN)End-to-end tests completed$(NC)"

# =============================================================================
# CODE QUALITY
# =============================================================================

lint: ## Run linting checks
	@echo "$(BLUE)Running linting checks...$(NC)"
	$(POETRY) run black --check services/
	$(POETRY) run isort --check-only services/
	$(POETRY) run flake8 services/
	$(POETRY) run mypy services/
	@echo "$(GREEN)Linting checks passed$(NC)"

format: ## Format code
	@echo "$(BLUE)Formatting code...$(NC)"
	$(POETRY) run black services/
	$(POETRY) run isort services/
	@echo "$(GREEN)Code formatted$(NC)"

security-scan: ## Run security scans
	@echo "$(BLUE)Running security scans...$(NC)"
	$(POETRY) run bandit -r services/
	$(POETRY) run safety check
	@echo "$(GREEN)Security scans completed$(NC)"

# =============================================================================
# HELM UTILITIES
# =============================================================================

helm-deps: ## Update Helm dependencies
	@echo "$(BLUE)Updating Helm dependencies...$(NC)"
	@helm dependency update infrastructure/helm/munshi
	@echo "$(GREEN)Helm dependencies updated$(NC)"

helm-lint: ## Lint Helm charts
	@echo "$(BLUE)Linting Helm charts...$(NC)"
	@helm lint infrastructure/helm/munshi
	@echo "$(GREEN)Helm charts linted$(NC)"

helm-template: ## Generate Helm templates (dry-run)
	@echo "$(BLUE)Generating Helm templates...$(NC)"
	@helm template munshi infrastructure/helm/munshi -f infrastructure/helm/munshi/values-local.yaml

# =============================================================================
# MONITORING & UTILITIES
# =============================================================================

status: ## Show deployment status
	@echo "$(BLUE)📊 Deployment Status:$(NC)"
	@./scripts/deploy.sh status

logs: ## Show application logs
	@echo "$(BLUE)📝 Application Logs:$(NC)"
	@./scripts/deploy.sh logs

health: ## Check service health
	@echo "$(BLUE)🏥 Checking service health...$(NC)"
	@if kubectl get svc api-gateway -n munshi-local >/dev/null 2>&1; then \
		echo "$(GREEN)Local deployment active$(NC)"; \
	elif kubectl get svc api-gateway -n munshi-prod >/dev/null 2>&1; then \
		echo "$(GREEN)Production deployment active$(NC)"; \
	else \
		echo "$(RED)No active deployments found$(NC)"; \
	fi

version: ## Show version information
	@echo "$(BLUE)🔖 Version information:$(NC)"
	@echo "Python: $$(python --version 2>&1)"
	@echo "Poetry: $$($(POETRY) --version 2>&1)"
	@echo "Docker: $$(docker --version 2>&1)"
	@echo "Kubernetes: $$(kubectl version --client --short 2>&1)"
	@echo "Helm: $$(helm version --short 2>&1)"

# =============================================================================
# EXAMPLES
# =============================================================================

examples: ## Show usage examples
	@echo "$(BLUE)📖 Usage Examples:$(NC)"
	@echo
	@echo "$(GREEN)🚀 Universal Deployment:$(NC)"
	@echo "  make deploy                       # Auto-detect and deploy"
	@echo "  make deploy-local                 # Force local (Docker Desktop)"
	@echo "  make deploy-dev                   # Force development environment"
	@echo "  make deploy-staging               # Force staging environment"
	@echo "  make deploy-prod                  # Force production environment"
	@echo
	@echo "$(GREEN)🔧 Management:$(NC)"
	@echo "  make status                       # Check deployment status"
	@echo "  make logs                         # View application logs"
	@echo "  make upgrade                      # Upgrade existing deployment"
	@echo "  make rollback                     # Rollback deployment"
	@echo "  make clean                        # Remove deployment"
	@echo
	@echo "$(GREEN)🐳 Image Management:$(NC)"
	@echo "  make build                        # Build images (local only)"
	@echo "  make push-cloud GITHUB_USERNAME=myuser TAG=v1.2.3"
	@echo
	@echo "$(GREEN)🧪 Testing & Quality:$(NC)"
	@echo "  make test                         # Run all tests"
	@echo "  make lint                         # Code quality checks"
	@echo "  make format                       # Format code"