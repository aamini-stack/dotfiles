"""The single implementation of jj workspace lifecycle operations."""

import os
import shutil
from collections.abc import Callable, Mapping
from pathlib import Path

from ..jj import (
    Workspace,
    add_workspace,
    current_workspace,
    forget_workspace,
    primary_root,
    workspace,
    workspaces,
)
from ..fzf import fzf_select
from . import config as config_module
from .copy_ignored import copy_ignored
from .hooks import run_hooks, run_named_hook
from .template import TemplateError, render, sanitize


class WtError(RuntimeError):
    pass


def workspace_destination(
    primary: Path,
    name: str,
    config: config_module.Config,
    env: Mapping[str, str] | None = None,
) -> Path:
    env = os.environ if env is None else env
    override = env.get("JJ_WORKSPACE_ROOT")
    if override:
        return Path(override).expanduser() / primary.name / sanitize(name)
    try:
        value = render(config.workspace_path, {"repo": primary.name, "name": name})
    except TemplateError as error:
        raise WtError(f"workspace-path: {error}") from error
    path = Path(value).expanduser()
    return path if path.is_absolute() else primary / path


def create_workspace(
    cwd: Path,
    name: str,
    revision: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Workspace:
    if not name.strip():
        raise WtError("workspace name cannot be empty")
    primary = primary_root(cwd)
    config = config_module.load(primary, env)
    destination = workspace_destination(primary, name, config, env)
    destination.parent.mkdir(parents=True, exist_ok=True)
    add_workspace(destination, name, cwd=cwd, revision=revision or "@")
    run_hooks(config, "post-create", name, destination, primary)
    return Workspace(name=name, root=destination)


def remove_workspace(
    cwd: Path,
    name: str | None = None,
    *,
    assume_yes: bool = False,
    input_fn: Callable[[str], str] = input,
    env: Mapping[str, str] | None = None,
) -> Workspace:
    primary = primary_root(cwd)
    target = current_workspace(cwd) if name is None else workspace(primary, name)
    if target.root.resolve() == primary.resolve():
        raise WtError("refusing to remove the primary workspace")

    if not assume_yes:
        answer = (
            input_fn(f"remove jj workspace '{target.name}' at {target.root}? [y/N] ")
            .strip()
            .lower()
        )
        if answer not in ("y", "yes"):
            raise WtError("aborted")

    config = config_module.load(primary, env)
    run_hooks(
        config,
        "pre-remove",
        target.name,
        target.root,
        primary,
        continue_on_error=True,
    )
    forget_workspace(target.name, cwd=primary)
    if target.root.exists():
        shutil.rmtree(target.root)
    return target


def list_workspaces(cwd: Path) -> tuple[Workspace, list[Workspace]]:
    current = current_workspace(cwd)
    return current, workspaces(primary_root(cwd))


def resolve_workspace(cwd: Path, name: str) -> Workspace:
    return workspace(primary_root(cwd), name)


def pick_workspace(cwd: Path, select=None) -> Workspace | None:
    select = fzf_select if select is None else select
    current, items = list_workspaces(cwd)
    choices = {
        f"{'*' if item.name == current.name else ' '} {item.name}\t{item.root}": item
        for item in items
    }
    _, line = select(list(choices))
    if line is None:
        return None
    return choices.get(line)


def run_configured_hook(cwd: Path, hook_name: str, env=None) -> None:
    current = current_workspace(cwd)
    primary = primary_root(cwd)
    config = config_module.load(primary, env)
    run_named_hook(config, hook_name, current.name, current.root, primary)


def copy_ignored_to_current(cwd: Path, env=None) -> int:
    current = current_workspace(cwd)
    primary = primary_root(cwd)
    config = config_module.load(primary, env)
    return copy_ignored(primary, current.root, config.copy_ignored_exclude)
