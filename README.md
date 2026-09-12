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

### API

```
cd api
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

See [api/README.md](api/README.md).

### Confirming it works

```
curl http://localhost:8000/health
```

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

### Controller RBAC

```
kubectl apply -f manifests/rbac/controller-rbac.yaml
```

Creates the `trident-controller` account the controller runs as. Namespaced to
`default`: `pods` (+ `pods/log`, `configmaps`) and `pipelineruns` (+ `status`).
Plus a small ClusterRole for two things Kopf always checks at startup regardless
of namespace scope: the PipelineRun CRD and the list of namespaces.

### API RBAC

```
kubectl apply -f manifests/rbac/api-rbac.yaml
```

Creates a `trident-api` account that can read/create `pipelineruns`, read
`configmaps` and Pod logs.

It does nothing yet. The API isn't deployed to the cluster, so nobody uses this
account. Right now you run the API on your own laptop, so it just uses your own
admin access. This account only matters once we deploy the API as a Pod.
