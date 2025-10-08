terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0"
    }
  }
}


# -----------------------------
# Enable Required APIs
# -----------------------------
resource "google_project_service" "firestore_api" {
  project             = var.project_id
  service             = "firestore.googleapis.com"
  disable_on_destroy  = false
}

resource "google_project_service" "vertex_ai_api" {
  project             = var.project_id
  service             = "aiplatform.googleapis.com"
  disable_on_destroy  = false
}

resource "google_project_service" "redis_api" {
  project             = var.project_id
  service             = "redis.googleapis.com"
  disable_on_destroy  = false
}

resource "google_project_service" "vpc_access_api" {
  project             = var.project_id
  service             = "vpcaccess.googleapis.com"
  disable_on_destroy  = false
}

# Add small delays after enabling services (API propagation)
resource "time_sleep" "wait_firestore" {
  depends_on      = [google_project_service.firestore_api]
  create_duration = "60s"
}

resource "time_sleep" "wait_redis" {
  depends_on      = [google_project_service.redis_api]
  create_duration = "60s"
}

# -----------------------------
# Storage Bucket
# -----------------------------
resource "google_storage_bucket" "research_data" {
  name                        = "${var.project_id}-research-data"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
}

# -----------------------------
# Firestore Database
# -----------------------------
# resource "google_firestore_database" "research_db" {
#   name        = "(default)"
#   location_id = var.region
#   type        = "FIRESTORE_NATIVE"
#   depends_on  = [time_sleep.wait_firestore]
# }

# -----------------------------
# Vertex AI Index + Endpoint
# -----------------------------
resource "google_vertex_ai_index" "research_index" {
  display_name = "research-papers-index"
  description  = "Index for research paper embeddings"
  region       = var.region
  depends_on   = [google_project_service.vertex_ai_api]

  metadata {
    contents_delta_uri     = "gs://${google_storage_bucket.research_data.name}/index/contents"
    config {
      dimensions             = 768
      distance_measure_type  = "DOT_PRODUCT_DISTANCE"
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 1000
          leaf_nodes_to_search_percent = 7
        }
      }
      approximate_neighbors_count = 100
    }
  }
}

resource "google_vertex_ai_index_endpoint" "research_index_endpoint" {
  provider     = google-beta
  display_name = "research-papers-index-endpoint"
  description  = "Endpoint for research paper similarity search"
  region       = var.region
  depends_on   = [google_project_service.vertex_ai_api]
}



resource "google_vertex_ai_index_endpoint_deployed_index" "research_deployed_index" {
  provider          = google-beta
  index             = google_vertex_ai_index.research_index.id
  index_endpoint    = google_vertex_ai_index_endpoint.research_index_endpoint.id
  # deployed_index_id = "research_deployed_index"   # ✅ underscore instead of hyphens
  deployed_index_id = local.deployed_index_id
  display_name      = "research-deployed-index"
  depends_on        = [google_vertex_ai_index_endpoint.research_index_endpoint]

  automatic_resources {
    min_replica_count = 1
    max_replica_count = 1
  }
}

# -----------------------------
# Redis (Memorystore)
# -----------------------------
resource "google_redis_instance" "research_cache" {
  name                 = local.redis_instance_name
  tier                 = "BASIC"
  memory_size_gb       = 1
  region               = var.region
  redis_version        = "REDIS_6_X"
  display_name         = "Research app cache"
  authorized_network   = "projects/${var.project_id}/global/networks/default"
  depends_on           = [time_sleep.wait_redis, google_project_service.vpc_access_api]

  maintenance_policy {
    weekly_maintenance_window {
      day = "SATURDAY"
      start_time {
        hours   = 0
        minutes = 30
      }
    }
  }
}

# -----------------------------
# VPC Connector
# -----------------------------

resource "google_vpc_access_connector" "serverless_connector" {
  name          = local.vpc_connector_name
  region        = var.region
  network       = "default"
  ip_cidr_range = "10.8.0.0/28"
  depends_on    = [google_project_service.vpc_access_api]


  min_instances = 2
  max_instances = 3


  # # ✅ must define throughput or instance scaling
  # min_throughput = 200
  # max_throughput = 300
}

# -----------------------------
# Service Account
# -----------------------------
resource "google_service_account" "research_app" {
  account_id   = "research-app"
  display_name = "Research Knowledge Graph Application"
}

