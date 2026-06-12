import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from gh2gl.models import Config


class ConfigError(Exception):
    pass


def load_config(config_path: str = "config.yaml", overrides: dict = None) -> Config:
    if overrides is None:
        overrides = {}

    path = Path(config_path)
    if not path.exists():
        raise ConfigError(
            f"'{config_path}' not found.\n"
            "Run 'gh2gl init' to create a workspace with config.yaml and .env,\n"
            "then run 'gh2gl' from inside that folder."
        )

    load_dotenv()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    gh = data.get("github", {})
    gl = data.get("gitlab", {})
    backup = data.get("backup", {})

    return Config(
        github_username=overrides.get("github_username") or gh.get("username", ""),
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        gitlab_username=overrides.get("gitlab_username") or gl.get("username", ""),
        gitlab_token=os.environ.get("GITLAB_TOKEN", ""),
        gitlab_url=gl.get("url", "https://gitlab.com"),
        include_forks=overrides.get("include_forks", backup.get("include_forks", False)),
        include_archived=overrides.get("include_archived", backup.get("include_archived", True)),
        temp_dir=backup.get("temp_dir", "./tmp"),
        dry_run=overrides.get("dry_run", False),
        filter_pattern=overrides.get("filter_pattern", "*"),
        verbose=overrides.get("verbose", False),
    )


def validate_config(config: Config) -> None:
    if not config.github_token:
        raise ConfigError(
            "GITHUB_TOKEN is not set.\n"
            "Add it to .env (edit the file created by 'gh2gl init'). Required scope: repo\n"
            "Create at: https://github.com/settings/tokens/new?scopes=repo"
        )
    if not config.gitlab_token:
        raise ConfigError(
            "GITLAB_TOKEN is not set.\n"
            "Add it to .env (edit the file created by 'gh2gl init'). Required scope: api\n"
            "Create at: https://gitlab.com/-/user_settings/personal_access_tokens"
        )
    if not config.github_username:
        raise ConfigError("github.username is not set in config.yaml")
    if not config.gitlab_username:
        raise ConfigError("gitlab.username is not set in config.yaml")
