"""Thin wrapper around the herdr CLI's JSON envelope."""

import json
import subprocess
from pathlib import Path
from typing import NotRequired, TypedDict, cast


class HerdrError(RuntimeError):
    pass


class Workspace(TypedDict):
    workspace_id: str
    label: NotRequired[str]
    cwd: NotRequired[str]
    worktree: NotRequired[dict]


def herdr(*args: str) -> dict:
    result = subprocess.run(
        ["herdr", *args], text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise HerdrError(
            f"herdr {' '.join(args)} failed ({result.returncode}): {result.stderr.strip()}"
        )
    if not result.stdout.strip():
        return {}
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise HerdrError(
            f"herdr {' '.join(args)} returned invalid JSON: {result.stdout.strip()}"
        ) from error
    return envelope.get("result", {})


def workspace_label(name: str) -> str:
    return name.replace("/", "-").replace("\\", "-")


def list_workspaces() -> list[Workspace]:
    return cast(list[Workspace], herdr("workspace", "list").get("workspaces", []))


def find_workspace(
    label: str, workspaces: list[Workspace] | None = None
) -> Workspace | None:
    items = list_workspaces() if workspaces is None else workspaces
    return next((item for item in items if item.get("label") == label), None)


def focused_workspace(workspaces: list[Workspace] | None = None) -> Workspace | None:
    items = list_workspaces() if workspaces is None else workspaces
    return next((item for item in items if item.get("focused")), None)


def find_for_jj(
    name: str, workspaces: list[Workspace] | None = None
) -> Workspace | None:
    return find_workspace(workspace_label(name), workspaces)


def find_by_worktree_path(
    path: Path, workspaces: list[Workspace] | None = None
) -> Workspace | None:
    items = list_workspaces() if workspaces is None else workspaces
    target = str(path)
    return next(
        (
            item
            for item in items
            if (item.get("worktree") or {}).get("checkout_path") == target
        ),
        None,
    )


def focus_workspace(workspace_id: str) -> None:
    herdr("workspace", "focus", workspace_id)


def ensure_open(
    name: str,
    cwd: Path,
    workspaces: list[Workspace] | None = None,
    project_path: Path | None = None,
) -> tuple[dict, bool, list[Workspace]]:
    # Never focuses: callers lay out panes first and focus last, because
    # switching focus closes the modal popup the plugin runs inside.
    items = list_workspaces() if workspaces is None else workspaces
    existing = find_for_jj(name, items)
    if existing is not None:
        if project_path is not None and "worktree" not in existing:
            # Opened before worktree provenance existed; re-opening through
            # worktree.open attaches it so the workspace nests under the repo.
            _worktree_open(project_path, cwd)
        return {"workspace": existing}, False, items
    if project_path is not None:
        opened = _worktree_open(project_path, cwd, label=workspace_label(name))
        if opened is not None and "workspace" in opened:
            return opened, not opened.get("already_open", False), items
    created = herdr(
        "workspace",
        "create",
        "--cwd",
        str(cwd),
        "--label",
        workspace_label(name),
        "--no-focus",
    )
    return created, True, items


def _worktree_open(
    project_path: Path, cwd: Path, label: str | None = None
) -> dict | None:
    # Fails when cwd is not a git worktree of the repo at project_path (e.g.
    # jj workspaces created before colocated worktree registration).
    args = ["worktree", "open", "--cwd", str(project_path), "--path", str(cwd)]
    if label is not None:
        args.extend(["--label", label])
    args.append("--no-focus")
    try:
        return herdr(*args)
    except HerdrError:
        return None


def close_for_jj(
    name: str,
    workspaces: list[Workspace] | None = None,
    path: Path | None = None,
) -> tuple[Workspace | None, list[Workspace]]:
    items = list_workspaces() if workspaces is None else workspaces
    existing = find_by_worktree_path(path, items) if path is not None else None
    if existing is None:
        existing = find_for_jj(name, items)
    if existing is not None:
        herdr("workspace", "close", existing["workspace_id"])
    return existing, items
