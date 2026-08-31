"""Connect Herdr to managed SSH development boxes."""

from __future__ import annotations

import argparse
import subprocess
import sys

from .boxes import (
    Box,
    BoxError,
    add_box,
    edit_box,
    get_box,
    list_boxes,
    list_managed_boxes,
    remove_box,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dev", description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    connect = subparsers.add_parser("connect", help="connect Herdr to a box")
    connect.add_argument("name", nargs="?", help="omit to select with fzf")
    connect.set_defaults(run=_connect)

    add = subparsers.add_parser("add", help="add a managed box")
    add.add_argument("name", nargs="?", help="omit to enter the name interactively")
    add.set_defaults(run=_add)

    edit = subparsers.add_parser("edit", help="edit a managed box")
    edit.add_argument("name", nargs="?", help="omit to select with fzf")
    edit.set_defaults(run=_edit)

    remove = subparsers.add_parser(
        "remove", aliases=["rm"], help="remove a managed box"
    )
    remove.add_argument("name", nargs="?", help="omit to select with fzf")
    remove.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    remove.set_defaults(run=_remove)

    listing = subparsers.add_parser("list", aliases=["ls"], help="list boxes")
    listing.set_defaults(run=_list)

    test = subparsers.add_parser("test", help="test SSH access to a box")
    test.add_argument("name", nargs="?", help="omit to select with fzf")
    test.set_defaults(run=_test)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    commands = {"connect", "add", "edit", "remove", "rm", "list", "ls", "test"}
    if not arguments:
        arguments = ["connect"]
    elif arguments[0] not in commands and not arguments[0].startswith("-"):
        arguments.insert(0, "connect")

    parser = build_parser()
    args = parser.parse_args(arguments)
    if not hasattr(args, "run"):
        parser.print_help()
        return 0
    try:
        return args.run(args)
    except KeyboardInterrupt:
        return 130
    except BoxError as error:
        print(f"dev: {error}", file=sys.stderr)
        return 1


def _connect(args: argparse.Namespace) -> int:
    box = get_box(args.name) if args.name else _select_box(list_boxes())
    if box is None:
        return 0
    try:
        return subprocess.run(
            ["herdr", "--remote", box.name, "--remote-keybindings", "server"],
            check=False,
        ).returncode
    except OSError as error:
        raise BoxError(f"could not start herdr: {error}") from error


def _add(args: argparse.Namespace) -> int:
    name = args.name or input("Box name: ").strip()
    if not name:
        raise BoxError("a box name is required")
    box = add_box(name)
    print(f"added {box.name}\t{box.hostname}")
    return 0


def _edit(args: argparse.Namespace) -> int:
    if args.name:
        updated = edit_box(args.name)
    else:
        box = _select_box(list_managed_boxes())
        if box is None:
            return 0
        updated = edit_box(box.name)
    print(f"updated {updated.name}\t{updated.hostname}")
    return 0


def _remove(args: argparse.Namespace) -> int:
    if args.name:
        name = args.name
    else:
        box = _select_box(list_managed_boxes())
        if box is None:
            return 0
        name = box.name
    if not args.yes:
        answer = input(f"Remove {name}? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            return 0
    remove_box(name)
    print(f"removed {name}")
    return 0


def _list(_args: argparse.Namespace) -> int:
    for box in list_boxes():
        print(f"{box.name}\t{box.hostname}\t{box.source}")
    return 0


def _test(args: argparse.Namespace) -> int:
    box = get_box(args.name) if args.name else _select_box(list_boxes())
    if box is None:
        return 0
    try:
        return subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=5",
                box.name,
                "true",
            ],
            check=False,
        ).returncode
    except OSError as error:
        raise BoxError(f"could not start ssh: {error}") from error


def _select_box(boxes: list[Box]) -> Box | None:
    if not boxes:
        raise BoxError("no boxes exist; add one with 'dev add'")
    lines = [f"{box.name}\t{box.hostname}\t{box.source}" for box in boxes]
    try:
        result = subprocess.run(
            [
                "fzf",
                "--prompt=devbox: ",
                "--delimiter=\t",
                "--with-nth=1,2,3",
                "--header=name\thostname\tsource",
            ],
            input="\n".join(lines),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise BoxError(f"could not start fzf: {error}") from error
    if result.returncode in {1, 130}:
        return None
    if result.returncode:
        detail = result.stderr.strip() or f"fzf exited with status {result.returncode}"
        raise BoxError(detail)
    selected_name = result.stdout.partition("\t")[0].strip()
    return next((box for box in boxes if box.name == selected_name), None)


if __name__ == "__main__":
    raise SystemExit(main())
