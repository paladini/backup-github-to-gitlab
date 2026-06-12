import time
from datetime import datetime, timezone

from github import Github, RateLimitExceededException
from rich.console import Console

from src.models import RepoInfo

_console = Console()


class GithubClient:
    def __init__(self, token: str, username: str):
        self._github = Github(token)
        self._username = username

    def list_repos(self, include_forks: bool = False, include_archived: bool = True) -> list[RepoInfo]:
        while True:
            try:
                return self._fetch_repos(include_forks, include_archived)
            except RateLimitExceededException:
                self._wait_for_rate_limit_reset()

    def _fetch_repos(self, include_forks: bool, include_archived: bool) -> list[RepoInfo]:
        user = self._github.get_user()
        repos = []
        for repo in user.get_repos(type="owner"):
            if not include_forks and repo.fork:
                continue
            if not include_archived and repo.archived:
                continue
            repos.append(RepoInfo(
                name=repo.name,
                full_name=repo.full_name,
                ssh_url=repo.ssh_url,
                is_private=repo.private,
                is_fork=repo.fork,
                is_archived=repo.archived,
                description=repo.description or "",
                default_branch=repo.default_branch,
            ))
        return repos

    def _wait_for_rate_limit_reset(self) -> None:
        reset_time = self._github.get_rate_limit().core.reset
        sleep_seconds = max(1, (reset_time - datetime.now(timezone.utc)).total_seconds()) + 5
        _console.print(
            f"[yellow]GitHub rate limit reached. "
            f"Waiting {sleep_seconds:.0f}s until reset...[/yellow]"
        )
        time.sleep(sleep_seconds)
