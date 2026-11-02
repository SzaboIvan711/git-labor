# Taskboard – Deployment Runbook

Dieses Runbook beschreibt die Installation, das Deployment und die Wiederherstellung des Taskboards.

**Repository:** https://github.com/SzaboIvan711/git-labor  
**Produktiv-URL:** https://taskboard-xm9x.onrender.com

## A. Voraussetzungen

Benötigt werden ein GitHub-Konto mit Repository-Zugriff, ein Render-Konto mit Berechtigung zur Verwaltung von Web Services sowie Ubuntu Linux (oder WSL Ubuntu).

Werkzeuge und Versionsprüfung:

```bash
git --version
python3 --version
python3 -m pip --version
make --version
curl --version
docker --version
```

Getestete Umgebung: Git 2.43.0, Python 3.13.11, pip 25.3, Make 4.3, curl 8.5.0. Docker ist für den lokalen Schnellstart optional.

## B. Lokale Installation

```bash
git clone https://github.com/SzaboIvan711/git-labor.git
cd git-labor/beispiel-app
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
make run
```

In einem zweiten Terminal:

```bash
curl http://127.0.0.1:8000/health
```

Erwartete Antwort:

```json
{"status":"ok","version":"0.0.0-dev"}
```

Die Oberfläche ist unter http://127.0.0.1:8000 erreichbar. Beenden mit `Ctrl+C`. Ohne Datenbank gehen Aufgaben beim Neustart verloren.

## C. Konfigurationsvariablen

| Name | Standardwert | Geheim | Wirkung |
|---|---|---|---|
| `DATABASE_URL` | Nicht gesetzt | Ja, wenn Zugangsdaten enthalten | PostgreSQL-Verbindung; ohne Wert In-Memory |
| `APP_VERSION` | `0.0.0-dev` | Nein | Version in `/health` |
| `LOG_LEVEL` | `INFO` | Nein | Protokollierungsstufe |
| `PORT` | `8000` im Docker-Setup | Nein | HTTP-Port |
| `GUNICORN_WORKERS` | `1` | Nein | Anzahl der Worker-Prozesse |

Passwörter und Tokens niemals committen. Lokal `.env` verwenden und in `.gitignore` ausschliessen. Auf Render sensible Werte unter **Environment**, in GitHub Actions unter **Secrets** speichern.

## D. Deployment auf Render

### Einmalige Einrichtung über das Dashboard

1. Auf https://render.com anmelden.
2. **New → Web Service → Git Provider → GitHub** auswählen.
3. GitHub autorisieren und Repository `SzaboIvan711/git-labor` verbinden.
4. Service konfigurieren:
   - Name: `taskboard` (falls verfügbar)
   - Language/Runtime: **Docker**
   - Branch: `main`
   - Root Directory: `beispiel-app`
   - Dockerfile: `Dockerfile` innerhalb dieses Verzeichnisses
   - Region: Frankfurt
   - Instance Type: Free
   - Health Check Path: `/health`
5. Unter **Environment** setzen:

```text
PORT=8000
GUNICORN_WORKERS=1
APP_VERSION=1.0.0
LOG_LEVEL=INFO
```

`DATABASE_URL` nicht setzen, solange keine PostgreSQL-Datenbank vorhanden ist.

6. **Create Web Service** auswählen und warten, bis Render den Status **Live** zeigt.
7. Die von Render angezeigte HTTPS-Adresse notieren.

### Wiederkehrendes Deployment

Änderungen über Feature-Branch und Pull Request nach `main` mergen. Nach erfolgreichem CI startet der CD-Workflow automatisch den Render Deploy Hook.

Für diese Automatisierung muss in GitHub unter **Settings → Secrets and variables → Actions** Folgendes hinterlegt sein:

- Secret `RENDER_DEPLOY_HOOK`: aus Render → Service → Settings → Deploy Hook
- Variable `APP_URL`: öffentliche HTTPS-Adresse des Services

