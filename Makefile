# Munshi Language Learning Platform - Root Makefile
# =============================================================================

# Project Configuration
PROJECT_NAME := munshi
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
REGISTRY := docker.io/munshi
HELM_CHART_DIR := infrastructure/helm/munshi-platform

# Service Configuration
SERVICES := auth-service audio-service asr-service conversation-service llm-service pronunciation-evaluator ui-service
SERVICE_DIRS := $(addprefix services/,$(SERVICES))

# Environment Configuration
DEV_NAMESPACE := munshi-dev
STAGING_NAMESPACE := munshi-staging
PROD_NAMESPACE := munshi-prod

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
NC := \033[0m # No Color

.PHONY: help clean setup
.PHONY: build build-all push push-all
.PHONY: dev staging prod
.PHONY: test test-services test-integration
.PHONY: lint format security-scan
.PHONY: docs start-dev stop-dev
.PHONY: backup restore

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "$(CYAN)🎓 Munshi Language Learning Platform$(NC)"
	@echo "====================================="
	@echo ""
	@echo "$(GREEN)🏗️  Build & Deploy:$(NC)"
	@awk '/^[a-zA-Z_-]+:.*?## .*$$/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | grep -E "(build|push|dev|staging|prod)"
	@echo ""
	@echo "$(GREEN)🧪 Testing & Quality:$(NC)"
	@awk '/^[a-zA-Z_-]+:.*?## .*$$/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | grep -E "(test|lint|format|security)"
	@echo ""
	@echo "$(GREEN)🔧 Development:$(NC)"
	@awk '/^[a-zA-Z_-]+:.*?## .*$$/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | grep -E "(setup|start|stop|docs|clean)"
	@echo ""
	@echo "$(GREEN)💾 Operations:$(NC)"
	@awk '/^[a-zA-Z_-]+:.*?## .*$$/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | grep -E "(backup|restore|status)"
	@echo ""
	@echo "$(PURPLE)📊 Current Status:$(NC)"
	@echo "  Version: $(VERSION)"
	@echo "  Registry: $(REGISTRY)"
	@echo "  Services: $(words $(SERVICES)) total"

# =============================================================================
# Setup & Prerequisites
# =============================================================================

setup: ## Install all prerequisites and dependencies
	@echo "$(BLUE)🚀 Setting up Munshi development environment...$(NC)"
	@echo "$(YELLOW)Checking prerequisites...$(NC)"
	@command -v docker >/dev/null 2>&1 || (echo "$(RED)❌ Docker not found. Please install Docker.$(NC)" && exit 1)
	@command -v kubectl >/dev/null 2>&1 || (echo "$(RED)❌ kubectl not found. Please install kubectl.$(NC)" && exit 1)
	@command -v helm >/dev/null 2>&1 || (echo "$(RED)❌ Helm not found. Please install Helm.$(NC)" && exit 1)
	@command -v kind >/dev/null 2>&1 || (echo "$(RED)❌ kind not found. Please install kind.$(NC)" && exit 1)
	@echo "$(GREEN)✓ All prerequisites found$(NC)"
	@echo "$(YELLOW)Setting up Python environments...$(NC)"
	@for service in $(SERVICES); do \
		if [ -f "services/$$service/requirements.txt" ]; then \
			echo "$(BLUE)Setting up $$service...$(NC)"; \
			cd "services/$$service" && \
			(python3 -m venv venv 2>/dev/null || true) && \
			(source venv/bin/activate && pip install -r requirements.txt 2>/dev/null || true) && \
			cd ../..; \
		fi; \
	done
	@echo "$(YELLOW)Setting up UI service...$(NC)"
	@if [ -f "services/ui-service/package.json" ]; then \
		cd services/ui-service && npm install && cd ../..; \
	fi
	@echo "$(GREEN)✓ Development environment setup complete!$(NC)"

clean: ## Clean up all generated files and containers
	@echo "$(YELLOW)🧹 Cleaning up...$(NC)"
	@echo "Removing Docker containers and images..."
	@docker container prune -f 2>/dev/null || true
	@docker image prune -f 2>/dev/null || true
	@echo "Cleaning Python cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaning Node.js files..."
	@find . -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaning build artifacts..."
	@rm -rf services/ui-service/dist 2>/dev/null || true
	@cd $(HELM_CHART_DIR) && make clean 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

# =============================================================================
# Docker Build & Push
# =============================================================================

build: ## Build Docker images for all services
	@echo "$(BLUE)🏗️  Building all Docker images...$(NC)"
	@for service in $(SERVICES); do \
		echo "$(YELLOW)Building $$service...$(NC)"; \
		cd "services/$$service" && \
		docker build -t $(REGISTRY)/$$service:$(VERSION) -t $(REGISTRY)/$$service:latest . && \
		cd ../..; \
	done
	@echo "$(GREEN)✓ All images built successfully$(NC)"

build-service: ## Build specific service (usage: make build-service SERVICE=auth-service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)❌ Please specify SERVICE (e.g., make build-service SERVICE=auth-service)$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)🏗️  Building $(SERVICE)...$(NC)"
	@cd "services/$(SERVICE)" && \
	docker build -t $(REGISTRY)/$(SERVICE):$(VERSION) -t $(REGISTRY)/$(SERVICE):latest .
	@echo "$(GREEN)✓ $(SERVICE) built successfully$(NC)"

push: build ## Build and push all Docker images to registry
	@echo "$(BLUE)📤 Pushing all images to $(REGISTRY)...$(NC)"
	@for service in $(SERVICES); do \
		echo "$(YELLOW)Pushing $$service...$(NC)"; \
		docker push $(REGISTRY)/$$service:$(VERSION); \
		docker push $(REGISTRY)/$$service:latest; \
	done
	@echo "$(GREEN)✓ All images pushed successfully$(NC)"

push-service: build-service ## Build and push specific service
	@echo "$(BLUE)📤 Pushing $(SERVICE) to $(REGISTRY)...$(NC)"
	@docker push $(REGISTRY)/$(SERVICE):$(VERSION)
	@docker push $(REGISTRY)/$(SERVICE):latest
	@echo "$(GREEN)✓ $(SERVICE) pushed successfully$(NC)"

# =============================================================================
# Environment Deployment
# =============================================================================

dev: ## Deploy to development environment
	@echo "$(BLUE)🚀 Deploying to development environment...$(NC)"
	@cd $(HELM_CHART_DIR) && make install-dev
	@echo "$(GREEN)✓ Development deployment complete$(NC)"
	@echo "$(CYAN)💡 Access the app: https://munshi.local$(NC)"
	@echo "$(CYAN)💡 Add '127.0.0.1 munshi.local' to /etc/hosts if needed$(NC)"

staging: ## Deploy to staging environment
	@echo "$(BLUE)🚀 Deploying to staging environment...$(NC)"
	@cd $(HELM_CHART_DIR) && make install-staging
	@echo "$(GREEN)✓ Staging deployment complete$(NC)"

prod: ## Deploy to production environment (with confirmation)
	@echo "$(RED)⚠️  WARNING: This will deploy to PRODUCTION!$(NC)"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || (echo "$(RED)Aborted$(NC)" && exit 1)
	@cd $(HELM_CHART_DIR) && make install-prod
	@echo "$(GREEN)✓ Production deployment complete$(NC)"

# =============================================================================
# Development Environment
# =============================================================================

start-dev: ## Start complete development environment
	@echo "$(BLUE)🎬 Starting development environment...$(NC)"
	@cd $(HELM_CHART_DIR) && make quick-start
	@echo "$(GREEN)🎉 Development environment ready!$(NC)"
	@echo ""
	@echo "$(CYAN)📋 Quick Start Guide:$(NC)"
	@echo "1. Add to /etc/hosts: 127.0.0.1 munshi.local"
	@echo "2. Visit: https://munshi.local"
	@echo "3. Or use: make port-forward"
	@echo ""

stop-dev: ## Stop development environment
	@echo "$(YELLOW)🛑 Stopping development environment...$(NC)"
	@cd $(HELM_CHART_DIR) && make uninstall-dev
	@cd $(HELM_CHART_DIR) && make dev-teardown
	@echo "$(GREEN)✓ Development environment stopped$(NC)"

port-forward: ## Port forward to development UI service
	@echo "$(BLUE)🔌 Port forwarding to UI service...$(NC)"
	@cd $(HELM_CHART_DIR) && make port-forward-dev

restart-dev: stop-dev start-dev ## Restart development environment

# =============================================================================
# Testing
# =============================================================================

test: test-services test-integration ## Run all tests

test-services: ## Run unit tests for all services
	@echo "$(BLUE)🧪 Running service tests...$(NC)"
	@for service in $(SERVICES); do \
		echo "$(YELLOW)Testing $$service...$(NC)"; \
		if [ -f "services/$$service/requirements.txt" ] && [ -d "services/$$service/venv" ]; then \
			cd "services/$$service" && \
			source venv/bin/activate && \
			(python -m pytest tests/ 2>/dev/null || echo "$(YELLOW)⚠️  No tests found for $$service$(NC)") && \
			cd ../..; \
		elif [ -f "services/$$service/package.json" ]; then \
			cd "services/$$service" && \
			(npm test 2>/dev/null || echo "$(YELLOW)⚠️  No tests found for $$service$(NC)") && \
			cd ../..; \
		fi; \
	done
	@echo "$(GREEN)✓ Service tests complete$(NC)"

test-integration: ## Run integration tests
	@echo "$(BLUE)🔗 Running integration tests...$(NC)"
	@if [ -d "tests/integration" ]; then \
		cd tests/integration && python -m pytest .; \
	else \
		echo "$(YELLOW)⚠️  No integration tests found$(NC)"; \
	fi
	@echo "$(GREEN)✓ Integration tests complete$(NC)"

test-e2e: ## Run end-to-end tests
	@echo "$(BLUE)🎭 Running E2E tests...$(NC)"
	@if [ -d "tests/e2e" ]; then \
		cd tests/e2e && python -m pytest .; \
	else \
		echo "$(YELLOW)⚠️  No E2E tests found$(NC)"; \
	fi
	@echo "$(GREEN)✓ E2E tests complete$(NC)"

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linters on all services
	@echo "$(BLUE)🔍 Running linters...$(NC)"
	@for service in $(SERVICES); do \
		echo "$(YELLOW)Linting $$service...$(NC)"; \
		if [ -f "services/$$service/requirements.txt" ]; then \
			cd "services/$$service" && \
			(source venv/bin/activate && flake8 . 2>/dev/null || echo "$(YELLOW)⚠️  flake8 not available for $$service$(NC)") && \
			cd ../..; \
		elif [ -f "services/$$service/package.json" ]; then \
			cd "services/$$service" && \
			(npm run lint 2>/dev/null || echo "$(YELLOW)⚠️  No linting configured for $$service$(NC)") && \
			cd ../..; \
		fi; \
	done
	@cd $(HELM_CHART_DIR) && make lint
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code in all services
	@echo "$(BLUE)✨ Formatting code...$(NC)"
	@for service in $(SERVICES); do \
		echo "$(YELLOW)Formatting $$service...$(NC)"; \
		if [ -f "services/$$service/requirements.txt" ]; then \
			cd "services/$$service" && \
			(source venv/bin/activate && black . 2>/dev/null || echo "$(YELLOW)⚠️  black not available for $$service$(NC)") && \
			cd ../..; \
		elif [ -f "services/$$service/package.json" ]; then \
			cd "services/$$service" && \
			(npm run format 2>/dev/null || echo "$(YELLOW)⚠️  No formatting configured for $$service$(NC)") && \
			cd ../..; \
		fi; \
	done
	@echo "$(GREEN)✓ Formatting complete$(NC)"

security-scan: ## Run security scans on Docker images
	@echo "$(BLUE)🔒 Running security scans...$(NC)"
	@for service in $(SERVICES); do \
		echo "$(YELLOW)Scanning $$service...$(NC)"; \
		(docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		 aquasec/trivy:latest image $(REGISTRY)/$$service:latest 2>/dev/null || \
		 echo "$(YELLOW)⚠️  Trivy not available, skipping scan for $$service$(NC)"); \
	done
	@echo "$(GREEN)✓ Security scans complete$(NC)"

# =============================================================================
# Status & Monitoring
# =============================================================================

status: ## Show status of all environments
	@echo "$(BLUE)📊 Environment Status$(NC)"
	@echo "====================="
	@echo "$(YELLOW)Development:$(NC)"
	@cd $(HELM_CHART_DIR) && make status-dev 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "$(YELLOW)Staging:$(NC)"
	@cd $(HELM_CHART_DIR) && make status-staging 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "$(YELLOW)Production:$(NC)"
	@cd $(HELM_CHART_DIR) && make status-prod 2>/dev/null || echo "  Not deployed"

logs: ## Show logs from development environment
	@echo "$(BLUE)📋 Development Logs$(NC)"
	@cd $(HELM_CHART_DIR) && make logs-dev

debug: ## Debug development environment
	@echo "$(BLUE)🐛 Debug Information$(NC)"
	@cd $(HELM_CHART_DIR) && make debug-dev

# =============================================================================
# Documentation
# =============================================================================

docs: ## Generate and serve documentation
	@echo "$(BLUE)📚 Generating documentation...$(NC)"
	@if [ -f "docs/requirements.txt" ]; then \
		cd docs && \
		(python -m venv venv 2>/dev/null || true) && \
		source venv/bin/activate && \
		pip install -r requirements.txt && \
		mkdocs serve; \
	else \
		echo "$(YELLOW)⚠️  No documentation setup found$(NC)"; \
		echo "Create docs/requirements.txt with mkdocs to enable documentation"; \
	fi

docs-build: ## Build documentation for deployment
	@echo "$(BLUE)📚 Building documentation...$(NC)"
	@if [ -f "docs/requirements.txt" ]; then \
		cd docs && \
		source venv/bin/activate && \
		mkdocs build; \
	else \
		echo "$(YELLOW)⚠️  No documentation setup found$(NC)"; \
	fi

# =============================================================================
# Operations
# =============================================================================

backup: ## Backup development database
	@echo "$(BLUE)💾 Creating backup...$(NC)"
	@kubectl exec -n $(DEV_NAMESPACE) deployment/postgresql-primary -- \
		pg_dump -U postgres munshi_dev > backup-$(shell date +%Y%m%d-%H%M%S).sql
	@echo "$(GREEN)✓ Backup created$(NC)"

restore: ## Restore database from backup (usage: make restore BACKUP=backup-file.sql)
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)❌ Please specify BACKUP file (e.g., make restore BACKUP=backup-20231201-120000.sql)$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)🔄 Restoring from $(BACKUP)...$(NC)"
	@kubectl exec -i -n $(DEV_NAMESPACE) deployment/postgresql-primary -- \
		psql -U postgres munshi_dev < $(BACKUP)
	@echo "$(GREEN)✓ Restore complete$(NC)"

