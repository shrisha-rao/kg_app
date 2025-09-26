provider "google" {
  # No credentials line. Terraform will use gcloud's auth
}

resource "google_project" "research" {
  name                = "Research Graph MVP"
  project_id          = var.project_id
  billing_account     = var.billing_account
  auto_create_network = false
  labels              = var.labels
}







# terraform {
#   required_version = ">= 1.0"
#   required_providers {
#     google = {
#       source  = "hashicorp/google"
#       version = "~> 4.0"
#     }
#   }
# }

# provider "google" {
#   # credentials = file(var.credentials_file) # optional: remove if using ADC
#   # org_id      = var.org_id != "" ? var.org_id : null
# }

# resource "google_project" "research" {
#   name            = "Research Graph MVP"
#   project_id      = var.project_id
#   billing_account = var.billing_account

#   # org_id    = var.org_id != "" ? var.org_id : null
#   # folder_id = var.folder_id != "" ? var.folder_id : null

#   auto_create_network = false
#   labels = var.labels
# }
