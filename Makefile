# Makefile for Munshi microservices project
# Provides common development tasks and deployment shortcuts

.PHONY: help install dev build test lint format clean deploy status logs docs

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON_VERSION := 3.11
POETRY := poetry
DOCKER_COMPOSE := docker-compose
KUBECTL := kubectl
LINKERD := linkerd

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
RED := \033[31m
YELLOW := \033[33m
NC := \033[0m

help: ## Show this help message
	@echo "$(BLUE)Munshi Microservices$(NC)"
	@echo "Available commands:"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install project dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(POETRY) install --with dev,test
	@echo "$(GREEN)Dependencies installed successfully$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(POETRY) install --with dev,test
	pre-commit install
	@echo "$(GREEN)Development environment ready$(NC)"

dev: ## Start development environment with Docker Compose
	@echo "$(BLUE)Starting development environment...$(NC)"
	cd infrastructure/docker && $(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "$(GREEN)Development environment started$(NC)"
	@echo "Services available at:"
	@echo "  - Auth Service: http://localhost:8001"
	@echo "  - API Gateway: http://localhost:8000"
	@echo "  - Adminer: http://localhost:8080"
	@echo "  - Redis Commander: http://localhost:8081"

dev-linkerd: ## Start development environment with Linkerd
	@echo "$(BLUE)Starting development environment with Linkerd...$(NC)"
	cd infrastructure/docker && $(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.linkerd.yml up -d
	@echo "$(GREEN)Development environment with Linkerd started$(NC)"

build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	cd infrastructure/docker && $(DOCKER_COMPOSE) build
	@echo "$(GREEN)Docker images built successfully$(NC)"

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

test-performance: ## Run performance tests
	@echo "$(BLUE)Running performance tests...$(NC)"
	$(POETRY) run pytest tests/ -m "performance" -v
	@echo "$(GREEN)Performance tests completed$(NC)"

test-security: ## Run security tests
	@echo "$(BLUE)Running security tests...$(NC)"
	$(POETRY) run pytest tests/ -m "security" -v
	@echo "$(GREEN)Security tests completed$(NC)"

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

clean: ## Clean up containers and volumes
	@echo "$(BLUE)Cleaning up...$(NC)"
	cd infrastructure/docker && $(DOCKER_COMPOSE) down -v
	docker system prune -f
	@echo "$(GREEN)Cleanup completed$(NC)"

deploy-dev: ## Deploy to development environment
	@echo "$(BLUE)Deploying to development...$(NC)"
	./infrastructure/scripts/deploy.sh docker development
	@echo "$(GREEN)Development deployment completed$(NC)"

deploy-staging: ## Deploy to staging environment
	@echo "$(BLUE)Deploying to staging...$(NC)"
	./infrastructure/scripts/deploy.sh k8s staging
	@echo "$(GREEN)Staging deployment completed$(NC)"

deploy-prod: ## Deploy to production environment
	@echo "$(YELLOW)WARNING: Deploying to production$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./infrastructure/scripts/deploy.sh k8s production --linkerd; \
		echo "$(GREEN)Production deployment completed$(NC)"; \
	else \
		echo "$(RED)Production deployment cancelled$(NC)"; \
	fi

status: ## Show service status
	@echo "$(BLUE)Service status:$(NC)"
	@if command -v docker &> /dev/null; then \
		echo "$(BLUE)Docker services:$(NC)"; \
		cd infrastructure/docker && $(DOCKER_COMPOSE) ps; \
	fi
	@if command -v kubectl &> /dev/null && kubectl cluster-info &> /dev/null; then \
		echo "$(BLUE)Kubernetes services:$(NC)"; \
		$(KUBECTL) get all -n munshi-dev 2>/dev/null || echo "No development namespace found"; \
		$(KUBECTL) get all -n munshi-staging 2>/dev/null || echo "No staging namespace found"; \
		$(KUBECTL) get all -n munshi-prod 2>/dev/null || echo "No production namespace found"; \
	fi

logs: ## Show service logs
	@echo "$(BLUE)Service logs:$(NC)"
	cd infrastructure/docker && $(DOCKER_COMPOSE) logs -f --tail=100

logs-auth: ## Show auth service logs
	@echo "$(BLUE)Auth service logs:$(NC)"
	cd infrastructure/docker && $(DOCKER_COMPOSE) logs -f --tail=100 auth-service

logs-gateway: ## Show gateway logs
	@echo "$(BLUE)Gateway logs:$(NC)"
	cd infrastructure/docker && $(DOCKER_COMPOSE) logs -f --tail=100 api-gateway

metrics: ## Open metrics dashboards
	@echo "$(BLUE)Opening metrics dashboards...$(NC)"
	@if command -v open &> /dev/null; then \
		open http://localhost:9090 & \
		open http://localhost:3000 & \
		open http://localhost:16686 & \
	else \
		echo "Metrics available at:"; \
		echo "  - Prometheus: http://localhost:9090"; \
		echo "  - Grafana: http://localhost:3000"; \
		echo "  - Jaeger: http://localhost:16686"; \
	fi

linkerd-check: ## Check Linkerd installation
	@echo "$(BLUE)Checking Linkerd...$(NC)"
	@if command -v linkerd &> /dev/null; then \
		$(LINKERD) check; \
		$(LINKERD) viz check; \
	else \
		echo "$(RED)Linkerd CLI not installed$(NC)"; \
	fi

linkerd-dashboard: ## Open Linkerd dashboard
	@echo "$(BLUE)Opening Linkerd dashboard...$(NC)"
	$(LINKERD) viz dashboard &

docs: ## Generate and serve documentation
	@echo "$(BLUE)Serving documentation...$(NC)"
	@if command -v mkdocs &> /dev/null; then \
		mkdocs serve; \
	else \
		echo "$(YELLOW)mkdocs not installed. Install with: pip install mkdocs$(NC)"; \
		echo "Documentation available in docs/ directory"; \
	fi

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	# Add migration commands here when implemented
	@echo "$(GREEN)Migrations completed$(NC)"

seed: ## Seed databases with test data
	@echo "$(BLUE)Seeding databases...$(NC)"
	# Add seeding commands here when implemented
	@echo "$(GREEN)Database seeding completed$(NC)"

backup: ## Backup databases
	@echo "$(BLUE)Creating database backups...$(NC)"
	# Add backup commands here when implemented
	@echo "$(GREEN)Backup completed$(NC)"

health: ## Check service health
	@echo "$(BLUE)Checking service health...$(NC)"
	@curl -s http://localhost:8001/health 2>/dev/null && echo "$(GREEN)Auth service: healthy$(NC)" || echo "$(RED)Auth service: unhealthy$(NC)"
	@curl -s http://localhost:8000/health 2>/dev/null && echo "$(GREEN)Gateway: healthy$(NC)" || echo "$(RED)Gateway: unhealthy$(NC)"

benchmark: ## Run performance benchmarks
	@echo "$(BLUE)Running performance benchmarks...$(NC)"
	$(POETRY) run pytest tests/performance/ -v --benchmark-only
	@echo "$(GREEN)Benchmarks completed$(NC)"

load-test: ## Run load tests
	@echo "$(BLUE)Running load tests...$(NC)"
	# Add load testing commands here (e.g., locust)
	@echo "$(GREEN)Load tests completed$(NC)"

init: ## Initialize project for first-time setup
	@echo "$(BLUE)Initializing project...$(NC)"
	@make install-dev
	@make build
	@echo "$(GREEN)Project initialized successfully$(NC)"
	@echo "Run 'make dev' to start development environment"

version: ## Show version information
	@echo "$(BLUE)Version information:$(NC)"
	@echo "Python: $$(python --version 2>&1)"
	@echo "Poetry: $$(poetry --version 2>&1)"
	@echo "Docker: $$(docker --version 2>&1)"
	@echo "Docker Compose: $$(docker-compose --version 2>&1)"
	@if command -v kubectl &> /dev/null; then echo "kubectl: $$(kubectl version --client --short 2>&1)"; fi
	@if command -v linkerd &> /dev/null; then echo "Linkerd: $$(linkerd version --client --short 2>&1)"; fi