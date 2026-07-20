"""wt: create and clean up jj workspaces."""

import argparse
import os
import sys
from pathlib import Path

from ..jj import JjError
from .config import ConfigError
from .copy_ignored import CopyIgnoredError
from .hooks import HookError
from .lifecycle import (
    WtError,
    copy_ignored_to_current,
    create_workspace,
    list_workspaces,
    remove_workspace,
    run_configured_hook,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wt", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    new = subparsers.add_parser("new", help="create a jj workspace")
    new.add_argument("name")
    new.add_argument(
        "-r", "--revision", help="revision/revset to base it on (default: @)"
    )
    new.set_defaults(run=_new)

    remove = subparsers.add_parser(
        "rm", aliases=["remove"], help="remove a jj workspace"
    )
    remove.add_argument("name", nargs="?", help="defaults to the current workspace")
    remove.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    remove.set_defaults(run=_remove)

    listing = subparsers.add_parser("ls", aliases=["list"], help="list jj workspaces")
    listing.set_defaults(run=_list)

    hook = subparsers.add_parser("hook", help="run a configured hook by name")
    hook.add_argument("name")
    hook.set_defaults(run=_hook)

    copy = subparsers.add_parser(
        "copy-ignored", help="copy ignored files from the primary workspace"
    )
    copy.set_defaults(run=_copy_ignored)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.run(args)
    except (JjError, WtError, ConfigError, HookError, CopyIgnoredError) as error:
        print(f"wt: {error}", file=sys.stderr)
        return 1


def _new(args: argparse.Namespace) -> int:
    created = create_workspace(Path.cwd(), args.name, args.revision)
    result_file = os.environ.get("WT_RESULT_FILE")
    if result_file:
        try:
            Path(result_file).write_text(str(created.root))
        except OSError as error:
            raise WtError(f"could not write shell result: {error}") from error
    else:
        print(created.root)
    return 0


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
    run_configured_hook(Path.cwd(), args.name)
    return 0


def _copy_ignored(args: argparse.Namespace) -> int:
    count = copy_ignored_to_current(Path.cwd())
    print(f"copied {count} ignored file{'s' if count != 1 else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
