import pytest

from cli.wt.config import ConfigError, load


def test_merges_user_then_project_hooks_and_excludes(tmp_path):
    xdg = tmp_path / "xdg"
    user_dir = xdg / "wt"
    user_dir.mkdir(parents=True)
    (user_dir / "config.toml").write_text(
        """
workspace-path = "/ws/{{ repo }}/{{ name | sanitize }}"

[[post-create]]
global = "echo global"

[[post-remove]]
close-herdr = "herdr-ws close --repo '{{ repo }}' --name '{{ name }}'"

[copy-ignored]
exclude = [".cache/"]
"""
    )
    primary = tmp_path / "repo"
    project_dir = primary / ".config"
    project_dir.mkdir(parents=True)
    (project_dir / "wt.toml").write_text(
        """
[[post-create]]
project = "echo project"

[pre-remove]
compose = "docker compose down"

[[post-remove]]
project-cleanup = "echo cleaned"

[step.copy-ignored]
exclude = [".env.local", ".cache/"]
"""
    )

    config = load(primary, {"XDG_CONFIG_HOME": str(xdg)})

    assert config.workspace_path == "/ws/{{ repo }}/{{ name | sanitize }}"
    assert [hook.name for hook in config.post_create] == ["global", "project"]
    assert [hook.name for hook in config.pre_remove] == ["compose"]
    assert [hook.name for hook in config.post_remove] == [
        "close-herdr",
        "project-cleanup",
    ]
    assert config.copy_ignored_exclude == (".cache/", ".env.local")


def test_rejects_non_table_legacy_step_config(tmp_path):
    primary = tmp_path / "repo"
    config_dir = primary / ".config"
    config_dir.mkdir(parents=True)
    (config_dir / "wt.toml").write_text('step = "bad"\n')

    with pytest.raises(ConfigError, match="step must be a table"):
        load(primary, {"XDG_CONFIG_HOME": str(tmp_path / "xdg")})


def test_rejects_non_table_copy_ignored_config(tmp_path):
    primary = tmp_path / "repo"
    config_dir = primary / ".config"
    config_dir.mkdir(parents=True)
    (config_dir / "wt.toml").write_text('copy-ignored = "bad"\n')

    with pytest.raises(ConfigError, match="copy-ignored must be a table"):
        load(primary, {"XDG_CONFIG_HOME": str(tmp_path / "xdg")})


@pytest.mark.parametrize("value", ['""', "false"])
def test_rejects_falsey_non_table_copy_ignored_config(tmp_path, value):
    primary = tmp_path / "repo"
    config_dir = primary / ".config"
    config_dir.mkdir(parents=True)
    (config_dir / "wt.toml").write_text(f"copy-ignored = {value}\n")

    with pytest.raises(ConfigError, match="copy-ignored must be a table"):
        load(primary, {"XDG_CONFIG_HOME": str(tmp_path / "xdg")})
