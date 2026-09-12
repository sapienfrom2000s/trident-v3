# Trident v3 — Design Doc

A small CI/CD system that runs entirely inside Kubernetes: pipeline state lives
in Kubernetes objects, and a Python controller reacts to them.

## The idea in one paragraph

Kubernetes already has a database (etcd) and a way to watch for changes (the API
server). Instead of building a separate CI/CD backend with its own database and
API, we teach Kubernetes a new kind of object — a "PipelineRun" — and write a
small Python program that watches for these objects and reacts to them by
starting build Pods. That's the whole system.

## The pieces

### 1. A new object type: PipelineRun

We define a Custom Resource Definition (CRD). Think of it as teaching `kubectl`
a new noun. After this, you can do:

```
kubectl apply -f my-build.yaml
kubectl get pipelineruns
```

A PipelineRun object holds:

- **spec** — what to build: git repo, branch/commit, the steps to run, what
  image to build. Written once, by the user or by a webhook.
- **status** — what happened: current phase (Pending / Running / Succeeded /
  Failed), start/end time, a pointer to where logs live. Written only by our
  controller.

No Postgres. The object itself, sitting in etcd, is the database row.

### 2. The controller: a Python script using Kopf

Kopf lets you write:

```python
@kopf.on.create('trident.dev', 'v1', 'pipelineruns')
def start_build(spec, status, patch, **kwargs):
    ...
```

That function fires automatically whenever someone creates a PipelineRun. No
polling loop, no webhook server to write by hand — Kopf watches the Kubernetes
API for us and calls our function.

What the function does:

1. Read the spec (repo, commit, steps).
2. Build a Pod definition for the actual build job.
3. Create that Pod in Kubernetes.
4. Write "Running" into the PipelineRun's status.

The same controller process registers a second Kopf handler that watches build
Pods. When one finishes, it copies the result (success/failure, exit code) back
onto the PipelineRun's status and deletes the Pod. This has to be the
controller, not the Pod reporting on itself: the Pod can die before any user
code runs (image pull failure, OOM kill, eviction), and giving build Pods write
access to PipelineRun objects would mean arbitrary build scripts can tamper with
CI state. The controller watches from outside and needs no trust in what's
running inside the Pod.

### 3. Running the actual build: one Pod per run

Each PipelineRun becomes one throwaway Pod:

- A shared empty scratch directory (`emptyDir` volume) is mounted into every
  step's container, so step 2 can see files step 1 produced.
- Steps run as ordinary containers (init containers, one per step, in order) —
  no container-inside-a-container. To actually build a container image, we use a
  rootless, unprivileged image-building tool (e.g. Kaniko or Buildah) instead of
  running Docker itself inside the Pod. This avoids giving the build Pod
  root/privileged access to the host.
- When the Pod finishes, it's gone. Nothing to clean up by hand.

**Current MVP shape** (before the init-containers-per-step model above is
built): a single container clones `spec.repo`, checks out `spec.commit`, and if
the repo has a `.trident.yml` at its root, runs it as a flat list of shell
commands, in order, stopping on the first failure.

No conditionals, no parallelism, no per-step images yet — that's what the
init-containers-per-step model above is for, once it's built.

### 4. Who's allowed to do what: login + permissions

- **Login**: users authenticate through an existing identity provider (Dex,
  Okta, etc.) using the standard login flow (OIDC). Kubernetes itself already
  knows how to accept these logins — we don't write our own login page or
  password database.
- **Permissions**: once logged in, what a user can do (create a PipelineRun,
  view logs, delete a run) is controlled by normal Kubernetes RBAC — the same
  Role/RoleBinding system used for everything else in the cluster. A "can
  trigger builds in the payments team's namespace" rule is just an RBAC rule,
  not custom code we maintain.

### 5. Keeping etcd small: logs and artifacts live outside Kubernetes

etcd is good at storing small objects (kilobytes), not gigabytes of logs or
build artifacts. So:

- The PipelineRun's **status** only ever holds small facts: phase, times, a
  link.
- The build Pod streams its logs and uploads any output files (build artifacts)
  straight to S3-compatible object storage (S3 or self-hosted MinIO).
- The "link" saved in status is just the S3 path — the UI/CLI fetches the actual
  log/artifact content directly from object storage, not through Kubernetes.

## What a build run looks like end to end

1. A webhook (or a person) creates a PipelineRun object.
2. Kopf's `on.create` handler fires, builds a Pod spec from it, creates the Pod,
   sets status to `Running`.
3. The Pod runs its steps in order, streaming logs to S3/MinIO as it goes.
4. Kopf's Pod-watching handler notices the Pod finished, sets status to
   `Succeeded` or `Failed`, records the S3 log path, deletes the Pod.
5. Anyone with RBAC access can `kubectl get pipelinerun my-build -o yaml` or use
   a small CLI/UI that reads the same object and fetches the log link.

## Why this stays simple

- One moving part we actually maintain: the Kopf controller (a few hundred lines
  of Python).
- No database to run, back up, or patch — Kubernetes already runs etcd for its
  own objects, we're just adding one more type.
- No custom login system — we lean on OIDC + RBAC that already exist.
- No privileged Docker-in-Docker — builds run as normal, unprivileged Pods.
- Everything is inspectable with tools people already know: `kubectl get`,
  `kubectl describe`, `kubectl logs`.

## Open questions to decide before building

1. **Step definition format** — resolved for the MVP: `.trident.yml` is a flat
   list of shell commands, run in order (see section 3). Conditionals, parallel
   steps, and per-step images are still undecided.
2. **Multi-tenancy** — one CRD across the whole cluster, or a namespace-per-team
   convention enforced via RBAC?
3. **Retention** — how long do finished PipelineRun objects stick around before
   we garbage-collect them (etcd doesn't want thousands of old objects sitting
   around forever)?
4. **Triggering** — do we build the git-webhook receiver ourselves, or bolt onto
   something existing?
