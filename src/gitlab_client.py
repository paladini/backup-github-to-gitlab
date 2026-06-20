import re
import time
from typing import Callable

import gitlab
from gitlab.exceptions import GitlabCreateError, GitlabGetError, GitlabHttpError
from rich.console import Console

from src.models import LabelData, MilestoneData, RepoInfo

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

    def get_project_id(self, name: str) -> int | None:
        try:
            project = self._call(self._gl.projects.get, f"{self._username}/{name}")
            return project.id
        except GitlabGetError:
            return None

    def get_wiki_ssh_url(self, name: str) -> str:
        project = self._call(self._gl.projects.get, f"{self._username}/{name}")
        return project.ssh_url_to_repo.replace(f"{name}.git", f"{name}.wiki.git")

    def list_issues_markers(self, project_id: int) -> set[int]:
        project = self._call(self._gl.projects.get, project_id)
        migrated: set[int] = set()
        page = 1
        while True:
            issues = self._call(project.issues.list, page=page, per_page=100)
            if not issues:
                break
            for issue in issues:
                body = issue.description or ""
                match = re.search(r"<!-- github-issue-id: (\d+) -->", body)
                if match:
                    migrated.add(int(match.group(1)))
            if len(issues) < 100:
                break
            page += 1
        return migrated

    def list_labels(self, project_id: int) -> set[str]:
        project = self._call(self._gl.projects.get, project_id)
        names: set[str] = set()
        page = 1
        while True:
            labels = self._call(project.labels.list, page=page, per_page=100)
            if not labels:
                break
            for label in labels:
                names.add(label.name)
            if len(labels) < 100:
                break
            page += 1
        return names

    def create_label(self, project_id: int, label: LabelData) -> None:
        project = self._call(self._gl.projects.get, project_id)
        try:
            self._call(project.labels.create, {
                "name": label.name,
                "color": f"#{label.color}",
                "description": label.description,
            })
        except GitlabCreateError as e:
            if e.response_code != 409:
                raise

    def list_milestones(self, project_id: int) -> dict[str, int]:
        project = self._call(self._gl.projects.get, project_id)
        result: dict[str, int] = {}
        page = 1
        while True:
            milestones = self._call(project.milestones.list, page=page, per_page=100)
            if not milestones:
                break
            for ms in milestones:
                result[ms.title] = ms.id
            if len(milestones) < 100:
                break
            page += 1
        return result

    def create_milestone(self, project_id: int, ms: MilestoneData) -> int:
        project = self._call(self._gl.projects.get, project_id)
        data: dict = {"title": ms.title, "description": ms.description}
        if ms.due_date:
            data["due_date"] = ms.due_date
        created = self._call(project.milestones.create, data)
        return created.id

    def close_milestone(self, project_id: int, milestone_id: int) -> None:
        project = self._call(self._gl.projects.get, project_id)
        ms = self._call(project.milestones.get, milestone_id)
        ms.state_event = "close"
        self._call(ms.save)

    def create_issue(
        self,
        project_id: int,
        title: str,
        body: str,
        label_names: list[str],
        milestone_id: int | None,
    ) -> int:
        project = self._call(self._gl.projects.get, project_id)
        data: dict = {"title": title, "description": body, "labels": ",".join(label_names)}
        if milestone_id is not None:
            data["milestone_id"] = milestone_id
        issue = self._call(project.issues.create, data)
        return issue.iid

    def close_issue(self, project_id: int, issue_iid: int) -> None:
        project = self._call(self._gl.projects.get, project_id)
        issue = self._call(project.issues.get, issue_iid)
        issue.state_event = "close"
        self._call(issue.save)

    def add_issue_comment(self, project_id: int, issue_iid: int, body: str) -> None:
        project = self._call(self._gl.projects.get, project_id)
        issue = self._call(project.issues.get, issue_iid)
        self._call(issue.notes.create, {"body": body})

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
