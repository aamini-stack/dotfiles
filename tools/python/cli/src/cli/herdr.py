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


def workspace_label(repo: str, name: str) -> str:
    safe_name = name.replace("/", "-").replace("\\", "-")
    return f"ws-{repo}-{safe_name}"


def list_workspaces() -> list[Workspace]:
    return cast(list[Workspace], herdr("workspace", "list").get("workspaces", []))


def find_workspace(
    label: str, workspaces: list[Workspace] | None = None
) -> Workspace | None:
    items = list_workspaces() if workspaces is None else workspaces
    return next((item for item in items if item.get("label") == label), None)


def find_for_jj(
    repo: str, name: str, workspaces: list[Workspace] | None = None
) -> Workspace | None:
    return find_workspace(workspace_label(repo, name), workspaces)


def focus_workspace(workspace_id: str) -> None:
    herdr("workspace", "focus", workspace_id)


def focus_or_create(
    repo: str,
    name: str,
    cwd: Path,
    workspaces: list[Workspace] | None = None,
) -> tuple[dict, bool, list[Workspace]]:
    items = list_workspaces() if workspaces is None else workspaces
    existing = find_for_jj(repo, name, items)
    if existing is not None:
        focus_workspace(existing["workspace_id"])
        return {"workspace": existing}, False, items
    created = herdr(
        "workspace",
        "create",
        "--cwd",
        str(cwd),
        "--label",
        workspace_label(repo, name),
        "--focus",
    )
    return created, True, items


def close_for_jj(
    repo: str, name: str, workspaces: list[Workspace] | None = None
) -> tuple[Workspace | None, list[Workspace]]:
    items = list_workspaces() if workspaces is None else workspaces
    existing = find_for_jj(repo, name, items)
    if existing is not None:
        herdr("workspace", "close", existing["workspace_id"])
    return existing, items
