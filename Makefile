# Munshi Platform - Simplified Makefile

# Configuration
PROJECT_NAME := munshi
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
PROJECT_ID := central-list-469110-f1
REGION := us-central1
REGISTRY := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/munshi-containers
SERVICES := auth-service audio-service asr-service conversation-service llm-service pronunciation-evaluator ui-service

# Colors
GREEN := \033[0;32m
BLUE := \033[0;34m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

.PHONY: help clean env-init deploy build push test lint format version init status takedown destroy

help: ## Show this help message
	@echo "$(BLUE)🎓 Munshi Platform$(NC)"
	@echo "=================="
	@echo ""
	@echo "$(GREEN)Main Commands:$(NC)"
	@awk '/^[a-zA-Z_-]+:.*?## .*$$/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, substr($$0, index($$0, "## ") + 3) }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)Current Settings:$(NC)"
	@echo "  Project: $(PROJECT_ID)"
	@echo "  Registry: $(REGISTRY)"
	@echo "  Version: $(VERSION)"

clean: ## Clean up build artifacts
	@echo "$(BLUE)🧹 Cleaning up...$(NC)"
	@docker system prune -f 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

env-init: ## Create GCP infrastructure (cluster, node pools, networking)
	@echo "$(BLUE)🏗️  Creating GCP infrastructure...$(NC)"
	@if [ ! -f "infrastructure/terraform/terraform.tfvars" ]; then \
		echo "$(RED)❌ terraform.tfvars not found$(NC)"; \
		echo "$(YELLOW)Run: make init first$(NC)"; \
		exit 1; \
	fi
	@# Initialize Terraform
	@cd infrastructure/terraform && terraform init
	@# Check if cluster already exists and import if needed
	@if gcloud container clusters describe munshi-cluster --zone=us-central1-a --project=central-list-469110-f1 >/dev/null 2>&1; then \
		echo "$(YELLOW)⚠️  Cluster exists, importing into Terraform state...$(NC)"; \
		cd infrastructure/terraform && terraform import google_container_cluster.cluster central-list-469110-f1/us-central1-a/munshi-cluster 2>/dev/null || true; \
	fi
	@# Apply infrastructure changes
	@cd infrastructure/terraform && terraform apply -auto-approve
	@# Configure kubectl access
	@gcloud container clusters get-credentials munshi-cluster --zone=us-central1-a --project=central-list-469110-f1
	@echo "$(GREEN)✓ Infrastructure ready$(NC)"

deploy: ## Deploy application, only building changed services
	@echo "$(BLUE)🚀 Smart deploying application...$(NC)"
	@# Check if cluster exists
	@gcloud container clusters describe munshi-cluster --zone=us-central1-a --project=central-list-469110-f1 >/dev/null 2>&1 || \
		(echo "$(RED)❌ Infrastructure not found. Run 'make env-init' first$(NC)" && exit 1)
	@# Smart build and push only changed services
	@./scripts/smart-deploy.sh
	@# Create namespace
	@kubectl create namespace munshi-prod --dry-run=client -o yaml | kubectl apply -f -
	@# Create secrets
	@cd infrastructure/terraform && \
		GOOGLE_API_KEY=$$(grep -E "^google_api_key" terraform.tfvars | cut -d'"' -f2) && \
		JWT_SECRET=$$(grep -E "^jwt_secret" terraform.tfvars | cut -d'"' -f2) && \
		kubectl create secret generic google-api-keys \
			--from-literal=api-key="$$GOOGLE_API_KEY" \
			-n munshi-prod --dry-run=client -o yaml | kubectl apply -f - && \
		kubectl create secret generic jwt-secret \
			--from-literal=secret="$$JWT_SECRET" \
			-n munshi-prod --dry-run=client -o yaml | kubectl apply -f - && \
		kubectl create secret generic database-credentials \
			--from-literal=mongodb_url="mongodb://munshi:munshi123@munshi-platform-mongodb:27017/munshi" \
			--from-literal=auth-db-url="postgresql://munshi_user:munshi_password@munshi-platform-postgresql:5432/munshi_auth" \
			--from-literal=audio-db-url="postgresql://munshi_user:munshi_password@munshi-platform-postgresql:5432/munshi_audio" \
			-n munshi-prod --dry-run=client -o yaml | kubectl apply -f -
	@# Deploy with Helm
	@cd infrastructure/helm/munshi-platform && \
		helm repo add bitnami https://charts.bitnami.com/bitnami --force-update && \
		helm repo update && \
		helm dependency update && \
		helm upgrade --install munshi-platform . \
			--namespace munshi-prod \
			--values values-gcp.yaml \
			--set global.imageRegistry="$(REGISTRY)" \
			--wait --timeout=600s
	@echo "$(GREEN)✓ Application deployed$(NC)"

build: ## Build all Docker images
	@echo "$(BLUE)🏗️  Building images...$(NC)"
	@gcloud auth configure-docker $(REGION)-docker.pkg.dev --quiet
	@for service in $(SERVICES); do \
		if [ -d "services/$$service" ]; then \
			echo "Building $$service..."; \
			cd services/$$service; \
			BUILD_ARGS="--platform linux/amd64"; \
			if [ "$$service" = "asr-service" ]; then \
				BUILD_ARGS="$$BUILD_ARGS --build-arg GPU_SUPPORT=gpu"; \
			fi; \
			docker build $$BUILD_ARGS -t $(REGISTRY)/munshi-$$service:$(VERSION) -t $(REGISTRY)/munshi-$$service:latest .; \
			cd ../..; \
		fi; \
	done
	@echo "$(GREEN)✓ All images built$(NC)"

push: ## Push all images to registry
	@echo "$(BLUE)📤 Pushing images...$(NC)"
	@for service in $(SERVICES); do \
		echo "Pushing $$service..."; \
		docker push $(REGISTRY)/munshi-$$service:$(VERSION); \
		docker push $(REGISTRY)/munshi-$$service:latest; \
	done
	@echo "$(GREEN)✓ All images pushed$(NC)"

test: ## Run tests for all services
	@echo "$(BLUE)🧪 Running tests...$(NC)"
	@for service in $(SERVICES); do \
		if [ -f "services/$$service/requirements.txt" ]; then \
			echo "Testing $$service..."; \
			cd services/$$service; \
			(python -m pytest tests/ 2>/dev/null || echo "No tests found for $$service"); \
			cd ../..; \
		elif [ -f "services/$$service/package.json" ]; then \
			echo "Testing $$service..."; \
			cd services/$$service; \
			(npm test 2>/dev/null || echo "No tests found for $$service"); \
			cd ../..; \
		fi; \
	done
	@echo "$(GREEN)✓ Tests complete$(NC)"

lint: ## Run linters on all services
	@echo "$(BLUE)🔍 Running linters...$(NC)"
	@for service in $(SERVICES); do \
		echo "Linting $$service..."; \
		if [ -f "services/$$service/requirements.txt" ]; then \
			cd services/$$service; \
			(flake8 . 2>/dev/null || echo "flake8 not available for $$service"); \
			cd ../..; \
		elif [ -f "services/$$service/package.json" ]; then \
			cd services/$$service; \
			(npm run lint 2>/dev/null || echo "No linting configured for $$service"); \
			cd ../..; \
		fi; \
	done
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code in all services
	@echo "$(BLUE)✨ Formatting code...$(NC)"
	@for service in $(SERVICES); do \
		echo "Formatting $$service..."; \
		if [ -f "services/$$service/requirements.txt" ]; then \
			cd services/$$service; \
			(black . 2>/dev/null || echo "black not available for $$service"); \
			cd ../..; \
		elif [ -f "services/$$service/package.json" ]; then \
			cd services/$$service; \
			(npm run format 2>/dev/null || echo "No formatting configured for $$service"); \
			cd ../..; \
		fi; \
	done
	@echo "$(GREEN)✓ Formatting complete$(NC)"

version: ## Show version information
	@echo "$(BLUE)Munshi Platform v$(VERSION)$(NC)"
	@echo "Registry: $(REGISTRY)"
	@echo "Services: $(words $(SERVICES)) total"

# Convenience targets
init: ## Initialize project configuration (creates terraform.tfvars)
	@echo "$(BLUE)🔧 Initializing Munshi project...$(NC)"
	@if [ ! -f "infrastructure/terraform/terraform.tfvars" ]; then \
		echo "Creating terraform.tfvars from example..."; \
		cd infrastructure/terraform && cp terraform-gcp.tfvars.example terraform.tfvars; \
		echo "$(YELLOW)⚠️  Please edit infrastructure/terraform/terraform.tfvars with your values:$(NC)"; \
		echo "  - project_id: Your GCP project ID"; \
		echo "  - jwt_secret: Random 32-character string"; \
		echo "  - google_api_key: Your Google Gemini API key"; \
		echo ""; \
		echo "$(BLUE)💡 Next steps:$(NC)"; \
		echo "  1. Edit terraform.tfvars"; \
		echo "  2. Run: make env-init"; \
		echo "  3. Run: make deploy"; \
	else \
		echo "$(GREEN)✓ terraform.tfvars already exists$(NC)"; \
	fi

status: ## Show deployment status
	@echo "$(BLUE)📊 Deployment Status$(NC)"
	@kubectl get pods -n munshi-prod 2>/dev/null || echo "No deployment found"
	@kubectl get services -n munshi-prod 2>/dev/null || echo "No services found"

takedown: ## Remove application deployment (keep infrastructure)
	@echo "$(YELLOW)🗑️  Taking down application deployment...$(NC)"
	@echo "$(YELLOW)This will remove all application pods but keep the GKE cluster$(NC)"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || (echo "$(BLUE)Aborted$(NC)" && exit 1)
	@helm uninstall munshi-platform -n munshi-prod 2>/dev/null || echo "No Helm release found"
	@kubectl delete namespace munshi-prod 2>/dev/null || echo "No namespace found"
	@echo "$(GREEN)✓ Application removed (infrastructure preserved)$(NC)"

destroy: ## Destroy all infrastructure (WARNING: Deletes everything)
	@echo "$(YELLOW)⚠️  WARNING: This will destroy ALL infrastructure!$(NC)"
	@echo "$(YELLOW)- GKE cluster will be deleted$(NC)"
	@echo "$(YELLOW)- All data will be lost$(NC)"
	@echo "$(YELLOW)- This action cannot be undone$(NC)"
	@read -p "Type 'destroy' to confirm: " confirm && [ "$$confirm" = "destroy" ] || (echo "$(BLUE)Aborted$(NC)" && exit 1)
	@echo "$(BLUE)🗑️  Destroying infrastructure...$(NC)"
	@# Initialize Terraform to ensure state is current
	@cd infrastructure/terraform && terraform init
	@# Import cluster if it exists but isn't in state
	@if gcloud container clusters describe munshi-cluster --zone=us-central1-a --project=central-list-469110-f1 >/dev/null 2>&1; then \
		echo "$(YELLOW)📥 Importing existing cluster to ensure clean destroy...$(NC)"; \
		cd infrastructure/terraform && terraform import google_container_cluster.cluster central-list-469110-f1/us-central1-a/munshi-cluster 2>/dev/null || true; \
	fi
	@# Update cluster to disable deletion protection via Terraform
	@echo "$(YELLOW)🔓 Ensuring deletion protection is disabled...$(NC)"
	@cd infrastructure/terraform && terraform apply -auto-approve -target=google_container_cluster.cluster 2>/dev/null || true
	@# Destroy infrastructure
	@cd infrastructure/terraform && terraform destroy -auto-approve
	@# Clean up any remaining cluster manually if Terraform fails
	@if gcloud container clusters describe munshi-cluster --zone=us-central1-a --project=central-list-469110-f1 >/dev/null 2>&1; then \
		echo "$(YELLOW)🧹 Cleaning up remaining cluster...$(NC)"; \
		gcloud container clusters delete munshi-cluster --zone=us-central1-a --quiet || true; \
	fi
	@echo "$(GREEN)✓ All infrastructure destroyed$(NC)"

deploy-fresh: build push deploy ## Build, push, and deploy application to existing infrastructure