# IAM Roles
resource "google_project_iam_member" "research_app_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.research_app.email}"
}

resource "google_project_iam_member" "research_app_storage" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.research_app.email}"
}

resource "google_project_iam_member" "research_app_redis" {
  project = var.project_id
  role    = "roles/redis.editor"
  member  = "serviceAccount:${google_service_account.research_app.email}"
}

# -----------------------------
# Cloud Router & NAT for outbound internet access
# -----------------------------
resource "google_compute_router" "nat_router" {
  name    = "nat-router"
  region  = var.region
  network = "default"
}

resource "google_compute_router_nat" "nat_config" {
  name                               = "nat-config"
  router                             = google_compute_router.nat_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}


# -----------------------------
# Cloud Run (v2)
# -----------------------------
resource "google_cloud_run_v2_service" "research_app" {
  name     = local.cloud_run_service_name
  location = var.region
  deletion_protection = false
  depends_on = [google_vpc_access_connector.serverless_connector]

  template {
    containers {
      image = "gcr.io/${var.project_id}/research-app:latest"
      ports {
        container_port = 8080
      }
      
      # # Override the CMD temporarily for testing
      # command = ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]


      # ADD MEMORY LIMIT:
      resources {
        limits = {
          memory = "1Gi"  # Increase from 512Mi to 1Gi
        }
      }      
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.research_data.name
      }
      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.research_cache.host
      }
      env {
        name  = "USE_MOCK_SERVICES"
	  value = "false"
      }
      env {
      	name  = "USE_OLLAMA" 
	value = "false"
      }
      env {
        name  = "ARANGODB_HOST"
	value = var.arangodb_host
      }
      env {
        name  = "ARANGODB_USERNAME"
	value = var.arangodb_username
      }
      env {
        name  = "ARANGODB_PASSWORD"
	value = var.arangodb_password
	}
      env {
      	name = "ARANGODB_DATABASE"
	value = var.arangodb_database
        }
      env {
      	name = "VECTOR_DB_TYPE"
	value = var.vector_db_type
        }
      env {
	name  = "VERTEX_AI_INDEX_ID"
	value = google_vertex_ai_index.research_index.id
	}
      env {
	name  = "VERTEX_AI_INDEX_ENDPOINT_ID" 
	value = google_vertex_ai_index_endpoint.research_index_endpoint.id
	}	

    }

    vpc_access {
      connector = google_vpc_access_connector.serverless_connector.id
      egress    = "PRIVATE_RANGES_ONLY" #"ALL_TRAFFIC"
    }

    service_account = google_service_account.research_app.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Public Access
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.research_app.location
  name     = google_cloud_run_v2_service.research_app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}




#######################################################


# terraform {
#   required_providers {
#     google = {
#       source  = "hashicorp/google"
#       version = ">= 5.0"
#     }
#     google-beta = {
#       source  = "hashicorp/google-beta"
#       version = ">= 5.0"
#     }
#   }
# }


# # The Cloud Storage bucket for storing research data.
# resource "google_storage_bucket" "research_data" {
#   name                        = "${var.project_id}-research-data"
#   location                    = var.region
#   force_destroy               = true
#   uniform_bucket_level_access = true
# }
# # Enable the required APIs
# resource "google_project_service" "firestore_api" {
#   project = var.project_id
#   service = "firestore.googleapis.com"
#   disable_on_destroy = false
# }

# resource "google_project_service" "vertex_ai_api" {
#   project = var.project_id
#   service = "aiplatform.googleapis.com"
#   disable_on_destroy = false
# }

# resource "google_project_service" "redis_api" {
#   project = var.project_id
#   service = "redis.googleapis.com"
#   disable_on_destroy = false
# }

# resource "google_project_service" "vpc_access_api" {
#   project = var.project_id
#   service = "vpcaccess.googleapis.com"
#   disable_on_destroy = false
# }

# # The Firestore database for storing graph data.
# resource "google_firestore_database" "research_db" {
#   name        = "(default)"
#   location_id = var.region
#   type        = "FIRESTORE_NATIVE"
#   depends_on  = [google_project_service.firestore_api]
# }

