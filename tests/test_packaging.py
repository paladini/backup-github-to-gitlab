from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_action_yml_inputs_and_composite():
    data = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
    assert data["name"] == "gh2gl"
    assert data["runs"]["using"] == "composite"
    inputs = data["inputs"]
    assert inputs["config"]["default"] == "config.yaml"
    assert inputs["dry-run"]["default"] == "false"
    assert "github-token" not in inputs
    assert "gitlab-token" not in inputs
    run_all = "\n".join(step.get("run", "") for step in data["runs"]["steps"])
    assert "GH_BACKUP_TOKEN" in run_all
    assert "GITHUB_TOKEN" in run_all
    assert "SSH_PRIVATE_KEY" in run_all
    assert "--dry-run" in run_all


def test_dockerfile_uses_non_root_and_git():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "git" in text
    assert "openssh-client" in text
    assert "USER gh2gl" in text
    assert "docker-entrypoint.sh" in text


def test_entrypoint_maps_backup_token(tmp_path, monkeypatch):
    stub = tmp_path / "gh2gl"
    stub.write_text(
        "#!/bin/sh\nprintf '%s' \"$GITHUB_TOKEN\"\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os_path()}")
    monkeypatch.setenv("GH_BACKUP_TOKEN", "mapped-pat")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("SSH_PRIVATE_KEY", raising=False)

    result = subprocess_run_entrypoint()
    assert result == "mapped-pat"


def test_entrypoint_preserves_github_token_without_backup_token(tmp_path, monkeypatch):
    stub = tmp_path / "gh2gl"
    stub.write_text(
        "#!/bin/sh\nprintf '%s' \"$GITHUB_TOKEN\"\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os_path()}")
    monkeypatch.delenv("GH_BACKUP_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "direct-pat")
    monkeypatch.delenv("SSH_PRIVATE_KEY", raising=False)

    result = subprocess_run_entrypoint()
    assert result == "direct-pat"


def os_path() -> str:
    import os

    return os.environ.get("PATH", "")


def subprocess_run_entrypoint() -> str:
    import subprocess

    entry = ROOT / "docker-entrypoint.sh"
    proc = subprocess.run(
        ["sh", str(entry), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout
