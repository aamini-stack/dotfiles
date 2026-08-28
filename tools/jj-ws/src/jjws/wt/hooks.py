"""Render and execute lifecycle hooks."""

import subprocess
import sys
from pathlib import Path

from .config import Config, Hook
from .template import TemplateError, render


class HookError(RuntimeError):
    pass


PHASES = (
    "pre-switch",
    "post-switch",
    "pre-start",
    "post-start",
    "post-create",
    "pre-remove",
    "post-remove",
)


def variables(
    name: str,
    workspace_path: Path,
    primary_path: Path,
    *,
    cwd: Path | None = None,
    hook_type: str = "",
    hook_name: str = "",
) -> dict[str, str]:
    return {
        "name": name,
        "branch": name,
        "repo": primary_path.name,
        "workspace_path": str(workspace_path),
        "worktree_path": str(workspace_path),
        "worktree_name": workspace_path.name,
        "primary_path": str(primary_path),
        "repo_path": str(primary_path),
        "primary_worktree_path": str(primary_path),
        "cwd": str(cwd or workspace_path),
        "hook_type": hook_type,
        "hook_name": hook_name,
    }


def run_hooks(
    config: Config,
    phase: str,
    name: str,
    workspace_path: Path,
    primary_path: Path,
    *,
    continue_on_error: bool = False,
    cwd: Path | None = None,
) -> bool:
    succeeded = True
    for hook in config.hooks(phase):
        try:
            run_hook(hook, name, workspace_path, primary_path, cwd=cwd)
        except HookError as error:
            succeeded = False
            if not continue_on_error:
                raise
            print(f"wt: warning: {error}", file=sys.stderr)
    return succeeded


def run_named_hook(
    config: Config,
    hook_name: str,
    name: str,
    workspace_path: Path,
    primary_path: Path,
) -> None:
    matching = []
    seen = set[tuple[str, str, str]]()
    for phase in PHASES:
        for hook in config.hooks(phase):
            logical_phase = (
                "start" if hook.phase in ("pre-start", "post-create") else hook.phase
            )
            identity = (logical_phase, hook.name, hook.command)
            if hook.name == hook_name and identity not in seen:
                matching.append(hook)
                seen.add(identity)
    if not matching:
        raise HookError(f"hook '{hook_name}' is not configured")
    for hook in matching:
        run_hook(hook, name, workspace_path, primary_path)


def run_hook(
    hook: Hook,
    name: str,
    workspace_path: Path,
    primary_path: Path,
    *,
    cwd: Path | None = None,
) -> None:
    try:
        command = render(
            hook.command,
            variables(
                name,
                workspace_path,
                primary_path,
                cwd=cwd,
                hook_type=hook.phase,
                hook_name=hook.name,
            ),
            shell=True,
        )
    except TemplateError as error:
        raise HookError(f"{hook.phase}.{hook.name}: {error}") from error

    print(f"wt: {hook.phase}.{hook.name}: {command}", file=sys.stderr)
    try:
        result = subprocess.run(
            command, cwd=cwd or workspace_path, shell=True, check=False
        )
    except OSError as error:
        raise HookError(f"{hook.phase}.{hook.name} could not run: {error}") from error
    if result.returncode:
        raise HookError(
            f"{hook.phase}.{hook.name} failed with exit code {result.returncode}"
        )
