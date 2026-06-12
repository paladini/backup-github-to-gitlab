import fnmatch

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from src.git_ops import GitOps
from src.github_client import GithubClient
from src.gitlab_client import GitlabClient
from src.models import BackupResult, Config, RepoInfo

_console = Console()


class BackupRunner:
    def __init__(self, config: Config, github: GithubClient, gitlab: GitlabClient, git_ops: GitOps):
        self._config = config
        self._github = github
        self._gitlab = gitlab
        self._git_ops = git_ops

    def run(self) -> list[BackupResult]:
        repos = self._github.list_repos(
            include_forks=self._config.include_forks,
            include_archived=self._config.include_archived,
        )

        if self._config.filter_pattern != "*":
            repos = [r for r in repos if fnmatch.fnmatch(r.name, self._config.filter_pattern)]
            if not repos:
                _console.print(
                    f"[yellow]Warning: --filter '{self._config.filter_pattern}' matched no repositories.[/yellow]"
                )
                return []

        results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=_console,
        ) as progress:
            task = progress.add_task("Backing up...", total=len(repos))
            for repo in repos:
                progress.update(task, description=f"[cyan]{repo.name}[/cyan]")
                result = self._backup_repo(repo)
                results.append(result)
                progress.advance(task)

        return results

    def _backup_repo(self, repo: RepoInfo) -> BackupResult:
        if self._config.dry_run:
            exists = self._gitlab.repo_exists(repo.name)
            action = "update" if exists else "create"
            visibility = "private" if repo.is_private else "public"
            return BackupResult(
                repo_name=repo.name,
                status="dry_run",
                message=f"would {action} as {visibility}",
            )

        clone_path = None
        try:
            exists = self._gitlab.repo_exists(repo.name)
            if exists:
                gitlab_ssh_url = self._gitlab.get_ssh_url(repo.name)
            else:
                gitlab_ssh_url = self._gitlab.create_repo(repo)

            clone_path = self._git_ops.clone(repo.ssh_url, repo.name)
            self._git_ops.push(clone_path, gitlab_ssh_url)
            return BackupResult(repo_name=repo.name, status="success", message="")
        except Exception as e:
            return BackupResult(repo_name=repo.name, status="error", message=str(e))
        finally:
            if clone_path is not None and clone_path.exists():
                self._git_ops.cleanup(clone_path)
