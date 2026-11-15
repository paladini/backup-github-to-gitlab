#!/bin/sh
set -eu

# Map a dedicated PAT onto the CLI's GITHUB_TOKEN without changing gh2gl.
# GitHub Actions injects a workflow GITHUB_TOKEN that is not a repo-scope PAT;
# callers should set GH_BACKUP_TOKEN instead. Local/docker users may still set
# GITHUB_TOKEN directly (same as .env.example).
if [ -n "${GH_BACKUP_TOKEN:-}" ]; then
  export GITHUB_TOKEN="$GH_BACKUP_TOKEN"
fi

if [ -n "${SSH_PRIVATE_KEY:-}" ]; then
  mkdir -p "${HOME}/.ssh"
  chmod 700 "${HOME}/.ssh"
  key_file="${HOME}/.ssh/id_ed25519"
  printf '%s\n' "$SSH_PRIVATE_KEY" | tr -d '\r' > "$key_file"
  chmod 600 "$key_file"
  : >> "${HOME}/.ssh/known_hosts"
  chmod 644 "${HOME}/.ssh/known_hosts"
fi

exec gh2gl "$@"
