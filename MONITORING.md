# MONITORING.md – Taskboard

Datum: 13.11.2026 · App-Version: `1.0.0` · Umgebung: lokaler Docker-Compose-Stack mit Prometheus und Grafana

## 1 – Dashboard-Dokumentation

Die Beobachtungen stammen aus dem eigenen Lauf mit `bash code/last-erzeugen.sh http://localhost:8000 200`. Das Skript sendet erfolgreiche API- und Health-Anfragen sowie absichtlich erzeugte HTTP-404-Antworten. Die folgenden Eingriffsschwellen sind Vorschläge für diesen Testbetrieb, keine produktiv validierten Grenzwerte.

### Panel 1 – Request-Rate (req/s)

| Feld | Inhalt |
| --- | --- |
| Metrik | `flask_http_request_total` |
| PromQL | `sum(rate(flask_http_request_total[5m]))` |
| Frage | Wie viele HTTP-Anfragen pro Sekunde bearbeitet Taskboard insgesamt? |
| Normalbereich | Im eigenen Test ungefähr 0,02–0,04 req/s ohne Last und zeitweise ca. 2–2,3 req/s während der Lastgenerierung; die Rate hängt stark vom Nutzungsmuster ab. |
| Eingriffsschwelle | Nicht bei einer festen hohen Rate allein alarmieren: Bei erwarteter Last, aber nahezu 0 req/s über 5 Minuten, zunächst Erreichbarkeit und Scrape-Status prüfen; ohne erwarteten Traffic ist 0 normal. |

### Panel 2 – Fehlerrate 5xx (Anteil)

| Feld | Inhalt |
| --- | --- |
| Metrik | `flask_http_request_total` mit Label `status` |
| PromQL | `sum(rate(flask_http_request_total{status=~"5.."}[5m])) / sum(rate(flask_http_request_total[5m]))` |
| Frage | Welcher Anteil der HTTP-Anfragen scheitert mit einem Serverfehler (5xx)? |
| Normalbereich | Erwartet nahe 0 %, weil der Lastgenerator normale Anfragen und absichtliche 404-, aber keine gezielten 5xx-Antworten erzeugt; im Dashboard erschien „No data“, daher ist 0 % **nicht empirisch bestätigt**. Die Abfrage kann bei fehlenden 5xx-Zeitreihen leer bleiben. |
| Eingriffsschwelle | Über 5 % bei ausreichendem Traffic für 5 Minuten: Nutzer erleben wiederholt Serverfehler; zunächst Zähler und Logs prüfen. |

### Panel 3 – p95-Latenz (s)

| Feld | Inhalt |
| --- | --- |
| Metrik | `flask_http_request_duration_seconds_bucket` |
| PromQL | `histogram_quantile(0.95, sum by (le) (rate(flask_http_request_duration_seconds_bucket[5m])))` |
| Frage | Wie lange dauern 95 % der HTTP-Anfragen höchstens (geschätzt)? |
| Normalbereich | Im eigenen Lauf etwa 0,0047 s (4,7 ms) im ruhigen Betrieb und bis ungefähr 0,0085 s (8,5 ms) unter Testlast; das Histogramm liefert eine Schätzung. |
| Eingriffsschwelle | p95 über 0,3 s für mindestens 5 Minuten untersuchen, weil das deutlich über dem gemessenen Bereich liegt und interaktive Nutzung spürbar verzögern kann. |

### Panel 4 – Version (taskboard_info)

| Feld | Inhalt |
| --- | --- |
| Metrik | `taskboard_info` mit Label `version` |
| PromQL | `taskboard_info` |
| Frage | Welche Anwendungsversion meldet die laufende Taskboard-Instanz? |
| Normalbereich | Im eigenen Lauf `1.0.0`, passend zum `APP_VERSION` im Compose-Stack; der Zahlenwert der Info-Metrik selbst ist typischerweise 1. |
| Eingriffsschwelle | Bei Abweichung von der geplanten Release-Version oder unerwartetem Versionswechsel sofort Deployment und Rollout prüfen; es gibt keinen sinnvollen numerischen Grenzwert. |

### Panel 5 – p95-Latenz (eigenes Panel)

| Feld | Inhalt |
| --- | --- |
| Metrik | `flask_http_request_duration_seconds_bucket` |
| PromQL | `histogram_quantile(0.95, sum by (le) (rate(flask_http_request_duration_seconds_bucket[5m])))` |
| Frage | Bestätigt das selbst angelegte Panel denselben p95-Latenzverlauf wie das vorinstallierte Panel? |
| Normalbereich | Identisch mit Panel 3: im eigenen Lauf ungefähr 4,7–8,5 ms; beide Panels verwenden dieselbe Abfrage und denselben Datenbestand. |
| Eingriffsschwelle | Bei p95 über 0,3 s für 5 Minuten reagieren; bei unterschiedlichen Kurven der beiden Panels zuerst Zeitbereich, Datenquelle und Query-Konfiguration vergleichen. |

