# backup-github-to-gitlab

> Mirror all your GitHub repositories to GitLab automatically — private stays private, public stays public.

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

## Prerequisites

- Python 3.11+
- `git` in your PATH
- SSH key registered on both GitHub and GitLab
- [GitHub token](#github-token) with `repo` scope
- [GitLab token](#gitlab-token) with `api` scope

## Quick Start

```bash
git clone git@github.com:paladini/backup-github-to-gitlab.git
cd backup-github-to-gitlab
pip install -r requirements.txt

cp config.example.yaml config.yaml   # then edit: set github.username and gitlab.username
cp .env.example .env                  # then edit: set GITHUB_TOKEN and GITLAB_TOKEN

python backup.py --dry-run            # preview — no changes made
python backup.py                      # run the backup
```

## Token Setup

### GitHub token

1. Go to **Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token (classic)**
3. Select scope: `repo` (required to list private repositories)
4. Paste the token into `.env` as `GITHUB_TOKEN`

### GitLab token

1. Go to **User Settings → Access Tokens → Add new token**
2. Select scope: `api` (required to create projects)
3. Paste the token into `.env` as `GITLAB_TOKEN`

## Configuration

**`config.yaml`** — copy from `config.example.yaml`:

```yaml
github:
  username: your-github-username

gitlab:
  username: your-gitlab-username    # can differ from GitHub
  url: https://gitlab.com           # change only for self-hosted GitLab

backup:
  include_forks: false      # include forked repositories? (default: false)
  include_archived: true    # include archived repositories? (default: true)
  temp_dir: ./tmp           # temporary dir for clones — auto-cleaned after each repo

  # Extended backup (opt-in)
  backup_wiki: false        # mirror each repo's wiki to GitLab
  backup_issues: false      # migrate GitHub Issues to GitLab
```

**`.env`** — copy from `.env.example`:

```
GITHUB_TOKEN=ghp_...
GITLAB_TOKEN=glpat-...
```

Tokens are loaded at runtime and never logged. `.env` is in `.gitignore`.

## Usage

```bash
# Back up all personal repositories
python backup.py

# Preview what would happen — no writes
python backup.py --dry-run

# Back up only repos matching a pattern
python backup.py --filter "myproject-*"

# Include forks (skipped by default)
python backup.py --include-forks

# Verbose: show raw git output (useful for debugging SSH issues)
python backup.py --verbose

# Use a different config file
python backup.py --config /path/to/config.yaml
```

### Example output

```
DRY RUN MODE — no changes will be made

 my-private-repo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/10

Repository                     Status          Details
my-private-repo                ~ dry run       would create as private
my-public-site                 ~ dry run       would create as public
archived-experiment            ~ dry run       would create as private

10 dry run

[DRY RUN] Nenhuma operação foi executada.
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
- [ ] **v2** — Auto-sync: GitLab pull mirror (Premium) or GitHub Actions push mirror
- [ ] **v2** — Organization repos with explicit opt-in

## Contributing

Issues and pull requests are welcome. Please open an issue first to discuss what you'd like to change.

## License

MIT — see [LICENSE](LICENSE).
