#/infrastructure/modules/firebase/main.tf

resource "google_firebase_project" "research_app" {
  provider = google-beta
  project  = var.project_id
}

resource "google_firebase_web_app" "research_app" {
  provider     = google-beta
  project      = var.project_id
  display_name = "Research Knowledge Graph App"

  depends_on = [google_firebase_project.research_app]
}

resource "google_identity_platform_config" "auth_config" {
  provider   = google-beta
  project    = var.project_id
  authorized_domains = ["your-domain.com", "localhost", "127.0.0.1"]
  
  depends_on = [google_firebase_project.research_app]
}

resource "google_project_iam_member" "firebase_admin" {
  project = var.project_id
  role    = "roles/firebaseauth.admin"
  member  = "serviceAccount:${google_service_account.research_app.email}"
}