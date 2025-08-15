# Makefile for Munshi Platform Helm Chart
# =============================================================================

# Configuration
CHART_NAME := munshi-platform
DEV_NAMESPACE := munshi-dev
STAGING_NAMESPACE := munshi-staging
PROD_NAMESPACE := munshi-prod
KIND_CLUSTER_NAME := munshi

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

.PHONY: help lint clean validate package
.PHONY: dependency-update template template-dev template-staging template-prod
.PHONY: install-dev install-staging install-prod
.PHONY: upgrade-dev upgrade-staging upgrade-prod
.PHONY: uninstall-dev uninstall-staging uninstall-prod
.PHONY: status-dev status-staging status-prod
.PHONY: logs-dev logs-staging logs-prod
.PHONY: dev-setup dev-teardown port-forward-dev
.PHONY: create-secrets-dev create-secrets-staging create-secrets-prod

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "$(BLUE)Munshi Platform Helm Chart$(NC)"
	@echo "=============================="
	@echo ""
	@echo "$(GREEN)Chart Operations:$(NC)"
	@awk '/^[a-zA-Z_-]+:.*?## .*$$/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | grep -E "(lint|template|dependency|validate|package|clean)"
	@echo ""
	@echo "$(GREEN)Environment Management:$(NC)"
	@awk '/^[a-zA-Z_-]+:.*?## .*$$/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | grep -E "(install|upgrade|uninstall)"
	@echo ""
	@echo "$(GREEN)Development Tools:$(NC)"
	@awk '/^[a-zA-Z_-]+:.*?## .*$$/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | grep -E "(dev-|status|logs|port-forward)"
	@echo ""
	@echo "$(GREEN)Secret Management:$(NC)"
	@awk '/^[a-zA-Z_-]+:.*?## .*$$/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | grep -E "create-secrets"

# =============================================================================
# Chart Operations
# =============================================================================

lint: ## Lint the Helm chart
	@echo "$(BLUE)Linting Helm chart...$(NC)"
	helm lint .

dependency-update: ## Update chart dependencies
	@echo "$(BLUE)Updating chart dependencies...$(NC)"
	helm dependency update

template: ## Generate all templates (dry-run)
	@echo "$(BLUE)Generating templates...$(NC)"
	helm template $(CHART_NAME) . --debug

template-dev: ## Generate templates for development
	@echo "$(BLUE)Generating development templates...$(NC)"
	helm template $(CHART_NAME)-dev . -f values-development.yaml --debug > manifests-dev.yaml
	@echo "$(GREEN)Development manifests saved to manifests-dev.yaml$(NC)"

template-staging: ## Generate templates for staging
	@echo "$(BLUE)Generating staging templates...$(NC)"
	helm template $(CHART_NAME)-staging . -f values-staging.yaml --debug > manifests-staging.yaml
	@echo "$(GREEN)Staging manifests saved to manifests-staging.yaml$(NC)"

template-prod: ## Generate templates for production
	@echo "$(BLUE)Generating production templates...$(NC)"
	helm template $(CHART_NAME)-prod . -f values-production.yaml --debug > manifests-prod.yaml
	@echo "$(GREEN)Production manifests saved to manifests-prod.yaml$(NC)"

validate: lint template-dev template-staging template-prod ## Validate chart across all environments
	@echo "$(GREEN)✓ Chart validation completed successfully$(NC)"

package: validate ## Package the Helm chart
	@echo "$(BLUE)Packaging Helm chart...$(NC)"
	helm package .
	@echo "$(GREEN)✓ Chart packaged successfully$(NC)"

