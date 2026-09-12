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


TERMINAL_PHASES = ("Succeeded", "Failed")


def build_pipelinerun_status_patch(phase: str) -> dict:
    status = {"phase": phase}
    if phase in TERMINAL_PHASES:
        status["completionTime"] = datetime.now(UTC).isoformat()
    return status


LOG_TRUNCATE_BYTES = 100_000  # stay well under the ~1MiB etcd/ConfigMap object limit


def truncate_log(log: str, limit: int = LOG_TRUNCATE_BYTES) -> str:
    return log[-limit:]


def build_log_configmap(pipelinerun_name: str, log: str) -> dict:
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": f"{pipelinerun_name}-logs"},
        "data": {"log": truncate_log(log)},
    }


@kopf.on.field(
    "",
    "v1",
    "pods",
    field="status.phase",
    when=lambda body, **_: find_owning_pipelinerun(body["metadata"].get("ownerReferences")) is not None,  # pyright: ignore
)
def on_pod_phase_change(namespace, new, name, body, **kwargs):
    pipelinerun_name = find_owning_pipelinerun(body["metadata"].get("ownerReferences"))  # pyright: ignore

    api = client.CustomObjectsApi()
    pipelinerun = api.patch_namespaced_custom_object_status(
        group="trident.dev",
        version="v1",
        namespace=namespace,
        plural="pipelineruns",
        name=pipelinerun_name,
        body={"status": build_pipelinerun_status_patch(new)},  # pyright: ignore
    )

    if new in TERMINAL_PHASES:
        v1 = client.CoreV1Api()
        log_response = v1.read_namespaced_pod_log(
            name=name, namespace=namespace, _preload_content=False
        )
        log = log_response.data.decode("utf-8", errors="replace")
        configmap = build_log_configmap(pipelinerun_name, log)  # pyright: ignore
        kopf.adopt(configmap, owner=pipelinerun)
        v1.create_namespaced_config_map(namespace=namespace, body=configmap)
        v1.delete_namespaced_pod(name=name, namespace=namespace)
