from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.runs import pipelinerun_to_summary

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
