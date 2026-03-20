output "documents_bucket" {
  value = google_storage_bucket.documents.name
}

output "bigquery_dataset" {
  value = google_bigquery_dataset.global_metrics.dataset_id
}

output "cloud_sql_instance" {
  value = google_sql_database_instance.regional.connection_name
}

output "cloud_sql_public_ip" {
  value = google_sql_database_instance.regional.public_ip_address
}

output "ingestion_service_account" {
  value = google_service_account.ingestion.email
}
