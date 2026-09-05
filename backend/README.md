# Trident backend

FastAPI app, managed with `uv`.

## Run

```
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Config

Loaded from `.env.development` in this directory (tracked in git — no secrets in
it, just dev defaults), via `python-dotenv`.

| Variable   | Default       | Description             |
| ---------- | ------------- | ----------------------- |
| `APP_NAME` | `Trident API` | Title shown in `/docs`. |
