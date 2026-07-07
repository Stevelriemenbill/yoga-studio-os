# Studio Operating System

Mandantenfähige SaaS-Plattform für Yogastudios: Kursverwaltung, Mitglieder,
Buchungen mit intelligenter Warteliste, QR-Check-in & Anwesenheit,
Ausbildungsmodul, Benachrichtigungen mit Smart Reminders, Analytics,
Kundenbindungs-Automatisierungen, KI-Prognosen & -Assistent, Event-/Retreat-
Modul sowie eine öffentliche API mit Webhooks und White-Label-Branding.

## Tech-Stack

| Bereich        | Technologie |
|----------------|-------------|
| Backend        | FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, PostgreSQL |
| Auth           | JWT (Access + Refresh), bcrypt, mandantenfähig |
| Background     | ARQ Worker (Redis) für Notifications, Automations, Insights |
| Realtime       | WebSockets + Redis Pub/Sub (Tenant-scoped Live-Updates) |
| Frontend       | Vue 3, TypeScript, Vite, Pinia, Vue Router, PrimeVue |
| Observability  | Prometheus (`/metrics`), Grafana, optional Sentry |
| Infra          | Docker Compose (dev) + Prod-Overlay mit Traefik |

## Projektstruktur

```
backend/
  app/
    api/v1/     Router: auth, members, courses, rooms, sessions, bookings,
                waitlist, checkin, attendance, training, notifications,
                analytics, automations, ai, events, integrations, realtime (ws)
    core/       Config, Security (JWT), Events (WebSocket + Redis Pub/Sub)
    db/         Base, Session, portabler GUID-Typ (Postgres/SQLite), Repository
    models/     ORM-Modelle (17+ Tabellen inkl. Integrations)
    schemas/    Pydantic-Schemas
    services/   Business-Logik (booking, waitlist, scoring, notification,
                analytics, automation, ai, event, integrations, ...)
    worker.py   ARQ Worker (Cron-Jobs)
    main.py     App-Factory (Lifespan, CORS, Metrics)
  alembic/      Migrationen (3 Revisions)
  tests/        Pytest (39 Tests, SQLite in-memory)
  entrypoint.sh Wartet auf DB -> Migrationen -> startet API
  Dockerfile
frontend/
  src/
    api/          Getypte Axios-Clients pro Modul (+ Token-Refresh)
    composables/  useRealtime (WebSocket, Auto-Reconnect)
    stores/       Pinia Auth-Store
    router/       Vue Router mit Auth-Guard
    views/        Dashboard + je ein View pro Modul
    layouts/      AppLayout (Sidebar-Navigation)
  Dockerfile
docker-compose.yml        Dev-Setup: db + redis + backend + worker + frontend
docker-compose.prod.yml   Overlay: Traefik + Prometheus + Grafana
infra/                    Prometheus- & Grafana-Konfiguration
```

## Lokales Docker-Setup

Voraussetzung: **Docker** mit Docker Compose v2 (`docker compose ...`).

### 1. Umgebungsvariablen vorbereiten

Für das reine Docker-Setup brauchst du keine `.env` – Compose setzt sinnvolle
Defaults. Es empfiehlt sich aber, einen eigenen `SECRET_KEY` zu setzen. Lege
dazu im Projekt-Root eine `.env` an (die Compose automatisch liest):

```bash
# .env im Projekt-Root
SECRET_KEY=$(openssl rand -hex 32)
```

> Alternativ kannst du `SECRET_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD` und
> `POSTGRES_DB` als Shell-Variablen exportieren – Compose übernimmt sie via
> `${VAR:-default}`.

### 2. Starten

```bash
docker compose up --build
```

Das startet fünf Container:

| Service    | Beschreibung                                            | Port  |
|------------|---------------------------------------------------------|-------|
| `db`       | PostgreSQL 16                                           | 5432  |
| `redis`    | Redis 7 (Worker-Queue + WebSocket Pub/Sub)             | 6379  |
| `backend`  | FastAPI-API (wartet auf DB, führt Migrationen aus)     | 8000  |
| `worker`   | ARQ Background-Worker (Cron-Jobs)                       | –     |
| `frontend` | Vue-Dev-Server (Vite)                                   | 5173  |

Ablauf beim ersten Start:

1. `db` und `redis` starten und werden über Healthchecks als „ready“ gemeldet.
2. `backend` wartet via `entrypoint.sh` auf die DB, führt `alembic upgrade head`
   aus und startet danach `uvicorn`.
3. `worker` verbindet sich mit Redis und beginnt, die Cron-Jobs abzuarbeiten.
4. `frontend` startet Vite und ist unter Port 5173 erreichbar.

### 3. Aufrufen

- **Frontend (App):** http://localhost:5173
- **API-Docs (Swagger):** http://localhost:8000/docs
- **OpenAPI-Schema:** http://localhost:8000/api/v1/openapi.json
- **Healthcheck:** http://localhost:8000/health
- **Metrics (Prometheus):** http://localhost:8000/metrics

### 4. Erstes Studio anlegen

Im Frontend auf **Registrieren** gehen oder per curl:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "studio_name": "Zen Flow",
    "studio_slug": "zen-flow",
    "admin_email": "admin@zenflow.example.com",
    "admin_password": "supersecret1",
    "admin_full_name": "Alex"
  }'
```

Danach im Frontend mit `tenant_slug` = `zen-flow`, E-Mail und Passwort einloggen.

### 5. Nützliche Befehle

```bash
# Im Hintergrund starten
docker compose up --build -d

# Logs verfolgen (alle oder einzelner Service)
docker compose logs -f
docker compose logs -f backend worker

# Nur einzelne Services starten (z.B. für lokale Backend-Entwicklung)
docker compose up -d db redis

