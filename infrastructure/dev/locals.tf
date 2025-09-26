# 🔹 What are locals in Terraform?

# locals let you define reusable constants or computed values in one place.
# They’re great for:

# Versioning names (e.g., index ID)

# Avoiding string duplication

# Keeping configs clean

locals {
  # Versioned IDs
  vertex_index_id = "research-index-v1"

  # Common resource names
  cloud_run_service_name = "research-knowledge-graph-app"
  redis_instance_name    = "research-cache"
  vpc_connector_name     = "research-connector"
}
