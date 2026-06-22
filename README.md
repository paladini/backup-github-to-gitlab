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

## Known Limitations

| Limitation | Details |
|---|---|
| Git LFS | LFS objects are not transferred (`git clone --mirror` skips them) |
| Organization repos | Not included in v1; planned for v2 with `--include-orgs` |
| GitLab pull mirroring | Requires GitLab Premium for private repos; a GitHub Actions alternative is planned for v2 |

## Roadmap

- [x] **v1** — Full backup: clone + push via SSH, idempotent, dry-run, selective filter
- [ ] **v2** — Auto-sync: GitLab pull mirror (Premium) or GitHub Actions push mirror
- [ ] **v2** — Organization repos with explicit opt-in
- [ ] **v3** — Wiki mirroring

## Contributing

Issues and pull requests are welcome. Please open an issue first to discuss what you'd like to change.

## License

MIT — see [LICENSE](LICENSE).
