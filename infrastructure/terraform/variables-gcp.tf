# Variables for Munshi Terraform infrastructure on GCP

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for the infrastructure"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone for the GKE cluster"
  type        = string
  default     = "us-central1-a"
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace for Munshi services"
  type        = string
  default     = "munshi-prod"
}

variable "environment" {
  description = "Environment (production, staging, development)"
  type        = string
  default     = "production"
}

variable "image_registry" {
  description = "Container image registry"
  type        = string
  default     = "gcr.io"
}

# Secrets
variable "jwt_secret" {
  description = "JWT secret for authentication"
  type        = string
  sensitive   = true
}

variable "postgres_auth_password" {
  description = "PostgreSQL password for auth service"
  type        = string
  sensitive   = true
}

variable "postgres_gateway_password" {
  description = "PostgreSQL password for gateway service"
  type        = string
  sensitive   = true
}

variable "mongodb_url" {
  description = "MongoDB connection URL (MongoDB Atlas or other cloud provider)"
  type        = string
  sensitive   = true
}

variable "mongodb_database" {
  description = "MongoDB database name"
  type        = string
  default     = "munshi"
}

variable "mongodb_username" {
  description = "MongoDB username"
  type        = string
  sensitive   = true
}

variable "mongodb_password" {
  description = "MongoDB password"
  type        = string
  sensitive   = true
}

variable "google_api_key" {
  description = "Google API key for Gemini LLM service"
  type        = string
  sensitive   = true
}

# GCP-specific variables
variable "use_cloud_sql" {
  description = "Whether to use Google Cloud SQL for PostgreSQL"
  type        = bool
  default     = true
}

variable "postgres_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "vpc_network" {
  description = "VPC network for Cloud SQL private IP"
  type        = string
  default     = "default"
}

# Replica counts
variable "auth_service_replicas" {
  description = "Number of auth service replicas"
  type        = number
  default     = 2
}

variable "ui_service_replicas" {
  description = "Number of UI service replicas"
  type        = number
  default     = 2
}

variable "audio_service_replicas" {
  description = "Number of audio service replicas"
  type        = number
  default     = 2
}

# HPA settings
variable "ui_service_min_replicas" {
  description = "Minimum replicas for UI service HPA"
  type        = number
  default     = 2
}

variable "ui_service_max_replicas" {
  description = "Maximum replicas for UI service HPA"
  type        = number
  default     = 10
}

variable "ui_service_cpu_target" {
  description = "CPU utilization target for UI service HPA"
  type        = number
  default     = 80
}

variable "ui_service_memory_target" {
  description = "Memory utilization target for UI service HPA"
  type        = number
  default     = 80
}

# Resource quotas
variable "total_cpu_requests" {
  description = "Total CPU requests for the namespace"
  type        = string
  default     = "2"
}

variable "total_memory_requests" {
  description = "Total memory requests for the namespace"
  type        = string
  default     = "4Gi"
}

variable "total_cpu_limits" {
  description = "Total CPU limits for the namespace"
  type        = string
  default     = "4"
}

variable "total_memory_limits" {
  description = "Total memory limits for the namespace"
  type        = string
  default     = "8Gi"
}

variable "max_pods" {
  description = "Maximum number of pods in the namespace"
  type        = number
  default     = 50
}

# Storage
variable "storage_class" {
  description = "Storage class for persistent volumes"
  type        = string
  default     = "standard-rwo"
}

# GKE cluster configuration
variable "node_count" {
  description = "Number of nodes in the GKE cluster node pool"
  type        = number
  default     = 3
}

variable "machine_type" {
  description = "Machine type for GKE cluster nodes"
  type        = string
  default     = "e2-medium"
}

variable "enable_memory_intensive_pool" {
  description = "Enable memory-intensive node pool for LLM and ASR services"
  type        = bool
  default     = true
}