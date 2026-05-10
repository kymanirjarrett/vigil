# Vigil

**Real-time monitoring, anomaly detection, and alerting for AWS Glue ETL pipelines.**

[![CI](https://github.com/kymanirjarrett/vigil/actions/workflows/ci.yml/badge.svg)](https://github.com/kymanirjarrett/vigil/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![React](https://img.shields.io/badge/React-19-61DAFB)

---

## Live Demo

**Frontend:** https://vigil-three-amber.vercel.app/
**API docs:** https://vigil-59y0.onrender.com

> The backend runs on Render's free tier and sleeps after 15 min of inactivity. The first request after a cold start may take ~30 seconds.

---

## Problem

AWS Glue ETL jobs fail silently. You know something is wrong when a downstream analyst notices stale data or a pipeline SLA is missed — hours after the actual failure. CloudWatch has the data, but building observability tooling on top of it is time-consuming. Vigil wraps that raw AWS data into a focused monitoring surface with anomaly detection and alerting baked in.

---

## Features

- **Live job dashboard** — all Glue jobs in your AWS account, latest status, worker config, last modified
- **Run history** — per-job execution log with duration bar charts and color-coded status badges
- **Anomaly detection** — flags duration spikes (>2× the job's mean) and consecutive failure streaks
- **Email alerting** — one-click anomaly scan + SendGrid alert to any recipient
- **Persistent history** — all anomaly events and alert sends stored in PostgreSQL via Supabase
- **JWT authentication** — token-based login protecting all API routes
- **Docker-ready** — backend ships as a Docker image published to GitHub Container Registry

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                React + Vite (Vercel)                        │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS (Bearer token)
┌────────────────────────▼────────────────────────────────────┐
│                   FastAPI (Render)                          │
│                                                             │
│   /api/glue ──────────────────────► AWS Glue (boto3)       │
│   /api/anomalies ─────────────────► detect + persist       │
│   /api/alerts ────────────────────► SendGrid               │
│   /api/history ───────────────────► read from DB           │
│   /api/auth ──────────────────────► JWT issue/verify       │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│            Supabase (PostgreSQL)                            │
│   anomaly_events  ·  alert_log                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend | React + Vite | 19 / 6 |
| Charts | Recharts | 2.x |
| Backend | FastAPI | 0.115 |
| ORM | SQLAlchemy | 2.0.36 |
| Database driver | psycopg2-binary | 2.9.9 |
| AWS SDK | boto3 | 1.35 |
| Auth | python-jose + passlib | 3.3 / 1.7.4 |
| Email | SendGrid | 6.11 |
| Database | PostgreSQL (Supabase) | 16 |
| Container | Docker + GHCR | — |
| Backend host | Render (free tier) | — |
| Frontend host | Vercel (free tier) | — |

---

## Quick Start

```bash
git clone https://github.com/kymanirjarrett/vigil.git
cd vigil
npm run setup
npm run reveal-secrets   # creates backend/.env — fill in your values
```

Then in two terminals:

```bash
npm run dev:backend   # terminal 1 — FastAPI on :8000
npm run dev:frontend  # terminal 2 — Vite on :5173
```

Open http://localhost:5173 and log in.

---

## Environment Variables

All variables live in `backend/.env` (created from `backend/.env.example` by `npm run reveal-secrets`).

| Variable | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user with read-only Glue + CloudWatch access |
| `AWS_SECRET_ACCESS_KEY` | Corresponding secret |
| `AWS_REGION` | Target region (e.g. `us-east-2`) |
| `SENDGRID_API_KEY` | SendGrid API key for alert emails |
| `ALERT_SENDER_EMAIL` | Verified sender address in SendGrid |
| `DATABASE_URL` | PostgreSQL connection string (Supabase Session Mode, port 5432) |
| `JWT_SECRET_KEY` | Random secret for signing JWTs — generate with `openssl rand -hex 32` |
| `VIGIL_USERNAME` | Login username |
| `VIGIL_PASSWORD_HASH` | bcrypt hash — generate with `python -c "from passlib.hash import bcrypt; print(bcrypt.hash('yourpass'))"` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins (e.g. `https://vigil.vercel.app`) |

---

## Project Structure

```
vigil/
├── .github/workflows/
│   ├── ci.yml              # lint + build on every push/PR
│   └── docker.yml          # publish Docker image to GHCR on release
├── .husky/
│   ├── pre-commit          # secretlint — blocks hardcoded secrets
│   └── pre-push            # ESLint + ruff before every push
├── .vscode/                # shared editor settings + extension recommendations
├── backend/
│   ├── routers/            # glue, anomalies, alerts, history, auth
│   ├── main.py             # FastAPI app, CORS, lifespan
│   ├── database.py         # SQLAlchemy engine + session factory
│   ├── models.py           # AnomalyEvent + AlertLog ORM models
│   ├── aws_client.py       # boto3 Glue client
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/     # JobsTable, JobRunsPanel, AnomalyBanner, AlertsPanel, HistoryPanel, LoginPage
│   │   ├── App.jsx         # auth state, global 401 interceptor
│   │   └── App.css         # design tokens, layout, component styles
│   ├── index.html
│   └── .env.example
├── scripts/
│   ├── setup.sh            # one-command project setup
│   ├── dev-backend.sh      # start uvicorn via venv
│   └── reveal-secrets.sh   # scaffold .env from .env.example
├── docker-compose.yml      # local container testing
├── railway.json            # Railway deploy config (alternative to Render)
├── Makefile                # make setup / dev-backend / dev-frontend
└── package.json            # root scripts + Husky + lint-staged
```

---

## Roadmap

- [ ] CloudWatch integration (Lambda error rates, Glue metrics tab)
- [ ] Auto-polling with real 60s refresh behind the LIVE indicator
- [ ] Slack alerting
- [ ] Anomaly sensitivity controls
- [ ] Historical trend charts
- [ ] Step Functions monitoring
- [ ] Monorepo restructure (`packages/` layout)

---

## License

MIT © 2025 Kymani Jarrett
