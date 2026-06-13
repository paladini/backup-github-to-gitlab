import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from gh2gl.backup_runner import BackupRunner
from gh2gl.config import ConfigError, load_config, validate_config
from gh2gl.git_ops import GitOps
from gh2gl.github_client import GithubClient
from gh2gl.gitlab_client import GitlabClient

_console = Console()

INIT_FOLDER = "github-backup"

_CONFIG_TEMPLATE = """\
github:
  username: seu-usuario-github

gitlab:
  username: seu-usuario-gitlab
  url: https://gitlab.com

backup:
  include_forks: false
  include_archived: true
  # temp_dir: ./tmp
"""

_ENV_TEMPLATE = """\
GITHUB_TOKEN=seu-token-github
GITLAB_TOKEN=seu-token-gitlab
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gh2gl",
        description="Mirror GitHub repositories to GitLab, preserving visibility.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  gh2gl init                         create workspace folder with config files
  gh2gl --dry-run                    preview without making changes
  gh2gl --filter "myproject-*"       backup only matching repos
  gh2gl --include-forks              include forked repositories
  gh2gl --verbose                    show git command output
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    backup_parser = subparsers.add_parser(
        "backup",
        help="run the backup (default when no subcommand is given)",
    )
    _add_backup_args(backup_parser)

    subparsers.add_parser(
        "init",
        help=f"create a '{INIT_FOLDER}/' workspace folder with config.yaml and .env",
    )

    # Top-level backup args for backwards compat: `gh2gl --dry-run` works without subcommand
    _add_backup_args(parser)

    args = parser.parse_args()

    if args.command == "init":
        _cmd_init()
    else:
        _cmd_backup(args)


def _add_backup_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--dry-run", action="store_true",
        help="show what would be done without making any changes",
    )
    p.add_argument(
        "--filter", metavar="PATTERN", dest="filter_pattern",
        help="only backup repos matching glob pattern (e.g. 'myproject-*')",
    )
    p.add_argument(
        "--verbose", action="store_true",
        help="show detailed git output for debugging",
    )
    p.add_argument(
        "--include-forks", action="store_true",
        help="include forked repositories (default: skip forks)",
    )
    p.add_argument(
        "--include-archived", action="store_true",
        help="force-include archived repositories even if config says false",
    )
    p.add_argument(
        "--config", metavar="PATH", default="config.yaml",
        help="path to config file (default: config.yaml)",
    )


def _cmd_backup(args: argparse.Namespace) -> None:
    overrides: dict = {}
    if args.dry_run:
        overrides["dry_run"] = True
    if args.filter_pattern:
        overrides["filter_pattern"] = args.filter_pattern
    if args.verbose:
        overrides["verbose"] = True
    if args.include_forks:
        overrides["include_forks"] = True
    if args.include_archived:
        overrides["include_archived"] = True

    try:
        config = load_config(args.config, overrides)
        validate_config(config)
    except ConfigError as e:
        _console.print(f"[bold red]Configuration error:[/bold red] {e}")
        sys.exit(1)

    if config.dry_run:
        _console.print("[yellow bold]DRY RUN MODE — no changes will be made[/yellow bold]\n")

    github = GithubClient(config.github_token, config.github_username)
    gitlab = GitlabClient(config.gitlab_token, config.gitlab_username, config.gitlab_url)
    git_ops = GitOps(config.temp_dir, config.verbose)
    runner = BackupRunner(config, github, gitlab, git_ops)

    results = runner.run()

    _print_report(results, config.dry_run)

    if any(r.status == "error" for r in results):
        sys.exit(1)


def _cmd_init() -> None:
    folder = Path(INIT_FOLDER)
    if folder.exists():
        _console.print(f"[yellow]Folder already exists:[/yellow] {folder}/")
        _console.print(f"  Edit [cyan]{folder}/config.yaml[/cyan] and [cyan]{folder}/.env[/cyan]")
        _console.print(f"  Then run [bold cyan]gh2gl[/bold cyan] from inside that folder.")
        return

    folder.mkdir()
    (folder / "config.yaml").write_text(_CONFIG_TEMPLATE, encoding="utf-8")
    (folder / ".env").write_text(_ENV_TEMPLATE, encoding="utf-8")

    _console.print(f"[green]Created:[/green] {folder}/config.yaml")
    _console.print(f"[green]Created:[/green] {folder}/.env")
    _console.print()
    _console.print("[bold]Next steps:[/bold]")
    _console.print(f"  [cyan]cd {folder}[/cyan]")
    _console.print(f"  # Edit config.yaml — set github.username and gitlab.username")
    _console.print(f"  # Edit .env — set GITHUB_TOKEN and GITLAB_TOKEN")
    _console.print(f"  [cyan]gh2gl --dry-run[/cyan]    # preview")
    _console.print(f"  [cyan]gh2gl[/cyan]              # run backup")


def _print_report(results: list, dry_run: bool) -> None:
    status_display = {
        "success": "[green]✓ success[/green]",
        "skip":    "[blue]→ skip[/blue]",
        "error":   "[red]✗ error[/red]",
        "dry_run": "[yellow]~ dry run[/yellow]",
    }

    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Repository", style="cyan", min_width=30)
    table.add_column("Status", min_width=14)
    table.add_column("Details", style="dim")

    for r in results:
        table.add_row(r.repo_name, status_display.get(r.status, r.status), r.message)

    _console.print()
    _console.print(table)

    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    parts = []
    if counts.get("success"):
        parts.append(f"[green]{counts['success']} copied[/green]")
    if counts.get("skip"):
        parts.append(f"[blue]{counts['skip']} skipped[/blue]")
    if counts.get("dry_run"):
        parts.append(f"[yellow]{counts['dry_run']} dry run[/yellow]")
    if counts.get("error"):
        parts.append(f"[red]{counts['error']} errors[/red]")

    _console.print(" • ".join(parts) if parts else "[dim]nothing to report[/dim]")

    if dry_run:
        _console.print("\n[yellow][DRY RUN] No operations were executed.[/yellow]")
