import kopf

from controller import build_pipelinerun_status_patch, build_pod_spec, find_owning_pipelinerun


def test_build_pod_spec_uses_generate_name_from_pipelinerun_name():
    pod = build_pod_spec("sample-run", {"repo": "https://example.com/r.git", "commit": "abc123"})

    assert pod["metadata"]["generateName"] == "sample-run-"


def test_build_pod_spec_never_restarts():
    pod = build_pod_spec("sample-run", {"repo": "https://example.com/r.git", "commit": "abc123"})

    assert pod["spec"]["restartPolicy"] == "Never"


def test_build_pod_spec_container_image_and_command_from_spec():
    pod = build_pod_spec("sample-run", {"repo": "https://example.com/r.git", "commit": "abc123"})
    [container] = pod["spec"]["containers"]

    assert container["image"] == "alpine/git"
    assert container["command"][-2:] == ["https://example.com/r.git", "abc123"]


def test_build_pod_spec_derives_command_args_per_pipelinerun():
    pod_a = build_pod_spec("run-a", {"repo": "https://example.com/a.git", "commit": "aaa"})
    pod_b = build_pod_spec("run-b", {"repo": "https://example.com/b.git", "commit": "bbb"})

    assert pod_a["spec"]["containers"][0]["command"][-2:] == ["https://example.com/a.git", "aaa"]
    assert pod_b["spec"]["containers"][0]["command"][-2:] == ["https://example.com/b.git", "bbb"]


def test_owner_reference_points_at_pipelinerun():
    pod = build_pod_spec("sample-run", {"repo": "https://example.com/r.git", "commit": "abc123"})
    body = {
        "apiVersion": "trident.dev/v1",
        "kind": "PipelineRun",
        "metadata": {"name": "sample-run", "namespace": "default", "uid": "abc-123-uid"},
    }

    kopf.adopt(pod, owner=body)

    [owner_ref] = pod["metadata"]["ownerReferences"]
    assert owner_ref["apiVersion"] == "trident.dev/v1"
    assert owner_ref["kind"] == "PipelineRun"
    assert owner_ref["name"] == "sample-run"
    assert owner_ref["uid"] == "abc-123-uid"
    assert owner_ref["controller"] is True
    assert owner_ref["blockOwnerDeletion"] is True


def test_find_owning_pipelinerun_returns_name_when_owned():
    owner_references = [{"apiVersion": "trident.dev/v1", "kind": "PipelineRun", "name": "sample-run"}]

    assert find_owning_pipelinerun(owner_references) == "sample-run"


def test_find_owning_pipelinerun_ignores_owners_of_other_kinds():
    owner_references = [{"apiVersion": "apps/v1", "kind": "ReplicaSet", "name": "some-replicaset"}]

    assert find_owning_pipelinerun(owner_references) is None


def test_find_owning_pipelinerun_ignores_other_groups_pipelinerun_kind():
    owner_references = [{"apiVersion": "other.group/v1", "kind": "PipelineRun", "name": "sample-run"}]

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
