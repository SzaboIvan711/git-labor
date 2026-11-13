# Analyse: Rolling Update ohne Ausfall

Für die Aufgabe wurde das Taskboard-Deployment deklarativ auf drei Replikate skaliert. Anschließend wurde ein Rolling Update durchgeführt und die Erreichbarkeit über den NodePort kontinuierlich mit curl überprüft.

Die readinessProbe prüft den Endpunkt /ready. Ein neuer Pod wird erst dann als bereit betrachtet, wenn die Anwendung gestartet ist und ihre benötigten Abhängigkeiten erreichbar sind. Solange diese Prüfung fehlschlägt, wird der Pod nicht als verfügbarer Endpunkt des Services verwendet. Ohne readinessProbe könnte der Service Anfragen an einen Pod weiterleiten, dessen Anwendung noch nicht vollständig gestartet ist.

Die Einstellung maxUnavailable: 0 verhindert, dass während des Rolling Updates die Anzahl verfügbarer Replikate unter drei fällt. Zusammen mit der readinessProbe wartet Kubernetes auf neue, tatsächlich bereite Pods, bevor alte ersetzt werden. Ohne eine aussagekräftige readinessProbe könnte Kubernetes einen noch nicht funktionsfähigen Pod als verfügbar zählen.

Die Anwendung besitzt zwei Prüfendpunkte: /health kontrolliert, ob der Prozess läuft, während /ready zusätzlich die Datenbankverbindung prüft, sofern eine Datenbank konfiguriert ist. Würde die livenessProbe ebenfalls die Datenbank prüfen, könnte eine vorübergehende Datenbankstörung unnötige Neustarts auslösen.

Beim ersten Versuch traten HTTP-Fehler auf. Deshalb wurde ein preStop-Hook mit zehn Sekunden Wartezeit ergänzt, um das Beenden alter Pods besser mit der Aktualisierung der Service-Endpunkte abzustimmen. Beim erneuten Test wurden keine fehlgeschlagenen Anfragen festgestellt.
