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

output "vector_search_index_id" {
  value = google_vertex_ai_index.rag_poc.id
}

output "vector_search_endpoint_id" {
  value = google_vertex_ai_index_endpoint.rag_poc.id
}
