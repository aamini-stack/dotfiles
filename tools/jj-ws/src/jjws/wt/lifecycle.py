"""The single implementation of jj workspace lifecycle operations."""

import os
import re
import shutil
import subprocess
import sys
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path

from ..lib.fzf import fzf_select
from ..lib.jj import (
    JjError,
    Workspace,
    add_workspace,
    commit_id,
    current_workspace,
    forget_workspace,
    primary_root,
    workspace,
    workspaces,
)
from . import config as config_module
from .copy_ignored import copy_ignored
from .hooks import PHASES, HookError, run_hooks, run_named_hook
from .template import TemplateError, render, sanitize, sanitize_hash


class WtError(RuntimeError):
    pass


class CreateHookError(HookError):
    def __init__(self, workspace: Workspace, message: str):
        super().__init__(message)
        self.workspace = workspace


_WORKSPACE_NAME = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*")


def validate_workspace_name(name: str) -> None:
    if not _WORKSPACE_NAME.fullmatch(name) or any(
        part in (".", "..") for part in name.split("/")
    ):
        raise WtError(
            "workspace name must contain only letters, digits, '.', '_', '-', and "
            "safe '/' separators"
        )


def _move_aside(path: Path) -> Path:
    trash = path.with_name(f".{path.name}.trash-{uuid.uuid4().hex[:8]}")
    try:
        path.rename(trash)
    except OSError as error:
        raise WtError(f"could not move {path} aside: {error}") from error
    return trash


def _delete_aside(trash: Path) -> None:
    shutil.rmtree(trash, ignore_errors=True)
    if trash.exists():
        print(f"wt: leftover files moved aside to {trash}", file=sys.stderr)


def _restore_destination(destination: Path, original: Path) -> None:
    partial = None
    if destination.exists():
        partial = _move_aside(destination)
    try:
        original.rename(destination)
    except OSError as error:
        details = f"; partial workspace remains at {partial}" if partial else ""
        raise WtError(
            f"could not restore original destination from {original}: {error}{details}"
        ) from error
    if partial:
        print(f"wt: partial workspace left at {partial}", file=sys.stderr)


def _rollback_new_registration(
    primary: Path,
    name: str,
    destination: Path,
    registrations: set[tuple[str, Path]],
) -> None:
    current = {(item.name, item.root.resolve()) for item in workspaces(primary)}
    target = (name, destination.resolve())
    if target in current and target not in registrations:
        forget_workspace(name, cwd=primary)


def _reject_registered_destination(primary: Path, name: str, destination: Path) -> None:
    owner = next(
        (
            item.name
            for item in workspaces(primary)
            if item.root.resolve() == destination.resolve() and item.name != name
        ),
        None,
    )
    if owner is not None:
        raise WtError(
            f"destination {destination} belongs to jj workspace '{owner}'; "
            "refusing --force"
        )


def workspace_destination(
    primary: Path,
    name: str,
    config: config_module.Config,
    env: Mapping[str, str] | None = None,
) -> Path:
    env = os.environ if env is None else env
    override = env.get("JJ_WORKSPACE_ROOT")
    if override:
        return Path(override).expanduser() / primary.name / sanitize_hash(name)
    try:
        value = render(
            config.workspace_path,
            {
                "repo": primary.name,
                "name": name,
                "branch": name,
                "repo_path": str(primary),
                "primary_worktree_path": str(primary),
            },
        )
    except TemplateError as error:
        raise WtError(f"workspace-path: {error}") from error
    path = Path(value).expanduser()
    return path if path.is_absolute() else primary / path


def create_workspace(
    cwd: Path,
    name: str,
    revision: str | None = None,
    env: Mapping[str, str] | None = None,
    *,
    force: bool = False,
    run_post_create: bool = True,
) -> Workspace:
    validate_workspace_name(name)
    primary = primary_root(cwd)
    config = config_module.load(primary, env)
    destination = workspace_destination(primary, name, config, env)
    if force:
        _reject_registered_destination(primary, name, destination)
    run_hooks(config, "pre-switch", name, destination, primary, cwd=cwd)
    destination.parent.mkdir(parents=True, exist_ok=True)
    original = None
    registrations = set()
    if destination.exists() and any(destination.iterdir()):
        if not force:
            raise WtError(
                f"destination {destination} already exists and is not empty; "
                "re-run with --force to move it aside"
            )
        registrations = {
            (item.name, item.root.resolve()) for item in workspaces(primary)
        }
        original = _move_aside(destination)
    try:
        add_workspace(destination, name, cwd=cwd, revision=revision or "@")
    except BaseException as error:
        if original is not None:
            try:
                _rollback_new_registration(primary, name, destination, registrations)
            except (JjError, OSError) as rollback_error:
                raise WtError(
                    f"workspace creation failed and rollback could not forget "
                    f"'{name}'; original destination remains at {original}: "
                    f"{rollback_error}"
                ) from error
            _restore_destination(destination, original)
        raise
    if original is not None:
        _delete_aside(original)
    created = Workspace(name=name, root=destination)
    _ensure_git_worktree(primary, created)
    if not run_post_create:
        return created
    try:
        run_hooks(config, "pre-start", name, destination, primary)
    except HookError as error:
        raise CreateHookError(created, str(error)) from error
    hook_error = None
    try:
        run_hooks(config, "post-start", name, destination, primary)
    except HookError as error:
        hook_error = error
    try:
        run_hooks(config, "post-switch", name, destination, primary)
    except HookError as error:
        if hook_error is None:
            hook_error = error
    if hook_error is not None:
        raise CreateHookError(created, str(hook_error)) from hook_error
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
        try:
            trash = _move_aside(target.root)
            _delete_aside(trash)
        except WtError as error:
            raise WtError(f"{error}; the workspace remains registered") from error
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


def _ensure_git_worktree(primary: Path, target: Workspace) -> None:
    # The aria jj fork dropped `workspace add --colocate`, so fresh workspaces
    # no longer arrive as git worktrees. herdr only nests workspaces with git
    # worktree provenance, so register them by hand; registration failure must
    # not fail a creation that already succeeded.
    if not (primary / ".git").exists() or (target.root / ".git").exists():
        return
    try:
        _register_git_worktree(primary, target)
    except (JjError, OSError, WtError) as error:
        print(
            f"wt: git worktree registration skipped for '{target.name}': {error}",
            file=sys.stderr,
        )


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


def switch_to_workspace(cwd: Path, name: str, env=None) -> Workspace:
    validate_workspace_name(name)
    primary = primary_root(cwd)
    target = workspace(primary, name)
    config = config_module.load(primary, env)
    run_hooks(config, "pre-switch", target.name, target.root, primary, cwd=cwd)
    run_hooks(config, "post-switch", target.name, target.root, primary)
    return target


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


def run_configured_phase(cwd: Path, phase: str, env=None) -> None:
    if phase not in PHASES:
        raise WtError(
            f"unknown hook phase '{phase}'; expected one of {', '.join(PHASES)}"
        )
    current = current_workspace(cwd)
    primary = primary_root(cwd)
    config = config_module.load(primary, env)
    run_hooks(config, phase, current.name, current.root, primary)


def copy_ignored_to_current(cwd: Path, env=None, *, force: bool = False) -> int:
    current = current_workspace(cwd)
    primary = primary_root(cwd)
    config = config_module.load(primary, env)
    return copy_ignored(
        primary,
        current.root,
        config.copy_ignored_exclude,
        config.copy_ignored_include,
        force=force,
    )
