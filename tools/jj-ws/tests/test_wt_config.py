import pytest

from jjws.wt.config import ConfigError, load


def test_merges_hooks_and_excludes_and_project_include_overrides_user(tmp_path):
    xdg = tmp_path / "xdg"
    user_dir = xdg / "wt"
    user_dir.mkdir(parents=True)
    (user_dir / "config.toml").write_text(
        """
workspace-path = "/ws/{{ repo }}/{{ name | sanitize }}"

[[post-create]]
global = "echo global"

[[post-remove]]
close-herdr = "herdr-jj close --repo '{{ repo }}' --name '{{ name }}'"

[copy-ignored]
include = [".env.local"]
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

[copy-ignored]
include = [".env*.local"]

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
    assert config.copy_ignored_include == (".env*.local",)
    assert config.copy_ignored_exclude == (".cache/", ".env.local")


def test_omitted_include_copies_all_ignored_files(tmp_path):
    primary = tmp_path / "repo"
    primary.mkdir()

    config = load(primary, {"XDG_CONFIG_HOME": str(tmp_path / "xdg")})

    assert config.copy_ignored_include is None


@pytest.mark.parametrize("key", ["include", "exclude"])
def test_rejects_non_list_copy_ignored_patterns(tmp_path, key):
    primary = tmp_path / "repo"
    config_dir = primary / ".config"
    config_dir.mkdir(parents=True)
    (config_dir / "wt.toml").write_text(f'[copy-ignored]\n{key} = "bad"\n')

    with pytest.raises(
        ConfigError, match=rf"copy-ignored\.{key} must be a list of strings"
    ):
        load(primary, {"XDG_CONFIG_HOME": str(tmp_path / "xdg")})


def test_hook_tables_hold_multiple_named_commands(tmp_path):
    primary = tmp_path / "repo"
    config_dir = primary / ".config"
    config_dir.mkdir(parents=True)
    (config_dir / "wt.toml").write_text(
        """
[post-create]
one = "echo one"
two = "echo two"
"""
    )

    config = load(primary, {"XDG_CONFIG_HOME": str(tmp_path / "xdg")})

    assert [hook.name for hook in config.post_create] == ["one", "two"]


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


def test_parses_worktrunk_hooks_aliases_and_list_url(tmp_path):
    xdg = tmp_path / "xdg"
    user_dir = xdg / "wt"
    user_dir.mkdir(parents=True)
    (user_dir / "config.toml").write_text(
        'worktree-path = "/worktrees/{{ branch }}"\n'
        'workspace-path = "/workspaces/{{ branch }}"\n'
        'pre-switch = "echo user"\n'
    )
    primary = tmp_path / "repo"
    config_dir = primary / ".config"
    config_dir.mkdir(parents=True)
    (config_dir / "wt.toml").write_text(
        """
[[pre-start]]
copy = "wt step copy-ignored"

[post-start]
server = "serve {{ branch }}"

[list]
url = "http://localhost:{{ branch | hash_port }}"

[switch]
base = "@"
"""
    )

    config = load(primary, {"XDG_CONFIG_HOME": str(xdg)})

    assert config.workspace_path == "/workspaces/{{ branch }}"
    assert [hook.name for hook in config.pre_switch] == ["pre-switch"]
    assert [hook.name for hook in config.pre_start] == ["copy"]
    assert [hook.name for hook in config.post_start] == ["server"]
    assert config.list_url == "http://localhost:{{ branch | hash_port }}"


def test_project_worktree_path_overrides_user_workspace_path(tmp_path):
    xdg = tmp_path / "xdg"
    user_dir = xdg / "wt"
    user_dir.mkdir(parents=True)
    (user_dir / "config.toml").write_text('workspace-path = "/user/{{ name }}"\n')
    primary = tmp_path / "repo"
    config_dir = primary / ".config"
    config_dir.mkdir(parents=True)
    (config_dir / "wt.toml").write_text('worktree-path = "/project/{{ branch }}"\n')

    config = load(primary, {"XDG_CONFIG_HOME": str(xdg)})

    assert config.workspace_path == "/project/{{ branch }}"


def test_explicit_pre_start_suppresses_all_legacy_post_create_hooks(tmp_path):
    xdg = tmp_path / "xdg"
    user_dir = xdg / "wt"
    user_dir.mkdir(parents=True)
    (user_dir / "config.toml").write_text('[[post-create]]\ncopy = "wt copy-ignored"\n')
    primary = tmp_path / "repo"
    config_dir = primary / ".config"
    config_dir.mkdir(parents=True)
    (config_dir / "wt.toml").write_text(
        '[[pre-start]]\ncopy = "wt step copy-ignored"\n'
    )

    config = load(primary, {"XDG_CONFIG_HOME": str(xdg)})

    assert [(hook.phase, hook.command) for hook in config.pre_start] == [
        ("pre-start", "wt step copy-ignored")
    ]
    assert config.hooks("post-start") == ()


def test_pre_start_replaces_same_source_legacy_post_create(tmp_path):
    xdg = tmp_path / "xdg"
    user_dir = xdg / "wt"
    user_dir.mkdir(parents=True)
    (user_dir / "config.toml").write_text(
        '[[post-create]]\nlegacy = "old"\n[[pre-start]]\ncurrent = "new"\n'
    )
    primary = tmp_path / "repo"
    primary.mkdir()

    config = load(primary, {"XDG_CONFIG_HOME": str(xdg)})

    assert [(hook.name, hook.command) for hook in config.pre_start] == [
        ("current", "new")
    ]


def test_legacy_post_create_runs_as_pre_start_without_explicit_pre_start(tmp_path):
    xdg = tmp_path / "xdg"
    user_dir = xdg / "wt"
    user_dir.mkdir(parents=True)
    (user_dir / "config.toml").write_text(
        '[[post-create]]\nlegacy = "wt copy-ignored"\n'
    )
    primary = tmp_path / "repo"
    primary.mkdir()

    config = load(primary, {"XDG_CONFIG_HOME": str(xdg)})

    assert [(hook.phase, hook.name) for hook in config.pre_start] == [
        ("pre-start", "legacy")
    ]


def test_project_list_url_overrides_user_and_user_is_fallback(tmp_path):
    xdg = tmp_path / "xdg"
    user_dir = xdg / "wt"
    user_dir.mkdir(parents=True)
    (user_dir / "config.toml").write_text('[list]\nurl = "user"\n')
    primary = tmp_path / "repo"
    config_dir = primary / ".config"
    config_dir.mkdir(parents=True)

    assert load(primary, {"XDG_CONFIG_HOME": str(xdg)}).list_url == "user"

    (config_dir / "wt.toml").write_text('[list]\nurl = "project"\n')
    assert load(primary, {"XDG_CONFIG_HOME": str(xdg)}).list_url == "project"
