from unittest.mock import patch

from fastapi.testclient import TestClient
from kubernetes.client.exceptions import ApiException

from app.main import app
from app.runs import (
    CreateRunRequest,
    build_pipelinerun_object,
    pipelinerun_to_detail,
    pipelinerun_to_summary,
)

client = TestClient(app)


def test_pipelinerun_to_summary_maps_status_fields() -> None:
    obj = {
        "metadata": {"name": "sample-run"},
        "status": {
            "phase": "Succeeded",
            "startTime": "2026-09-12T00:00:00+00:00",
            "completionTime": "2026-09-12T00:01:00+00:00",
        },
    }

    summary = pipelinerun_to_summary(obj)

    assert summary.name == "sample-run"
    assert summary.phase == "Succeeded"
    assert summary.start_time == "2026-09-12T00:00:00+00:00"
    assert summary.completion_time == "2026-09-12T00:01:00+00:00"


def test_pipelinerun_to_summary_handles_missing_status() -> None:
    obj = {"metadata": {"name": "brand-new-run"}}

    summary = pipelinerun_to_summary(obj)

    assert summary.name == "brand-new-run"
    assert summary.phase is None
    assert summary.start_time is None
    assert summary.completion_time is None


def test_get_runs_returns_simplified_shape() -> None:
    fake_items = {
        "items": [
            {
                "metadata": {"name": "sample-run"},
                "status": {"phase": "Running", "startTime": "2026-09-12T00:00:00+00:00"},
            }
        ]
    }

    with patch("app.runs.custom_objects_api") as custom_objects_api:
        custom_objects_api.return_value.list_namespaced_custom_object.return_value = fake_items
        response = client.get("/runs")

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "sample-run",
            "phase": "Running",
            "start_time": "2026-09-12T00:00:00+00:00",
            "completion_time": None,
        }
    ]


def test_pipelinerun_to_detail_includes_pod_name_and_log_placeholder() -> None:
    obj = {
        "metadata": {"name": "sample-run"},
        "status": {"phase": "Running", "podName": "sample-run-abc12"},
    }

    detail = pipelinerun_to_detail(obj)

    assert detail.pod_name == "sample-run-abc12"
    assert detail.log_url is None


def test_get_run_detail_returns_simplified_shape() -> None:
    fake_obj = {
        "metadata": {"name": "sample-run"},
        "status": {
            "phase": "Succeeded",
            "startTime": "2026-09-12T00:00:00+00:00",
            "completionTime": "2026-09-12T00:01:00+00:00",
            "podName": "sample-run-abc12",
        },
    }

    with patch("app.runs.custom_objects_api") as custom_objects_api:
        custom_objects_api.return_value.get_namespaced_custom_object.return_value = fake_obj
        response = client.get("/runs/sample-run")

    assert response.status_code == 200
    assert response.json() == {
        "name": "sample-run",
        "phase": "Succeeded",
        "start_time": "2026-09-12T00:00:00+00:00",
        "completion_time": "2026-09-12T00:01:00+00:00",
        "pod_name": "sample-run-abc12",
        "log_url": None,
    }


def test_get_run_detail_returns_404_when_not_found() -> None:
    with patch("app.runs.custom_objects_api") as custom_objects_api:
        custom_objects_api.return_value.get_namespaced_custom_object.side_effect = ApiException(
            status=404
        )
        response = client.get("/runs/does-not-exist")

    assert response.status_code == 404


def test_build_pipelinerun_object_from_request() -> None:
    req = CreateRunRequest(
        name="new-run",
        repo="https://example.com/r.git",
        commit="abc123",
        steps=[{"name": "build", "image": "alpine"}],
    )

    obj = build_pipelinerun_object(req)

    assert obj["apiVersion"] == "trident.dev/v1"
    assert obj["kind"] == "PipelineRun"
    assert obj["metadata"]["name"] == "new-run"
    assert obj["spec"] == {
        "repo": "https://example.com/r.git",
        "commit": "abc123",
        "steps": [{"name": "build", "image": "alpine"}],
    }


def test_post_run_creates_pipelinerun() -> None:
    created_obj = {
        "metadata": {"name": "new-run"},
        "status": {},
    }

    with patch("app.runs.custom_objects_api") as custom_objects_api:
        custom_objects_api.return_value.create_namespaced_custom_object.return_value = created_obj
        response = client.post(
            "/runs",
            json={
                "name": "new-run",
                "repo": "https://example.com/r.git",
                "commit": "abc123",
                "steps": [{"name": "build", "image": "alpine"}],
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "name": "new-run",
        "phase": None,
        "start_time": None,
        "completion_time": None,
    }
    _, kwargs = custom_objects_api.return_value.create_namespaced_custom_object.call_args
    assert kwargs["body"]["spec"]["repo"] == "https://example.com/r.git"


def test_post_run_returns_409_when_already_exists() -> None:
    with patch("app.runs.custom_objects_api") as custom_objects_api:
        custom_objects_api.return_value.create_namespaced_custom_object.side_effect = (
            ApiException(status=409)
        )
        response = client.post(
            "/runs",
            json={
                "name": "sample-run",
                "repo": "https://example.com/r.git",
                "commit": "abc123",
                "steps": [{"name": "build", "image": "alpine"}],
            },
        )

    assert response.status_code == 409
