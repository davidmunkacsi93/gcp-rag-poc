data "google_project" "project" {}

terraform {
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

# ── GCS bucket (Box substitute) ──────────────────────────────────────────────

resource "google_storage_bucket" "documents" {
  name                        = "${var.project_id}-documents-dev"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
}

# ── BigQuery dataset (global metrics) ────────────────────────────────────────

resource "google_bigquery_dataset" "global_metrics" {
  dataset_id = "global_metrics"
  location   = var.region
}

resource "google_bigquery_table" "global_metrics" {
  dataset_id          = google_bigquery_dataset.global_metrics.dataset_id
  table_id            = "global_metrics"
  deletion_protection = false

  schema = jsonencode([
    { name = "id",                type = "INTEGER" },
    { name = "date",              type = "DATE"    },
    { name = "year",              type = "INTEGER" },
    { name = "quarter",           type = "STRING"  },
    { name = "product_line",      type = "STRING"  },
    { name = "region",            type = "STRING"  },
    { name = "revenue_usd",       type = "FLOAT"   },
    { name = "cost_usd",          type = "FLOAT"   },
    { name = "profit_usd",        type = "FLOAT"   },
    { name = "profit_margin_pct", type = "FLOAT"   },
    { name = "yoy_growth_pct",    type = "FLOAT"   },
    { name = "headcount",         type = "INTEGER" },
    { name = "customer_count",    type = "INTEGER" }
  ])
}

# ── Cloud SQL — PostgreSQL (Snowflake substitute) ─────────────────────────────

resource "google_sql_database_instance" "regional" {
  name             = "rag-poc-regional-dev"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    edition           = "ENTERPRISE"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_autoresize   = false

    backup_configuration {
      enabled = false
    }

    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "dev-machine"
        value = "31.46.241.123/32"
      }
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "regional" {
  name     = "regional"
  instance = google_sql_database_instance.regional.name
}

resource "google_sql_user" "rag" {
  name     = "rag"
  instance = google_sql_database_instance.regional.name
  password = var.db_password
}

# ── Secret Manager ────────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "db_password" {
  secret_id = "rag-poc-db-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

# ── Service account ───────────────────────────────────────────────────────────

resource "google_service_account" "ingestion" {
  account_id   = "rag-poc-ingestion"
  display_name = "RAG POC Ingestion Service Account"
}

resource "google_project_iam_member" "ingestion_gcs" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_member" "ingestion_bq" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_member" "ingestion_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_member" "ingestion_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_secret_manager_secret_iam_member" "ingestion_secret" {
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ingestion.email}"
}

# ── Firestore (metadata store) ────────────────────────────────────────────────

resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

resource "google_firestore_index" "documents_status_source_key" {
  project    = var.project_id
  database   = google_firestore_database.default.name
  collection = "documents"

  fields {
    field_path = "status"
    order      = "ASCENDING"
  }
  fields {
    field_path = "source_key"
    order      = "ASCENDING"
  }
  fields {
    field_path = "__name__"
    order      = "ASCENDING"
  }
}

resource "google_project_iam_member" "ingestion_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

# ── Vertex AI Vector Search ───────────────────────────────────────────────────

resource "google_vertex_ai_index" "rag_poc" {
  display_name = "rag-poc-vector-index-dev"
  region       = var.region

  metadata {
    config {
      dimensions                  = 768
      approximate_neighbors_count = 10
      distance_measure_type       = "DOT_PRODUCT_DISTANCE"
      algorithm_config {
        brute_force_config {}
      }
    }
  }

  index_update_method = "STREAM_UPDATE"
}

resource "google_vertex_ai_index_endpoint" "rag_poc" {
  display_name = "rag-poc-index-endpoint-dev"
  region       = var.region
  public_endpoint_enabled = true
}

resource "google_vertex_ai_index_endpoint_deployed_index" "rag_poc" {
  index_endpoint   = google_vertex_ai_index_endpoint.rag_poc.id
  index            = google_vertex_ai_index.rag_poc.id
  deployed_index_id = "rag_poc_index_v1"
}

