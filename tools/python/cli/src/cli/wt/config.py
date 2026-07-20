"""Load and merge wt's user and project configuration."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


DEFAULT_WORKSPACE_PATH = "~/.herdr/workspaces/{{ repo }}/{{ name | sanitize }}"


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
    post_create: tuple[Hook, ...] = ()
    pre_remove: tuple[Hook, ...] = ()
    copy_ignored_exclude: tuple[str, ...] = ()

    def hooks(self, phase: str) -> tuple[Hook, ...]:
        if phase == "post-create":
            return self.post_create
        if phase == "pre-remove":
            return self.pre_remove
        raise ConfigError(f"unknown hook phase '{phase}'")


def user_config_path(env: Mapping[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    base = Path(env.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "wt" / "config.toml"


def load(primary: Path, env: Mapping[str, str] | None = None) -> Config:
    user = _read(user_config_path(env))
    project = _read(primary / ".config" / "wt.toml")

    workspace_path = user.get("workspace-path", DEFAULT_WORKSPACE_PATH)
    if "workspace-path" in project:
        workspace_path = project["workspace-path"]
    if not isinstance(workspace_path, str):
        raise ConfigError("workspace-path must be a string")

    return Config(
        workspace_path=workspace_path,
        post_create=tuple(_hooks(user, "post-create") + _hooks(project, "post-create")),
        pre_remove=tuple(_hooks(user, "pre-remove") + _hooks(project, "pre-remove")),
        copy_ignored_exclude=tuple(dict.fromkeys(_excludes(user) + _excludes(project))),
    )


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"failed to read {path}: {error}") from error


def _hooks(data: dict[str, Any], phase: str) -> list[Hook]:
    raw = data.get(phase, [])
    if isinstance(raw, dict):
        raw = [raw]
    if isinstance(raw, str):
        raw = [{phase: raw}]
    if not isinstance(raw, list):
        raise ConfigError(f"{phase} must be a table or array of tables")

    hooks = []
    for entry in raw:
        if not isinstance(entry, dict) or len(entry) != 1:
            raise ConfigError(f"each {phase} hook must have exactly one named command")
        name, command = next(iter(entry.items()))
        if not isinstance(command, str):
            raise ConfigError(f"{phase}.{name} must be a string")
        hooks.append(Hook(phase=phase, name=name, command=command))
    return hooks


def _excludes(data: dict[str, Any]) -> list[str]:
    if "copy-ignored" in data:
        section = data["copy-ignored"]
    else:
        step = data.get("step", {})
        if not isinstance(step, dict):
            raise ConfigError("step must be a table")
        section = step.get("copy-ignored", {})
    if not isinstance(section, dict):
        raise ConfigError("copy-ignored must be a table")
    raw = section.get("exclude", [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigError("copy-ignored.exclude must be a list of strings")
    return raw
