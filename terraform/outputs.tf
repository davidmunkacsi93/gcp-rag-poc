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

output "retrieval_service_account" {
  value = google_service_account.retrieval.email
}

output "vector_search_index_id" {
  value = google_vertex_ai_index.rag_poc.id
}

output "vector_search_endpoint_id" {
  value = google_vertex_ai_index_endpoint.rag_poc.id
}

output "generation_service_account" {
  value = google_service_account.generation.email
}

output "frontend_service_account" {
  value = google_service_account.frontend.email
}

output "artifact_registry_repository" {
  value = google_artifact_registry_repository.rag_poc_images.name
}

output "retrieval_service_url" {
  value = google_cloud_run_v2_service.retrieval.uri
}

output "generation_service_url" {
  value = google_cloud_run_v2_service.generation.uri
}

output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}
