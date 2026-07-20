"""Popup wizard: name a new jj workspace, create it, open it in herdr."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable, Mapping

from ..jj import JjError, primary_root
from ..open import open_workspace
from ..wt.config import ConfigError
from ..wt.hooks import HookError
from ..wt.lifecycle import WtError, create_workspace
from . import state
from .reporter import ensure


def workspace_root(env: Mapping[str, str]) -> Path:
    override = env.get("JJ_WORKSPACE_ROOT")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".herdr" / "workspaces"


def _cwd_from(ctx: dict) -> str | None:
    return ctx.get("focused_pane_cwd") or ctx.get("workspace_cwd") or ctx.get("cwd")


def resolve_context(env: Mapping[str, str]) -> dict:
    raw = env.get("HERDR_PLUGIN_CONTEXT_JSON")
    if raw:
        try:
            ctx = json.loads(raw)
        except json.JSONDecodeError:
            ctx = None
        if ctx:
            cwd = _cwd_from(ctx)
            if cwd:
                return {**ctx, "cwd": cwd}
    ctx = state.read_context(env)
    if ctx is not None:
        cwd = _cwd_from(ctx)
        if cwd:
            return {**ctx, "cwd": cwd}
    return {"cwd": str(Path.cwd())}


def wizard(
    env: Mapping[str, str] | None = None,
    input_fn: Callable[[str], str] = input,
) -> int:
    env = os.environ if env is None else env
    cwd = Path(resolve_context(env)["cwd"])

    try:
        primary = primary_root(cwd)
    except JjError as error:
        print(f"herdr-jj wizard: {error}", file=sys.stderr)
        return 1

    name = input_fn("workspace name: ").strip()
    if not name:
        print("herdr-jj wizard: empty workspace name", file=sys.stderr)
        return 1

    try:
        created = create_workspace(cwd, name, env=env)
    except (JjError, WtError, ConfigError, HookError) as error:
        print(f"herdr-jj wizard: {error}", file=sys.stderr)
        return 1

    rc = open_workspace(created.root, primary, created.name)
    if rc == 0:
        ensure(env)
    return rc


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("wizard", help="create a new jj workspace (popup)")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    return wizard()
