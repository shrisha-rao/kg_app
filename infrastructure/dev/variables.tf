variable "project_id" {
  description = "The GCP project ID to deploy resources into"
  type        = string
}

variable "region" {
  description = "The GCP region to deploy resources into"
  type        = string
  default     = "us-central1" # override if needed
}

variable "environment" {
  type        = string
  description = "Deployment environment: dev, stage, prod"
}

variable "app_name" {
  type        = string
}

variable "app_version" {
  type        = string
}

variable "arangodb_instance_size" {
  type        = string
  default     = "small"
}

variable "arangodb_host" {
  description = "ArangoDB host URL"
  type        = string
  sensitive   = true
}

variable "arangodb_username" {
  description = "ArangoDB username"
  type        = string
  sensitive   = true
}

variable "arangodb_password" {
  description = "ArangoDB password"
  type        = string
  sensitive   = true
}

variable "arangodb_database" {
  description = "ArangoDB database name"
  type        = string
  default     = "research"
}


variable "redis_memory_size_gb" {
  type        = number
  default     = 1
}

variable "llm_model" {
  type        = string
}

variable "embedding_model" {
  type        = string
}

variable "labels" {
  description = "A map of labels to apply to resources"
  type        = map(string)
  default     = {}
}