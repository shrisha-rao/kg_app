# Outputs for easy access to deployment information.
output "cloud_run_url" {
  value = google_cloud_run_v2_service.research_app.uri
}

output "redis_host" {
  value = google_redis_instance.research_cache.host
}






# output "cloud_run_url" {
#   description = "The public URL of the Cloud Run service"
#   value       = google_cloud_run_service.research_app.status[0].url
# }

# output "redis_host" {
#   description = "The internal host address of the Redis instance"
#   value       = google_redis_instance.research_cache.host
# }
