"""Personal Jujutsu workflow helpers."""

import argparse
import os
import shutil
import subprocess
import sys
import time
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
    switch.add_argument(
        "-c",
        "--create",
        action="store_true",
        help="create the workspace with jj workspace add if it does not exist",
    )
    remove = commands.add_parser("remove", help="remove a Herdr jj workspace")
    remove.add_argument(
        "workspace",
        nargs="?",
        help="workspace name or project/workspace path (defaults to the current workspace)",
    )
    remove.add_argument(
        "--force",
        action="store_true",
        help="remove without confirming work that is not on a bookmark",
    )

    args, gh_args = parser.parse_known_args()
    if args.command == "pr" and args.pr_command == "create":
        return create_pr(args.bookmark, gh_args)
    if args.command == "switch":
        if gh_args:
            parser.error(f"unrecognized arguments: {' '.join(gh_args)}")
        return switch_workspace(args.workspace, args.create)
    if args.command == "remove":
        if gh_args:
            parser.error(f"unrecognized arguments: {' '.join(gh_args)}")
        return remove_workspace(args.workspace, args.force)
    return 2


def switch_workspace(
    workspace: str | None, create: bool = False, root: Path = WORKSPACES_ROOT
) -> int:
    if create:
        if workspace is None:
            print("wt: --create requires a workspace name", file=sys.stderr)
            return 1
        destination = find_or_create_workspace(workspace, root)
    else:
        destination = resolve_workspace(workspace, root)
    if destination is None:
        return 1
    print(destination)
    return 0


def find_or_create_workspace(workspace: str, root: Path) -> Path | None:
    matches = find_workspace(workspace, root)
    if len(matches) > 1:
        labels = ", ".join(path.relative_to(root).as_posix() for path in matches)
        print(f"wt: workspace {workspace!r} is ambiguous: {labels}", file=sys.stderr)
        return None
    if matches:
        return matches[0]
    return create_workspace(workspace, root)


def create_workspace(name: str, root: Path) -> Path | None:
    checkout = main_checkout()
    if checkout is None:
        return None

    destination = root / checkout.name / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["jj", "workspace", "add", str(destination)], check=False)
    if result.returncode:
        return None
    return destination


def main_checkout() -> Path | None:
    workspace_root = jj_workspace_root()
    if workspace_root is None:
        return None

    main = workspace_main_checkout(workspace_root)
    if main is not None:
        return main
    return workspace_root


def workspace_main_checkout(workspace: Path) -> Path | None:
    pointer = workspace / ".jj" / "repo"
    if not pointer.is_file():
        return None
    repo_dir = (pointer.parent / pointer.read_text().strip()).resolve()
    return repo_dir.parent.parent


def jj_workspace_root() -> Path | None:
    result = subprocess.run(["jj", "root"], text=True, capture_output=True, check=False)
    if result.returncode:
        sys.stderr.write(result.stderr)
        return None
    return Path(result.stdout.strip())


def current_workspace() -> Path | None:
    workspace = jj_workspace_root()
    if workspace is None:
        return None
    if not (workspace / ".jj" / "repo").is_file():
        print(
            f"wt: {workspace} is the default checkout; refusing to remove it",
            file=sys.stderr,
        )
        return None
    return workspace


def resolve_workspace(workspace: str | None, root: Path) -> Path | None:
    if workspace is None:
        workspaces = discover_workspaces(root)
        if not workspaces:
            print(f"wt: no jj workspaces found under {root}", file=sys.stderr)
            return None
        if shutil.which("fzf") is None:
            print("wt: fzf is required to pick a workspace", file=sys.stderr)
            return None
        labels = {path.relative_to(root).as_posix(): path for path in workspaces}
        picker = subprocess.run(
            ["fzf", "--prompt=workspace: ", "--height=60%", "--reverse", "--border"],
            input="\n".join(labels),
            text=True,
            stdout=subprocess.PIPE,
            check=False,
        )
        if picker.returncode:
            return None
        workspace = picker.stdout.rstrip("\n")

    return resolve_named_workspace(workspace, root)


def resolve_named_workspace(workspace: str, root: Path) -> Path | None:
    if not discover_workspaces(root):
        print(f"wt: no jj workspaces found under {root}", file=sys.stderr)
        return None

    matches = find_workspace(workspace, root)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        labels = ", ".join(path.relative_to(root).as_posix() for path in matches)
        print(f"wt: workspace {workspace!r} is ambiguous: {labels}", file=sys.stderr)
        return None
    print(f"wt: workspace {workspace!r} not found under {root}", file=sys.stderr)
    return None


def find_workspace(workspace: str, root: Path) -> list[Path]:
    workspaces = discover_workspaces(root)
    labels = {path.relative_to(root).as_posix(): path for path in workspaces}
    destination = labels.get(workspace.strip("/"))
    if destination is not None:
        return [destination]
    return [path for path in workspaces if path.name == workspace]


def remove_workspace(
    workspace: str | None, force: bool = False, root: Path = WORKSPACES_ROOT
) -> int:
    if workspace is None:
        destination = current_workspace()
        if destination is None:
            return 1
        label = destination.name
    else:
        destination = resolve_named_workspace(workspace, root)
        if destination is None:
            return 1
        label = destination.relative_to(root).as_posix()

    cwd = Path.cwd()
    fallback = None
    if cwd == destination or destination in cwd.parents:
        main = workspace_main_checkout(destination)
        if main is not None and main.is_dir():
            fallback = main

    if not force:
        pending = subprocess.run(
            [
                "jj",
                "log",
                "--no-graph",
                "--revisions",
                '(::@ ~ ::bookmarks()) ~ (empty() & description(exact:""))',
                "--template",
                'commit_id ++ "\\n"',
            ],
            cwd=destination,
            text=True,
            capture_output=True,
            check=False,
        )
        if pending.returncode:
            sys.stderr.write(pending.stderr)
            return pending.returncode

        commits = pending.stdout.split()
        if commits:
            print(
                f"wt: {label} has {len(commits)} commit(s) not on any bookmark",
                file=sys.stderr,
            )
            answer = ""
            if sys.stdin.isatty():
                try:
                    print(
                        f"remove {label} anyway? [y/N] ",
                        end="",
                        file=sys.stderr,
                        flush=True,
                    )
                    answer = input()
                except EOFError:
                    pass
            if answer.lower() not in ("y", "yes"):
                return 1

    forget = subprocess.run(["jj", "workspace", "forget"], cwd=destination, check=False)
    if forget.returncode:
        return forget.returncode

    if not remove_tree(destination):
        print(
            f"wt: workspace forgotten; delete {destination} manually", file=sys.stderr
        )
        return 1
    if fallback is not None:
        print(fallback)
    return 0


def remove_tree(destination: Path) -> bool:
    error: OSError | None = None
    for _ in range(3):
        if not destination.exists():
            return True
        try:
            shutil.rmtree(destination)
            return True
        except OSError as caught:
            error = caught
            time.sleep(0.2)
    print(f"wt: could not delete {destination}: {error}", file=sys.stderr)
    return False


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

    bookmarks = [name for name in result.stdout.splitlines() if name]
    if len(bookmarks) != 1:
        print(
            "wt: specify a bookmark; @ must have exactly one local bookmark",
            file=sys.stderr,
        )
        return None
    return bookmarks[0]


if __name__ == "__main__":
    raise SystemExit(main())
