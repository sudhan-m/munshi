# Munshi Platform - Simplified Variables

# Required Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "jwt_secret" {
  description = "JWT secret for authentication"
  type        = string
  sensitive   = true
}

variable "google_api_key" {
  description = "Google API key for Gemini LLM service"
  type        = string
  sensitive   = true
}

# Optional Configuration (sensible defaults)
variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
  default     = "munshi-cluster"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "namespace" {
  description = "Kubernetes namespace"
  type        = string
  default     = "munshi-prod"
}

variable "environment" {
  description = "Environment (production, staging, development)"
  type        = string
  default     = "production"
}

# Cost Optimization (spot instances enabled by default)
variable "use_spot_instances" {
  description = "Use spot instances for application workloads (70% cost savings)"
  type        = bool
  default     = true
}