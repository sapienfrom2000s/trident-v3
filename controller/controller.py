from datetime import UTC, datetime

import kopf
from kubernetes import client

from logs import build_log_configmap
from pipelineruns import (
    TERMINAL_PHASES,
    build_pipelinerun_status_patch,
    find_owning_pipelinerun,
)
from pods import build_pod_spec


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


@kopf.on.field(
    "",
    "v1",
    "pods",
    field="status.phase",
    when=lambda body, **_: (
        find_owning_pipelinerun(body["metadata"].get("ownerReferences")) is not None
    ),  # pyright: ignore
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
