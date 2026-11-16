from pathlib import Path

import pytest

from gh2gl.config import ConfigError, load_config, validate_config


def _write_config(path: Path, **kwargs) -> Path:
    text = (
        "github:\n"
        f"  username: {kwargs.get('github_username', 'octocat')}\n"
        "gitlab:\n"
        f"  username: {kwargs.get('gitlab_username', 'octocat')}\n"
        f"  url: {kwargs.get('gitlab_url', 'https://gitlab.com')}\n"
        "backup:\n"
        f"  include_forks: {str(kwargs.get('include_forks', False)).lower()}\n"
        f"  include_archived: {str(kwargs.get('include_archived', True)).lower()}\n"
        f"  backup_wiki: {str(kwargs.get('backup_wiki', False)).lower()}\n"
        f"  backup_issues: {str(kwargs.get('backup_issues', False)).lower()}\n"
    )
    path.write_text(text, encoding="utf-8")
    return path


def test_load_config_reads_env_and_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr("gh2gl.config.load_dotenv", lambda: None)
    cfg_path = _write_config(tmp_path / "config.yaml")
    monkeypatch.setenv("GITHUB_TOKEN", "gh-test-token")
    monkeypatch.setenv("GITLAB_TOKEN", "gl-test-token")
    monkeypatch.chdir(tmp_path)

    config = load_config(str(cfg_path))

    assert config.github_username == "octocat"
    assert config.gitlab_username == "octocat"
    assert config.github_token == "gh-test-token"
    assert config.gitlab_token == "gl-test-token"
    assert config.dry_run is False
    assert config.include_forks is False
    assert config.include_archived is True
    assert config.backup_wiki is False
    assert config.backup_issues is False
    validate_config(config)


def test_dry_run_override_does_not_require_changing_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr("gh2gl.config.load_dotenv", lambda: None)
    cfg_path = _write_config(tmp_path / "config.yaml")
    monkeypatch.setenv("GITHUB_TOKEN", "gh-test-token")
    monkeypatch.setenv("GITLAB_TOKEN", "gl-test-token")

    config = load_config(str(cfg_path), {"dry_run": True, "filter_pattern": "mine-*"})

    assert config.dry_run is True
    assert config.filter_pattern == "mine-*"


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(str(tmp_path / "missing.yaml"))


def test_validate_config_requires_tokens(tmp_path, monkeypatch):
    monkeypatch.setattr("gh2gl.config.load_dotenv", lambda: None)
    cfg_path = _write_config(tmp_path / "config.yaml")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    # load_dotenv may pick up a developer .env; force empty after load
    config = load_config(str(cfg_path))
    config.github_token = ""
    config.gitlab_token = "gl"
    with pytest.raises(ConfigError, match="GITHUB_TOKEN"):
        validate_config(config)

    config.github_token = "gh"
    config.gitlab_token = ""
    with pytest.raises(ConfigError, match="GITLAB_TOKEN"):
        validate_config(config)


def test_cli_does_not_read_gh_backup_token(tmp_path, monkeypatch):
    """CLI env names stay GITHUB_TOKEN / GITLAB_TOKEN; mapping is Action/image only."""
    monkeypatch.setattr("gh2gl.config.load_dotenv", lambda: None)
    cfg_path = _write_config(tmp_path / "config.yaml")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GH_BACKUP_TOKEN", "should-not-be-used-by-cli")
    monkeypatch.setenv("GITLAB_TOKEN", "gl-test-token")
    config = load_config(str(cfg_path))
    assert config.github_token != "should-not-be-used-by-cli"
