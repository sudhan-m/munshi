# Terraform configuration for Munshi microservices infrastructure on GCP
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
  }
}

# Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
  # Use gcloud credentials
}

# Create GKE cluster
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

  # Enable network policy
  network_policy {
    enabled = true
  }

  # Enable IP aliasing
  ip_allocation_policy {}
}

# Create a separately managed node pool
resource "google_container_node_pool" "cluster_nodes" {
  name       = "${var.cluster_name}-node-pool"
  location   = var.zone
  cluster    = google_container_cluster.cluster.name
  node_count = var.node_count

  node_config {
    spot         = var.environment != "production"  # Use spot instances for max cost savings (newer than preemptible)
    machine_type = var.machine_type

    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = google_service_account.cluster_service_account.email
    oauth_scopes    = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    # Cost optimization: smaller disk
    disk_size_gb = var.environment != "production" ? 20 : 100
    disk_type    = "pd-standard"  # Use standard disks instead of SSD

    # Cost optimization: enable autorepair but not autoupgrade for spot instances
    labels = {
      environment = var.environment
      cost-optimized = "true"
    }

    taint {
      key    = "cloud.google.com/gke-spot"
      value  = "true"
      effect = "NO_SCHEDULE"
    }
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

resource "kubernetes_secret" "mongodb" {
  metadata {
    name      = "mongodb-secret"
    namespace = kubernetes_namespace.munshi.metadata[0].name
  }

  data = {
    password = var.mongodb_password
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

# Google Cloud Storage bucket for audio files
resource "google_storage_bucket" "audio_storage" {
  name          = "${var.project_id}-munshi-audio"
  location      = var.region
  force_destroy = var.environment != "production"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
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
    }
  }
}