# # The Vertex AI Index for storing and searching vector embeddings.
# resource "google_vertex_ai_index" "research_index" {
#   display_name = "research-papers-index"
#   description  = "Index for research paper embeddings"
#   region       = var.region
#   depends_on = [google_project_service.vertex_ai_api]

#   metadata {
#     contents_delta_uri = "gs://${google_storage_bucket.research_data.name}/index/contents"
#     config {
#       dimensions          = 768
#       distance_measure_type = "DOT_PRODUCT_DISTANCE"
#       algorithm_config {
#         tree_ah_config {
#           leaf_node_embedding_count    = 1000
#           leaf_nodes_to_search_percent = 7
#         }
#       }
#     }
#   }
# }

# # The Vertex AI Index Endpoint.
# resource "google_vertex_ai_index_endpoint" "research_index_endpoint" {
#   provider     = google-beta
#   display_name = "research-papers-index-endpoint"
#   description  = "Endpoint for research paper similarity search"
#   region       = var.region
#   depends_on = [google_project_service.vertex_ai_api]
# }

# # The Memorystore (Redis) instance for caching.
# resource "google_redis_instance" "research_cache" {
#   name                 = local.redis_instance_name
#   tier                 = "BASIC"
#   memory_size_gb       = 1
#   region               = var.region
#   redis_version        = "REDIS_6_X"
#   display_name         = "Research app cache"
#   authorized_network = "projects/${var.project_id}/global/networks/default"
#   depends_on = [google_project_service.redis_api, google_project_service.vpc_access_api]

#   maintenance_policy {
#     weekly_maintenance_window {
#       day = "SATURDAY"
#       start_time {
#         hours   = 0
#         minutes = 30
#       }
#     }
#   }
# }

# # The service account for the application.
# resource "google_service_account" "research_app" {
#   account_id   = "research-app"
#   display_name = "Research Knowledge Graph Application"
# }

# # IAM Bindings for the application's service account.
# resource "google_project_iam_member" "research_app_vertex_ai" {
#   project = var.project_id
#   role    = "roles/aiplatform.user"
#   member  = "serviceAccount:${google_service_account.research_app.email}"
# }

# resource "google_project_iam_member" "research_app_storage" {
#   project = var.project_id
#   role    = "roles/storage.admin"
#   member  = "serviceAccount:${google_service_account.research_app.email}"
# }

# resource "google_project_iam_member" "research_app_redis" {
#   project = var.project_id
#   role    = "roles/redis.editor"
#   member  = "serviceAccount:${google_service_account.research_app.email}"
# }

# # The Serverless VPC Connector for Cloud Run to access private network resources.
# resource "google_vpc_access_connector" "serverless_connector" {
#   name    = local.vpc_connector_name
#   region  = var.region
#   network = "default"
#   depends_on = [google_project_service.vpc_access_api]
# }

# # The Cloud Run V2 service that deploys the application.
# resource "google_cloud_run_v2_service" "research_app" {
#   name     = local.cloud_run_service_name
#   location = var.region
#   depends_on = [google_project_service.vpc_access_api]

#   template {
#     containers {
#       image = "gcr.io/${var.project_id}/research-app:latest"
#       ports {
#         container_port = 8080
#       }
#       env {
#         name  = "GCP_PROJECT_ID"
#         value = var.project_id
#       }
#       env {
#         name  = "GCS_BUCKET_NAME"
#         value = google_storage_bucket.research_data.name
#       }
#       env {
#         name  = "REDIS_HOST"
#         value = google_redis_instance.research_cache.host
#       }
#     }
    
#     vpc_access {
#       connector = google_vpc_access_connector.serverless_connector.id
#       egress    = "ALL_TRAFFIC"
#     }

#     service_account = google_service_account.research_app.email
#   }

#   traffic {
#     type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
#     percent = 100
#   }
# }

# # Makes the Cloud Run service publicly accessible.
# resource "google_cloud_run_v2_service_iam_member" "public_access" {
#   location = google_cloud_run_v2_service.research_app.location
#   name     = google_cloud_run_v2_service.research_app.name
#   role     = "roles/run.invoker"
#   member   = "allUsers"
# }

# # The new resource for deploying the Vertex AI Index to the Endpoint
# resource "google_vertex_ai_index_endpoint_deployed_index" "research_deployed_index" {
#   provider          = google-beta
#   index             = google_vertex_ai_index.research_index.id
#   index_endpoint = google_vertex_ai_index_endpoint.research_index_endpoint.id
#   deployed_index_id = "research_deployed_index_id"
#   display_name      = "research-deployed-index"
#   depends_on        = [google_project_service.vertex_ai_api]

