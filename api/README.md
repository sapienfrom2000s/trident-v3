# Trident API

FastAPI app, managed with `uv`.

## Run

```
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Endpoints

| Method | Path                | What it does                                                         |
| ------ | ------------------- | -------------------------------------------------------------------- |
| GET    | `/health`           | Health check.                                                        |
| GET    | `/runs`             | List PipelineRuns.                                                   |
| GET    | `/runs/{name}`      | Fetch one PipelineRun (404 if missing).                              |
| GET    | `/runs/{name}/logs` | Full log text: ConfigMap if terminal, live Pod log if still running. |
| POST   | `/runs`             | Create a PipelineRun (409 if name taken).                            |

See [app/runs.py](app/runs.py) for request/response shapes.

## Config

| Variable   | Default       | Description             |
| ---------- | ------------- | ----------------------- |
| `APP_NAME` | `Trident API` | Title shown in `/docs`. |
