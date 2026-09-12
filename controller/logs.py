LOG_TRUNCATE_BYTES = 100_000  # stay well under the ~1MiB etcd/ConfigMap object limit


def truncate_log(log: str, limit: int = LOG_TRUNCATE_BYTES) -> str:
    return log[-limit:]


def build_log_configmap(pipelinerun_name: str, log: str) -> dict:
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": f"{pipelinerun_name}-logs"},
        "data": {"log": truncate_log(log)},
    }
