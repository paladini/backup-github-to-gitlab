from dataclasses import dataclass
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
