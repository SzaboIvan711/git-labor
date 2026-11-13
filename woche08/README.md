# Hausaufgabe Woche 08 – Kubernetes

## Skalierung

Die Anwendung wurde deklarativ mit `replicas: 3` im Deployment skaliert.

## Cluster und Deployment

```bash
kind create cluster --config woche08/manifeste/kind-config.yaml
docker build -t taskboard:local ./beispiel-app
kind load docker-image taskboard:local --name taskboard

kubectl apply -f woche08/manifeste/namespace.yaml
kubectl apply -f woche08/manifeste/configmap.yaml
kubectl apply -f woche08/manifeste/deployment.yaml
kubectl apply -f woche08/manifeste/service.yaml
kubectl apply -f woche08/manifeste/service-nodeport.yaml

kubectl -n taskboard rollout status deployment/taskboard
kubectl -n taskboard get pods -o wide
```

## Rolling Update

Neue Version erstellen und in den Cluster laden:

```bash
docker build --build-arg APP_VERSION=2.0.0 -t taskboard:v2 ./beispiel-app
kind load docker-image taskboard:v2 --name taskboard
```

In einem zweiten Terminal vor dem Update kontinuierlich HTTP-Anfragen
an http://localhost:30080/health senden und protokollieren.

```bash
kubectl -n taskboard set image deployment/taskboard taskboard=taskboard:v2
kubectl -n taskboard rollout status deployment/taskboard
```

## Graceful Shutdown

Beim ersten Versuch traten Verbindungsfehler auf. Deshalb wurden
ein preStop-Hook mit zehn Sekunden Wartezeit und
terminationGracePeriodSeconds: 30 ergänzt.

Der erfolgreiche Test wurde beim Update von taskboard:v2
auf taskboard:local durchgeführt. Das erste fehlerhafte
Protokoll bleibt zur Dokumentation erhalten.

## Rollback

```bash
kubectl -n taskboard rollout history deployment/taskboard
kubectl -n taskboard rollout undo deployment/taskboard
kubectl -n taskboard rollout status deployment/taskboard
```

## Ergebnisse

- protokoll-scale.txt: drei laufende Pods
- protokoll-rollout.txt: erfolgreicher Rollout ohne HTTP-Fehler
- protokoll-rollout-erster-versuch.txt: erster Versuch mit Fehlern
- protokoll-rollback.txt: erfolgreicher Rollback
- analyse.md: Erklärung der Zero-Downtime-Mechanismen