#   automatic_resources {
#     min_replica_count = 1
#     max_replica_count = 1
#   }
# }



#####################################################






# # The Cloud Storage bucket for storing research data.
# resource "google_storage_bucket" "research_data" {
#   name                        = "${var.project_id}-research-data"
#   location                    = var.region
#   force_destroy               = true
#   uniform_bucket_level_access = true
# }

# # The Firestore database for storing graph data.
# resource "google_firestore_database" "research_db" {
#   name        = "(default)"
#   location_id = var.region
#   type        = "FIRESTORE_NATIVE"
# }

# # The Vertex AI Index for storing and searching vector embeddings.
# resource "google_vertex_ai_index" "research_index" {
#   display_name = "research-papers-index"
#   description  = "Index for research paper embeddings"
#   region       = var.region

#   metadata {
#     contents_delta_uri = "gs://${google_storage_bucket.research_data.name}/index/contents"
#     config {
#       dimensions          = 768
#       distance_measure_type = "DOT_PRODUCT_DISTANCE"
#       algorithm_config {
#         tree_ah_config {
#           leaf_node_embedding_count    = 1000
#           leaf_nodes_to_search_percent = 7
#         }
#       }
#     }
#   }
# }

# # The Vertex AI Index Endpoint. The deployed index is now a separate resource.
# resource "google_vertex_ai_index_endpoint" "research_index_endpoint" {
#   provider     = google-beta
#   display_name = "research-papers-index-endpoint"
#   description  = "Endpoint for research paper similarity search"
#   region       = var.region
# }

# # The Memorystore (Redis) instance for caching.
# resource "google_redis_instance" "research_cache" {
#   name                 = local.redis_instance_name
#   tier                 = "BASIC"
#   memory_size_gb       = 1
#   region               = var.region
#   redis_version        = "REDIS_6_X"
#   display_name         = "Research app cache"
#   authorized_network = "projects/${var.project_id}/global/networks/default"

#   maintenance_policy {
#     weekly_maintenance_window {
#       day = "SATURDAY"
#       start_time {
#         hours   = 0
#         minutes = 30
#       }
#     }
#   }
# }

# # The service account for the application.
# resource "google_service_account" "research_app" {
#   account_id   = "research-app"
#   display_name = "Research Knowledge Graph Application"
# }

# # IAM Bindings for the application's service account.
# resource "google_project_iam_member" "research_app_vertex_ai" {
#   project = var.project_id
#   role    = "roles/aiplatform.user"
#   member  = "serviceAccount:${google_service_account.research_app.email}"
# }

# resource "google_project_iam_member" "research_app_storage" {
#   project = var.project_id
#   role    = "roles/storage.admin"
#   member  = "serviceAccount:${google_service_account.research_app.email}"
# }

# resource "google_project_iam_member" "research_app_redis" {
#   project = var.project_id
#   role    = "roles/redis.editor"
#   member  = "serviceAccount:${google_service_account.research_app.email}"
# }

# # The Serverless VPC Connector for Cloud Run to access private network resources.
# resource "google_vpc_access_connector" "serverless_connector" {
#   name    = local.vpc_connector_name
#   region  = var.region
#   network = "default"
# }

# # The Cloud Run V2 service that deploys the application.
# resource "google_cloud_run_v2_service" "research_app" {
#   name     = local.cloud_run_service_name
#   location = var.region

#   template {
#     containers {
#       image = "gcr.io/${var.project_id}/research-app:latest"
#       ports {
#         container_port = 8080
#       }
#       env {
#         name  = "GCP_PROJECT_ID"
#         value = var.project_id
#       }
#       env {
#         name  = "GCS_BUCKET_NAME"
#         value = google_storage_bucket.research_data.name
#       }
#       env {
#         name  = "REDIS_HOST"
#         value = google_redis_instance.research_cache.host
#       }
#     }
    
#     vpc_access {
#       connector = google_vpc_access_connector.serverless_connector.id
#       egress    = "ALL_TRAFFIC"
#     }

#     service_account = google_service_account.research_app.email
#   }

