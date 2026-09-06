# Trident v3

Kubernetes-native CI/CD system. See [DESIGN.md](DESIGN.md) for the architecture
and [CONTROLLER_CONCURRENCY.md](CONTROLLER_CONCURRENCY.md) for the controller's
concurrency model.

## One-time setup

```
git config core.hooksPath .githooks
```

Enables the repo's pre-commit hook — see
[.githooks/pre-commit](.githooks/pre-commit).

## Local dev

### Backend

```
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

See [backend/README.md](backend/README.md).

### Frontend

```
cd frontend
pnpm install
pnpm dev
```

Proxies `/api/*` to the backend on `:8000` — see
[frontend/vite.config.js](frontend/vite.config.js) and
[frontend/README.md](frontend/README.md).

### Confirming it works

With both running, open <http://localhost:5173> — should show "Backend health:
ok".

## Local Kubernetes cluster

```
brew install --cask orbstack
brew install kind

kind create cluster --name trident-dev
kubectl cluster-info --context kind-trident-dev
```

### PipelineRun CRD

```
kubectl apply -f manifests/crds/pipelinerun-crd.yaml
kubectl get crd pipelineruns.trident.dev
kubectl get pipelineruns
```

```
kubectl apply -f manifests/samples/pipelinerun-sample.yaml
kubectl get pipelinerun sample-run
```
