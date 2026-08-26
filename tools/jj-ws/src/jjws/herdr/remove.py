"""Remove the current jj workspace: close herdr side, forget in jj, delete dir."""

import argparse
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from ..lib.jj import JjError, primary_root, repo_root
from ..wt.config import ConfigError
from ..wt.hooks import HookError
from ..wt.lifecycle import WtError
from ..wt.lifecycle import remove_workspace as wt_remove_workspace
from .close import close_workspace


def remove_workspace(
    root: Path,
    primary: Path,
    env: Mapping[str, str] | None = None,
    input_fn: Callable[[str], str] = input,
    assume_yes: bool = False,
) -> int:
    env = os.environ if env is None else env
    root = Path(root)
    primary = Path(primary)

    try:
        removed = wt_remove_workspace(
            root,
            assume_yes=assume_yes,
            input_fn=input_fn,
            env=env,
        )
    except (JjError, WtError, ConfigError, HookError) as error:
        print(f"herdr-jj remove: {error}", file=sys.stderr)
        return 1
    return close_workspace(removed.name, removed.root)


def remove_current(
    env: Mapping[str, str] | None = None,
    input_fn: Callable[[str], str] = input,
    assume_yes: bool = False,
) -> int:
    env = os.environ if env is None else env
    cwd = Path.cwd()
    try:
        root = repo_root(cwd)
        primary = primary_root(cwd)
    except JjError as error:
        print(f"herdr-jj remove: {error}", file=sys.stderr)
        return 1
    return remove_workspace(root, primary, env, input_fn, assume_yes)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("remove", help="remove the current jj workspace")
    parser.add_argument(
        "--current",
        action="store_true",
        help="remove the workspace containing the current directory",
    )
    parser.add_argument("--yes", action="store_true", help="skip confirmation")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    return remove_current(assume_yes=args.yes)
