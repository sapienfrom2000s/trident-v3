from kubernetes.client.exceptions import ApiException
from pydantic import BaseModel

from app.k8s import core_v1_api, custom_objects_api

GROUP = "trident.dev"
VERSION = "v1"
PLURAL = "pipelineruns"
NAMESPACE = "default"
TERMINAL_PHASES = ("Succeeded", "Failed")


class RunSummary(BaseModel):
    name: str
    phase: str | None = None
    start_time: str | None = None
    completion_time: str | None = None


def pipelinerun_to_summary(obj: dict) -> RunSummary:
    status = obj.get("status") or {}
    return RunSummary(
        name=obj["metadata"]["name"],
        phase=status.get("phase"),
        start_time=status.get("startTime"),
        completion_time=status.get("completionTime"),
    )


def list_runs() -> list[RunSummary]:
    api = custom_objects_api()
    result = api.list_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=NAMESPACE, plural=PLURAL
    )
    return [pipelinerun_to_summary(item) for item in result["items"]]


class RunDetail(RunSummary):
    pod_name: str | None = None
    log_url: str | None = None  # placeholder; real log fetching lands in Phase 5


def pipelinerun_to_detail(obj: dict) -> RunDetail:
    status = obj.get("status") or {}
    return RunDetail(
        name=obj["metadata"]["name"],
        phase=status.get("phase"),
        start_time=status.get("startTime"),
        completion_time=status.get("completionTime"),
        pod_name=status.get("podName"),
    )


def get_run(name: str) -> RunDetail:
    api = custom_objects_api()
    obj = api.get_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=NAMESPACE, plural=PLURAL, name=name
    )
    return pipelinerun_to_detail(obj)


class CreateRunRequest(BaseModel):
    name: str
    repo: str
    commit: str
    steps: list[dict]


def build_pipelinerun_object(req: CreateRunRequest) -> dict:
    return {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "PipelineRun",
        "metadata": {"name": req.name},
        "spec": {"repo": req.repo, "commit": req.commit, "steps": req.steps},
    }


def create_run(req: CreateRunRequest) -> RunSummary:
    api = custom_objects_api()
    created = api.create_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural=PLURAL,
        body=build_pipelinerun_object(req),
    )
    return pipelinerun_to_summary(created)


def get_run_logs(name: str) -> str:
    detail = get_run(name)
    v1 = core_v1_api()

    if detail.phase in TERMINAL_PHASES:
        configmap = v1.read_namespaced_config_map(name=f"{name}-logs", namespace=NAMESPACE)
        return (configmap.data or {}).get("log", "")

    if detail.pod_name:
        try:
            log_response = v1.read_namespaced_pod_log(
                name=detail.pod_name, namespace=NAMESPACE, follow=False, _preload_content=False
            )
        except ApiException as e:
            if e.status == 400:
                return ""
            raise
        return log_response.data.decode("utf-8", errors="replace")

    return ""
