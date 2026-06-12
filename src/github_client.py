from github import Github
from src.models import RepoInfo


class GithubClient:
    def __init__(self, token: str, username: str):
        self._github = Github(token)
        self._username = username

    def list_repos(self, include_forks: bool = False, include_archived: bool = True) -> list[RepoInfo]:
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