## 2 – SLOs mit Error Budget

### SLO 1 – Verfügbarkeit / serverseitige Fehlerrate

- **SLI:** Anteil der HTTP-Anfragen ohne 5xx-Status, ermittelt aus `flask_http_request_total` und dessen `status`-Label: `1 - (sum(increase(flask_http_request_total{status=~"5.."}[30d])) / sum(increase(flask_http_request_total[30d])))`. Voraussetzung: tatsächlich vorhandener Traffic; ohne Requests ist die Quote nicht definiert.
- **SLO:** Mindestens **99,9 %** aller HTTP-Anfragen liefern über ein rollierendes 30-Tage-Fenster keinen 5xx-Status. HTTP 4xx zählen in dieser Definition nicht als Serverfehler.
- **Error Budget:** `100 % - 99,9 % = 0,1 %`. Bei beispielsweise 100.000 Requests in 30 Tagen sind `100.000 × 0,001 = 100` Requests mit 5xx erlaubt. Als reine zeitbasierte Vergleichsgrösse entsprächen 0,1 % von `30 × 24 × 60 = 43.200 min` genau **43,2 Minuten**; da dieser SLI requestbasiert ist, ist die tatsächlich massgebliche Einheit **Fehl-Requests**, nicht Ausfallminuten.
- **Begründung:** Für ein kleines Taskboard ist hohe Zuverlässigkeit sinnvoll; ein Ziel unter 100 % lässt Spielraum für Wartung, kurzzeitige Fehler und Verbesserungen.

### SLO 2 – Latenz

- **SLI:** Anteil aller HTTP-Anfragen mit Antwortzeit **≤ 0,3 s**, gemessen anhand des Histogramms `flask_http_request_duration_seconds_bucket`. Eine genaue Grenze bei 0,3 s setzt einen passenden Bucket voraus; andernfalls müssen Buckets bzw. Instrumentierung angepasst werden. Die vorhandene p95-Abfrage liefert zunächst eine geschätzte Kontrollgrösse.
- **SLO:** Mindestens **95 %** aller HTTP-Anfragen sollen über ein rollierendes 30-Tage-Fenster höchstens 300 ms dauern.
- **Error Budget:** `100 % - 95 % = 5 %`. Bei beispielsweise 100.000 Requests dürfen `100.000 × 0,05 = 5.000` Requests länger als 300 ms dauern. Die Berechnung ist requestbasiert, nicht in Minuten.
- **Begründung:** 300 ms liegt deutlich über den im Labor beobachteten ca. 5–9 ms und lässt Reserven für Lastspitzen, ohne langsame Nutzererlebnisse dauerhaft zu akzeptieren.

## 3 – Eigene symptombasierte Alarmregel

Die Regel ist zusätzlich zu `TaskboardDown`, `HighErrorRate` und `HighLatencyP95` gedacht. Sie erkennt eine ungewöhnlich hohe Quote nicht gefundener Ressourcen (404), beispielsweise durch kaputte Links oder fehlerhafte API-Pfade.

```yaml
groups:
  - name: taskboard-custom
    rules:
      - alert: HighNotFoundRate
        expr: |
          (
            sum(rate(flask_http_request_total{status="404"}[5m]))
            /
            clamp_min(sum(rate(flask_http_request_total[5m])), 0.001)
          ) > 0.30
          and
          sum(rate(flask_http_request_total[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Viele Taskboard-Anfragen enden mit HTTP 404"
          description: "Mehr als 30 % der Anfragen liefern seit 5 Minuten HTTP 404; aktuelle Quote: {{ $value | humanizePercentage }}."
```

**Begründung:** Viele 404-Antworten können auf ein für Nutzer sichtbares Problem nach einem Release hindeuten. Die Schwelle von 30 % ist ein vorläufiger Laborwert; das Lastskript erzeugt selbst absichtliche 404-Antworten. Die Mindest-Request-Rate vermeidet Alarme aufgrund weniger Einzelanfragen. `for: 5m` reduziert kurzzeitige Fehlalarme. Vor Produktion muss die Schwelle mit echtem Nutzertraffic kalibriert werden.

**Runbook-Skizze:**
1. Im Grafana-Dashboard und in Prometheus prüfen, ob die 404-Quote und die Gesamt-Request-Rate tatsächlich erhöht sind.
2. In den HTTP-Logs die betroffenen Pfade, Zeitpunkte und Clients ermitteln; Testtraffic von echten Nutzern unterscheiden.
3. Prüfen, ob ein neues Deployment, geänderte API-Routen oder defekte Links mit dem Anstieg zusammenfallen.
4. Fehlende Routen bzw. Links korrigieren oder bei einem fehlerhaften Release einen Rollback erwägen.
5. Nach der Korrektur die Quote mindestens 5–10 Minuten beobachten und den Vorfall dokumentieren.

