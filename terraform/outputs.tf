output "webserver_url" {
  description = "URL of the nginx webserver"
  value       = "http://localhost:${var.host_port}"
}
