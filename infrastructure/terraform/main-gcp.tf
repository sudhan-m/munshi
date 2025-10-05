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
  }
}

# Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
  # Use gcloud credentials
}

# Enable required APIs
resource "google_project_service" "container_api" {
  service = "container.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry_api" {
  service = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# Create GKE cluster optimized for pronunciation profiling workloads
resource "google_container_cluster" "cluster" {
  name     = var.cluster_name
  location = var.zone
  
  # Ensure required APIs are enabled first
  depends_on = [
    google_project_service.container_api,
    google_project_service.artifact_registry_api
  ]
  
  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1
  deletion_protection      = false

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

  # Enable cluster autoscaling
  cluster_autoscaling {
    enabled = true
    
    resource_limits {
      resource_type = "cpu"
      minimum       = 0
      maximum       = 100
    }
    
    resource_limits {
      resource_type = "memory"
      minimum       = 0
      maximum       = 1000
    }
  }

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

# Optimized general purpose node pool - cost-effective packing
resource "google_container_node_pool" "general_nodes" {
  name       = "${var.cluster_name}-general-pool"
  location   = var.zone
  cluster    = google_container_cluster.cluster.name

  autoscaling {
    min_node_count = 1  # Always keep at least 1 for core services
    max_node_count = 3  # Reduced for cost control
  }

  node_config {
    spot         = true  # Force spot instances for maximum savings
    machine_type = "e2-standard-4"  # Larger nodes for better packing (4 vCPU, 16GB)

    service_account = google_service_account.cluster_service_account.email
    oauth_scopes    = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    disk_size_gb = 50  # Balanced size for multiple services
    disk_type    = "pd-standard"  # Cost-effective storage

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

# Optimized memory node pool - cost-effective for LLM services
resource "google_container_node_pool" "memory_nodes" {
  name     = "${var.cluster_name}-memory-pool"
  location = var.zone
  cluster  = google_container_cluster.cluster.name

  autoscaling {
    min_node_count = 0  # Scale to zero when not needed
    max_node_count = 1  # Single node for cost control
  }

  node_config {
    spot         = true  # Force spot instances for 80% cost savings
    machine_type = "e2-highmem-2"  # Smaller but sufficient (2 vCPU, 16GB)

    service_account = google_service_account.cluster_service_account.email
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    disk_size_gb = 30  # Reduced disk size
    disk_type    = "pd-standard"  # Cost-effective storage

    labels = {
      workload-type = "memory-intensive"
    }

    taint {
      key    = "workload-type"
      value  = "memory-intensive"
      effect = "NO_SCHEDULE"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# GPU node pool for ASR service - ENABLED (moved to us-east1-a with upgraded billing)
resource "google_container_node_pool" "gpu_nodes" {
  name     = "${var.cluster_name}-gpu-pool"
  location = var.zone
  cluster  = google_container_cluster.cluster.name

  autoscaling {
    min_node_count = 0  # Scales to zero when idle
    max_node_count = 1  # Reduced to 1 for cost optimization
  }

  node_config {
    spot         = true  # Force spot instances for maximum cost savings
    machine_type = "g2-standard-4"  # Required for nvidia-l4 GPU

    guest_accelerator {
      type  = "nvidia-l4"  # L4 is available in us-east1-b (newer than T4)
      count = 1
    }

    service_account = google_service_account.cluster_service_account.email
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    disk_size_gb = 20    # Minimal disk size
    disk_type    = "pd-standard"  # Cheapest storage

    labels = {
      workload-type = "gpu"
    }

    # GPU nodes get automatic taints, no need for manual taint
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Optimized database node pool - balanced cost and reliability
resource "google_container_node_pool" "database_nodes" {
  name     = "${var.cluster_name}-database-pool"
  location = var.zone
  cluster  = google_container_cluster.cluster.name

  autoscaling {
    min_node_count = 1  # Keep minimum for database availability
    max_node_count = 2  # Reduced scaling for cost control
  }

  node_config {
    spot         = true  # Use spot for cost savings (databases can handle restarts)
    machine_type = "e2-standard-2"  # Smaller instance (2 vCPU, 8GB)

    service_account = google_service_account.cluster_service_account.email
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    disk_size_gb = 50  # Reduced disk size
    disk_type    = "pd-standard"  # Cost-effective storage

    labels = {
      workload-type = "database"
    }

    taint {
      key    = "workload-type"
      value  = "database"
      effect = "NO_SCHEDULE"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}


# Artifact Registry for container images
resource "google_artifact_registry_repository" "munshi_containers" {
  location      = var.region
  repository_id = "munshi-containers"
  description   = "Docker repository for Munshi platform services"
  format        = "DOCKER"

  labels = {
    environment = var.environment
    project     = "munshi"
  }

  lifecycle {
    # Ignore changes to labels that might be managed externally
    ignore_changes = [labels]
    # Don't recreate if it already exists - just import it
    create_before_destroy = false
    # Prevent destruction if it already exists
    prevent_destroy = false
  }

  depends_on = [google_project_service.artifact_registry_api]
}

# Service account for cluster nodes
resource "google_service_account" "cluster_service_account" {
  account_id   = "${var.cluster_name}-nodes"
  display_name = "GKE Cluster Service Account"
}

# Grant required IAM roles to the cluster service account
resource "google_project_iam_member" "cluster_service_account_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cluster_service_account.email}"
}

resource "google_project_iam_member" "cluster_service_account_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.cluster_service_account.email}"
}

resource "google_project_iam_member" "cluster_service_account_monitoring_viewer" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.cluster_service_account.email}"
}

resource "google_project_iam_member" "cluster_service_account_artifact_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.cluster_service_account.email}"
}

# Storage bucket for model files
resource "google_storage_bucket" "model_storage" {
  name          = "${var.project_id}-munshi-models"
  location      = var.region
  force_destroy = true

  versioning {
    enabled = true
  }

  labels = {
    environment = var.environment
    project     = "munshi"
  }
}

# Grant storage access to cluster service account
resource "google_project_iam_member" "cluster_service_account_storage" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.cluster_service_account.email}"
}

# Get current Google Cloud client configuration
data "google_client_config" "provider" {}

# Kubernetes Provider - Commented out to avoid chicken-and-egg with cluster creation
# Namespace creation is handled by kubectl in Makefile
# provider "kubernetes" {
#   host                   = "https://${google_container_cluster.cluster.endpoint}"
#   cluster_ca_certificate = base64decode(google_container_cluster.cluster.master_auth[0].cluster_ca_certificate)
#   token                  = data.google_client_config.provider.access_token
# }

# Helm Provider - Commented out to avoid chicken-and-egg with cluster creation
# Helm deployments are handled by Makefile
# provider "helm" {
#   kubernetes {
#     host                   = "https://${google_container_cluster.cluster.endpoint}"
#     cluster_ca_certificate = base64decode(google_container_cluster.cluster.master_auth[0].cluster_ca_certificate)
#     token                  = data.google_client_config.provider.access_token
#   }
# }

# Create main application namespace - Commented out, handled by kubectl in Makefile
# resource "kubernetes_namespace" "munshi_namespace" {
#   metadata {
#     name = var.namespace
#     labels = {
#       "app.kubernetes.io/name" = "munshi-platform"
#     }
#   }
#   depends_on = [google_container_cluster.cluster]
# }

# Create cert-manager namespace - Commented out, handled by kubectl in Makefile
# Optional cert-manager namespace
# resource "kubernetes_namespace" "cert_manager" {
#   count = var.enable_cert_manager ? 1 : 0
#
#   metadata {
#     name = "cert-manager"
#     labels = {
#       "app.kubernetes.io/name" = "cert-manager"
#     }
#   }
#   depends_on = [google_container_cluster.cluster]
# }

# Optional cert-manager installation using Helm - Commented out, handled by Helm in Makefile
# resource "helm_release" "cert_manager" {
#   count = var.enable_cert_manager ? 1 : 0
#
#   name       = "cert-manager"
#   repository = "https://charts.jetstack.io"
#   chart      = "cert-manager"
#   version    = "v1.13.2"
#   namespace  = kubernetes_namespace.cert_manager[0].metadata[0].name
#   timeout    = var.deployment_timeout
#
#   set {
#     name  = "installCRDs"
#     value = "true"
#   }
#
#   set {
#     name  = "global.leaderElection.namespace"
#     value = kubernetes_namespace.cert_manager[0].metadata[0].name
#   }
#
#   depends_on = [
#     kubernetes_namespace.cert_manager,
#     google_container_node_pool.general_nodes
#   ]
# }

# Database initialization job - Commented out, handled by Makefile/Helm
# resource "kubernetes_job" "database_init" {
#   count = var.enable_database_init ? 1 : 0
#
#   metadata {
#     name      = "database-init"
#     namespace = var.namespace
#   }
#
#   spec {
#     template {
#       metadata {}
#       spec {
#         restart_policy = "OnFailure"
#
#         container {
#           name    = "postgres-init"
#           image   = "postgres:15-alpine"
#           command = ["/bin/sh"]
#           args = ["-c", <<-EOT
#             export PGPASSWORD="$POSTGRES_PASSWORD"
#             echo "Waiting for PostgreSQL to be ready..."
#             until pg_isready -h $POSTGRES_HOST -p 5432 -U postgres; do
#               echo "PostgreSQL not ready, waiting..."
#               sleep 5
#             done
#             echo "PostgreSQL is ready, creating database and user..."
#             psql -h $POSTGRES_HOST -U postgres -c "CREATE DATABASE IF NOT EXISTS munshi_auth;"
#             psql -h $POSTGRES_HOST -U postgres -c "CREATE USER IF NOT EXISTS munshi_user WITH PASSWORD '$MUNSHI_PASSWORD';"
#             psql -h $POSTGRES_HOST -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE munshi_auth TO munshi_user;"
#             psql -h $POSTGRES_HOST -U postgres -d munshi_auth -c "GRANT ALL ON SCHEMA public TO munshi_user;"
#             psql -h $POSTGRES_HOST -U postgres -d munshi_auth -c "GRANT CREATE ON SCHEMA public TO munshi_user;"
#             echo "Database initialization completed successfully!"
#           EOT
#           ]
#
#           env {
#             name  = "POSTGRES_HOST"
#             value = "munshi-platform-postgresql"
#           }
#           env {
#             name  = "POSTGRES_PASSWORD"
#             value = var.postgres_password
#           }
#           env {
#             name  = "MUNSHI_PASSWORD"
#             value = var.munshi_db_password
#           }
#         }
#
#         # Use database node pool
#         node_selector = {
#           workload-type = "database"
#         }
#
#         toleration {
#           key    = "workload-type"
#           value  = "database"
#           effect = "NoSchedule"
#         }
#       }
#     }
#
#     backoff_limit              = 3
#     ttl_seconds_after_finished = 300
#   }
#
#   depends_on = [
#     kubernetes_namespace.munshi_namespace,
#     google_container_node_pool.database_nodes,
#     google_container_cluster.cluster
#   ]
#
#   lifecycle {
#     # Allow graceful handling if namespace doesn't exist yet
#     ignore_changes = [metadata[0].namespace]
#   }
# }