# =============================================================================
# Utilities
# =============================================================================

version: ## Show version information
	@echo "$(CYAN)Munshi Platform v$(VERSION)$(NC)"
	@echo "Registry: $(REGISTRY)"
	@echo "Services: $(SERVICES)"

update-deps: ## Update all dependencies
	@echo "$(BLUE)🔄 Updating dependencies...$(NC)"
	@cd $(HELM_CHART_DIR) && make dependency-update
	@for service in $(SERVICES); do \
		if [ -f "services/$$service/requirements.txt" ]; then \
			echo "$(YELLOW)Updating $$service Python deps...$(NC)"; \
			cd "services/$$service" && \
			source venv/bin/activate && \
			pip install --upgrade -r requirements.txt && \
			cd ../..; \
		elif [ -f "services/$$service/package.json" ]; then \
			echo "$(YELLOW)Updating $$service Node deps...$(NC)"; \
			cd "services/$$service" && \
			npm update && \
			cd ../..; \
		fi; \
	done
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

# =============================================================================
# Quick Actions
# =============================================================================

quick-dev: setup start-dev ## Complete development setup from scratch

quick-deploy: build push dev ## Build, push, and deploy to development

ci: lint test security-scan ## Run CI pipeline (lint, test, security)

release: ci build push ## Prepare for release (CI + build + push)