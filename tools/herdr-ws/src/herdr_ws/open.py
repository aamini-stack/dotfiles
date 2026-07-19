"""Open a jj workspace as a laid-out herdr workspace.

Invoked by dojjo's post-start and post-switch hooks with the workspace path.
If a herdr workspace labeled ws-<project>-<name> already exists it is focused;
otherwise it is created with a vertical split: the left pane runs the
project's `mise run bootstrap` task (if any) and the right pane runs opencode.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import guard
from .herdr import HerdrError, herdr


def sanitize_name(name: str) -> str:
    """Mirror dojjo's `sanitize` template filter (slashes become dashes)."""
    return name.replace("/", "-").replace("\\", "-")


def herdr_label_for(project: str, name: str) -> str:
    return f"ws-{project}-{sanitize_name(name)}"


def herdr_label(path: Path, project_path: Path | None = None) -> str:
    project = project_path.name if project_path is not None else path.parent.name
    return herdr_label_for(project, path.name)


def find_workspace(label: str, workspaces: list | None = None) -> dict | None:
    if workspaces is None:
        workspaces = herdr("workspace", "list").get("workspaces", [])
    return next((w for w in workspaces if w.get("label") == label), None)


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


def open_workspace(path: Path, project_path: Path | None = None) -> int:
    label = herdr_label(path, project_path)

    workspaces = herdr("workspace", "list").get("workspaces", [])
    existing = find_workspace(label, workspaces)
    if existing is not None:
        herdr("workspace", "focus", existing["workspace_id"])
        _arm(existing["workspace_id"], path, workspaces)
        return 0

    created = herdr(
        "workspace", "create", "--cwd", str(path), "--label", label, "--focus"
    )
    left = created["root_pane"]["pane_id"]
    right = herdr("pane", "split", left, "--direction", "right", "--focus")["pane"][
        "pane_id"
    ]

    if has_bootstrap_task(path):
        herdr("pane", "run", left, "mise run bootstrap")
    herdr("pane", "run", right, "opencode")
    _arm(created["workspace"]["workspace_id"], path, workspaces)
    return 0


def _arm(workspace_id: str, path: Path, workspaces: list) -> None:
    live_ids = {w["workspace_id"] for w in workspaces} | {workspace_id}
    try:
        guard.arm(workspace_id, path, live_ids)
    except OSError as error:
        print(f"herdr-ws-open: cd-guard arm failed: {error}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(prog="herdr-ws-open")
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
    args = parser.parse_args()

    path = args.path.resolve()
    project_path = args.project_path.resolve() if args.project_path else None
    try:
        return open_workspace(path, project_path)
    except HerdrError as error:
        print(f"herdr-ws-open: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
