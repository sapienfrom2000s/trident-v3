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
