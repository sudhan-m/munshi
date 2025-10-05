# Output values for easy access to important resources

output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.cluster.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.cluster.endpoint
}

output "cluster_location" {
  description = "GKE cluster location"
  value       = google_container_cluster.cluster.location
}

output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.cluster.name} --zone=${google_container_cluster.cluster.location} --project=${var.project_id}"
}

output "artifact_registry_url" {
  description = "Artifact Registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.munshi_containers.repository_id}"
}

output "model_storage_bucket" {
  description = "Model storage bucket name"
  value       = google_storage_bucket.model_storage.name
}

output "service_account_email" {
  description = "Cluster service account email"
  value       = google_service_account.cluster_service_account.email
}

output "deployment_instructions" {
  description = "Quick deployment instructions"
  value = <<-EOT
    1. Configure kubectl: ${local.kubectl_config_command}
    2. Deploy application: make deploy
    3. Get app URL: kubectl get service ui-service -n munshi-prod -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
  EOT
}

# Local values for internal use
locals {
  kubectl_config_command = "gcloud container clusters get-credentials ${google_container_cluster.cluster.name} --zone=${google_container_cluster.cluster.location} --project=${var.project_id}"
}