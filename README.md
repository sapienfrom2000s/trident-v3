# Trident v3

Kubernetes-native CI/CD system. See [DESIGN.md](DESIGN.md) for the architecture
and [CONTROLLER_CONCURRENCY.md](CONTROLLER_CONCURRENCY.md) for how the
controller's concurrency model works.

## One-time setup

```
git config core.hooksPath .githooks
```

Enables the repo's pre-commit hook (formatting + running backend/frontend tests
for whichever side you touched) — see
[.githooks/pre-commit](.githooks/pre-commit).

## Phase 0 — local dev

Backend and frontend run as two separate local processes, talking to each other
through the frontend's dev-server proxy (no Docker, no Kubernetes yet).

### Backend

```
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Config is loaded from `backend/.env.development` (tracked in git — no secrets).
See [backend/README.md](backend/README.md) for details.

### Frontend

```
cd frontend
pnpm install
pnpm dev
```

Requests to `/api/*` are proxied to the backend on `:8000` — see
[frontend/vite.config.js](frontend/vite.config.js). See
[frontend/README.md](frontend/README.md) for lint/test commands.

### Confirming it works

With both processes running, open <http://localhost:5173> (Vite prints the
actual URL on startup — it picks a different port automatically if 5173 is
already taken) — the page should show "Backend health: ok", fetched live from
the backend through the proxy.
