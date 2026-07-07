# Studio Operating System

Mandantenfähige SaaS-Plattform für Yogastudios (Kursverwaltung, Buchungen,
intelligente Warteliste, Check-in, Analytics, KI). Dieses Repository enthält
das **Fundament**: Multi-Tenant-Architektur, Authentifizierung mit JWT
(Access + Refresh) und Rollen.

## Tech-Stack

| Bereich   | Technologie |
|-----------|-------------|
| Backend   | FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, PostgreSQL |
| Auth      | JWT (Access + Refresh), bcrypt |
| Frontend  | Vue 3, TypeScript, Vite, Pinia, Vue Router, PrimeVue |
| Infra     | Docker Compose (Postgres + Backend + Frontend) |

> Redis, Celery/ARQ, WebSockets und Monitoring werden in späteren Phasen
> ergänzt, sobald die entsprechenden Module (Benachrichtigungen, Background
> Jobs, Live-Updates) implementiert werden.

## Projektstruktur

```
backend/
  app/
    api/        FastAPI-Router & Dependencies (Auth, Rollen, Tenant-Scope)
    core/       Konfiguration & Security (JWT, Passwort-Hashing)
    db/         Base, Session, portable UUID-Typ (Postgres/SQLite)
    models/     ORM-Modelle (Tenant, User + TenantMixin)
    schemas/    Pydantic-Schemas
    services/   Business-Logik (Auth-Service)
    main.py     App-Factory
  alembic/      Migrationen
  tests/        Pytest (Auth-Flow, 12 Tests)
frontend/
  src/
    api/        Axios-Client (Token-Refresh-Interceptor) & Auth-API
    stores/     Pinia Auth-Store
    router/     Vue Router mit Auth-Guard
    views/      Login, Register, Dashboard
    layouts/    AppLayout
docker-compose.yml
```

## Schnellstart mit Docker

```bash
cp backend/.env.example backend/.env   # SECRET_KEY anpassen!
docker compose up --build
```

- Backend: http://localhost:8000  (Docs: http://localhost:8000/docs)
- Frontend: http://localhost:5173
- Postgres: localhost:5432

Der Backend-Container wartet auf die Datenbank und führt automatisch die
Alembic-Migrationen aus (`entrypoint.sh`).

## Lokale Entwicklung

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Datenbank (Postgres) – z.B. via Docker:
docker compose up -d db

cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Tests (nutzen SQLite in-memory, keine Datenbank nötig):

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # Typecheck + Produktions-Build
```

## API – Auth

| Methode | Pfad                    | Beschreibung |
|---------|-------------------------|--------------|
| POST    | `/api/v1/auth/register` | Neues Studio (Tenant) + Admin anlegen |
| POST    | `/api/v1/auth/login`    | Login mit `tenant_slug`, `email`, `password` |
| POST    | `/api/v1/auth/refresh`  | Neue Tokens aus Refresh-Token |
| GET     | `/api/v1/auth/me`       | Aktuellen User abrufen (Bearer-Token) |

Beispiel Registrierung:

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

## Multi-Tenant-Konzept

- Jeder Datensatz einer tenant-spezifischen Tabelle erbt `TenantMixin`
  (`tenant_id` FK auf `tenants`, mit Index).
- E-Mails sind **pro Tenant** eindeutig (`uq_users_tenant_email`), nicht global.
- Der `get_current_user`-Dependency löst Tenant und Rolle aus dem JWT auf und
  stellt einen `CurrentUser`-Kontext bereit. Rollenprüfung über
  `require_roles(...)` bzw. `require_staff`.

## Rollen

`studio_admin`, `studio_manager`, `teacher`, `reception`, `member`, `trainee`
(Yogalehrer in Ausbildung). Staff-Rollen (Admin, Manager, Reception, Teacher)
haben Verwaltungszugriff.

## Roadmap (Auszug)

- **Phase 1 (MVP):** ✅ Fundament & Auth · Kursverwaltung · Mitglieder ·
  Buchungen · intelligente Warteliste · Benachrichtigungen · QR-Check-in ·
  Anwesenheit · Dashboards
- **Phase 2:** Smart Reminder · dynamische Warteliste · Heat Maps ·
  Lehrer-Analytics · Ausbildungsmodul · Wetterintegration
- **Phase 3:** KI-Prognosen · KI-Assistent · Überbuchung · Event-/Retreat-Modul
  · Integrationen · öffentliche API
