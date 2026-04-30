terraform {
  required_version = ">= 1.6.0"

  # bucket is supplied via -backend-config="bucket=<name>" in CI.
  # One-time setup: create the bucket manually before the first deploy.
  backend "gcs" {
    prefix = "andela-mcp/state"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  environment  = terraform.workspace
  service_name = "andela-mcp-api-${local.environment}"
  image_url    = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}/${var.image_name}:${var.image_tag}"
}

resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "secretmanager.googleapis.com",
  ])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

resource "google_service_account" "cloud_run_sa" {
  account_id   = "cloud-run-api-${local.environment}"
  display_name = "Cloud Run API SA (${local.environment})"

  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key-${local.environment}"

  replication {
    auto {}
  }

  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "openai_api_key" {
  secret      = google_secret_manager_secret.openai_api_key.id
  secret_data = var.openai_api_key
}

resource "google_secret_manager_secret_iam_member" "cloud_run_sa_accessor" {
  secret_id = google_secret_manager_secret.openai_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_artifact_registry_repository" "app" {
  location      = var.region
  repository_id = var.repository_id
  description   = "Docker repository for Andela MCP FastAPI app"
  format        = "DOCKER"

  depends_on = [google_project_service.services]
}

resource "google_cloud_run_v2_service" "api" {
  name     = local.service_name
  location = var.region

  template {
    service_account = google_service_account.cloud_run_sa.email

    containers {
      image = local.image_url

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        period_seconds    = 30
        failure_threshold = 3
      }

      env {
        name  = "APP_ENV"
        value = local.environment
      }

      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }

      env {
        name  = "BACKEND_CORS_ORIGINS"
        value = var.backend_cors_origins
      }

      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "OPENAI_MODEL"
        value = var.openai_model
      }

      env {
        name  = "MCP_SERVER_URL"
        value = var.mcp_server_url
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }

  depends_on = [
    google_project_service.services,
    google_artifact_registry_repository.app,
    google_secret_manager_secret_iam_member.cloud_run_sa_accessor,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
