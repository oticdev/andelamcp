variable "project_id" {
  description = "The GCP project ID."
  type        = string
}

variable "region" {
  description = "The GCP region where resources will be created."
  type        = string
  default     = "us-central1"
}

variable "repository_id" {
  description = "Artifact Registry Docker repository name."
  type        = string
  default     = "andela-mcp"
}

variable "image_name" {
  description = "Docker image name."
  type        = string
  default     = "fastapi-api"
}

variable "image_tag" {
  description = "Docker image tag to deploy. Must be set explicitly — no default to prevent accidental 'latest' deploys."
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key."
  type        = string
  sensitive   = true
}

variable "openai_model" {
  description = "OpenAI model ID."
  type        = string
  default     = "gpt-4o-mini"
}

variable "mcp_server_url" {
  description = "MCP server URL."
  type        = string
  default     = "https://order-mcp-74afyau24q-uc.a.run.app/mcp"
}

variable "log_level" {
  description = "Application log level."
  type        = string
  default     = "info"
}

variable "backend_cors_origins" {
  description = "JSON array of allowed CORS origins."
  type        = string
  default     = "[]"
}