#   traffic {
#     type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
#     percent = 100
#   }
# }

# # Makes the Cloud Run service publicly accessible.
# resource "google_cloud_run_v2_service_iam_member" "public_access" {
#   location = google_cloud_run_v2_service.research_app.location
#   name     = google_cloud_run_v2_service.research_app.name
#   role     = "roles/run.invoker"
#   member   = "allUsers"
# }



# # The new resource for deploying the Vertex AI Index to the Endpoint
# resource "google_vertex_ai_index_endpoint_deployed_index" "research_deployed_index" {
#   provider = google-beta

#   # The ID of the index to be deployed.
#   index = google_vertex_ai_index.research_index.id

#   # The ID of the index endpoint to which the index is deployed.
#   index_endpoint = google_vertex_ai_index_endpoint.research_index_endpoint.id

#   # The ID of the deployed index. This must be a unique, user-provided string.
#   deployed_index_id = "research_deployed_index"
#   display_name      = "research-deployed-index"

#   automatic_resources {
#     min_replica_count = 1
#     max_replica_count = 1
#   }
# }



###################################################
# # The new resource for deploying the Vertex AI Index to the Endpoint
# resource "google_vertex_ai_index_endpoint_deployed_index" "research_deployed_index" {
#   provider          = google-beta
#   index             = google_vertex_ai_index.research_index.id
#   endpoint          = google_vertex_ai_index_endpoint.research_index_endpoint.id
#   deployed_index_id = "research_deployed_index_id"
#   display_name      = "research-deployed-index"

#   automatic_resources {
#     min_replica_count = 1
#     max_replica_count = 1
#   }
# }


# # Cloud Storage Bucket
# resource "google_storage_bucket" "research_data" {
#   name          = "${var.project_id}-research-data"
#   location      = var.region
#   force_destroy = true

#   uniform_bucket_level_access = true
# }

# # Firestore Database
# resource "google_firestore_database" "research_db" {
#   name        = "(default)"
#   location_id = var.region # must be a Firestore-supported region
#   type        = "FIRESTORE_NATIVE"
# }

# # Vertex AI Index
# resource "google_vertex_ai_index" "research_index" {
#   display_name = "research-papers-index"
#   description  = "Index for research paper embeddings"
#   region       = var.region

#   metadata {
#     contents_delta_uri = "gs://${google_storage_bucket.research_data.name}/index/contents"
#     config {
#       dimensions = 768
#       distance_measure_type = "DOT_PRODUCT_DISTANCE"
#       algorithm_config {
#         tree_ah_config {
#           leaf_node_embedding_count = 1000
#           leaf_nodes_to_search_percent = 7
#         }
#       }
#     }
#   }
# }
# # resource "google_vertex_ai_index" "research_index" {
# #   display_name = "research-papers-index"
# #   description  = "Index for research paper embeddings"
# #   region       = var.region

# #   metadata = jsonencode({
# #     contents_delta_uri = "gs://${google_storage_bucket.research_data.name}/index/contents"
# #     config = {
# #       dimensions = 768
# #       distance_measure_type = "DOT_PRODUCT_DISTANCE"
# #       algorithm_config = {
# #         tree_ah_config = {
# #           leaf_node_embedding_count = 1000
# #           leaf_nodes_to_search_percent = 7
# #         }
# #       }
# #     }
# #   })
# # }

# # Vertex AI Index Endpoint (public)
# resource "google_vertex_ai_index_endpoint" "research_index_endpoint" {
#   display_name = "research-papers-index-endpoint"
#   description  = "Endpoint for research paper similarity search"
#   region       = var.region
# }

# # Deploy Index to Endpoint
# resource "google_vertex_ai_index_endpoint_deployed_index" "research_deployed_index" {
#   provider = google-beta
#   index_endpoint     = google_vertex_ai_index_endpoint.research_index_endpoint.id
#   index              = google_vertex_ai_index.research_index.id
#   deployed_index_id  = local.vertex_index_id # "research-index-v1" # stable value
#   display_name       = "research-deployed-index"

#   automatic_resources {
#     min_replica_count = 1
#     max_replica_count = 1
#   }
# }

