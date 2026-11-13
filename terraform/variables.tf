variable "host_port" {
  description = "Host port for the nginx webserver"
  type        = number
  default     = 8080

  validation {
    condition     = var.host_port > 1024 && var.host_port <= 65535 && floor(var.host_port) == var.host_port
    error_message = "Port must be an integer between 1025 and 65535."
  }
}
