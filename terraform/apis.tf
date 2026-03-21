locals {
  required_apis = [
    "aiplatform.googleapis.com",     # Vertex AI — Vector Search, Embeddings, Gemini
    "firestore.googleapis.com",      # Firestore metadata store
    "storage.googleapis.com",        # GCS document store
    "bigquery.googleapis.com",       # BigQuery global metrics
    "sqladmin.googleapis.com",       # Cloud SQL (regional metrics)
    "secretmanager.googleapis.com",  # Secret Manager (DB credentials)
    "compute.googleapis.com",        # Required dependency for Vertex AI
  ]
}

resource "google_project_service" "required" {
  for_each = toset(local.required_apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
