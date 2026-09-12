from datetime import UTC, datetime

TERMINAL_PHASES = ("Succeeded", "Failed")


def find_owning_pipelinerun(owner_references: list[dict] | None) -> str | None:
    for ref in owner_references or []:
        if ref.get("kind") == "PipelineRun" and ref.get("apiVersion", "").startswith(
            "trident.dev/"
        ):
            return ref["name"]
    return None


def build_pipelinerun_status_patch(phase: str) -> dict:
    status = {"phase": phase}
    if phase in TERMINAL_PHASES:
        status["completionTime"] = datetime.now(UTC).isoformat()
    return status
