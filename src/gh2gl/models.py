from dataclasses import dataclass, field
from typing import Literal


@dataclass
class RepoInfo:
    name: str
    full_name: str
    ssh_url: str
    is_private: bool
    is_fork: bool
    is_archived: bool
    description: str
    default_branch: str


@dataclass
class BackupResult:
    repo_name: str
    status: Literal["success", "skip", "error", "dry_run"]
    message: str


@dataclass
class Config:
    github_username: str
    github_token: str
    gitlab_username: str
    gitlab_token: str
    gitlab_url: str
    include_forks: bool
    include_archived: bool
    temp_dir: str
    dry_run: bool
    filter_pattern: str
    verbose: bool
    backup_wiki: bool = False
    backup_issues: bool = False


@dataclass
class LabelData:
    name: str
    color: str
    description: str


@dataclass
class MilestoneData:
    github_number: int
    title: str
    description: str
    state: Literal["open", "closed"]
    due_date: str | None


@dataclass
class CommentData:
    author: str
    created_at: str
    body: str


@dataclass
class IssueData:
    github_number: int
    title: str
    body: str
    state: Literal["open", "closed"]
    author: str
    created_at: str
    labels: list[str]
    milestone_number: int | None
    comments: list[CommentData] = field(default_factory=list)


@dataclass
class IssueMigratorResult:
    repo_name: str
    created: int
    skipped: int
    errors: int
