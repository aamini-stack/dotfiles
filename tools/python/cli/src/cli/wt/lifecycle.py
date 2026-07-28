"""The single implementation of jj workspace lifecycle operations."""

import os
import shutil
import subprocess
import sys
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path

from ..jj import (
    Workspace,
    add_workspace,
    commit_id,
    current_workspace,
    forget_workspace,
    primary_root,
    workspace,
    workspaces,
)
from ..fzf import fzf_select
from . import config as config_module
from .copy_ignored import copy_ignored
from .hooks import HookError, run_hooks, run_named_hook
from .template import TemplateError, render, sanitize


class WtError(RuntimeError):
    pass


class CreateHookError(HookError):
    def __init__(self, workspace: Workspace, message: str):
        super().__init__(message)
        self.workspace = workspace


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
    created = Workspace(name=name, root=destination)
    try:
        run_hooks(config, "post-create", name, destination, primary)
    except HookError as error:
        raise CreateHookError(created, str(error)) from error
    return created


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
    if target.root.exists():
        trash = target.root.with_name(
            f".{target.root.name}.trash-{uuid.uuid4().hex[:8]}"
        )
        try:
            target.root.rename(trash)
        except OSError as error:
            raise WtError(
                f"could not move workspace directory {target.root} aside: {error}; "
                "the workspace remains registered"
            ) from error
        shutil.rmtree(trash, ignore_errors=True)
        if trash.exists():
            print(f"wt: leftover files moved aside to {trash}", file=sys.stderr)
    forget_workspace(target.name, cwd=primary)
    run_hooks(
        config,
        "post-remove",
        target.name,
        target.root,
        primary,
        continue_on_error=True,
        cwd=primary,
    )
    return target


def colocate_workspaces(cwd: Path, name: str | None = None) -> list[Workspace]:
    primary = primary_root(cwd)
    if not (primary / ".git").exists():
        raise WtError("primary workspace is not colocated with git")
    targets = [w for w in workspaces(primary) if w.root.resolve() != primary.resolve()]
    if name is not None:
        targets = [w for w in targets if w.name == name]
        if not targets:
            raise WtError(f"'{name}' is not a jj workspace")
    converted = []
    for target in targets:
        if (target.root / ".git").exists() or not target.root.is_dir():
            continue
        _register_git_worktree(primary, target)
        converted.append(target)
    return converted


def _register_git_worktree(primary: Path, target: Workspace) -> None:
    # jj cannot register a workspace in an existing directory, so pre-fork
    # workspaces get git worktree metadata hand-built here: an admin entry
    # under .git/worktrees plus the gitfile in the workspace. HEAD starts at
    # the workspace's @-, matching what the jj fork maintains from then on.
    admin = primary / ".git" / "worktrees" / sanitize(target.name)
    if admin.exists():
        raise WtError(f"git worktree admin entry already exists for '{target.name}'")
    commit = commit_id(f"{target.name}@-", cwd=primary)
    result = subprocess.run(
        ["git", "-C", str(primary), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise WtError(
            f"parent commit of '{target.name}' is not in the git object store yet; "
            "run a jj command in that workspace first"
        )
    admin.mkdir(parents=True)
    (admin / "gitdir").write_text(f"{target.root / '.git'}\n")
    (admin / "commondir").write_text("../..\n")
    (admin / "HEAD").write_text(f"{commit}\n")
    (target.root / ".git").write_text(f"gitdir: {admin}\n")
    subprocess.run(
        ["git", "-C", str(primary), "worktree", "repair", str(target.root)],
        capture_output=True,
        check=False,
    )
    # The hand-built admin entry has no index; without one, git status
    # reports every tracked file as deleted.
    subprocess.run(
        ["git", "-C", str(target.root), "read-tree", "HEAD"],
        capture_output=True,
        check=False,
    )


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
