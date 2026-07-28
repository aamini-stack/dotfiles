"""Render and execute lifecycle hooks."""

import subprocess
import sys
from pathlib import Path

from .config import Config, Hook
from .template import TemplateError, render


class HookError(RuntimeError):
    pass


def variables(name: str, workspace_path: Path, primary_path: Path) -> dict[str, str]:
    return {
        "name": name,
        "repo": primary_path.name,
        "workspace_path": str(workspace_path),
        "primary_path": str(primary_path),
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
    matching = [
        hook
        for phase in ("post-create", "pre-remove", "post-remove")
        for hook in config.hooks(phase)
        if hook.name == hook_name
    ]
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
            variables(name, workspace_path, primary_path),
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
