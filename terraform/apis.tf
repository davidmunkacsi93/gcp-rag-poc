locals {
  required_apis = [
    "aiplatform.googleapis.com",        # Vertex AI — Vector Search, Embeddings, Gemini
    "firestore.googleapis.com",         # Firestore metadata store
    "storage.googleapis.com",           # GCS document store
    "bigquery.googleapis.com",          # BigQuery global metrics
    "sqladmin.googleapis.com",          # Cloud SQL (regional metrics)
    "secretmanager.googleapis.com",     # Secret Manager (DB credentials)
    "compute.googleapis.com",           # Required dependency for Vertex AI
    "run.googleapis.com",               # Cloud Run — service hosting
    "artifactregistry.googleapis.com",  # Artifact Registry — Docker images
    "cloudbuild.googleapis.com",        # Cloud Build — CI/CD pipeline
  ]
}

resource "google_project_service" "required" {
  for_each = toset(local.required_apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
