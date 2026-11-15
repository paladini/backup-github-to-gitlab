# gh2gl

> Mirror all your GitHub repositories to GitLab automatically — private stays private, public stays public.

[![PyPI](https://img.shields.io/pypi/v/gh2gl.svg)](https://pypi.org/project/gh2gl/)
[![Python](https://img.shields.io/badge/python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Why

Having all your code on a single platform is a risk. This tool clones every repository from your GitHub account and creates matching repositories on GitLab, preserving visibility exactly. Run it once for a full backup, run it again anytime to sync incrementally.

## Features

- **Visibility-safe** — private repos are *never* created as public; defaults to private when in doubt
- **Idempotent** — safe to re-run; existing GitLab repos receive incremental pushes, not duplicates
- **Full mirror** — clones all branches and tags via `git clone --mirror`
- **Wiki backup** — mirrors each repo's wiki (a separate git repo) to GitLab *(opt-in)*
- **Issue migration** — copies GitHub Issues with labels, milestones, and comments to GitLab *(opt-in)*
- **Dry-run mode** — preview every action before executing a single write
- **Selective backup** — filter by glob pattern (`--filter "myproject-*"`)
- **Works on Windows** — handles read-only `.git` files; tested on Windows 10 / PowerShell
- **Rich terminal output** — progress bar and per-repo status table
- **GitHub Action** — scheduled backups from a workflow without changing the CLI
- **Docker image** — `git` + Python image for cron on a NAS or VPS

## Prerequisites

- Python 3.11+
- `git` in your PATH
- SSH key registered on both GitHub and GitLab
- [GitHub token](#github-token) with `repo` scope
- [GitLab token](#gitlab-token) with `api` scope

## Quick Start

```bash
pip install gh2gl

gh2gl init
# Creates a github-backup/ folder in the current directory

cd github-backup
# Edit config.yaml — set github.username and gitlab.username
# Edit .env — set GITHUB_TOKEN and GITLAB_TOKEN

gh2gl --dry-run    # preview — no changes made
gh2gl              # run the backup
```

<details>
<summary>Running from source</summary>

```bash
git clone git@github.com:paladini/backup-github-to-gitlab.git
cd backup-github-to-gitlab
pip install -e .
```

</details>

## Token Setup

### GitHub token

1. Go to **Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token (classic)**
3. Select scope: `repo` (required to list private repositories)
4. Paste the token into `.env` as `GITHUB_TOKEN`

The CLI always reads **`GITHUB_TOKEN`**. GitHub Actions already injects a workflow token with that same name; it is **not** a `repo`-scope PAT and cannot list your private repositories. For the Action (and optionally Docker), set **`GH_BACKUP_TOKEN`** to your PAT — the wrapper maps it onto `GITHUB_TOKEN` before `gh2gl` runs. Do not rely on the default Actions `GITHUB_TOKEN`.

### GitLab token

1. Go to **User Settings → Access Tokens → Add new token**
2. Select scope: `api` (required to create projects)
3. Paste the token into `.env` as `GITLAB_TOKEN`

## Configuration

After running `gh2gl init`, two files are created in the `github-backup/` folder:

**`config.yaml`**:

```yaml
github:
  username: your-github-username

gitlab:
  username: your-gitlab-username    # can differ from GitHub
  url: https://gitlab.com           # change only for self-hosted GitLab

backup:
  include_forks: false      # include forked repositories? (default: false)
  include_archived: true    # include archived repositories? (default: true)
  # temp_dir: ./tmp         # temporary dir for clones — auto-cleaned after each repo

  # Extended backup (opt-in)
  backup_wiki: false        # mirror each repo's wiki to GitLab
  backup_issues: false      # migrate GitHub Issues to GitLab
```

**`.env`**:

```
GITHUB_TOKEN=ghp_...
GITLAB_TOKEN=glpat-...
```

Tokens are loaded at runtime and never logged. `.env` is in `.gitignore`.

## Usage

Run all commands from inside the `github-backup/` folder (or any folder with `config.yaml` and `.env`):

```bash
# Back up all personal repositories
gh2gl

# Preview what would happen — no writes
gh2gl --dry-run

# Back up only repos matching a pattern
gh2gl --filter "myproject-*"

# Include forks (skipped by default)
gh2gl --include-forks

# Verbose: show raw git output (useful for debugging SSH issues)
gh2gl --verbose

# Use a different config file
gh2gl --config /path/to/config.yaml
```

## GitHub Action (scheduled backups)

Keep `config.yaml` in the repository that *runs* the workflow (usernames only). Store tokens and the SSH key as repository secrets. Git clone/push still use SSH, same as the CLI.

**Secrets**

| Secret | Maps to | Purpose |
|---|---|---|
| `GH_BACKUP_TOKEN` | `GITHUB_TOKEN` (CLI) | Classic PAT with `repo` — **not** the default Actions token |
| `GITLAB_TOKEN` | `GITLAB_TOKEN` | GitLab PAT with `api` |
| `SSH_PRIVATE_KEY` | `~/.ssh/id_ed25519` | Private key whose public half is on GitHub **and** GitLab |

```yaml
name: Backup GitHub to GitLab
on:
  schedule:
    - cron: "0 3 * * *"   # daily 03:00 UTC
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: paladini/backup-github-to-gitlab@v1
        with:
          config: config.yaml
          # dry-run: "true"
          # filter: "myproject-*"
        env:
          GH_BACKUP_TOKEN: ${{ secrets.GH_BACKUP_TOKEN }}
          GITLAB_TOKEN: ${{ secrets.GITLAB_TOKEN }}
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
```

Action inputs: `config`, `dry-run`, `filter`, `include-forks`, `include-archived`, `verbose`. Tokens are **not** inputs (they can leak in logs); pass them only via `env` / secrets.

A copy-paste workflow lives at `examples/gitlab-backup.workflow.yml`.

## Docker / cron (NAS or VPS)

Image: **`ghcr.io/paladini/gh2gl`** (includes `git` and OpenSSH, runs as non-root user `gh2gl`).

| Tag | Meaning |
|---|---|
| `latest` | default branch |
| short git SHA | every publish from `main` |
| `1.0.0` | version tags (`v1.0.0`) |

```bash
docker pull ghcr.io/paladini/gh2gl:latest
docker run --rm ghcr.io/paladini/gh2gl:latest --help
```

**Compose** (see `docker-compose.example.yml`):

```yaml
services:
  gh2gl:
    image: ghcr.io/paladini/gh2gl:latest
    env_file: .env
    volumes:
      - ./config.yaml:/config/config.yaml:ro
    command: ["--config", "/config/config.yaml"]
```

`.env` can use the CLI names (`GITHUB_TOKEN`, `GITLAB_TOKEN`) or `GH_BACKUP_TOKEN` + `GITLAB_TOKEN`. Mount the config **file** (not a read-only directory) so clone temp files can be written. For SSH, either set `SSH_PRIVATE_KEY` in `.env` or mount a key at `/home/gh2gl/.ssh/id_ed25519`.

**Cron** on the host:

```
0 3 * * * cd /opt/gh2gl && docker compose run --rm gh2gl --config /config/config.yaml
```

Laptop install is unchanged: `pip install gh2gl`.

### Example output

```
DRY RUN MODE — no changes will be made

 my-private-repo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/10

Repository                     Status          Details
my-private-repo                ~ dry run       would create as private
my-public-site                 ~ dry run       would create as public
archived-experiment            ~ dry run       would create as private

10 dry run

[DRY RUN] No operations were executed.
```

## Security

Private repositories on GitHub are **always** created as private on GitLab. Visibility is derived exclusively from the GitHub API response — there is no code path that can promote a private repository to public. If visibility cannot be determined, the tool defaults to private and logs a warning.

SSH keys are used for all git operations. API tokens are read from environment variables (`.env`), never from the config file, and never written to logs.

## Wiki & Issue Backup

Enable in `config.yaml`:

```yaml
backup:
  backup_wiki: true
  backup_issues: true
```

**Wiki backup** clones each repo's wiki as a separate git repository and pushes it to the corresponding GitLab wiki. Repos without a wiki are skipped silently. Fully idempotent (`git push --mirror`).

**Issue migration** copies GitHub Issues (open and closed) to GitLab, including labels, milestones, and comments. Pull Requests are not migrated.

> **Known limitations for issue migration:**
>
> - **Timestamps are not preserved.** GitLab's API does not allow setting `created_at` without an admin token. All migrated issues will show the migration date.
> - **Authors are not preserved.** All issues and comments will be attributed to the token owner in GitLab. The original author and date are recorded at the top of each issue/comment body.
> - **Issue migration is idempotent.** A hidden marker (`<!-- github-issue-id: N -->`) is embedded in each migrated issue. Re-running the script skips already-migrated issues.

## Known Limitations

| Limitation | Details |
|---|---|
| Git LFS | LFS objects are not transferred (`git clone --mirror` skips them) |
| Organization repos | Not included in v1; planned for v2 with `--include-orgs` |
| GitLab pull mirroring | Requires GitLab Premium for private repos; a GitHub Actions alternative is planned for v2 |
| Issue timestamps/authors | Cannot be preserved without a GitLab admin token (see Wiki & Issue Backup above) |
| Pull Requests | Not migrated (GitLab Merge Requests have different semantics) |

## Roadmap

- [x] **v1** — Full backup: clone + push via SSH, idempotent, dry-run, selective filter
- [x] **v1.5** — Wiki mirroring and GitHub Issues migration (opt-in)
- [x] **GitHub Action + Docker image** — scheduled workflow and GHCR image for cron (CLI unchanged)
- [ ] **v2** — Auto-sync: GitLab pull mirror (Premium) or GitHub Actions push mirror
- [ ] **v2** — Organization repos with explicit opt-in

## Contributing

Issues and pull requests are welcome. Please open an issue first to discuss what you'd like to change.

## License

MIT — see [LICENSE](LICENSE).
