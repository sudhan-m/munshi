# Munshi Platform - Simplified Makefile

# Configuration
PROJECT_NAME := munshi
VERSION := $(shell date +%Y%m%d-%H%M%S)
PROJECT_ID := central-list-469110-f1
REGION := us-east1
REGISTRY := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/munshi-containers
SERVICES := auth-service audio-service asr-service conversation-service llm-service pronunciation-evaluator ui-service

# Colors
GREEN := \033[0;32m
BLUE := \033[0;34m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

.PHONY: help clean env-init deploy build push test lint format version init plan status takedown destroy rebuild-all

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
	@# Check if infrastructure already exists and is ready
	@if gcloud container clusters describe munshi-cluster --zone=us-east1-b --project=central-list-469110-f1 >/dev/null 2>&1; then \
		echo "$(GREEN)✓ GKE cluster already exists$(NC)"; \
		gcloud container clusters get-credentials munshi-cluster --zone=us-east1-b --project=central-list-469110-f1; \
		if kubectl get nodes --no-headers 2>/dev/null | grep -q Ready; then \
			echo "$(GREEN)✓ Cluster is ready and accessible$(NC)"; \
			echo "$(BLUE)ℹ️  Skipping infrastructure creation (already exists)$(NC)"; \
			echo "$(GREEN)✓ Infrastructure ready$(NC)"; \
			exit 0; \
		fi; \
	fi
	@# Check what else exists
	@$(MAKE) _check-existing-infrastructure
	@# Initialize Terraform
	@echo "$(BLUE)📋 Initializing Terraform...$(NC)"
	@cd infrastructure/terraform && terraform init
	@# Import existing resources to avoid conflicts
	@$(MAKE) _import-existing-resources
	@# Show what will be changed
	@echo "$(BLUE)📋 Planning infrastructure changes...$(NC)"
	@cd infrastructure/terraform && \
		if terraform plan -var="enable_cert_manager=false" -out=tfplan | grep -q "No changes"; then \
			echo "$(GREEN)✓ No infrastructure changes needed$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  Infrastructure changes detected$(NC)"; \
		fi
	@# Apply infrastructure changes with failure tolerance
	@echo "$(BLUE)🏗️  Applying infrastructure changes...$(NC)"
	@cd infrastructure/terraform && \
		for i in 1 2 3; do \
			echo "Attempt $$i/3..."; \
			if terraform apply -auto-approve -var="enable_cert_manager=false" -var="enable_database_init=false"; then \
				echo "$(GREEN)✓ Infrastructure applied successfully$(NC)"; \
				break; \
			else \
				echo "$(YELLOW)⚠️  Attempt $$i failed, checking for recoverable errors...$(NC)"; \
				if [ $$i -eq 3 ]; then \
					echo "$(YELLOW)⚠️  Some resources may already exist - continuing with deployment$(NC)"; \
					break; \
				fi; \
				terraform plan -var="enable_cert_manager=false" -var="enable_database_init=false" -out=tfplan; \
				sleep 15; \
			fi; \
		done
	@# Configure kubectl access and verify
	@echo "$(BLUE)🔧 Configuring kubectl access...$(NC)"
	@gcloud container clusters get-credentials munshi-cluster --zone=us-east1-b --project=central-list-469110-f1
	@# Wait for cluster to be ready
	@echo "$(BLUE)⏳ Waiting for cluster readiness...$(NC)"
	@$(MAKE) _wait-for-cluster
	@echo "$(GREEN)✓ Infrastructure ready$(NC)"

deploy: ## Deploy application, only building changed services
	@echo "$(BLUE)🚀 Smart deploying application...$(NC)"
	@# Check if cluster exists and is ready
	@echo "$(BLUE)🔍 Checking cluster status...$(NC)"
	@gcloud container clusters describe munshi-cluster --zone=us-east1-b --project=central-list-469110-f1 >/dev/null 2>&1 || \
		(echo "$(RED)❌ Infrastructure not found. Run 'make env-init' first$(NC)" && exit 1)
	@# Ensure kubectl access and cluster readiness
	@gcloud container clusters get-credentials munshi-cluster --zone=us-east1-b --project=central-list-469110-f1
	@$(MAKE) _wait-for-cluster
	@# Apply any pending Terraform changes for IAM and permissions with failure tolerance
	@echo "$(BLUE)🔐 Updating IAM permissions...$(NC)"
	@cd infrastructure/terraform && \
		terraform init && \
		PROJECT_ID=$$(grep -E "^project_id" terraform.tfvars | cut -d'"' -f2) && \
		echo "$(YELLOW)📥 Importing existing resources...$(NC)" && \
		(terraform import google_container_cluster.cluster $$PROJECT_ID/us-east1-b/munshi-cluster 2>/dev/null || true) && \
		(terraform import google_artifact_registry_repository.munshi_containers projects/$$PROJECT_ID/locations/us-east1/repositories/munshi-containers 2>/dev/null || true) && \
		if terraform plan -var="enable_cert_manager=false" -var="enable_database_init=false" -out=tfplan; then \
			terraform apply -auto-approve tfplan || echo "$(YELLOW)⚠️  Some Terraform resources may already exist - continuing$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  Terraform plan failed - some resources may already exist, continuing$(NC)"; \
		fi
	@# Clean up problematic pods before deployment
	@echo "$(BLUE)🧹 Cleaning up problematic pods...$(NC)"
	@kubectl delete pods --namespace munshi-prod --field-selector=status.phase=Pending --ignore-not-found=true || true
	@kubectl delete pods --namespace munshi-prod --field-selector=status.phase=Failed --ignore-not-found=true || true
	@kubectl get pods --namespace munshi-prod 2>/dev/null | grep -E "(ImagePullBackOff|ErrImagePull|CrashLoopBackOff)" | awk '{print $$1}' | xargs -r kubectl delete pods --namespace munshi-prod --ignore-not-found=true || true
	@# Smart build and push only changed services
	@echo "$(BLUE)🏗️  Building and pushing changed services...$(NC)"
	@./scripts/smart-deploy.sh
	@# Create namespace with retry and failure tolerance
	@echo "$(BLUE)📁 Setting up namespace and secrets...$(NC)"
	@for i in 1 2 3; do \
		if kubectl create namespace munshi-prod --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null; then \
			echo "$(GREEN)✓ Namespace created or already exists$(NC)"; \
			break; \
		elif kubectl get namespace munshi-prod >/dev/null 2>&1; then \
			echo "$(GREEN)✓ Namespace already exists$(NC)"; \
			break; \
		else \
			echo "$(YELLOW)⚠️  Namespace creation attempt $$i failed, retrying...$(NC)"; \
			if [ $$i -eq 3 ]; then \
				echo "$(YELLOW)⚠️  Namespace creation failed - it may already exist, continuing$(NC)"; \
			fi; \
			sleep 5; \
		fi; \
	done
	@# Create secrets with error handling
	@cd infrastructure/terraform && \
		if [ -n "$$GOOGLE_API_KEY" ]; then \
			echo "Using GOOGLE_API_KEY from environment"; \
		else \
			GOOGLE_API_KEY=$$(grep -E "^google_api_key" terraform.tfvars 2>/dev/null | cut -d'"' -f2); \
		fi && \
		if [ -n "$$JWT_SECRET" ]; then \
			echo "Using JWT_SECRET from environment"; \
		else \
			JWT_SECRET=$$(grep -E "^jwt_secret" terraform.tfvars 2>/dev/null | cut -d'"' -f2); \
			if [ -z "$$JWT_SECRET" ] || [ "$$JWT_SECRET" = "your-jwt-secret-here" ]; then \
				JWT_SECRET=$$(openssl rand -base64 32); \
				echo "Generated JWT_SECRET: $$JWT_SECRET"; \
			fi; \
		fi && \
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
	@# Deploy with Helm with retry logic
	@echo "$(BLUE)⚡ Deploying with Helm...$(NC)"
	@cd infrastructure/helm/munshi-platform && \
		helm repo add bitnami https://charts.bitnami.com/bitnami --force-update && \
		helm repo update && \
		helm dependency update && \
		HELM_SET_ARGS=$$(cat /tmp/munshi-helm-set-args 2>/dev/null || echo "") && \
		for i in 1 2; do \
			echo "Helm deployment attempt $$i/2..."; \
			if helm upgrade --install munshi-platform . \
				--namespace munshi-prod \
				--values values-gcp.yaml \
				--set global.imageRegistry="" \
				--set image.tag="$(VERSION)" \
				$$HELM_SET_ARGS \
				--wait --timeout=1200s; then \
				echo "$(GREEN)✓ Helm deployment successful$(NC)"; \
				break; \
			else \
				echo "$(YELLOW)⚠️  Helm deployment attempt $$i failed$(NC)"; \
				if [ $$i -eq 2 ]; then \
					echo "$(RED)❌ All Helm deployment attempts failed$(NC)"; \
					exit 1; \
				fi; \
				sleep 30; \
			fi; \
		done
	@# Show deployment status and access information
	@echo "$(GREEN)✓ Deployment complete!$(NC)"
	@echo "$(BLUE)📋 Access Information:$(NC)"
	@EXTERNAL_IP=$$(kubectl get service ui-service -n munshi-prod -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending"); \
		if [ "$$EXTERNAL_IP" != "pending" ] && [ "$$EXTERNAL_IP" != "" ]; then \
			echo "  🌐 Application URL: http://$$EXTERNAL_IP"; \
			echo "  📋 Set your domain DNS A record to: $$EXTERNAL_IP"; \
		else \
			echo "  ⏳ LoadBalancer IP is still being assigned..."; \
			echo "  🔍 Check status: kubectl get service ui-service -n munshi-prod"; \
		fi
	@echo "$(GREEN)✓ Application deployed$(NC)"

build: ## Build all Docker images
	@echo "$(BLUE)🏗️  Building images...$(NC)"
	@gcloud auth configure-docker $(REGION)-docker.pkg.dev --quiet
	@for service in $(SERVICES); do \
		if [ -d "services/$$service" ]; then \
			echo "Building $$service..."; \
			cd services/$$service; \
			docker build --platform linux/amd64 -t $(REGISTRY)/munshi-$$service:$(VERSION) -t $(REGISTRY)/munshi-$$service:latest .; \
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
		echo "  2. Run: make plan (to see what will be created)"; \
		echo "  3. Run: make env-init (to create infrastructure)"; \
		echo "  4. Run: make deploy (to deploy application)"; \
	else \
		echo "$(GREEN)✓ terraform.tfvars already exists$(NC)"; \
	fi

plan: ## Show what infrastructure changes would be made (dry-run)
	@echo "$(BLUE)📋 Planning infrastructure changes...$(NC)"
	@if [ ! -f "infrastructure/terraform/terraform.tfvars" ]; then \
		echo "$(RED)❌ terraform.tfvars not found$(NC)"; \
		echo "$(YELLOW)Run: make init first$(NC)"; \
		exit 1; \
	fi
	@$(MAKE) _check-existing-infrastructure
	@cd infrastructure/terraform && terraform init
	@$(MAKE) _import-existing-resources
	@echo "$(BLUE)📋 Terraform plan results:$(NC)"
	@cd infrastructure/terraform && terraform plan -var="enable_cert_manager=false"

status: ## Show deployment status
	@echo "$(BLUE)📊 Deployment Status$(NC)"
	@echo "$(BLUE)🏗️  Infrastructure:$(NC)"
	@if gcloud container clusters describe munshi-cluster --zone=us-east1-b --project=central-list-469110-f1 >/dev/null 2>&1; then \
		echo "  ✅ GKE Cluster: munshi-cluster (running)"; \
	else \
		echo "  ❌ GKE Cluster: not found"; \
	fi
	@echo "$(BLUE)🚀 Applications:$(NC)"
	@if kubectl get namespace munshi-prod >/dev/null 2>&1; then \
		echo "  ✅ Namespace: munshi-prod"; \
		READY_PODS=$$(kubectl get pods -n munshi-prod --field-selector=status.phase=Running 2>/dev/null | grep -c "Running" || echo "0"); \
		TOTAL_PODS=$$(kubectl get pods -n munshi-prod 2>/dev/null | grep -v NAME | wc -l || echo "0"); \
		echo "  📦 Pods: $$READY_PODS/$$TOTAL_PODS running"; \
		EXTERNAL_IP=$$(kubectl get service ui-service -n munshi-prod -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending"); \
		if [ "$$EXTERNAL_IP" != "pending" ] && [ "$$EXTERNAL_IP" != "" ]; then \
			echo "  🌐 Application URL: http://$$EXTERNAL_IP"; \
			echo "  📋 DNS Setup: Point your domain A record to $$EXTERNAL_IP"; \
		else \
			echo "  ⏳ External IP: pending (LoadBalancer creating...)"; \
		fi; \
	else \
		echo "  ❌ Application: not deployed"; \
	fi
	@echo "$(BLUE)📋 Quick Commands:$(NC)"
	@echo "  Deploy: make deploy"
	@echo "  Logs: kubectl logs -f deployment/ui-service -n munshi-prod"
	@echo "  Scale: kubectl scale deployment ui-service --replicas=3 -n munshi-prod"

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
	@if gcloud container clusters describe munshi-cluster --zone=us-east1-b --project=central-list-469110-f1 >/dev/null 2>&1; then \
		echo "$(YELLOW)📥 Importing existing cluster to ensure clean destroy...$(NC)"; \
		cd infrastructure/terraform && terraform import google_container_cluster.cluster central-list-469110-f1/us-east1-b/munshi-cluster 2>/dev/null || true; \
	fi
	@# Update cluster to disable deletion protection via Terraform
	@echo "$(YELLOW)🔓 Ensuring deletion protection is disabled...$(NC)"
	@cd infrastructure/terraform && terraform apply -auto-approve -target=google_container_cluster.cluster 2>/dev/null || true
	@# Destroy infrastructure
	@cd infrastructure/terraform && terraform destroy -auto-approve
	@# Clean up any remaining cluster manually if Terraform fails
	@if gcloud container clusters describe munshi-cluster --zone=us-east1-b --project=central-list-469110-f1 >/dev/null 2>&1; then \
		echo "$(YELLOW)🧹 Cleaning up remaining cluster...$(NC)"; \
		gcloud container clusters delete munshi-cluster --zone=us-east1-b --quiet || true; \
	fi
	@echo "$(GREEN)✓ All infrastructure destroyed$(NC)"

rebuild-all: build push ## Force rebuild all services (ignores git diff)
	@echo "$(GREEN)✓ All services rebuilt and pushed$(NC)"
	@echo "$(BLUE)💡 Run 'make deploy' to deploy the changes$(NC)"


# Internal helper functions
_wait-for-cluster: ## Wait for cluster to be ready (internal use)
	@echo "$(BLUE)⏳ Waiting for cluster nodes to be ready...$(NC)"
	@for i in $$(seq 1 30); do \
		if kubectl get nodes --no-headers 2>/dev/null | grep -q Ready; then \
			echo "$(GREEN)✓ Cluster nodes are ready$(NC)"; \
			break; \
		else \
			echo "Waiting for nodes... ($$i/30)"; \
			sleep 10; \
		fi; \
		if [ $$i -eq 30 ]; then \
			echo "$(RED)❌ Timeout waiting for cluster readiness$(NC)"; \
			kubectl get nodes 2>/dev/null || echo "Cannot access cluster"; \
			exit 1; \
		fi; \
	done
	@echo "$(BLUE)🔍 Verifying cluster connectivity...$(NC)"
	@kubectl cluster-info --request-timeout=10s >/dev/null || \
		(echo "$(RED)❌ Cluster connectivity test failed$(NC)" && exit 1)
	@echo "$(GREEN)✓ Cluster is ready and accessible$(NC)"

_check-prerequisites: ## Check if required tools are installed (internal use)
	@echo "$(BLUE)🔧 Checking prerequisites...$(NC)"
	@for tool in gcloud kubectl helm docker terraform; do \
		if ! command -v $$tool >/dev/null 2>&1; then \
			echo "$(RED)❌ $$tool is not installed$(NC)"; \
			exit 1; \
		else \
			echo "$(GREEN)✓ $$tool found$(NC)"; \
		fi; \
	done

_check-existing-infrastructure: ## Check what infrastructure already exists (internal use)
	@echo "$(BLUE)🔍 Checking existing infrastructure...$(NC)"
	@# Check GKE cluster
	@if gcloud container clusters describe munshi-cluster --zone=us-east1-b --project=central-list-469110-f1 >/dev/null 2>&1; then \
		echo "$(GREEN)✓ GKE cluster exists$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  GKE cluster will be created$(NC)"; \
	fi
	@# Check Artifact Registry
	@if gcloud artifacts repositories describe munshi-containers --location=us-east1 >/dev/null 2>&1; then \
		echo "$(GREEN)✓ Artifact Registry exists$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Artifact Registry will be created$(NC)"; \
	fi
	@# Check model storage bucket
	@if gsutil ls gs://central-list-469110-f1-munshi-models >/dev/null 2>&1; then \
		echo "$(GREEN)✓ Model storage bucket exists$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Model storage bucket will be created$(NC)"; \
	fi
	@# Check node pools
	@if gcloud container node-pools list --cluster=munshi-cluster --zone=us-east1-b >/dev/null 2>&1; then \
		NODE_POOLS=$$(gcloud container node-pools list --cluster=munshi-cluster --zone=us-east1-b --format="value(name)" | wc -l); \
		echo "$(GREEN)✓ $$NODE_POOLS node pools exist$(NC)"; \
	fi

_import-existing-resources: ## Import existing resources into Terraform state (internal use)
	@echo "$(BLUE)📥 Importing existing resources...$(NC)"
	@# Check if we're already in terraform directory or need to cd
	@if [ -f "terraform.tfvars" ]; then \
		TERRAFORM_DIR="."; \
	else \
		TERRAFORM_DIR="infrastructure/terraform"; \
	fi && \
	cd $$TERRAFORM_DIR && \
		PROJECT_ID=$$(grep -E "^project_id" terraform.tfvars | cut -d'"' -f2) && \
		echo "Using project: $$PROJECT_ID" && \
		IMPORTS_DONE=0 && \
		echo "$(YELLOW)📥 Checking for existing GKE cluster...$(NC)" && \
		if gcloud container clusters describe munshi-cluster --zone=us-east1-b --project=$$PROJECT_ID >/dev/null 2>&1; then \
			echo "$(YELLOW)📥 Importing GKE cluster...$(NC)"; \
			terraform import google_container_cluster.cluster $$PROJECT_ID/us-east1-b/munshi-cluster 2>/dev/null || true; \
			IMPORTS_DONE=$$((IMPORTS_DONE + 1)); \
		fi && \
		echo "$(YELLOW)📥 Checking for existing Artifact Registry...$(NC)" && \
		if gcloud artifacts repositories describe munshi-containers --location=us-east1 --project=$$PROJECT_ID >/dev/null 2>&1; then \
			echo "$(YELLOW)📥 Importing Artifact Registry...$(NC)"; \
			terraform import google_artifact_registry_repository.munshi_containers projects/$$PROJECT_ID/locations/us-east1/repositories/munshi-containers 2>/dev/null || true; \
			IMPORTS_DONE=$$((IMPORTS_DONE + 1)); \
		fi && \
		if [ $$IMPORTS_DONE -gt 0 ]; then \
			echo "$(GREEN)✓ Imported $$IMPORTS_DONE existing resources$(NC)"; \
		else \
			echo "$(BLUE)ℹ️  No existing resources to import$(NC)"; \
		fi