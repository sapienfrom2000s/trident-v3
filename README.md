<div align="center">

# Trident v3

_Kubernetes-native CI/CD: etcd, one CRD, a controller, and a thin custom API
server._

[![CI](https://img.shields.io/github/actions/workflow/status/sapienfrom2000s/trident-v3/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/sapienfrom2000s/trident-v3/actions)
[![Python](https://img.shields.io/badge/Python-3.12-3c873a?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![Go](https://img.shields.io/badge/Go-1.23-00ADD8?style=flat-square&logo=go&logoColor=white)](https://go.dev)
[![Kopf](https://img.shields.io/badge/Kopf-Kubernetes_operator-326ce5?style=flat-square&logo=kubernetes&logoColor=white)](https://kopf.readthedocs.io)

[Concepts](#concepts) • [Getting started](#getting-started) • [Usage](#usage) •
[Project layout](#project-layout) • [Docs](#documentation)

</div>

## Concepts

### Kubernetes primitives, briefly

Four quick definitions, for reference:

- **Object** — a record stored in etcd.
- **etcd** — Kubernetes' built-in database. No setup needed.
- **Controller** — a program that watches one kind of object and reacts to
  changes. Kubernetes ships some by default. Trident's controller is a custom
  one built for this project.
- **CRD** (Custom Resource Definition) — how a new kind of object gets added to
  Kubernetes. `PipelineRun` is one.

### The pieces

Trident adds `PipelineRun` as a new object type, and a small Python controller
that reacts to it. The object in etcd is the build record. A small FastAPI
wrapper ([`api/`](api/)) also exists for convenience, but holds no state of its
own — it just reads and writes the same `PipelineRun` objects.

### Flow

What happens end to end, from creating a `PipelineRun` to a finished build:

1. A `PipelineRun` gets created (`kubectl apply` or the API) — repo and commit,
   nothing else yet.
2. The controller notices it, builds a Pod, and starts it. `status.phase`
   becomes `Pending`, then `Running`.
3. The Pod clones the repo, checks out the commit, and runs `.trident.yml`'s
   commands in order.
4. The Pod finishes. The controller sets `status.phase` to `Succeeded` or
   `Failed`, saves the log to a ConfigMap, and deletes the Pod.
5. The result can be checked with `kubectl` or the API — see
   [Checking on a run](#checking-on-a-run).

See [CONTROLLER_CONCURRENCY.md](CONTROLLER_CONCURRENCY.md) for exactly how Kopf
schedules and orders handler calls under the hood.

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python 3.12, used by both `api/` and
  `controller/`)
- [Go](https://go.dev/dl/) 1.23+ (only needed to run/test
  `controller/buildscript/`)
- [OrbStack](https://orbstack.dev) + [kind](https://kind.sigs.k8s.io) for a
  local cluster

### One-time setup

```bash
git config core.hooksPath .githooks
```

Enables the repo's pre-commit hook (runs the relevant test suite for whichever
of `api/`, `controller/` changed) — see
[.githooks/pre-commit](.githooks/pre-commit).

### Local Kubernetes cluster

```bash
kind create cluster --name trident-dev
kubectl cluster-info --context kind-trident-dev

kubectl apply -f manifests/crds/pipelinerun-crd.yaml
kubectl apply -f manifests/rbac/controller-rbac.yaml
kubectl apply -f manifests/rbac/api-rbac.yaml
```

### Run the controller

```bash
cd controller
uv sync
uv run kopf run controller.py --namespace=default
```

Requires `kubectl config current-context` to be `kind-trident-dev` (or whichever
cluster is the target) — `kopf run` has no `--context` flag of its own, it
follows the ambient kubeconfig context.

### Run the API (optional)

```bash
cd api
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

```bash
curl http://localhost:8000/health
```

See [api/README.md](api/README.md) for the full endpoint list.

## Usage

### `.trident.yml`

Drop this at the root of the repo being built to actually run something beyond a
clone + checkout — a flat YAML list of shell commands, run in order, stopping at
the first failure:

```yaml
- echo "building"
- go build ./...
- go test ./...
```

> [!IMPORTANT]
>
> Commands run inside a `golang:1.23-alpine` container with `git` installed —
> nothing else. A build that needs Node, Python, etc. must install it as an
> explicit step first (e.g. `apk add --no-cache nodejs npm`). Per-step,
> per-language images aren't built yet — see [Limitations](#limitations).

### Creating a pipeline

With the controller running, create a `PipelineRun` either via `kubectl`:

```yaml
# my-run.yaml
apiVersion: trident.dev/v1
kind: PipelineRun
metadata:
  name: my-run
spec:
  repo: https://github.com/example-org/example-repo
  commit: main # a branch name or a full SHA both work
  steps:
    - name: build
      image: alpine # required by the CRD schema, currently unused
```

```bash
kubectl apply -f my-run.yaml
kubectl get pipelinerun my-run --watch
```

...or via the API:

```bash
curl -X POST http://localhost:8000/runs -H "Content-Type: application/json" -d '{
  "name": "my-run",
  "repo": "https://github.com/example-org/example-repo",
  "commit": "main",
  "steps": [{"name": "build", "image": "alpine"}]
}'
```

### Checking on a run

```bash
kubectl get pipelinerun my-run -o yaml           # phase, timestamps, pod name
kubectl get configmap my-run-logs -o jsonpath='{.data.log}'   # full log (terminal runs)

curl http://localhost:8000/runs/my-run           # same, via the API
curl http://localhost:8000/runs/my-run/logs      # log: ConfigMap if terminal, live Pod log otherwise
```

## Project layout

```
manifests/
  crds/        PipelineRun CustomResourceDefinition
  rbac/        ServiceAccount/Role/RoleBinding for the controller and API
  samples/     example PipelineRun and .trident.yml
controller/    Kopf operator (Python) + the build-Pod step runner (Go)
api/           optional FastAPI wrapper over the same PipelineRun objects
```

## Documentation

- [CONTROLLER_CONCURRENCY.md](CONTROLLER_CONCURRENCY.md) — how Kopf schedules
  and orders handlers under `asyncio`
- [api/README.md](api/README.md) — endpoint reference
- [controller/README.md](controller/README.md) — running the controller locally

## Limitations

- The build container only has `git` and Go — no Node, Python, etc. unless
  installed as an explicit `.trident.yml` step first.
- Logs are capped at ~100KB and stored in a ConfigMap, not durable long-term
  storage.
- The API has no authentication — anyone who can reach it can list, create, and
  read logs for any `PipelineRun`.
- Finished `PipelineRun` objects stay in etcd forever; nothing cleans them up.
- One Pod, one container per run — no parallel steps, no per-step images yet.
- The controller is a single Python process — no horizontal scaling, no leader
  election. Fine for a handful of runs at a time; not tested under heavy load.
- No limit on concurrent builds — a burst of `PipelineRun`s creates a burst of
  Pods immediately, with no queueing or throttling.
