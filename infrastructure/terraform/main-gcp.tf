# Terraform configuration for Munshi pronunciation profiling platform on GCP
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "~> 1.14"
    }
  }
}

# Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
  # Use gcloud credentials
}

# Create GKE cluster optimized for pronunciation profiling workloads
resource "google_container_cluster" "cluster" {
  name     = var.cluster_name
  location = var.zone
  
  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  # Enable Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Enable network policy for security
  network_policy {
    enabled = true
  }

  # Enable IP aliasing for better networking
  ip_allocation_policy {}

  # Enable addons for pronunciation profiling workloads
  addons_config {
    horizontal_pod_autoscaling {
      disabled = false
    }
    http_load_balancing {
      disabled = false
    }
    network_policy_config {
      disabled = false
    }
  }

  # Enable binary authorization for security
  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }

  # Enable private cluster for security
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  # Release channel for automatic updates
  release_channel {
    channel = var.environment == "production" ? "REGULAR" : "RAPID"
  }

  # Master auth networks
  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "All networks"
    }
  }
}

# General purpose node pool for most services
resource "google_container_node_pool" "general_nodes" {
  name       = "${var.cluster_name}-general-pool"
  location   = var.zone
  cluster    = google_container_cluster.cluster.name
  
  autoscaling {
    min_node_count = var.environment == "production" ? 2 : 1
    max_node_count = var.environment == "production" ? 10 : 5
  }

  node_config {
    spot         = var.environment != "production"
    machine_type = var.machine_type

    service_account = google_service_account.cluster_service_account.email
    oauth_scopes    = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    disk_size_gb = var.environment != "production" ? 30 : 100
    disk_type    = "pd-standard"

    labels = {
      environment    = var.environment
      node-pool-type = "general"
    }

    # Enable secure boot and integrity monitoring
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# High-memory node pool for LLM and ASR services
resource "google_container_node_pool" "memory_intensive_nodes" {
  count      = var.enable_memory_intensive_pool ? 1 : 0
  name       = "${var.cluster_name}-memory-pool"
  location   = var.zone
  cluster    = google_container_cluster.cluster.name
  
  autoscaling {
    min_node_count = 0
    max_node_count = var.environment == "production" ? 3 : 2
  }

  node_config {
    spot         = var.environment != "production"
    machine_type = "e2-highmem-4"  # 4 vCPUs, 32GB RAM for LLM processing

    service_account = google_service_account.cluster_service_account.email
    oauth_scopes    = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    disk_size_gb = 50
    disk_type    = "pd-ssd"  # Faster storage for model loading

    labels = {
      environment    = var.environment
      node-pool-type = "memory-intensive"
      workload-type  = "llm-asr"
    }

    taint {
      key    = "workload-type"
      value  = "memory-intensive"
      effect = "NO_SCHEDULE"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Service account for the cluster nodes
resource "google_service_account" "cluster_service_account" {
  account_id   = "${var.cluster_name}-nodes"
  display_name = "GKE Cluster ${var.cluster_name} Service Account"
}

# Kubernetes Provider
provider "kubernetes" {
  host                   = "https://${google_container_cluster.cluster.endpoint}"
  cluster_ca_certificate = base64decode(google_container_cluster.cluster.master_auth[0].cluster_ca_certificate)
  token                  = data.google_client_config.provider.access_token
}

# Helm Provider
provider "helm" {
  kubernetes {
    host                   = "https://${google_container_cluster.cluster.endpoint}"
    cluster_ca_certificate = base64decode(google_container_cluster.cluster.master_auth[0].cluster_ca_certificate)
    token                  = data.google_client_config.provider.access_token
  }
}

# Get current Google Cloud client configuration
data "google_client_config" "provider" {}

# Create namespace
resource "kubernetes_namespace" "munshi" {
  metadata {
    name = var.namespace
    annotations = {
      "linkerd.io/inject" = "enabled"
    }
  }
}

# Secrets
resource "kubernetes_secret" "jwt_secret" {
  metadata {
    name      = "jwt-secret"
    namespace = kubernetes_namespace.munshi.metadata[0].name
  }

  data = {
    secret = var.jwt_secret
  }

  type = "Opaque"
}

resource "kubernetes_secret" "postgres_auth" {
  metadata {
    name      = "postgres-auth-secret"
    namespace = kubernetes_namespace.munshi.metadata[0].name
  }

  data = {
    password = var.postgres_auth_password
  }

  type = "Opaque"
}

resource "kubernetes_secret" "postgres_gateway" {
  metadata {
    name      = "postgres-gateway-secret"
    namespace = kubernetes_namespace.munshi.metadata[0].name
  }

  data = {
    password = var.postgres_gateway_password
  }

  type = "Opaque"
}

resource "kubernetes_secret" "database_credentials" {
  metadata {
    name      = "database-credentials"
    namespace = kubernetes_namespace.munshi.metadata[0].name
  }

  data = {
    mongodb_url      = var.mongodb_url
    mongodb_database = var.mongodb_database
    mongodb_username = var.mongodb_username
    mongodb_password = var.mongodb_password
  }

  type = "Opaque"
}

# Secret for Google API keys (LLM service)
resource "kubernetes_secret" "google_api_keys" {
  metadata {
    name      = "google-api-keys"
    namespace = kubernetes_namespace.munshi.metadata[0].name
  }

  data = {
    google_api_key = var.google_api_key
  }

  type = "Opaque"
}

# Google Cloud SQL (PostgreSQL) instance
resource "google_sql_database_instance" "postgres" {
  count            = var.use_cloud_sql ? 1 : 0
  name             = "${var.project_id}-postgres"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = var.postgres_tier
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = var.vpc_network
      authorized_networks {
        name  = "gke-cluster"
        value = google_container_cluster.cluster.cluster_ipv4_cidr
      }
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
    }

    database_flags {
      name  = "log_statement"
      value = "all"
    }
  }

  deletion_protection = var.environment == "production"
}

# Google Artifact Registry for container images
resource "google_artifact_registry_repository" "munshi_containers" {
  location      = var.region
  repository_id = "munshi-containers"
  description   = "Container repository for Munshi pronunciation profiling platform"
  format        = "DOCKER"

  cleanup_policies {
    id     = "delete-old-images"
    action = "DELETE"
    condition {
      tag_state    = "UNTAGGED"
      older_than   = "2592000s"  # 30 days
    }
  }

  cleanup_policies {
    id     = "keep-recent-tagged"
    action = "KEEP"
    most_recent_versions {
      package_name_prefixes = ["munshi-"]
      keep_count           = 10
    }
  }
}

# Google Cloud Storage bucket for audio files
resource "google_storage_bucket" "audio_storage" {
  name          = "${var.project_id}-munshi-audio"
  location      = var.region
  force_destroy = var.environment != "production"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  # CORS for browser audio uploads
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# Google Cloud Storage bucket for model artifacts (Whisper models, etc.)
resource "google_storage_bucket" "model_storage" {
  name          = "${var.project_id}-munshi-models"
  location      = var.region
  force_destroy = var.environment != "production"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  # Models are read-heavy, optimize for that
  lifecycle_rule {
    condition {
      age = 180  # Keep models longer
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# IAM service account for workload identity
resource "google_service_account" "munshi_workload" {
  account_id   = "munshi-workload"
  display_name = "Munshi Workload Identity Service Account"
}

# Grant storage access to the service account
resource "google_storage_bucket_iam_member" "audio_storage_access" {
  bucket = google_storage_bucket.audio_storage.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.munshi_workload.email}"
}

resource "google_storage_bucket_iam_member" "model_storage_access" {
  bucket = google_storage_bucket.model_storage.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.munshi_workload.email}"
}

# Grant Artifact Registry access for pulling images
resource "google_artifact_registry_repository_iam_member" "container_access" {
  location   = google_artifact_registry_repository.munshi_containers.location
  repository = google_artifact_registry_repository.munshi_containers.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.cluster_service_account.email}"
}

# Kubernetes service account
resource "kubernetes_service_account" "munshi_workload" {
  metadata {
    name      = "munshi-workload"
    namespace = kubernetes_namespace.munshi.metadata[0].name
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.munshi_workload.email
    }
  }
}

# Workload Identity binding
resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.munshi_workload.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${kubernetes_namespace.munshi.metadata[0].name}/${kubernetes_service_account.munshi_workload.metadata[0].name}]"
}

# Note: Helm deployment will be done separately after infrastructure is ready
# This allows us to get the core infrastructure up first, then deploy applications

# Note: HPA will be created with the Helm deployment

# Network Policy for enhanced security
resource "kubernetes_network_policy" "munshi_network_policy" {
  metadata {
    name      = "munshi-network-policy"
    namespace = kubernetes_namespace.munshi.metadata[0].name
  }

  spec {
    pod_selector {}

    policy_types = ["Ingress", "Egress"]

    ingress {
      from {
        namespace_selector {
          match_labels = {
            name = kubernetes_namespace.munshi.metadata[0].name
          }
        }
      }
    }

    egress {
      to {
        namespace_selector {
          match_labels = {
            name = kubernetes_namespace.munshi.metadata[0].name
          }
        }
      }
    }

    egress {
      ports {
        protocol = "TCP"
        port     = "53"
      }
      ports {
        protocol = "UDP"
        port     = "53"
      }
    }

    # Allow egress to GCP APIs
    egress {
      ports {
        protocol = "TCP"
        port     = "443"
      }
    }
  }
}

# Resource Quota
resource "kubernetes_resource_quota" "munshi_quota" {
  metadata {
    name      = "munshi-quota"
    namespace = kubernetes_namespace.munshi.metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = var.total_cpu_requests
      "requests.memory" = var.total_memory_requests
      "limits.cpu"      = var.total_cpu_limits
      "limits.memory"   = var.total_memory_limits
      "pods"           = var.max_pods
      "secrets"        = "50"
      "configmaps"     = "50"
    }
  }
}

# Outputs for deployment information
output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.cluster.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.cluster.endpoint
  sensitive   = true
}

output "cluster_location" {
  description = "GKE cluster location"
  value       = google_container_cluster.cluster.location
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.munshi_containers.repository_id}"
}

output "audio_storage_bucket" {
  description = "Audio storage bucket name"
  value       = google_storage_bucket.audio_storage.name
}

output "model_storage_bucket" {
  description = "Model storage bucket name"
  value       = google_storage_bucket.model_storage.name
}

output "namespace" {
  description = "Kubernetes namespace"
  value       = kubernetes_namespace.munshi.metadata[0].name
}

output "workload_identity_service_account" {
  description = "Workload Identity service account email"
  value       = google_service_account.munshi_workload.email
}