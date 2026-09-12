from logs import build_log_configmap, truncate_log


def test_truncate_log_leaves_short_log_untouched():
    log = "line one\nline two\n"

    assert truncate_log(log) == log


def test_truncate_log_keeps_only_the_tail():
    log = "x" * 200_000

    truncated = truncate_log(log, limit=100)

    assert truncated == "x" * 100
    assert truncated == log[-100:]


def test_build_log_configmap_names_it_after_the_pipelinerun():
    configmap = build_log_configmap("sample-run", "some log output")

    assert configmap["metadata"]["name"] == "sample-run-logs"
    assert configmap["data"]["log"] == "some log output"


def test_build_log_configmap_truncates_long_logs():
    configmap = build_log_configmap("sample-run", "x" * 200_000)

    assert len(configmap["data"]["log"]) == 100_000
