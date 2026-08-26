"""Push a bookmark and open its pull request."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "pr", help="push a bookmark and open its pull request"
    )
    parser.add_argument(
        "bookmark",
        nargs="?",
        help="bookmark to push and use as the PR head (defaults to the sole bookmark on @)",
    )
    parser.set_defaults(run=run, gh_args=[])


def run(args: argparse.Namespace) -> int:
    return create_pr(args.bookmark, args.gh_args)


def create_pr(bookmark: str | None, gh_args: list[str]) -> int:
    for command in ("jj", "gh"):
        if shutil.which(command) is None:
            print(f"wt pr: {command} is required", file=sys.stderr)
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
        print("wt pr: jj did not return a Git directory", file=sys.stderr)
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
            "wt pr: specify a bookmark; @ must have exactly one local bookmark",
            file=sys.stderr,
        )
        return None
    return bookmarks[0]
