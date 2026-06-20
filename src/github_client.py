import time
from datetime import datetime, timezone

from github import Github, RateLimitExceededException
from rich.console import Console

from src.models import CommentData, IssueData, LabelData, MilestoneData, RepoInfo

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

    def get_wiki_ssh_url(self, repo_name: str) -> str:
        return f"git@github.com:{self._username}/{repo_name}.wiki.git"

    def list_labels(self, repo_name: str) -> list[LabelData]:
        while True:
            try:
                return self._fetch_labels(repo_name)
            except RateLimitExceededException:
                self._wait_for_rate_limit_reset()

    def _fetch_labels(self, repo_name: str) -> list[LabelData]:
        repo = self._github.get_user().get_repo(repo_name)
        result = []
        for label in repo.get_labels():
            result.append(LabelData(
                name=label.name,
                color=label.color,
                description=label.description or "",
            ))
        return result

    def list_milestones(self, repo_name: str) -> list[MilestoneData]:
        while True:
            try:
                return self._fetch_milestones(repo_name)
            except RateLimitExceededException:
                self._wait_for_rate_limit_reset()

    def _fetch_milestones(self, repo_name: str) -> list[MilestoneData]:
        repo = self._github.get_user().get_repo(repo_name)
        result = []
        for ms in repo.get_milestones(state="all"):
            due_date = ms.due_on.strftime("%Y-%m-%d") if ms.due_on else None
            result.append(MilestoneData(
                github_number=ms.number,
                title=ms.title,
                description=ms.description or "",
                state="closed" if ms.state == "closed" else "open",
                due_date=due_date,
            ))
        return result

    def list_issue_comments(self, repo_name: str, issue_number: int) -> list[CommentData]:
        while True:
            try:
                return self._fetch_issue_comments(repo_name, issue_number)
            except RateLimitExceededException:
                self._wait_for_rate_limit_reset()

    def _fetch_issue_comments(self, repo_name: str, issue_number: int) -> list[CommentData]:
        repo = self._github.get_user().get_repo(repo_name)
        issue = repo.get_issue(issue_number)
        result = []
        for comment in issue.get_comments():
            result.append(CommentData(
                author=comment.user.login if comment.user else "unknown",
                created_at=comment.created_at.isoformat(),
                body=comment.body or "",
            ))
        return result

    def list_issues(self, repo_name: str) -> list[IssueData]:
        while True:
            try:
                return self._fetch_issues(repo_name)
            except RateLimitExceededException:
                self._wait_for_rate_limit_reset()

    def _fetch_issues(self, repo_name: str) -> list[IssueData]:
        repo = self._github.get_user().get_repo(repo_name)
        result = []
        for issue in repo.get_issues(state="all", sort="created", direction="asc"):
            if issue.pull_request is not None:
                continue
            comments = self._fetch_issue_comments(repo_name, issue.number)
            result.append(IssueData(
                github_number=issue.number,
                title=issue.title,
                body=issue.body or "",
                state="closed" if issue.state == "closed" else "open",
                author=issue.user.login if issue.user else "unknown",
                created_at=issue.created_at.isoformat(),
                labels=[label.name for label in issue.labels],
                milestone_number=issue.milestone.number if issue.milestone else None,
                comments=comments,
            ))
        return result

    def _wait_for_rate_limit_reset(self) -> None:
        reset_time = self._github.get_rate_limit().core.reset
        sleep_seconds = max(1, (reset_time - datetime.now(timezone.utc)).total_seconds()) + 5
        _console.print(
            f"[yellow]GitHub rate limit reached. "
            f"Waiting {sleep_seconds:.0f}s until reset...[/yellow]"
        )
        time.sleep(sleep_seconds)
