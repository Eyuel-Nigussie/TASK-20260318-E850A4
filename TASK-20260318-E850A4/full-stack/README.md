# Activity Registration and Funding Audit Management Platform

This project is designed for production-grade **offline** deployment and is fully containerized.

## Startup

Run the entire system with one command from project root:

```bash
docker compose up
```

If needed, copy `.env.example` to `.env` and adjust host ports/secrets.

## Services and Ports

- Frontend (Vue.js via Nginx): `http://localhost:15173`
- Backend (FastAPI): `http://localhost:18000`
- Backend OpenAPI docs: `http://localhost:18000/docs`
- PostgreSQL: `localhost:15432`

If your machine already uses these ports, either set `.env` values or override at runtime:

```bash
BACKEND_PORT=28000 FRONTEND_PORT=25173 POSTGRES_PORT=25432 docker compose up
```

Default seeded credentials (for initial verification only):

- Username: `sysadmin`
- Password: `Admin#123456`

## Verification Steps

1. Start services:
   - `docker compose up`
2. Confirm all containers are healthy/running:
   - `docker compose ps`
3. Open frontend:
   - Visit `http://localhost:15173`
4. Verify backend API responds:
   - Visit `http://localhost:18000/docs`
5. Confirm database connectivity from backend logs:
   - `docker compose logs backend`
6. Validate core flow smoke checks:
   - Login endpoint works
   - Registration creation works
   - Material upload init/finalize works
   - Reviewer transition endpoint works

All tiers are implemented: authentication, uploads/versioning, reviewer workflow/batch, financial module, quality metrics, audit, backups/restore, exports, and role-based masking.

Notes:

- Backend container healthcheck is self-contained and does not require `curl` in the image.
- Verified in this environment with default project ports: frontend `15173`, backend `18000`, postgres `15432`.

## Automated Tests

- Run complete test pipeline:
  - `./run_tests.sh`
- Included test suites:
  - `unit_tests/` (unit tests)
  - `API_tests/` (API smoke and contract checks)

## Daily Automatic Backup

- A built-in scheduler runs inside backend service and triggers a daily local backup.
- Default schedule: `02:00 UTC`.
- Configurable environment variables:
  - `BACKUP_SCHEDULE_ENABLED=true|false`
  - `BACKUP_SCHEDULE_HOUR_UTC=0..23`
- Each scheduled backup writes:
  - backup artifacts under `/data/backups`
  - a `backup_records` row
  - an audit entry (`action=BACKUP_RUN`, `entity_type=BACKUP`)

## Deployment Principles

- No mandatory local host dependencies except Docker + Compose.
- All data persists in Docker volumes (database, file storage, backups).
- Core functions do not depend on external SaaS.

## Planned Top-Level Structure

```text
.
├── docker-compose.yml
├── README.md
├── docs/
│   ├── design.md
│   └── api-spec.md
├── frontend/
├── backend/
└── shared/
    └── database/
```
