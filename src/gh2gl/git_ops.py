import os
import shutil
import stat
import subprocess
from pathlib import Path


class GitOpsError(Exception):
    pass


def _handle_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


class GitOps:
    def __init__(self, temp_dir: str | Path, verbose: bool = False):
        self._temp_dir = Path(temp_dir)
        self._verbose = verbose
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    def _make_env(self) -> dict:
        env = os.environ.copy()
        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=accept-new"
        return env

    def _run(self, cmd: list[str], cwd: Path | None = None) -> None:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=not self._verbose,
            env=self._make_env(),
        )
        if result.returncode != 0:
            stderr = result.stderr.decode() if result.stderr else ""
            raise GitOpsError(
                f"Command {cmd[0]} failed (exit {result.returncode}): {stderr.strip()}"
            )

    def clone(self, github_ssh_url: str, repo_name: str) -> Path:
        clone_path = self._temp_dir / f"{repo_name}.git"
        if clone_path.exists():
            shutil.rmtree(clone_path, onerror=_handle_readonly)
        self._run(["git", "clone", "--mirror", github_ssh_url, str(clone_path)])
        return clone_path

    def push(self, clone_path: Path, gitlab_ssh_url: str) -> None:
        self._run(["git", "push", "--mirror", gitlab_ssh_url], cwd=clone_path)

    def cleanup(self, clone_path: Path) -> None:
        if Path(clone_path).exists():
            shutil.rmtree(clone_path, onerror=_handle_readonly)
