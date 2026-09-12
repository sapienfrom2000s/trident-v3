CLONE_SCRIPT = 'git clone "$1" repo && cd repo && git checkout "$2" && echo done'


def build_pod_spec(name: str, spec: dict) -> dict:
    repo = spec["repo"]
    commit = spec["commit"]

    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"generateName": f"{name}-"},
        "spec": {
            "restartPolicy": "Never",
            "containers": [
                {
                    "name": "build",
                    "image": "alpine/git",
                    "command": ["sh", "-c", CLONE_SCRIPT, "--", repo, commit],
                }
            ],
        },
    }
