"""Personal Jujutsu workflow helpers."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


WORKSPACES_ROOT = Path.home() / ".herdr" / "workspaces"


def main() -> int:
    parser = argparse.ArgumentParser(prog="wt")
    commands = parser.add_subparsers(dest="command", required=True)
    pr = commands.add_parser("pr", help="create pull requests")
    pr_commands = pr.add_subparsers(dest="pr_command", required=True)
    create = pr_commands.add_parser(
        "create", help="push a bookmark and create its pull request"
    )
    create.add_argument(
        "bookmark",
        nargs="?",
        help="bookmark to push and use as the PR head (defaults to the sole bookmark on @)",
    )
    switch = commands.add_parser("switch", help="switch to a Herdr jj workspace")
    switch.add_argument(
        "workspace",
        nargs="?",
        help="workspace name or project/workspace path (opens a picker if omitted)",
    )

    args, gh_args = parser.parse_known_args()
    if args.command == "pr" and args.pr_command == "create":
        return create_pr(args.bookmark, gh_args)
    if args.command == "switch":
        if gh_args:
            parser.error(f"unrecognized arguments: {' '.join(gh_args)}")
        return switch_workspace(args.workspace)
    return 2


def switch_workspace(workspace: str | None, root: Path = WORKSPACES_ROOT) -> int:
    workspaces = discover_workspaces(root)
    if not workspaces:
        print(f"wt: no jj workspaces found under {root}", file=sys.stderr)
        return 1

    labels = {path.relative_to(root).as_posix(): path for path in workspaces}
    if workspace is None:
        if shutil.which("fzf") is None:
            print("wt: fzf is required for interactive switching", file=sys.stderr)
            return 1
        picker = subprocess.run(
            ["fzf", "--prompt=workspace: ", "--height=60%", "--reverse", "--border"],
            input="\n".join(labels),
            text=True,
            stdout=subprocess.PIPE,
            check=False,
        )
        if picker.returncode:
            return picker.returncode
        workspace = picker.stdout.rstrip("\n")

    destination = labels.get(workspace.strip("/"))
    if destination is None:
        leaf_matches = [path for path in workspaces if path.name == workspace]
        if len(leaf_matches) == 1:
            destination = leaf_matches[0]
        elif len(leaf_matches) > 1:
            matches = ", ".join(
                path.relative_to(root).as_posix() for path in leaf_matches
            )
            print(
                f"wt: workspace {workspace!r} is ambiguous: {matches}", file=sys.stderr
            )
            return 1
        else:
            print(
                f"wt: workspace {workspace!r} not found under {root}", file=sys.stderr
            )
            return 1

    print(destination)
    return 0


def discover_workspaces(root: Path) -> list[Path]:
    if not root.is_dir():
        return []

    workspaces = []
    for current, directories, files in os.walk(root):
        if ".jj" in directories or ".jj" in files:
            workspaces.append(Path(current))
            directories.clear()
    return sorted(
        workspaces, key=lambda path: path.relative_to(root).as_posix().casefold()
    )


def create_pr(bookmark: str | None, gh_args: list[str]) -> int:
    for command in ("jj", "gh"):
        if shutil.which(command) is None:
            print(f"wt: {command} is required", file=sys.stderr)
            return 1

    if bookmark is None:
        bookmark = current_bookmark()
        if bookmark is None:
            return 1

    git_root = subprocess.run(
        ["jj", "git", "root"], text=True, capture_output=True, check=False
    )
    if git_root.returncode:
        sys.stderr.write(git_root.stderr)
        return git_root.returncode

    git_dir = Path(git_root.stdout.strip())
    if not git_dir.is_dir():
        print("wt: jj did not return a Git directory", file=sys.stderr)
        return 1

    push = subprocess.run(["jj", "git", "push", "--bookmark", bookmark], check=False)
    if push.returncode:
        return push.returncode

    env = os.environ | {"GIT_DIR": str(git_dir)}
    return subprocess.run(
        ["gh", "pr", "create", "--head", bookmark, *gh_args], env=env, check=False
    ).returncode


def current_bookmark() -> str | None:
    result = subprocess.run(
        [
            "jj",
            "log",
            "--no-graph",
            "--revisions",
            "@",
            "--template",
            'local_bookmarks.map(|b| b.name()).join("\\n") ++ "\\n"',
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        sys.stderr.write(result.stderr)
        return None

    bookmarks = result.stdout.splitlines()
    if len(bookmarks) != 1:
        print(
            "wt: specify a bookmark; @ must have exactly one local bookmark",
            file=sys.stderr,
        )
        return None
    return bookmarks[0]


if __name__ == "__main__":
    raise SystemExit(main())