## 4 – Trivy-Auswertung

Scan: `trivy image taskboard:local` am **13.11.2026**. Die folgenden drei unterschiedlichen CVEs gehören zu den vom Scan ausgegebenen HIGH-Funden. „Fixed Version: keine angegeben“ bedeutet, dass Trivy für die installierte Paketversion keine konkrete Fix-Version meldet; daraus folgt nicht, dass es grundsätzlich keine Abhilfe gibt.

### Fund 1 – CVE-2025-69720

- **Paket:** `libncursesw6` (auch andere ncurses-Pakete betroffen); **Severity:** HIGH; **Installed Version:** `6.5+20250216-2`; **Fixed Version:** keine angegeben.
- **Beschreibung und Kontext:** Laut Scan liegt ein Stack-Buffer-Overflow im Kommandozeilentool `infocmp` vor. Taskboard stellt eine Flask-basierte HTTP-API bereit; die durchgeführte Quelltextsuche in `beispiel-app/app/` fand keine direkten Aufrufe von `infocmp`, `subprocess` oder `os.system`. Eine HTTP-Eingabe erreicht die betroffene Funktion nach den geprüften Aufrufpfaden daher nicht erkennbar. Die Ausnutzbarkeit über die Web-API erscheint **gering**, ist damit aber nicht vollständig ausgeschlossen.
- **Empfehlung:** Sicherheitsupdates des Basisimages bzw. der Distribution beobachten und zeitnah einspielen; kein pauschaler `.trivyignore`-Eintrag ohne dokumentierte Ausnahme.

### Fund 2 – CVE-2026-9538

- **Paket:** `perl-base`; **Severity:** HIGH; **Installed Version:** `5.40.1-6+deb13u1`; **Fixed Version:** keine angegeben.
- **Beschreibung und Kontext:** Der Scan beschreibt möglichen Speicherverbrauch durch manipulierte TAR-Header in Perls `Archive::Tar`. Die Taskboard-API verarbeitet Aufgaben und Gesundheitsanfragen; die Quelltextsuche fand in `beispiel-app/app/` keine direkten TAR-Verarbeitungsaufrufe oder Shell-Ausführung. Eine über HTTP hochgeladene, mit Perl entpackte TAR-Datei ist im geprüften Anwendungspfad nicht ersichtlich. Deshalb erscheint die direkte Ausnutzbarkeit **gering**, sofern keine indirekten Aufrufpfade bestehen.
- **Empfehlung:** Paket- und Basisimage-Updates beobachten; nicht allein wegen des HIGH-Scores die App als unmittelbar angreifbar einstufen. Keine unbegründete Ignorierung.

### Fund 3 – CVE-2026-76642

- **Paket:** `bsdutils`; **Severity:** HIGH; **Installed Version:** `1:2.41.5-0+deb13u1`; **Fixed Version:** keine angegeben.
- **Beschreibung und Kontext:** Laut Scan betrifft die Schwachstelle die Prüfung des Exit-Status eines Mount-Helfers vor der Ausführung von Post-Mount-Hooks und kann unter bestimmten Voraussetzungen lokale Privilegieneskalation ermöglichen. Taskboard führt HTTP-Anfragen als `appuser` (UID 10001) aus (`USER appuser` im Dockerfile). Die Quelltextsuche fand keine direkten `mount`-Aufrufe. Damit ist die Schwachstelle nicht unmittelbar über die bekannten HTTP-Endpunkte erreichbar. **Wichtig:** `appuser` verhindert eine lokale Privilegieneskalation nicht automatisch; Mount-Rechte, Container-Capabilities und tatsächliche Ausnutzungsbedingungen müssten gesondert geprüft werden.
- **Empfehlung:** **Priorisiert beobachten und beheben**, sobald ein geeignetes Paket- oder Basisimage-Update verfügbar ist; Container-Rechte minimal halten und keine unnötigen Mount-Privilegien vergeben. Nicht ignorieren.

## Nachweise

- `taskboard-overview.json` – exportiertes Dashboard mit fünf Panels, inklusive selbst angelegtem p95-Panel.
- `dashboard.png` – Dashboard mit Messdaten.
- `alert-firing.png` – Prometheus-Alarm `TaskboardDown` im Zustand **Firing**.

**Hinweis:** Die Screenshots müssen tatsächlich im Repository abgelegt werden; ihre Existenz wird durch dieses Dokument nicht ersetzt.
