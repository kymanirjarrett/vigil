# Vigil

**ETL observability for AWS Glue: real-time monitoring, anomaly detection, and alerting, on a security foundation built like an internal tool would need.**

[![CI](https://github.com/kymanirjarrett/vigil/actions/workflows/ci.yml/badge.svg)](https://github.com/kymanirjarrett/vigil/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688)
![React](https://img.shields.io/badge/React-19-61DAFB)

**Live demo:** [vigil-etl.vercel.app](https://vigil-etl.vercel.app/) · **API docs:** [vigil-59y0.onrender.com/docs](https://vigil-59y0.onrender.com/docs)

> Click **Try the demo** to sign in as a shared read-only guest. The app runs on sample pipeline data. The API runs on Render's free tier and sleeps when idle, so the first request after a while can take about a minute while it wakes up.

Feature-complete portfolio project, not accepting contributions. Fork freely under the MIT license.

---

## Why

AWS Glue jobs fail quietly. Usually the first sign is a downstream user noticing stale data, hours after the job actually broke. CloudWatch has the raw signal, but turning it into something a team can watch takes real work. Vigil puts every Glue job on one dashboard, flags runs that look wrong, and emails someone before the failure cascades downstream.

## Features

**Monitoring**
- Sample pipeline data by default (`DATA_SOURCE=seed`), so the app is fully explorable without AWS access
- With `DATA_SOURCE=aws`, a live dashboard of every Glue job in the account, with latest status and worker configuration
- Per-job run history with duration charts and status badges
- Anomaly detection that flags duration spikes (more than 2 standard deviations above the job's mean run time) and consecutive failure streaks
- One-click anomaly scans, with every anomaly and alert stored for history. Alerts are simulated on sample data and sent by SendGrid email with `DATA_SOURCE=aws`
- A shared read-only guest account ("Try the demo") that sees synthetic security data with masked IP addresses

**Security model**
- **Role-based access control.** Admin and Analyst roles map to granular permissions (`jobs:read`, `alerts:trigger`, `users:manage`, `audit:read`, and more), stored in the database and enforced server-side on every route. Analysts get read-only access by default.
- **Row-level security on every table.** RLS is enabled in the same Alembic migration that creates each table, with an explicit `service_role` policy, so a new table can't ship without it.
- **Append-only audit log.** Every significant action is recorded with the user, resource, IP address, and user agent. Rows are never updated or deleted.
- **Authentication hardening.** bcrypt password hashing, 15-minute JWT access tokens, rotating refresh tokens stored only as SHA-256 hashes, rate-limited login (5 per minute), and account lockout after repeated failures. Reusing a refresh token that was already rotated revokes that whole session chain (its token family), so a stolen token stops working for the attacker and the victim alike, while the user's other devices stay signed in.
- **Two-factor authentication.** TOTP enrollment with one-time backup codes.
- **Threat detection.** Every login attempt is recorded, including attempts for emails that don't exist, which is what makes brute force (repeated failures against one account) and credential stuffing (failures spread across many accounts) detectable.
- **Security posture dashboard.** Hourly login successes and failures, the IPs with the most failures, open threat detections, users by role, and recent admin actions in one view. Users can also see their active sessions and sign any of them out.

## Architecture

```mermaid
flowchart LR
    U[Browser] -->|HTTPS + JWT| FE[React + Vite<br/>Vercel]
    FE -->|REST| API[FastAPI<br/>Render, Docker]
    API -->|boto3, read-only IAM<br/>DATA_SOURCE=aws| AWS[AWS Glue, Athena, S3]
    API -->|SQLAlchemy| DB[(PostgreSQL<br/>Supabase, RLS on every table)]
    API -->|alerts| SG[SendGrid]
    CF[CloudFormation<br/>infra/vigil-stack.yaml] -.provisions.-> AWS
```

The API checks permissions on every request through a single `require_permission` dependency, and every write that matters goes through `log_action`, so authorization and auditing live in one place instead of being repeated per route.

### Database keep-alive

Supabase pauses free projects after a week of low database activity, and a paused project can only be restored from the dashboard for up to a year. A [cron-job.org](https://cron-job.org) job sends `GET /health/deep` every 3 days, with failure emails on. That endpoint runs a real `SELECT 1`, which resets the inactivity timer.

The ping used to be a scheduled GitHub Actions workflow. GitHub disables scheduled workflows in public repositories after 60 days without repository activity, so a finished project would lose its keep-alive silently. [`supabase-ping.yml`](.github/workflows/supabase-ping.yml) remains as a manual fallback. A 3-day interval is deliberate: a 5-minute uptime monitor would keep the Render instance awake all month and use up the free instance hours.

### Infrastructure as code

[`infra/vigil-stack.yaml`](infra/vigil-stack.yaml) provisions a real pipeline for Vigil to monitor: S3 buckets for input, output, scripts, and Athena results, a Glue database, table, job, and crawler, a Glue service role, and a read-only IAM policy for the backend. It deploys through a manual GitHub Actions workflow per environment, and `prod` requires an approval from a repository admin. The stack is not currently deployed; the live app runs on sample data. See [`infra/README.md`](infra/README.md).

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, React Router, Recharts |
| Backend | FastAPI, SQLAlchemy 2, Alembic, SlowAPI |
| Auth | python-jose (JWT), passlib (bcrypt), PyOTP |
| AWS | boto3 for Glue, Athena, and S3; CloudFormation |
| Database | PostgreSQL on Supabase |
| Email | SendGrid |
| Hosting | Vercel (frontend), Render via Docker (API) |
| Tooling | GitHub Actions, Husky, secretlint, ESLint, Ruff |

## Engineering practices

- **CI on every pull request and on `main`:** Ruff and a compile check on the backend; ESLint, a production build, and `npm audit` (fails on high severity) on the frontend; pytest and Vitest suites with coverage in the job summary.
- **Tests against real Postgres:** the backend suite applies the actual Alembic migrations to a disposable Postgres 17 (a service container in CI), so RLS and constraints behave as in production. It refuses to run against any non-local database host.
- **Secret scanning before every commit:** a Husky pre-commit hook runs secretlint on staged files, and a pre-push hook lints both apps.
- **Migrations only:** every schema change is an Alembic migration, and RLS ships in the same migration as the table.
- **Issue-driven workflow:** every pull request closes an issue (`Closes #N`).

## Run it locally

```bash
git clone https://github.com/kymanirjarrett/vigil.git
cd vigil
npm run setup            # installs both apps and the git hooks
npm run reveal-secrets   # creates backend/.env from backend/.env.example
```

Fill in `backend/.env`, then run each app in its own terminal:

```bash
npm run dev:backend    # FastAPI on :8000
npm run dev:frontend   # Vite on :5173
```

### Run the tests

```bash
# Backend: needs a disposable Postgres, never the production database
docker run -d --name vigil-test-pg -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:17
cd backend && pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql://postgres:test@localhost:5433/postgres python -m pytest

# Frontend
cd frontend && npm test
```

### Environment variables

| Variable | Purpose |
|---|---|
| `DATA_SOURCE` | `seed` (default, sample data) or `aws` (live Glue, Athena, and S3) |
| `DATABASE_URL` | PostgreSQL connection string (Supabase session mode) |
| `VIGIL_JWT_SECRET` | Secret for signing JWTs (`openssl rand -hex 32`) |
| `VIGIL_ADMIN_EMAIL`, `VIGIL_ADMIN_PASSWORD` | Seeds the first Admin account |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | Read-only IAM user for Glue, Athena, and S3. Only with `DATA_SOURCE=aws` |
| `GLUE_DATABASE_NAME`, `GLUE_TABLE_NAME`, `ATHENA_RESULTS_BUCKET` | Resources created by the CloudFormation stack. Only with `DATA_SOURCE=aws` |
| `SENDGRID_API_KEY`, `ALERT_SENDER_EMAIL` | Alert email delivery. Only with `DATA_SOURCE=aws` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |

## Project structure

```
vigil/
├── backend/
│   ├── routers/          auth, totp, admin, glue, anomalies, alerts, history,
│   │                     audit, auth_events, auth_anomalies, security, health
│   ├── data_sources/     pipeline data providers: seed (sample data) and aws
│   ├── alembic/          migrations (RLS enabled per table)
│   ├── tests/            pytest suite, run against a disposable Postgres
│   ├── permissions.py    RBAC: role to permission mapping and require_permission
│   ├── audit.py          append-only audit logging
│   ├── auth_detection.py brute force and credential stuffing detection
│   ├── guest.py          shared read-only guest account
│   ├── security_seed.py  synthetic security data for the guest
│   ├── settings.py       environment settings, including DATA_SOURCE
│   ├── start.sh          container entrypoint
│   └── main.py
├── frontend/src/
│   ├── api.js            shared API base URL
│   └── components/       dashboard, admin, audit, security, and account pages
├── infra/                     CloudFormation stack, Glue script, seed data
├── .github/workflows/         CI, CloudFormation deploy, manual keep-alive fallback
└── .husky/                    pre-commit secret scan, pre-push lint
```

## License

[MIT](LICENSE) © 2026 Kymani Jarrett
