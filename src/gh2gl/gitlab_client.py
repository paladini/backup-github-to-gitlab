import time
from typing import Callable

import gitlab
from gitlab.exceptions import GitlabGetError, GitlabHttpError
from rich.console import Console

from gh2gl.models import RepoInfo

_console = Console()
_RATE_LIMIT_SLEEP = 60
_MAX_RETRIES = 4


class GitlabClient:
    def __init__(self, token: str, username: str, gitlab_url: str):
        self._gl = gitlab.Gitlab(gitlab_url, private_token=token)
        self._username = username

    def repo_exists(self, name: str) -> bool:
        try:
            self._call(self._gl.projects.get, f"{self._username}/{name}")
            return True
        except GitlabGetError:
            return False

    def create_repo(self, repo: RepoInfo) -> str:
        visibility = "private" if repo.is_private else "public"
        project = self._call(self._gl.projects.create, {
            "name": repo.name,
            "description": repo.description,
            "visibility": visibility,
        })
        return project.ssh_url_to_repo

    def get_ssh_url(self, name: str) -> str:
        project = self._call(self._gl.projects.get, f"{self._username}/{name}")
        return project.ssh_url_to_repo

    def _call(self, func: Callable, *args, **kwargs):
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except GitlabHttpError as e:
                if e.response_code == 429 and attempt < _MAX_RETRIES:
                    _console.print(
                        f"[yellow]GitLab rate limit reached (attempt {attempt}/{_MAX_RETRIES}). "
                        f"Waiting {_RATE_LIMIT_SLEEP}s...[/yellow]"
                    )
                    time.sleep(_RATE_LIMIT_SLEEP)
                else:
                    raise
