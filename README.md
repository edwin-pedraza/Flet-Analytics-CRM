# CRM Analytics (LAN)

Internal-only CRM analytics with login + live presence. Designed to stay inside your router/LAN.

## What you get
- FastAPI backend (login, users, presence)
- Postgres database
- Flet web UI (LAN dashboard)
- Presence WebSocket (who is connected)

---

## Quick Start (Docker: recommended for server)

1) Create `.env` from the example:
```
cp .env.example .env
```

2) Start services:
```
docker compose up --build
```

3) Open the UI on the host:
```
http://127.0.0.1:8550
```

4) Login with the bootstrap admin:
- Email: from `.env`
- Password: from `.env`

> The web UI is internal. Do NOT expose ports to the public internet.

---

## Local Run (no Docker)

### 1) Start Postgres
You can use Docker for Postgres only:
```
docker run --name crm-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=crm -p 5432:5432 -d postgres:16
```

### 2) Run the API
```
uv run --active uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 3) Run the UI
```
uv run --active python main.py --host 0.0.0.0 --port 8550
```

Open:
```
http://127.0.0.1:8550
```

---

## LAN Only Access
- Default allows only LAN/private IP ranges.
- To disable, set `ENFORCE_LAN_ONLY=false` in `.env`.

Allowed by default:
- `127.0.0.0/8`
- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`

---

## Files
- `backend/` FastAPI server
- `app/` Flet UI
- `docker-compose.yml` LAN stack

---

## Next Steps
- Add CRM tables (accounts, deals, contacts)
- Add analytics charts (sales pipeline, activity)
- Add role-based dashboards