# # Memorystore (Redis) Instance
# # By default, Memorystore Redis doesn’t enable AUTH,
# # so Cloud Run would connect without a password.
# resource "google_redis_instance" "research_cache" {
#   name           = local.redis_instance_name #"research-cache"
#   tier           = "BASIC"
#   memory_size_gb = 1
#   region         = var.region
#   redis_version  = "REDIS_6_X"
#   display_name   = "Research app cache"

#   authorized_network = "projects/${var.project_id}/global/networks/default"

#   maintenance_policy {
#     weekly_maintenance_window {
#       day = "SATURDAY"
#       start_time {
#         hours   = 0
#         minutes = 30
#       }
#     }
#   }
# }

# # Service Account for Application
# resource "google_service_account" "research_app" {
#   account_id   = "research-app"
#   display_name = "Research Knowledge Graph Application"
# }

# # IAM Bindings
# resource "google_project_iam_member" "research_app_vertex_ai" {
#   project = var.project_id
#   role    = "roles/aiplatform.user"
#   member  = "serviceAccount:${google_service_account.research_app.email}"
# }

# resource "google_project_iam_member" "research_app_storage" {
#   project = var.project_id
#   role    = "roles/storage.admin"
#   member  = "serviceAccount:${google_service_account.research_app.email}"
# }

# resource "google_project_iam_member" "research_app_redis" {
#   project = var.project_id
#   role    = "roles/redis.editor"
#   member  = "serviceAccount:${google_service_account.research_app.email}"
# }

# # Serverless VPC Connector for Cloud Run -> Redis
# resource "google_vpc_access_connector" "serverless_connector" {
#   name   = local.vpc_connector_name # "research-connector"
#   region = var.region
#   network = "default"
# }

# # Cloud Run Service
# resource "google_cloud_run_v2_service" "research_app" {
#   name     = local.cloud_run_service_name # "research-knowledge-graph-app"
#   location = var.region

#   template {
#     spec {
#       containers {
#         image = "gcr.io/${var.project_id}/research-app:latest"
#         ports {
#           container_port = 8080
#         }
#         env {
#           name  = "GCP_PROJECT_ID"
#           value = var.project_id
#         }
#         env {
#           name  = "GCS_BUCKET_NAME"
#           value = google_storage_bucket.research_data.name
#         }
#         env {
#           name  = "REDIS_HOST"
#           value = google_redis_instance.research_cache.host
#         }
#       }

#      vpc_access {
#       connector = google_vpc_access_connector.serverless_connector.id
#       egress    = "ALL_TRAFFIC"
#     }
#       service_account_name = google_service_account.research_app.email
#     }


#   }

#   traffic {
#     percent         = 100
#     latest_revision = true
#   }

#   autogenerate_revision_name = true
# }

# # Make Cloud Run service publicly accessible
# resource "google_cloud_run_service_iam_member" "public_access" {
#   service  = google_cloud_run_service.research_app.name
#   location = google_cloud_run_service.research_app.location
#   role     = "roles/run.invoker"
#   member   = "allUsers"
# }

# # # Outputs
# # output "cloud_run_url" {
# #   value = google_cloud_run_service.research_app.status[0].url
# # }

# # output "redis_host" {
# #   value = google_redis_instance.research_cache.host
# # }







# # terraform {
# #   required_version = ">= 1.0"
# #   required_providers {
# #     google = {
# #       source  = "hashicorp/google"
# #       version = "~> 4.0"
# #     }
# #   }
# # }

# # provider "google" {
# #   project = var.project_id
# #   region  = var.region
# # }

# # # Cloud Storage Bucket
# # resource "google_storage_bucket" "research_data" {
# #   name          = "${var.project_id}-research-data"
# #   location      = var.region
# #   force_destroy = true

# #   uniform_bucket_level_access = true
# # }

# # # Firestore Database
# # resource "google_firestore_database" "research_db" {
# #   name        = "(default)"
# #   location_id = var.region
# #   type        = "FIRESTORE_NATIVE"
# # }

# # # Vertex AI Index
# # resource "google_vertex_ai_index" "research_index" {
# #   display_name = "research-papers-index"
# #   description  = "Index for research paper embeddings"
# #   region       = var.region

