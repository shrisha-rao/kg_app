variable "project_id" {
  type        = string
  description = "Unique GCP project id to create"
  sensitive   = true
}

variable "billing_account" {
  type        = string
  description = "Billing account ID to attach to the project"
  sensitive   = true
}

variable "org_id" {
  type        = string
  description = "(optional) Organization ID"
  default     = ""
  sensitive   = true
}

variable "folder_id" {
  type        = string
  description = "(optional) Folder ID"
  default     = ""
  sensitive   = true
}

variable "labels" {
  type        = map(string)
  description = "Labels to apply to the project"
  default     = {}
  sensitive   = false
}

variable "credentials_file" {
  type        = string
  description = "(optional) Path to a service account JSON for provider authentication; remove or leave empty to use Application Default Credentials"
  default     = ""
  sensitive   = true
}
