"""wt: create and clean up jj workspaces."""

import argparse
import os
import sys
from pathlib import Path

from ..lib.jj import JjError
from . import env, pr
from .config import ConfigError
from .copy_ignored import CopyIgnoredError
from .hooks import PHASES, HookError
from .lifecycle import (
    CreateHookError,
    WtError,
    colocate_workspaces,
    copy_ignored_to_current,
    create_workspace,
    list_workspaces,
    pick_workspace,
    remove_workspace,
    resolve_workspace,
    run_configured_hook,
    run_configured_phase,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wt", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    switch = subparsers.add_parser("switch", help="switch to a jj workspace")
    switch.add_argument("name", nargs="?", help="omit to pick a workspace with fzf")
    switch.add_argument(
        "-c", "--create", action="store_true", help="create the workspace"
    )
    switch.add_argument(
        "-r",
        "--revision",
        help="revision/revset to base a created workspace on (default: @)",
    )
    switch.add_argument(
        "--force",
        action="store_true",
        help="move aside a leftover directory occupying the workspace destination",
    )
    switch.set_defaults(run=_switch)

    remove = subparsers.add_parser(
        "rm", aliases=["remove"], help="remove a jj workspace"
    )
    remove.add_argument("name", nargs="?", help="defaults to the current workspace")
    remove.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    remove.set_defaults(run=_remove)

    listing = subparsers.add_parser("ls", aliases=["list"], help="list jj workspaces")
    listing.set_defaults(run=_list)

    hook = subparsers.add_parser(
        "hook",
        help="run a configured hook by name, or a whole phase "
        "(post-create, pre-remove, post-remove)",
    )
    hook.add_argument("name")
    hook.set_defaults(run=_hook)

    copy = subparsers.add_parser(
        "copy-ignored", help="copy ignored files from the primary workspace"
    )
    copy.set_defaults(run=_copy_ignored)

    colocate = subparsers.add_parser(
        "colocate",
        help="register git worktrees for workspaces created before colocation",
    )
    colocate.add_argument(
        "name", nargs="?", help="defaults to all workspaces missing a .git"
    )
    colocate.set_defaults(run=_colocate)
    pr.add_parser(subparsers)
    env.add_parser(subparsers)
    return parser


def main() -> int:
    parser = build_parser()
    args, extra = parser.parse_known_args()
    if extra:
        if args.command != "pr":
            parser.error(f"unrecognized arguments: {' '.join(extra)}")
        args.gh_args = extra
    try:
        return args.run(args)
    except (JjError, WtError, ConfigError, HookError, CopyIgnoredError) as error:
        print(f"wt: {error}", file=sys.stderr)
        return 1


def _switch(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    if args.create:
        if not args.name:
            raise WtError("switch --create requires a name")
        try:
            target = create_workspace(cwd, args.name, args.revision, force=args.force)
        except CreateHookError as error:
            _emit(error.workspace.root)
            print(f"wt: {error}", file=sys.stderr)
            print(
                f"wt: workspace created; re-run hooks with 'wt hook <name>' in {error.workspace.root}",
                file=sys.stderr,
            )
            return 1
    elif args.name:
        if args.revision:
            raise WtError("--revision only applies with --create")
        target = resolve_workspace(cwd, args.name)
    else:
        target = pick_workspace(cwd)
        if target is None:
            return 0
    _emit(target.root)
    return 0


def _emit(path: Path) -> None:
    result_file = os.environ.get("WT_RESULT_FILE")
    if result_file:
        try:
            Path(result_file).write_text(str(path))
        except OSError as error:
            raise WtError(f"could not write shell result: {error}") from error
    else:
        print(path)


def _remove(args: argparse.Namespace) -> int:
    removed = remove_workspace(Path.cwd(), args.name, assume_yes=args.yes)
    print(f"removed {removed.name}")
    return 0


def _list(args: argparse.Namespace) -> int:
    current, items = list_workspaces(Path.cwd())
    for item in items:
        marker = "*" if item.name == current.name else " "
        print(f"{marker} {item.name}\t{item.root}")
    return 0


def _hook(args: argparse.Namespace) -> int:
    if args.name in PHASES:
        run_configured_phase(Path.cwd(), args.name)
    else:
        run_configured_hook(Path.cwd(), args.name)
    return 0


def _copy_ignored(args: argparse.Namespace) -> int:
    count = copy_ignored_to_current(Path.cwd())
    print(f"copied {count} ignored file{'s' if count != 1 else ''}")
    return 0


def _colocate(args: argparse.Namespace) -> int:
    converted = colocate_workspaces(Path.cwd(), args.name)
    if not converted:
        print("nothing to colocate")
        return 0
    for item in converted:
        print(f"colocated {item.name}\t{item.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