# #   metadata = jsonencode({
# #   	   contents_delta_uri = "gs://${google_storage_bucket.research_data.name}/index/contents"
# #   	   config = {
# #     	     dimensions = 768
# #     	     approximate_neighbors_count = 150
# #     	     distance_measure_type = "DOT_PRODUCT_DISTANCE"
# #     	     algorithm_config = {
# #       	       tree_ah_config = {
# #                  leaf_node_embedding_count = 1000
# #              	 leaf_nodes_to_search_percent = 7
# #       		 }
# #     	       }
# #   	     }
# # 	   })

# #   # metadata {
# #   #   contents_delta_uri = "gs://${google_storage_bucket.research_data.name}/index/contents"
# #   #   config {
# #   #     dimensions = 768  # Adjust based on your embedding model
# #   #     approximate_neighbors_count = 150
# #   #     distance_measure_type = "DOT_PRODUCT_DISTANCE"
# #   #     algorithm_config {
# #   #       tree_ah_config {
# #   #         leaf_node_embedding_count = 1000
# #   #         leaf_nodes_to_search_percent = 7
# #   #       }
# #   #     }
# #   #   }
# #   # }


# # }

# # # Vertex AI Index Endpoint
# # resource "google_vertex_ai_index_endpoint" "research_index_endpoint" {
# #   display_name = "research-papers-index-endpoint"
# #   description  = "Endpoint for research paper similarity search"
# #   region       = var.region
# #   network      = "projects/${var.project_id}/global/networks/default"
# # }

# # # Deploy Index to Endpoint
# # resource "google_vertex_ai_index_endpoint" "research_deployed_index" {
# #   index_endpoint = google_vertex_ai_index_endpoint.research_index_endpoint.id
# #   display_name   = "research-deployed-index"
# #   description    = "Deployed index for research papers"
# #   region         = var.region
# #   index          = google_vertex_ai_index.research_index.id
# #   deployed_index {
# #     id = "research_index_${formatdate("YYYYMMDDhhmmss", timestamp())}"
# #   }
# # }

# # # Memorystore (Redis) Instance
# # resource "google_redis_instance" "research_cache" {
# #   name           = "research-cache"
# #   tier           = "BASIC"
# #   memory_size_gb = 1
# #   region         = var.region
# #   redis_version  = "REDIS_6_X"
# #   display_name   = "Research app cache"

# #   maintenance_policy {
# #     weekly_maintenance_window {
# #       day = "SATURDAY"
# #       start_time {
# #         hours   = 0
# #         minutes = 30
# #       }
# #     }
# #   }
# # }

# # # Service Account for Application
# # resource "google_service_account" "research_app" {
# #   account_id   = "research-app"
# #   display_name = "Research Knowledge Graph Application"
# # }

# # # IAM Bindings
# # resource "google_project_iam_member" "research_app_vertex_ai" {
# #   project = var.project_id
# #   role    = "roles/aiplatform.user"
# #   member  = "serviceAccount:${google_service_account.research_app.email}"
# # }

# # resource "google_project_iam_member" "research_app_storage" {
# #   project = var.project_id
# #   role    = "roles/storage.admin"
# #   member  = "serviceAccount:${google_service_account.research_app.email}"
# # }

# # # Cloud Run Service
# # resource "google_cloud_run_service" "research_app" {
# #   name     = "research-knowledge-graph-app"
# #   location = var.region

# #   template {
# #     spec {
# #       containers {
# #         image = "gcr.io/${var.project_id}/research-app:latest"
# #         ports {
# #           container_port = 8080
# #         }
# #         env {
# #           name  = "GCP_PROJECT_ID"
# #           value = var.project_id
# #         }
# #         env {
# #           name  = "GCS_BUCKET_NAME"
# #           value = google_storage_bucket.research_data.name
# #         }
# #         # Add other environment variables as needed
# #       }
# #       service_account_name = google_service_account.research_app.email
# #     }
# #   }

# #   traffic {
# #     percent         = 100
# #     latest_revision = true
# #   }
# # }

# # # Make Cloud Run service publicly accessible
# # resource "google_cloud_run_service_iam_member" "public_access" {
# #   service  = google_cloud_run_service.research_app.name
# #   location = google_cloud_run_service.research_app.location
# #   role     = "roles/run.invoker"
# #   member   = "allUsers"
# # }

# # output "cloud_run_url" {
# #   value = google_cloud_run_service.research_app.status[0].url
# # }

# # output "redis_host" {
# #   value = google_redis_instance.research_cache.host
# # }