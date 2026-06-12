import gitlab
from gitlab.exceptions import GitlabGetError
from src.models import RepoInfo


class GitlabClient:
    def __init__(self, token: str, username: str, gitlab_url: str):
        self._gl = gitlab.Gitlab(gitlab_url, private_token=token)
        self._username = username

    def repo_exists(self, name: str) -> bool:
        try:
            self._gl.projects.get(f"{self._username}/{name}")
            return True
        except GitlabGetError:
            return False

    def create_repo(self, repo: RepoInfo) -> str:
        visibility = "private" if repo.is_private else "public"
        project = self._gl.projects.create({
            "name": repo.name,
            "description": repo.description,
            "visibility": visibility,
        })
        return project.ssh_url_to_repo

    def get_ssh_url(self, name: str) -> str:
        project = self._gl.projects.get(f"{self._username}/{name}")
        return project.ssh_url_to_repo
