terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

resource "docker_image" "nginx" {
  name = "nginx:alpine"
}

resource "docker_container" "webserver" {
  name  = "terraform-nginx"
  image = docker_image.nginx.image_id

  ports {
    internal = 80
    external = var.host_port
  }

  volumes {
    host_path      = "${abspath(path.module)}/index.html"
    container_path = "/usr/share/nginx/html/index.html"
    read_only      = true
  }
}