# Migrationen manuell im Backend-Container ausführen
docker compose exec backend alembic upgrade head

# Neue Migration erzeugen (nach Modelländerung)
docker compose exec backend alembic revision --autogenerate -m "beschreibung"

# Tests im Backend-Container laufen lassen
docker compose exec backend pytest

# Container stoppen (Daten bleiben erhalten)
docker compose down

# Container stoppen UND Volumes (DB-Daten) löschen -> frischer Start
docker compose down -v
```

Der Code ist per Volume gemountet (`./backend` bzw. `./frontend`), d.h.
Änderungen werden dank `--reload` (Uvicorn) und Vite-HMR sofort übernommen.
Nach Änderungen an `pyproject.toml` oder `package.json` ist ein
`docker compose up --build` nötig.

### Troubleshooting

- **`backend` startet nicht / bleibt bei „db not ready“:** Warten – der
  Healthcheck kann beim ersten Start einige Sekunden brauchen. Prüfe
  `docker compose logs db`.
- **Port belegt (5432/6379/8000/5173):** Stoppe lokale Postgres-/Redis-Instanzen
  oder passe die Port-Mappings in `docker-compose.yml` an.
- **Worker verarbeitet nichts:** Er läuft über Cron (Notifications minütlich,
  Automations stündlich, Insights täglich). Zum sofortigen Auslösen die API
  nutzen (`POST /api/v1/notifications/process`, `POST /api/v1/automations/run`).

## Lokale Entwicklung ohne Docker

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Infrastruktur (Postgres + Redis) via Docker bereitstellen:
docker compose up -d db redis

cp .env.example .env      # SECRET_KEY anpassen!
alembic upgrade head
uvicorn app.main:app --reload
```

Optional den Worker separat starten:

```bash
arq app.worker.WorkerSettings
```

Tests nutzen SQLite in-memory und benötigen weder DB noch Redis:

```bash
cd backend
pytest
ruff check app tests      # Linting
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # Typecheck (vue-tsc) + Produktions-Build
```

## Produktions-Overlay (Traefik + Monitoring)

Das Overlay ergänzt Reverse-Proxy (TLS via Let's Encrypt) und Monitoring:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Zusätzliche Services: **Traefik** (Ports 80/443), **Prometheus** (9090),
**Grafana** (3000, Login `admin` / `${GRAFANA_PASSWORD}`). Hosts (`API_HOST`,
`APP_HOST`), `ACME_EMAIL` und `GRAFANA_PASSWORD` via Umgebung/`.env` setzen.

## Umgebungsvariablen (Backend)

| Variable                  | Default                        | Beschreibung |
|---------------------------|--------------------------------|--------------|
| `SECRET_KEY`              | `change-me-...`                | JWT-Signatur – in Prod ändern! |
| `POSTGRES_*`              | `studio` / `studio_os`         | DB-Verbindung |
| `DATABASE_URL`            | –                              | Kompletter Override (z.B. SQLite) |
| `REDIS_URL`               | `redis://localhost:6379/0`     | Worker + Pub/Sub |
| `REDIS_ENABLED`           | `true`                         | Redis-Features abschaltbar (Tests) |
| `METRICS_ENABLED`         | `true`                         | Prometheus `/metrics` |
| `SENTRY_DSN`              | –                              | Optionales Error-Tracking |
| `BACKEND_CORS_ORIGINS`    | `http://localhost:5173,...`    | Erlaubte Origins (kommagetrennt) |

## Wichtige API-Endpunkte

Vollständige Referenz: http://localhost:8000/docs. Basis-Prefix: `/api/v1`.

| Bereich          | Beispiele |
|------------------|-----------|
| Auth             | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` |
| Mitglieder       | `GET/POST /members`, `PATCH/DELETE /members/{id}` |
| Kurse/Termine    | `GET/POST /courses`, `POST /courses/{id}/sessions`, `GET/POST /rooms` |
| Buchungen        | `POST /bookings`, `POST /bookings/{id}/cancel`, `POST /waitlist` |
| Check-in         | `GET /checkin/pass/{member_id}`, `POST /checkin/qr`, `POST /checkin/manual` |
| Ausbildung       | `POST /training/hours`, `GET /training/dashboard/{trainee_id}` |
| Benachrichtigungen | `POST /notifications`, `POST /notifications/process`, `POST /notifications/reminders` |
| Analytics        | `GET /analytics/kpis`, `/heatmap`, `/teachers`, `/popular-courses` |
| Automatisierung  | `GET/POST /automations`, `POST /automations/run` |
| KI               | `GET /ai/insights`, `GET /ai/forecast`, `POST /ai/assistant` |
| Events           | `GET/POST /events`, `POST /events/{id}/register` |
| Integrationen    | `/integrations/api-keys`, `/integrations/webhooks`, `/integrations/branding` |
| Realtime         | `WS /api/v1/ws?token=<access_token>` |

## Multi-Tenant-Konzept

- Jeder Datensatz einer tenant-spezifischen Tabelle erbt `TenantMixin`
  (`tenant_id` FK auf `tenants`, mit Index). Datenzugriff läuft über
  `TenantRepository`, das Queries stets nach `tenant_id` filtert.
- E-Mails sind **pro Tenant** eindeutig (`uq_users_tenant_email`), nicht global.
- `get_current_user` löst Tenant und Rolle aus dem JWT auf und stellt einen
  `CurrentUser`-Kontext bereit. Rollenprüfung über `require_roles(...)` bzw.
  `require_staff`.

## Rollen

`studio_admin`, `studio_manager`, `teacher`, `reception`, `member`, `trainee`
(Yogalehrer in Ausbildung). Staff-Rollen (Admin, Manager, Reception, Teacher)
haben Verwaltungszugriff.
