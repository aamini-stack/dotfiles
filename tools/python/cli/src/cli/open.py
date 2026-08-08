"""Open a jj workspace as a laid-out herdr workspace.

Invoked by herdr-jj with the workspace path. If a herdr workspace labeled with
the jj workspace name already exists it is focused; otherwise it is created
with a vertical split: the left pane runs the project's setup (post-create
hooks for freshly created workspaces, then the `mise run bootstrap` task if
any) and the right pane runs opencode.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import guard
from .herdr import (
    HerdrError,
    Workspace,
    ensure_open,
    focus_workspace,
    herdr,
    workspace_label,
)


def herdr_label(path: Path) -> str:
    return workspace_label(path.name)


def has_bootstrap_task(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["mise", "tasks", "--json"],
            cwd=path,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode:
        return False
    try:
        tasks = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return any(task.get("name", "").split(":")[-1] == "bootstrap" for task in tasks)


def open_workspace(
    path: Path,
    project_path: Path | None = None,
    workspace_name: str | None = None,
    run_setup: bool = False,
) -> int:
    name = path.name if workspace_name is None else workspace_name
    created, is_new, workspaces = ensure_open(name, path, project_path=project_path)
    workspace_id = created["workspace"]["workspace_id"]
    if not is_new:
        focus_workspace(workspace_id)
        _arm(workspace_id, path, workspaces)
        return 0

    left = created["root_pane"]["pane_id"]
    right = herdr("pane", "split", left, "--direction", "right", "--no-focus")["pane"][
        "pane_id"
    ]

    setup = []
    if run_setup:
        setup.append("wt hook post-create")
    if has_bootstrap_task(path):
        setup.append("mise run bootstrap")
    if setup:
        herdr("pane", "run", left, " && ".join(setup))
    herdr("pane", "run", right, "opencode")
    _arm(workspace_id, path, workspaces)
    focus_workspace(workspace_id)
    return 0


def _arm(workspace_id: str, path: Path, workspaces: list[Workspace]) -> None:
    live_ids = {w["workspace_id"] for w in workspaces} | {workspace_id}
    try:
        guard.arm(workspace_id, path, live_ids)
    except OSError as error:
        print(f"herdr-ws open: cd-guard arm failed: {error}", file=sys.stderr)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("open", help="open a jj workspace in herdr")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="jj workspace path to open (defaults to the current directory)",
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        default=None,
        help="primary jj workspace path; its directory name labels the herdr "
        "workspace (defaults to the parent directory of PATH)",
    )
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    path = args.path.resolve()
    project_path = args.project_path.resolve() if args.project_path else None
    try:
        return open_workspace(path, project_path)
    except HerdrError as error:
        print(f"herdr-ws open: {error}", file=sys.stderr)
        return 1
