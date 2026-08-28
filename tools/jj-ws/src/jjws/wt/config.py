"""Load and merge wt's user and project configuration."""

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_WORKSPACE_PATH = "~/.herdr/workspaces/{{ repo }}/{{ name | sanitize_hash }}"


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Hook:
    phase: str
    name: str
    command: str


@dataclass(frozen=True)
class Config:
    workspace_path: str = DEFAULT_WORKSPACE_PATH
    pre_switch: tuple[Hook, ...] = ()
    post_switch: tuple[Hook, ...] = ()
    pre_start: tuple[Hook, ...] = ()
    post_start: tuple[Hook, ...] = ()
    post_create: tuple[Hook, ...] = ()
    pre_remove: tuple[Hook, ...] = ()
    post_remove: tuple[Hook, ...] = ()
    copy_ignored_include: tuple[str, ...] | None = None
    copy_ignored_exclude: tuple[str, ...] = ()
    list_url: str | None = None

    def hooks(self, phase: str) -> tuple[Hook, ...]:
        if phase == "pre-switch":
            return self.pre_switch
        if phase == "post-switch":
            return self.post_switch
        if phase == "pre-start":
            return self.pre_start
        if phase == "post-start":
            return self.post_start
        if phase == "post-create":
            return self.post_create
        if phase == "pre-remove":
            return self.pre_remove
        if phase == "post-remove":
            return self.post_remove
        raise ConfigError(f"unknown hook phase '{phase}'")


def user_config_path(env: Mapping[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    base = Path(env.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "wt" / "config.toml"


def load(primary: Path, env: Mapping[str, str] | None = None) -> Config:
    user = _read(user_config_path(env))
    project = _read(primary / ".config" / "wt.toml")

    workspace_path = _workspace_path(user, DEFAULT_WORKSPACE_PATH)
    workspace_path = _workspace_path(project, workspace_path)
    if not isinstance(workspace_path, str):
        raise ConfigError("workspace-path/worktree-path must be a string")

    user_includes = _patterns(user, "include")
    project_includes = _patterns(project, "include")

    return Config(
        workspace_path=workspace_path,
        pre_switch=_merged_hooks(user, project, "pre-switch"),
        post_switch=_merged_hooks(user, project, "post-switch"),
        pre_start=_merged_start_hooks(user, project),
        post_start=_merged_hooks(user, project, "post-start"),
        post_create=tuple(_hooks(user, "post-create") + _hooks(project, "post-create")),
        pre_remove=tuple(_hooks(user, "pre-remove") + _hooks(project, "pre-remove")),
        post_remove=tuple(_hooks(user, "post-remove") + _hooks(project, "post-remove")),
        copy_ignored_include=(
            project_includes if project_includes is not None else user_includes
        ),
        copy_ignored_exclude=tuple(
            dict.fromkeys(
                (_patterns(user, "exclude") or ())
                + (_patterns(project, "exclude") or ())
            )
        ),
        list_url=_list_url(project, _list_url(user)),
    )


def _workspace_path(data: dict[str, Any], fallback: Any) -> Any:
    if "workspace-path" in data:
        return data["workspace-path"]
    return data.get("worktree-path", fallback)


def _merged_hooks(
    user: dict[str, Any], project: dict[str, Any], phase: str
) -> tuple[Hook, ...]:
    return tuple(_hooks(user, phase) + _hooks(project, phase))


def _merged_start_hooks(
    user: dict[str, Any], project: dict[str, Any]
) -> tuple[Hook, ...]:
    hooks = _hooks(user, "pre-start") + _hooks(project, "pre-start")
    if hooks:
        return tuple(hooks)
    return tuple(
        Hook("pre-start", hook.name, hook.command)
        for hook in _hooks(user, "post-create") + _hooks(project, "post-create")
    )


def _list_url(data: dict[str, Any], fallback: str | None = None) -> str | None:
    section = data.get("list", {})
    if not isinstance(section, dict):
        raise ConfigError("list must be a table")
    value = section.get("url")
    if value is not None and not isinstance(value, str):
        raise ConfigError("list.url must be a string")
    return fallback if value is None else value


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"failed to read {path}: {error}") from error


def _hooks(data: dict[str, Any], phase: str) -> list[Hook]:
    raw = data.get(phase, {})
    if isinstance(raw, str):
        raw = {phase: raw}
    if isinstance(raw, dict):
        entries = list(raw.items())
    elif isinstance(raw, list):
        entries = []
        for entry in raw:
            if not isinstance(entry, dict) or len(entry) != 1:
                raise ConfigError(
                    f"each {phase} hook must have exactly one named command"
                )
            entries.extend(entry.items())
    else:
        raise ConfigError(f"{phase} must be a table or array of tables")

    hooks = []
    for name, command in entries:
        if not isinstance(command, str):
            raise ConfigError(f"{phase}.{name} must be a string")
        hooks.append(Hook(phase=phase, name=name, command=command))
    return hooks


def _patterns(data: dict[str, Any], key: str) -> tuple[str, ...] | None:
    if "copy-ignored" in data:
        section = data["copy-ignored"]
        if not isinstance(section, dict):
            raise ConfigError("copy-ignored must be a table")
        if key in section:
            return _validated_patterns(section[key], key)

    step = data.get("step", {})
    if not isinstance(step, dict):
        raise ConfigError("step must be a table")
    section = step.get("copy-ignored", {})
    if not isinstance(section, dict):
        raise ConfigError("copy-ignored must be a table")
    if key in section:
        return _validated_patterns(section[key], key)
    return None


def _validated_patterns(raw: Any, key: str) -> tuple[str, ...]:
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigError(f"copy-ignored.{key} must be a list of strings")
    return tuple(dict.fromkeys(raw))
