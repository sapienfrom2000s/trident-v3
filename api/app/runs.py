from pydantic import BaseModel

from app.k8s import custom_objects_api

GROUP = "trident.dev"
VERSION = "v1"
PLURAL = "pipelineruns"
NAMESPACE = "default"


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
