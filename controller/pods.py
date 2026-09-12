from pathlib import Path

BUILD_SCRIPT_PATH = Path(__file__).parent / "buildscript" / "build.go"
BUILD_SCRIPT = BUILD_SCRIPT_PATH.read_text()

SETUP_SCRIPT = f"""
set -e
apk add --no-cache git >/dev/null
cat > /tmp/build.go <<'GOEOF'
{BUILD_SCRIPT}
GOEOF
go run /tmp/build.go "$1" "$2"
"""


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
                    "image": "golang:1.23-alpine",
                    "command": ["sh", "-c", SETUP_SCRIPT, "--", repo, commit],
                }
            ],
        },
    }