Der Render Deploy Hook darf niemals im Repository oder in Logs veröffentlicht werden. Für diesen Workflow wird Render Auto-Deploy deaktiviert, damit Deployments über GitHub Actions gesteuert werden.

## E. Verifikation

Öffentliche URL prüfen (bei einer neuen Installation die eigene Render-URL einsetzen):

```bash
APP_URL=https://taskboard-xm9x.onrender.com
curl -i "$APP_URL/health"
```

Erwartet: HTTP `200 OK` und:

```json
{"status":"ok","version":"1.0.0"}
```

Smoke-Test aus dem Repository starten:

```bash
cd beispiel-app
bash tests/smoke-test.sh "$APP_URL"
```

Erwartet werden erfolgreiche Prüfungen von `/health`, `/ready`, `POST /api/tasks`, `GET /api/tasks/1` und `DELETE /api/tasks/1`. Die letzte Zeile muss lauten:

```text
SMOKE TEST PASSED
```

In Render unter **Logs** auf Startmeldungen und Fehler prüfen. Unter **Events** muss das Deployment als erfolgreich angezeigt werden. In GitHub Actions müssen CI und CD grün sein.

## F. Rollback

Bei einem fehlerhaften Deployment:

1. Render Dashboard → Taskboard-Service → **Events** öffnen.
2. Letztes funktionierendes Deployment anhand von Commit und Status identifizieren.
3. Wenn verfügbar, über die Render-Option **Rollback** beziehungsweise **Deploy a specific commit** die funktionierende Version erneut bereitstellen.
4. Warten, bis der Service wieder **Live** ist.
5. `/health` und den Smoke-Test aus Abschnitt E erneut ausführen.
6. Fehlerhaften Commit im Repository korrigieren und per Pull Request nach `main` übernehmen.

**Grenzen:** Ein Code-Rollback stellt keine verlorenen In-Memory-Aufgaben wieder her. Datenbankmigrationen werden nicht automatisch rückgängig gemacht. Bei inkompatiblen Migrationen ist ein separater Wiederherstellungsplan erforderlich.

## G. Troubleshooting

| Symptom | Ursache | Lösung |
|---|---|---|
| Service startet nicht oder antwortet nicht | Falscher Port | `PORT=8000` setzen, Render-Logs prüfen und erneut deployen |
| Health Check schlägt fehl | `/ready` statt `/health`, z. B. bei Datenbankproblemen | Health Check Path auf `/health` setzen |
| Erste Anfrage dauert lange | Cold Start der Free-Instanz | Kurz warten, erneut testen und Logs prüfen |
| Task nach Erstellung nicht auffindbar (`404`) | Mehrere Worker mit getrenntem In-Memory-Speicher | `GUNICORN_WORKERS=1` setzen oder PostgreSQL verwenden |
| CD meldet fehlendes Smoke-Test-Skript | Datei nicht committed oder falscher Pfad | `beispiel-app/tests/smoke-test.sh` ins Repository aufnehmen und Workflow-Pfad prüfen |
| CD schlägt beim Deploy Hook fehl | Secret fehlt oder ist ungültig | `RENDER_DEPLOY_HOOK` in GitHub Secrets kontrollieren |
| Secret erscheint im Log | Versehentliche Ausgabe sensibler Daten | Secret sofort rotieren, Ausgabe entfernen und betroffene Logs/Zugriffe prüfen |

## H. Kontakt und Eskalation

- **Service-Owner:** `<Name/Team>` – zuständig für Anwendung und Repository.
- **Deployment-Verantwortliche:** `<Name/Team>` – zuständig für GitHub Actions und Render.
- **Kommunikationsweg:** GitHub Issue im Repository; bei dringenden Störungen direkter Kontakt zum verantwortlichen Team.
- **Eskalation:** Wenn die Anwendung länger als 30 Minuten nicht verfügbar ist oder ein Rollback scheitert, an Service-Owner und Betriebsverantwortliche eskalieren.
- **Sicherheitsvorfälle:** Bei veröffentlichten Secrets sofort Verantwortliche informieren und betroffene Zugangsdaten rotieren.
