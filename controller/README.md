# Trident controller

Kopf-based controller, managed with `uv`.

## Run

```
uv sync
uv run kopf run controller.py --all-namespaces
```

Requires `kubectl config current-context` to be `kind-trident-dev` (or whichever
cluster you intend to target) — `kopf run` has no `--context` flag of its own,
it follows the ambient kubeconfig context.
