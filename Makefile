# Munshi Microservices

.PHONY: help install test lint format deploy status logs clean
.DEFAULT_GOAL := help

# Variables
POETRY := poetry
GITHUB_USERNAME ?= your-username
TAG ?= latest

# Colors
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
NC := \033[0m

help: ## Show available commands
	@echo "$(BLUE)Munshi Microservices$(NC)"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# SETUP
# =============================================================================

install: ## Install dependencies
	$(POETRY) install --with dev,test

# =============================================================================
# DEPLOYMENT
# =============================================================================

deploy: ## Deploy to current Kubernetes context
	@./scripts/deploy.sh

build: ## Build images (local only)
	@./scripts/deploy.sh build

upgrade: ## Upgrade deployment
	@./scripts/deploy.sh upgrade

status: ## Show deployment status
	@./scripts/deploy.sh status

logs: ## Show application logs
	@./scripts/deploy.sh logs

rollback: ## Rollback deployment
	@./scripts/deploy.sh rollback

clean: ## Remove deployment
	@./scripts/deploy.sh delete

# =============================================================================
# DEVELOPMENT
# =============================================================================

test: ## Run tests
	$(POETRY) run pytest tests/ -v

lint: ## Check code style
	$(POETRY) run black --check services/
	$(POETRY) run isort --check-only services/
	$(POETRY) run flake8 services/

format: ## Format code
	$(POETRY) run black services/
	$(POETRY) run isort services/

# =============================================================================
# CLOUD IMAGES
# =============================================================================

push: ## Build and push images to registry
	@if [ "$(GITHUB_USERNAME)" = "your-username" ]; then \
		echo "$(YELLOW)Set GITHUB_USERNAME: make push GITHUB_USERNAME=myuser$(NC)"; \
		exit 1; \
	fi
	@docker build -t ghcr.io/$(GITHUB_USERNAME)/munshi/api-gateway:$(TAG) services/api-gateway/
	@docker build -t ghcr.io/$(GITHUB_USERNAME)/munshi/auth-service:$(TAG) services/auth-service/
	@docker push ghcr.io/$(GITHUB_USERNAME)/munshi/api-gateway:$(TAG)
	@docker push ghcr.io/$(GITHUB_USERNAME)/munshi/auth-service:$(TAG)
	@echo "$(GREEN)Images pushed to ghcr.io/$(GITHUB_USERNAME)/munshi$(NC)"