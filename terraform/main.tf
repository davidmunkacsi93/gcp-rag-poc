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
