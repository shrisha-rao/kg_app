resource "google_vertex_ai_index" "research_index" {
  display_name = "research-papers-index"
  description  = "Index for research paper embeddings"
  region       = var.region
  
  metadata {
    contents_delta_uri = "gs://${var.bucket_name}/index/contents"
    config {
      dimensions = 768  # Must match your embedding dimension
      approximate_neighbors_count = 150
      distance_measure_type = "DOT_PRODUCT_DISTANCE"
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count = 1000
          leaf_nodes_to_search_percent = 7
        }
      }
    }
  }
}

resource "google_vertex_ai_index_endpoint" "research_endpoint" {
  display_name = "research-papers-endpoint"
  description  = "Endpoint for research paper similarity search"
  region       = var.region
  network      = var.network_name
  
  depends_on = [google_vertex_ai_index.research_index]
}

resource "google_vertex_ai_index_endpoint" "research_deployed_index" {
  index_endpoint = google_vertex_ai_index_endpoint.research_endpoint.id
  display_name   = "research-deployed-index"
  description    = "Deployed index for research papers"
  region         = var.region
  index          = google_vertex_ai_index.research_index.id
  
  deployed_index {
    id = "research_index_${formatdate("YYYYMMDDhhmmss", timestamp())}"
  }
}

# IAM permissions for Matching Engine
resource "google_project_iam_member" "matching_engine_admin" {
  project = var.project_id
  role    = "roles/aiplatform.admin"
  member  = "serviceAccount:${google_service_account.research_app.email}"
}

resource "google_project_iam_member" "matching_engine_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.research_app.email}"
}

# Firestore for metadata storage
resource "google_firestore_database" "vector_metadata" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  concurrency_mode = "OPTIMISTIC"
}

# IAM permissions for Firestore
resource "google_project_iam_member" "firestore_admin" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.research_app.email}"
}