resource "google_project_iam_member" "ingestion_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

# ── Retrieval service account ─────────────────────────────────────────────────

resource "google_service_account" "retrieval" {
  account_id   = "rag-poc-retrieval"
  display_name = "RAG POC Retrieval Service Account"
}

resource "google_project_iam_member" "retrieval_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.retrieval.email}"
}

resource "google_project_iam_member" "retrieval_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.retrieval.email}"
}

resource "google_project_iam_member" "retrieval_bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.retrieval.email}"
}

resource "google_project_iam_member" "retrieval_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.retrieval.email}"
}

resource "google_project_iam_member" "retrieval_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.retrieval.email}"
}

resource "google_secret_manager_secret_iam_member" "retrieval_secret" {
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.retrieval.email}"
}

# ── Generation service account ────────────────────────────────────────────────

resource "google_service_account" "generation" {
  account_id   = "rag-poc-generation"
  display_name = "RAG POC Generation Service Account"
}

resource "google_project_iam_member" "generation_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.generation.email}"
}

resource "google_project_iam_member" "generation_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.generation.email}"
}

resource "google_artifact_registry_repository" "rag_poc_images" {
  repository_id = "rag-poc-images"
  location      = var.region
  format        = "DOCKER"
  description   = "Docker images for RAG POC services"

  depends_on = [google_project_service.required]
}

# ── Service cloud run instances ────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "retrieval" {
  name     = "retrieval-service"
  location = var.region

  template {
    service_account = google_service_account.retrieval.email

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        limits = {
          memory = "512Mi"
          cpu    = "1"
        }
      }

      ports {
        container_port = 8080
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  depends_on = [
    google_artifact_registry_repository.rag_poc_images,
    google_project_service.required,
  ]
}

resource "google_cloud_run_v2_service" "generation" {
  name     = "generation-service"
  location = var.region

  template {
    service_account = google_service_account.generation.email

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        limits = {
          memory = "512Mi"
          cpu    = "1"
        }
      }

      ports {
        container_port = 8080
      }

      env {
        name  = "RETRIEVAL_SERVICE_URL"
        value = google_cloud_run_v2_service.retrieval.uri
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  depends_on = [
    google_artifact_registry_repository.rag_poc_images,
    google_project_service.required,
  ]
}

resource "google_service_account" "frontend" {
  account_id   = "rag-poc-frontend"
  display_name = "RAG POC Frontend Service Account"
}

resource "google_cloud_run_v2_service" "frontend" {
  name     = "frontend"
  location = var.region

  template {
    service_account = google_service_account.frontend.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        limits = {
          memory = "512Mi"
          cpu    = "1"
        }
      }

      ports {
        container_port = 8501
      }

      env {
        name  = "GENERATION_SERVICE_URL"
        value = google_cloud_run_v2_service.generation.uri
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  depends_on = [
    google_artifact_registry_repository.rag_poc_images,
    google_project_service.required,
  ]
}

# Make the frontend publicly accessible
resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# IAM bindings for service-to-service invocation

resource "google_cloud_run_v2_service_iam_member" "frontend_invokes_generation" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.generation.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.frontend.email}"
}

resource "google_cloud_run_v2_service_iam_member" "generation_invokes_retrieval" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.retrieval.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.generation.email}"
}

# Cloud Build uses the Compute Engine default SA.
# Grant the minimum roles needed to build, push images, and write logs.
locals {
  cloudbuild_sa = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

resource "google_project_iam_member" "cloudbuild_storage" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = local.cloudbuild_sa
}

resource "google_project_iam_member" "cloudbuild_artifact_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = local.cloudbuild_sa
}

resource "google_project_iam_member" "cloudbuild_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = local.cloudbuild_sa
}

resource "google_project_iam_member" "cloudbuild_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = local.cloudbuild_sa
}

