import argparse
import sys

from rich.console import Console
from rich.table import Table

from src.backup_runner import BackupRunner
from src.config import ConfigError, load_config, validate_config
from src.git_ops import GitOps
from src.github_client import GithubClient
from src.gitlab_client import GitlabClient

_console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="backup.py",
        description="Backup GitHub repositories to GitLab, preserving visibility.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python backup.py                           backup all personal repos
  python backup.py --dry-run                 preview without making changes
  python backup.py --filter "myproject-*"   backup only matching repos
  python backup.py --include-forks           include forked repositories
  python backup.py --verbose                 show git command output
        """,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="show what would be done without making any changes",
    )
    parser.add_argument(
        "--filter", metavar="PATTERN", dest="filter_pattern",
        help="only backup repos matching glob pattern (e.g. 'myproject-*')",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="show detailed git output for debugging",
    )
    parser.add_argument(
        "--include-forks", action="store_true",
        help="include forked repositories (default: skip forks)",
    )
    parser.add_argument(
        "--include-archived", action="store_true",
        help="force-include archived repositories even if config says false",
    )
    parser.add_argument(
        "--config", metavar="PATH", default="config.yaml",
        help="path to config file (default: config.yaml)",
    )
    args = parser.parse_args()

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
        _console.print("\n[yellow][DRY RUN] Nenhuma operação foi executada.[/yellow]")


if __name__ == "__main__":
    main()
