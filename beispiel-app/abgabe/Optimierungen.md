# Begründung der Docker-Optimierungen

Bei der Erstellung des Docker-Images wurden mehrere Optimierungen vorgenommen, um die Image-Grösse zu reduzieren und die Sicherheit zu verbessern.

Als Basis-Image wird `python:3.12-slim` verwendet. Dieses enthält nur die notwendigen Bestandteile und ist dadurch deutlich kleiner als ein vollständiges Python-Image.

Durch den Multi-Stage-Build werden die Installation der Abhängigkeiten und die eigentliche Laufzeitumgebung voneinander getrennt. Im Builder-Stage werden die benötigten Python-Pakete installiert. Anschliessend werden nur die installierten Abhängigkeiten in das Runtime-Image übernommen. Dadurch werden unnötige Dateien und Werkzeuge aus dem finalen Image ausgeschlossen.

Auch die Reihenfolge der Dockerfile-Anweisungen spielt eine wichtige Rolle. Die Datei `requirements.txt` wird vor dem Anwendungscode kopiert. Dadurch kann Docker den Layer mit den installierten Abhängigkeiten wiederverwenden, solange sich diese Datei nicht verändert. Das beschleunigt zukünftige Builds.

Mit der Datei `.dockerignore` werden unnötige Dateien wie virtuelle Umgebungen, Cache-Dateien und Git-Daten vom Build-Kontext ausgeschlossen.

Zusätzlich wird ein unprivilegierter Benutzer (`appuser`, UID 10001) verwendet. Die Anwendung läuft dadurch nicht mit Root-Rechten, wodurch mögliche Sicherheitsrisiken reduziert werden.

Das naive Image benötigt **1,67 GB**, während das optimierte Image nur **217 MB** gross ist. Dies entspricht einer Reduktion der Image-Grösse um ungefähr **87 %**. Das optimierte Image ist somit fast **7,7-mal kleiner** als die naive Variante.
