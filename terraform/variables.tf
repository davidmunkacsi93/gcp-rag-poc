variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west1"
}

variable "db_password" {
  description = "Cloud SQL postgres user password"
  type        = string
  sensitive   = true
}
