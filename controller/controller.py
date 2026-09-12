from datetime import UTC, datetime

import kopf
from kubernetes import client

CLONE_SCRIPT = 'git clone "$1" repo && cd repo && git checkout "$2" && echo done'


def build_pod_spec(name: str, spec: dict) -> dict:
    repo = spec["repo"]
    commit = spec["commit"]

    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"generateName": f"{name}-"},
        "spec": {
            "restartPolicy": "Never",
            "containers": [
                {
                    "name": "build",
                    "image": "alpine/git",
                    "command": ["sh", "-c", CLONE_SCRIPT, "--", repo, commit],
                }
            ],
        },
    }


@kopf.on.create("trident.dev", "v1", "pipelineruns")
def on_create(body, **kwargs):
    name = kwargs["name"]
    namespace = kwargs["namespace"]
    spec = kwargs["spec"]
    patch = kwargs["patch"]

    pod = build_pod_spec(name, spec)

    # body is the whole pipelinerun object
    kopf.adopt(pod, owner=body)

    v1 = client.CoreV1Api()
    created_pod = v1.create_namespaced_pod(namespace=namespace, body=pod)

    patch.status["podName"] = created_pod.metadata.name  # pyright: ignore
    patch.status["startTime"] = datetime.now(UTC).isoformat()


def find_owning_pipelinerun(owner_references: list[dict] | None) -> str | None:
    for ref in owner_references or []:
        if ref.get("kind") == "PipelineRun" and ref.get("apiVersion", "").startswith("trident.dev/"):
            return ref["name"]
    return None


def build_pipelinerun_status_patch(phase: str) -> dict:
    status = {"phase": phase}
    if phase in ("Succeeded", "Failed"):
        status["completionTime"] = datetime.now(UTC).isoformat()
    return status


@kopf.on.field(
    "",
    "v1",
    "pods",
    field="status.phase",
    when=lambda body, **_: find_owning_pipelinerun(body["metadata"].get("ownerReferences")) is not None,  # pyright: ignore
)
def on_pod_phase_change(namespace, new, body, **kwargs):
    pipelinerun_name = find_owning_pipelinerun(body["metadata"].get("ownerReferences"))  # pyright: ignore

    api = client.CustomObjectsApi()
    api.patch_namespaced_custom_object_status(
        group="trident.dev",
        version="v1",
        namespace=namespace,
        plural="pipelineruns",
        name=pipelinerun_name,
        body={"status": build_pipelinerun_status_patch(new)},  # pyright: ignore
    )
