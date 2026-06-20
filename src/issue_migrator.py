from rich.console import Console

from src.github_client import GithubClient
from src.gitlab_client import GitlabClient
from src.models import IssueData, IssueMigratorResult

_console = Console()


class IssueMigrator:
    def __init__(self, github: GithubClient, gitlab: GitlabClient, verbose: bool = False):
        self._github = github
        self._gitlab = gitlab
        self._verbose = verbose

    def migrate(self, repo_name: str, project_id: int, dry_run: bool) -> IssueMigratorResult:
        label_map = self._sync_labels(repo_name, project_id, dry_run)
        milestone_map = self._sync_milestones(repo_name, project_id, dry_run)
        migrated_ids = set() if dry_run else self._gitlab.list_issues_markers(project_id)

        issues = self._github.list_issues(repo_name)
        new_issues = [i for i in issues if i.github_number not in migrated_ids]

        if dry_run:
            _console.print(
                f"  [dim]Issues: {len(issues)} total, "
                f"{len(issues) - len(new_issues)} already migrated, "
                f"{len(new_issues)} would be created[/dim]"
            )
            return IssueMigratorResult(
                repo_name=repo_name,
                created=0,
                skipped=len(issues) - len(new_issues),
                errors=0,
            )

        created = 0
        skipped = len(issues) - len(new_issues)
        errors = 0

        for issue in new_issues:
            try:
                self._migrate_issue(issue, project_id, label_map, milestone_map)
                created += 1
                if self._verbose:
                    _console.print(f"  [dim]  ✓ issue #{issue.github_number}: {issue.title}[/dim]")
            except Exception as e:
                errors += 1
                _console.print(
                    f"  [red]  ✗ issue #{issue.github_number} failed: {e}[/red]"
                )

        return IssueMigratorResult(
            repo_name=repo_name,
            created=created,
            skipped=skipped,
            errors=errors,
        )

    def _sync_labels(self, repo_name: str, project_id: int, dry_run: bool) -> dict[str, int]:
        gh_labels = self._github.list_labels(repo_name)
        if not gh_labels:
            return {}
        if not dry_run:
            existing = self._gitlab.list_labels(project_id)
            for label in gh_labels:
                if label.name not in existing:
                    self._gitlab.create_label(project_id, label)
        return {label.name: 0 for label in gh_labels}

    def _sync_milestones(
        self, repo_name: str, project_id: int, dry_run: bool
    ) -> dict[int, int]:
        gh_milestones = self._github.list_milestones(repo_name)
        if not gh_milestones:
            return {}
        if dry_run:
            return {ms.github_number: 0 for ms in gh_milestones}

        existing = self._gitlab.list_milestones(project_id)
        milestone_map: dict[int, int] = {}

        for ms in gh_milestones:
            if ms.title in existing:
                milestone_map[ms.github_number] = existing[ms.title]
            else:
                gl_id = self._gitlab.create_milestone(project_id, ms)
                if ms.state == "closed":
                    self._gitlab.close_milestone(project_id, gl_id)
                milestone_map[ms.github_number] = gl_id

        return milestone_map

    def _migrate_issue(
        self,
        issue: IssueData,
        project_id: int,
        label_map: dict[str, int],
        milestone_map: dict[int, int],
    ) -> None:
        body = self._format_issue_body(issue)
        milestone_id = milestone_map.get(issue.milestone_number) if issue.milestone_number else None
        issue_iid = self._gitlab.create_issue(
            project_id=project_id,
            title=issue.title,
            body=body,
            label_names=issue.labels,
            milestone_id=milestone_id,
        )
        if issue.state == "closed":
            self._gitlab.close_issue(project_id, issue_iid)
        for comment in issue.comments:
            self._gitlab.add_issue_comment(
                project_id, issue_iid, self._format_comment_body(comment)
            )

    def _format_issue_body(self, issue: IssueData) -> str:
        date = issue.created_at[:10]
        header = f"> 🔄 Migrado do GitHub — originalmente reportado por @{issue.author} em {date}"
        parts = [header]
        if issue.body:
            parts.append("")
            parts.append(issue.body)
        parts.append("")
        parts.append(f"<!-- github-issue-id: {issue.github_number} -->")
        return "\n".join(parts)

    def _format_comment_body(self, comment: "CommentData") -> str:  # noqa: F821
        ts = comment.created_at[:16].replace("T", " ")
        header = f"> 🔄 @{comment.author} em {ts} UTC"
        if comment.body:
            return f"{header}\n\n{comment.body}"
        return header
