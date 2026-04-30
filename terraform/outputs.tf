output "environment" {
  description = "The active Terraform workspace/environment."
  value       = terraform.workspace
}

output "service_name" {
  description = "The Cloud Run service name."
  value       = google_cloud_run_v2_service.api.name
}

output "service_url" {
  description = "The Cloud Run service URL."
  value       = google_cloud_run_v2_service.api.uri
}

output "image_url" {
  description = "The Docker image URL deployed to Cloud Run."
  value       = local.image_url
}

output "artifact_registry_repository" {
  description = "The Artifact Registry repository name."
  value       = google_artifact_registry_repository.app.name
}
