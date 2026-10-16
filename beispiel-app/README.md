# Taskboard – Beispielanwendung

Die durchgehende Referenzanwendung des Moduls **CDS212 – DevOps**. Ab Woche 3
begleitet sie den gesamten Kurs: Sie wird gebaut, containerisiert, getestet,
deployt, in Kubernetes betrieben und schliesslich überwacht.

Bewusst klein gehalten – eine Aufgabenliste mit REST-API. Interessant ist nicht
die Fachlogik, sondern alles, was um sie herum passiert.

## Schnellstart

```bash
cd beispiel-app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

make run        # http://127.0.0.1:8000
make test       # 21 Tests
make lint       # ruff
```

Ohne `DATABASE_URL` läuft die Anwendung mit einem In-Memory-Speicher – ideal für
Woche 3, wo es noch keine Datenbank gibt. Mit Docker Compose kommt Postgres dazu:

```bash
docker compose up --build     # http://localhost:8000
```

## Endpunkte

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/` | HTML-Oberfläche |
| `GET` | `/health` | Liveness – läuft der Prozess? Ohne Datenbankzugriff |
| `GET` | `/ready` | Readiness – kann die Instanz Anfragen bedienen? Prüft die Datenbank |
| `GET` | `/metrics` | Prometheus-Metriken (Woche 9) |
| `GET` | `/api/tasks` | Alle Aufgaben |
| `POST` | `/api/tasks` | Aufgabe anlegen, Body `{"title": "..."}` |
| `GET` | `/api/tasks/<id>` | Einzelne Aufgabe |
| `PUT` | `/api/tasks/<id>` | Status ändern, Body `{"done": true}` |
| `DELETE` | `/api/tasks/<id>` | Aufgabe löschen |

Ungültige Eingaben beantwortet die API mit `400` und `{"error": "..."}`,
unbekannte IDs mit `404`.

Der Unterschied zwischen `/health` und `/ready` ist keine Spitzfindigkeit: In
Kubernetes (Woche 8) startet die Liveness-Probe den Container neu, wenn sie
fehlschlägt. Würde `/health` die Datenbank prüfen, führte eine langsame Datenbank
zu einer Neustartschleife – und damit zu einem Ausfall, den erst das Monitoring
verursacht hat.

## Konfiguration

Konfiguration kommt aus der Umgebung, nie aus dem Code. Dasselbe Image läuft so
in Entwicklung, CI und Produktion.

| Variable | Standard | Wirkung |
|---|---|---|
| `DATABASE_URL` | *(leer)* | Leer ⇒ In-Memory. Gesetzt ⇒ Postgres |
| `APP_VERSION` | `0.0.0-dev` | Erscheint in `/health` und `/metrics` |
| `LOG_LEVEL` | `INFO` | Log-Schwelle |
| `GUNICORN_WORKERS` | `1` | Anzahl Worker-Prozesse im Container |

Vorlage: `cp .env.example .env`. Die Datei `.env` gehört **nie** ins Repository.

> **Warum nur ein Worker als Standard?** Jeder Gunicorn-Worker ist ein eigener
> Prozess mit eigenem Speicher. Der In-Memory-Speicher wird deshalb *nicht*
> zwischen Workern geteilt: Legt man mit zwei Workern sechs Aufgaben an, sieht
> ein späteres `GET /api/tasks` womöglich nur fünf davon – die sechste liegt im
> Speicher des anderen Prozesses. Sobald `DATABASE_URL` auf Postgres zeigt, ist
> der Zustand geteilt und mehrere Worker sind unbedenklich; `docker-compose.yml`
> setzt darum `GUNICORN_WORKERS: 2`.
>
> Das ist kein Schönheitsfehler, sondern die Miniaturausgabe des Problems, das
> in Woche 8 wiederkehrt: Zustand im Prozess verhindert horizontale Skalierung.

## Aufbau

```
beispiel-app/
├── wsgi.py              Einstiegspunkt für Gunicorn
├── app/
│   ├── __init__.py      create_app() – Application Factory
│   ├── config.py        Konfiguration aus der Umgebung
│   ├── models.py        Task-Datenklasse und Validierung
│   ├── repository.py    Speicher-Abstraktion: In-Memory oder Postgres
│   ├── routes.py        HTTP-Endpunkte
│   ├── templates/       Jinja2-Template der Oberfläche
│   └── static/          Stylesheet
├── tests/               pytest-Suite
├── Dockerfile           Multi-Stage-Build, unprivilegierter Benutzer
├── docker-compose.yml   web + db
└── Makefile             make help zeigt alle Ziele
```

Zwei Entwurfsentscheidungen tragen den ganzen Kurs:

**Application Factory.** `create_app()` nimmt Konfiguration, Repository und
Metrik-Registry als Argumente entgegen. Deshalb kann die Testsuite die App ohne
Datenbank und ohne Umgebungsvariablen aufbauen.

**Repository-Abstraktion.** `routes.py` kennt nur das `TaskRepository`-Protokoll,
nie Postgres. Der Wechsel von In-Memory zu Postgres ist eine Umgebungsvariable,
keine Codeänderung.

## Häufige Make-Ziele

| Befehl | Wirkung |
|---|---|
| `make run` | Entwicklungsserver mit Auto-Reload |
| `make test` | Testsuite |
| `make cov` | Tests mit Abdeckungsbericht (Gate: 80 %) |
| `make lint` | `ruff check` und Formatprüfung |
| `make fmt` | Code automatisch formatieren |
| `make build` | Image `taskboard:local` bauen |
| `make up` / `make down` | Compose-Stack starten/stoppen |