clean: ## Clean up generated files
	@echo "$(BLUE)Cleaning up generated files...$(NC)"
	rm -f manifests-*.yaml
	rm -f charts/*.tgz
	rm -rf charts/postgresql charts/redis charts/cert-manager
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

# =============================================================================
# Development Environment
# =============================================================================

install-dev: dependency-update ## Install development environment
	@echo "$(BLUE)Installing development environment...$(NC)"
	kubectl create namespace $(DEV_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	helm install $(CHART_NAME)-dev . -f values-development.yaml --namespace $(DEV_NAMESPACE)
	@echo "$(GREEN)✓ Development environment installed$(NC)"

upgrade-dev: ## Upgrade development environment
	@echo "$(BLUE)Upgrading development environment...$(NC)"
	helm upgrade $(CHART_NAME)-dev . -f values-development.yaml --namespace $(DEV_NAMESPACE)
	@echo "$(GREEN)✓ Development environment upgraded$(NC)"

uninstall-dev: ## Uninstall development environment
	@echo "$(YELLOW)Uninstalling development environment...$(NC)"
	helm uninstall $(CHART_NAME)-dev --namespace $(DEV_NAMESPACE) || true
	kubectl delete namespace $(DEV_NAMESPACE) || true
	@echo "$(GREEN)✓ Development environment uninstalled$(NC)"

# =============================================================================
# Staging Environment
# =============================================================================

install-staging: dependency-update ## Install staging environment
	@echo "$(BLUE)Installing staging environment...$(NC)"
	kubectl create namespace $(STAGING_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	helm install $(CHART_NAME)-staging . -f values-staging.yaml --namespace $(STAGING_NAMESPACE)
	@echo "$(GREEN)✓ Staging environment installed$(NC)"

upgrade-staging: ## Upgrade staging environment
	@echo "$(BLUE)Upgrading staging environment...$(NC)"
	helm upgrade $(CHART_NAME)-staging . -f values-staging.yaml --namespace $(STAGING_NAMESPACE)
	@echo "$(GREEN)✓ Staging environment upgraded$(NC)"

uninstall-staging: ## Uninstall staging environment
	@echo "$(YELLOW)Uninstalling staging environment...$(NC)"
	helm uninstall $(CHART_NAME)-staging --namespace $(STAGING_NAMESPACE) || true
	kubectl delete namespace $(STAGING_NAMESPACE) || true
	@echo "$(GREEN)✓ Staging environment uninstalled$(NC)"

# =============================================================================
# Production Environment
# =============================================================================

install-prod: dependency-update ## Install production environment (with confirmation)
	@echo "$(RED)⚠️  WARNING: This will install to PRODUCTION!$(NC)"
	@echo "$(YELLOW)Make sure all secrets are properly configured.$(NC)"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || (echo "$(RED)Aborted$(NC)" && exit 1)
	kubectl create namespace $(PROD_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	helm install $(CHART_NAME)-prod . -f values-production.yaml --namespace $(PROD_NAMESPACE)
	@echo "$(GREEN)✓ Production environment installed$(NC)"

upgrade-prod: ## Upgrade production environment (with confirmation)
	@echo "$(RED)⚠️  WARNING: This will upgrade PRODUCTION!$(NC)"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || (echo "$(RED)Aborted$(NC)" && exit 1)
	helm upgrade $(CHART_NAME)-prod . -f values-production.yaml --namespace $(PROD_NAMESPACE)
	@echo "$(GREEN)✓ Production environment upgraded$(NC)"

uninstall-prod: ## Uninstall production environment (with confirmation)
	@echo "$(RED)⚠️  WARNING: This will DESTROY PRODUCTION!$(NC)"
	@read -p "Are you absolutely sure? (y/N): " confirm && [ "$$confirm" = "y" ] || (echo "$(RED)Aborted$(NC)" && exit 1)
	helm uninstall $(CHART_NAME)-prod --namespace $(PROD_NAMESPACE) || true
	kubectl delete namespace $(PROD_NAMESPACE) || true
	@echo "$(YELLOW)Production environment uninstalled$(NC)"

# =============================================================================
# Development Tools
# =============================================================================

dev-setup: ## Set up local development cluster with kind
	@echo "$(BLUE)Setting up development cluster...$(NC)"
	kind create cluster --name $(KIND_CLUSTER_NAME) || true
	kubectl config use-context kind-$(KIND_CLUSTER_NAME)
	@echo "$(BLUE)Installing NGINX Ingress Controller...$(NC)"
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
	kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=90s
	@echo "$(BLUE)Installing cert-manager...$(NC)"
	kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.1/cert-manager.yaml
	kubectl wait --namespace cert-manager --for=condition=ready pod --selector=app.kubernetes.io/name=cert-manager --timeout=90s
	@echo "$(GREEN)✓ Development cluster ready!$(NC)"

dev-teardown: ## Tear down local development cluster
	@echo "$(YELLOW)Tearing down development cluster...$(NC)"
	kind delete cluster --name $(KIND_CLUSTER_NAME)
	@echo "$(GREEN)✓ Development cluster removed$(NC)"

port-forward-dev: ## Port forward to UI service in development
	@echo "$(BLUE)Port forwarding to UI service...$(NC)"
	@echo "$(GREEN)Access the application at: https://localhost:8080$(NC)"
	kubectl port-forward svc/ui-service 8080:8002 -n $(DEV_NAMESPACE)

# =============================================================================
# Status and Monitoring
# =============================================================================

status-dev: ## Show development environment status
	@echo "$(BLUE)Development Environment Status:$(NC)"
	kubectl get all -n $(DEV_NAMESPACE)

status-staging: ## Show staging environment status
	@echo "$(BLUE)Staging Environment Status:$(NC)"
	kubectl get all -n $(STAGING_NAMESPACE)

status-prod: ## Show production environment status
	@echo "$(BLUE)Production Environment Status:$(NC)"
	kubectl get all -n $(PROD_NAMESPACE)

logs-dev: ## Follow UI service logs in development
	@echo "$(BLUE)Following development logs...$(NC)"
	kubectl logs -f deployment/ui-service -n $(DEV_NAMESPACE)

logs-staging: ## Follow UI service logs in staging
	@echo "$(BLUE)Following staging logs...$(NC)"
	kubectl logs -f deployment/ui-service -n $(STAGING_NAMESPACE)

logs-prod: ## Follow UI service logs in production
	@echo "$(BLUE)Following production logs...$(NC)"
	kubectl logs -f deployment/ui-service -n $(PROD_NAMESPACE)

# =============================================================================
# Secret Management
# =============================================================================

create-secrets-dev: ## Create development secrets (included in values)
	@echo "$(BLUE)Development secrets are included in values-development.yaml$(NC)"
	@echo "$(GREEN)✓ No additional secret creation needed for development$(NC)"

create-secrets-staging: ## Create staging secrets (template)
	@echo "$(BLUE)Creating staging secrets...$(NC)"
	kubectl create namespace $(STAGING_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	@echo "$(YELLOW)Manual secret creation may be required for staging$(NC)"
	@echo "Review values-staging.yaml for secret configuration"

create-secrets-prod: ## Show production secret creation commands
	@echo "$(RED)Production secrets must be created manually:$(NC)"
	@echo ""
	@echo "$(YELLOW)Database credentials:$(NC)"
	@echo "kubectl create secret generic database-credentials \\"
	@echo "  --from-literal=auth-db-url=postgresql://user:pass@host:5432/munshi_auth \\"
	@echo "  --from-literal=audio-db-url=postgresql://user:pass@host:5432/munshi_audio \\"
	@echo "  --from-literal=conversation-db-url=postgresql://user:pass@host:5432/munshi_conversation \\"
	@echo "  -n $(PROD_NAMESPACE)"
	@echo ""
	@echo "$(YELLOW)Redis credentials:$(NC)"
	@echo "kubectl create secret generic redis-credentials \\"
	@echo "  --from-literal=redis-url=redis://user:pass@host:6379 \\"
	@echo "  -n $(PROD_NAMESPACE)"
	@echo ""
	@echo "$(YELLOW)Auth secrets:$(NC)"
	@echo "kubectl create secret generic auth-secrets \\"
	@echo "  --from-literal=jwt-secret=your-strong-jwt-secret \\"
	@echo "  -n $(PROD_NAMESPACE)"
	@echo ""
	@echo "$(YELLOW)LLM API keys:$(NC)"
	@echo "kubectl create secret generic llm-secrets \\"
	@echo "  --from-literal=google-api-key=your-google-api-key \\"
	@echo "  --from-literal=openai-api-key=your-openai-api-key \\"
	@echo "  -n $(PROD_NAMESPACE)"

# =============================================================================
# Testing and Debugging
# =============================================================================

test-dev: ## Run Helm tests in development
	@echo "$(BLUE)Running development tests...$(NC)"
	helm test $(CHART_NAME)-dev --namespace $(DEV_NAMESPACE)

test-staging: ## Run Helm tests in staging
	@echo "$(BLUE)Running staging tests...$(NC)"
	helm test $(CHART_NAME)-staging --namespace $(STAGING_NAMESPACE)

debug-dev: ## Debug development deployment
	@echo "$(BLUE)Development Debug Information:$(NC)"
	@echo "$(YELLOW)Pods:$(NC)"
	kubectl get pods -n $(DEV_NAMESPACE)
	@echo "$(YELLOW)Services:$(NC)"
	kubectl get services -n $(DEV_NAMESPACE)
	@echo "$(YELLOW)Ingress:$(NC)"
	kubectl get ingress -n $(DEV_NAMESPACE)
	@echo "$(YELLOW)Certificates:$(NC)"
	kubectl get certificates -n $(DEV_NAMESPACE)

# =============================================================================
# Quick Start
# =============================================================================

quick-start: dev-setup install-dev ## Complete development setup (cluster + deployment)
	@echo "$(GREEN)🎉 Quick start complete!$(NC)"
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "1. Add '127.0.0.1 munshi.local' to your /etc/hosts file"
	@echo "2. Access the application at: https://munshi.local"
	@echo "3. Use 'make port-forward-dev' for direct access via localhost:8080"