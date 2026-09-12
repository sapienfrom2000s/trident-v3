import subprocess
import tempfile
from pathlib import Path

from pods import BUILD_SCRIPT_PATH


def _init_repo_with_trident_yml(repo_dir: Path, trident_yml: str) -> str:
    subprocess.run(["git", "init", "-q", str(repo_dir)], check=True)
    (repo_dir / ".trident.yml").write_text(trident_yml)
    subprocess.run(["git", "-C", str(repo_dir), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo_dir),
            "-c",
            "user.email=t@t.com",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "x",
        ],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _run_build_script(
    tmp_path: Path, repo_url: str, commit: str
) -> subprocess.CompletedProcess:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    return subprocess.run(
        ["go", "run", str(BUILD_SCRIPT_PATH), repo_url, commit],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )


def test_runs_commands_from_trident_yml_in_order():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_repo = tmp_path / "source"
        source_repo.mkdir()
        commit = _init_repo_with_trident_yml(source_repo, "- echo one\n- echo two\n")

        result = _run_build_script(tmp_path, f"file://{source_repo}", commit)

    assert result.returncode == 0
    assert "+ echo one" in result.stdout
    assert "one" in result.stdout
    assert "+ echo two" in result.stdout
    assert "two" in result.stdout
    assert "done" in result.stdout


def test_stops_and_fails_when_a_command_fails():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_repo = tmp_path / "source"
        source_repo.mkdir()
        commit = _init_repo_with_trident_yml(
            source_repo, "- echo before\n- false\n- echo after\n"
        )

        result = _run_build_script(tmp_path, f"file://{source_repo}", commit)

    assert result.returncode != 0
    assert "before" in result.stdout
    assert "after" not in result.stdout
    assert "done" not in result.stdout


def test_clone_and_checkout_only_when_no_trident_yml():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_repo = tmp_path / "source"
        source_repo.mkdir()
        subprocess.run(["git", "init", "-q", str(source_repo)], check=True)
        (source_repo / "README.md").write_text("hi")
        subprocess.run(["git", "-C", str(source_repo), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(source_repo),
                "-c",
                "user.email=t@t.com",
                "-c",
                "user.name=t",
                "commit",
                "-q",
                "-m",
                "x",
            ],
            check=True,
        )
        commit = subprocess.run(
            ["git", "-C", str(source_repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        result = _run_build_script(tmp_path, f"file://{source_repo}", commit)

    assert result.returncode == 0
    assert result.stdout.strip() == "done"
