resource "google_project_service" "aiplatform" {
  project = var.project_id
  service = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_vertex_ai_feature_store" "research_feature_store" {
  name     = "research-feature-store"
  region   = var.region
  provider = google-beta
  
  depends_on = [google_project_service.aiplatform]
}

resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.research_app.email}"
  
  depends_on = [google_project_service.aiplatform]
}