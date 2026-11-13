# Terraform Webserver – Woche 7

Dieses Projekt erstellt einen nginx-Webserver mit Terraform und Docker.

## Voraussetzungen

- Docker muss laufen.
- Terraform muss installiert sein.

## Verwendung

terraform init
terraform fmt
terraform validate
terraform plan
terraform apply

Die Webseite ist unter http://localhost:8080 erreichbar.

## Port ändern

terraform apply -var="host_port=8081"

Erlaubte Ports: 1025 bis 65535.

## Aufräumen

terraform destroy
