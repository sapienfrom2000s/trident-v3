from pipelineruns import build_pipelinerun_status_patch, find_owning_pipelinerun


def test_find_owning_pipelinerun_returns_name_when_owned():
    owner_references = [
        {"apiVersion": "trident.dev/v1", "kind": "PipelineRun", "name": "sample-run"}
    ]

    assert find_owning_pipelinerun(owner_references) == "sample-run"


def test_find_owning_pipelinerun_ignores_owners_of_other_kinds():
    owner_references = [
        {"apiVersion": "apps/v1", "kind": "ReplicaSet", "name": "some-replicaset"}
    ]

    assert find_owning_pipelinerun(owner_references) is None


def test_find_owning_pipelinerun_ignores_other_groups_pipelinerun_kind():
    owner_references = [
        {"apiVersion": "other.group/v1", "kind": "PipelineRun", "name": "sample-run"}
    ]

    assert find_owning_pipelinerun(owner_references) is None


def test_find_owning_pipelinerun_returns_none_when_no_owners():
    assert find_owning_pipelinerun(None) is None
    assert find_owning_pipelinerun([]) is None


def test_status_patch_for_pending_has_no_completion_time():
    patch = build_pipelinerun_status_patch("Pending")

    assert patch["phase"] == "Pending"
    assert "completionTime" not in patch


def test_status_patch_for_running_has_no_completion_time():
    patch = build_pipelinerun_status_patch("Running")

    assert patch["phase"] == "Running"
    assert "completionTime" not in patch


def test_status_patch_for_succeeded_sets_completion_time():
    patch = build_pipelinerun_status_patch("Succeeded")

    assert patch["phase"] == "Succeeded"
    assert "completionTime" in patch


def test_status_patch_for_failed_sets_completion_time():
    patch = build_pipelinerun_status_patch("Failed")

    assert patch["phase"] == "Failed"
    assert "completionTime" in patch
