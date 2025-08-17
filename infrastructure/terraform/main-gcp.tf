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
    spot         = var.use_spot_instances
    machine_type = "e2-medium"

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

# High-memory node pool for LLM services
resource "google_container_node_pool" "memory_nodes" {
  name     = "${var.cluster_name}-memory-pool"
  location = var.zone
  cluster  = google_container_cluster.cluster.name
  
  autoscaling {
    min_node_count = 0
    max_node_count = 3
  }

  node_config {
    spot         = var.use_spot_instances
    machine_type = "e2-highmem-4"

    service_account = google_service_account.cluster_service_account.email
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    disk_size_gb = 50
    disk_type    = "pd-ssd"

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

# GPU node pool for ASR service
resource "google_container_node_pool" "gpu_nodes" {
  name     = "${var.cluster_name}-gpu-pool"
  location = var.zone
  cluster  = google_container_cluster.cluster.name
  
  autoscaling {
    min_node_count = 0
    max_node_count = 2
  }

  node_config {
    spot         = var.use_spot_instances
    machine_type = "n1-standard-4"

    guest_accelerator {
      type  = "nvidia-tesla-t4"
      count = 1
    }

    service_account = google_service_account.cluster_service_account.email
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    disk_size_gb = 100
    disk_type    = "pd-ssd"

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

# Database node pool - on-demand for reliability
resource "google_container_node_pool" "database_nodes" {
  name     = "${var.cluster_name}-database-pool"
  location = var.zone
  cluster  = google_container_cluster.cluster.name
  
  autoscaling {
    min_node_count = 1
    max_node_count = 3
  }

  node_config {
    spot         = false  # Databases need reliability
    machine_type = "e2-standard-4"

    service_account = google_service_account.cluster_service_account.email
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    metadata = {
      disable-legacy-endpoints = "true"
    }

    disk_size_gb = 100
    disk_type    = "pd-ssd"

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

  depends_on = [google_project_service.artifact_registry_api]
}

# Service account for cluster nodes
resource "google_service_account" "cluster_service_account" {
  account_id   = "${var.cluster_name}-nodes"
  display_name = "GKE Cluster Service Account"
}

# Get current Google Cloud client configuration
data "google_client_config" "provider" {}

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

# Create cert-manager namespace
resource "kubernetes_namespace" "cert_manager" {
  metadata {
    name = "cert-manager"
    labels = {
      "app.kubernetes.io/name" = "cert-manager"
    }
  }
  depends_on = [google_container_cluster.cluster]
}

# Install cert-manager using Helm
resource "helm_release" "cert_manager" {
  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  version    = "v1.13.2"
  namespace  = kubernetes_namespace.cert_manager.metadata[0].name

  set {
    name  = "installCRDs"
    value = "true"
  }

  set {
    name  = "global.leaderElection.namespace"
    value = kubernetes_namespace.cert_manager.metadata[0].name
  }

  depends_on = [
    kubernetes_namespace.cert_manager,
    google_container_node_pool.general_nodes
  ]
}
