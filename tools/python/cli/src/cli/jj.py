"""Thin wrapper around the jj CLI, mirroring herdr.py."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


class JjError(RuntimeError):
    pass


@dataclass(frozen=True)
class Workspace:
    name: str
    root: Path


def jj(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["jj", *args], cwd=cwd, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise JjError(
            f"jj {' '.join(args)} failed ({result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def repo_root(cwd: Path) -> Path:
    return Path(jj("root", cwd=cwd).strip())


def primary_root(cwd: Path) -> Path:
    """Root of the primary workspace for the repo containing cwd.

    A secondary workspace's `.jj/repo` is a pointer file to the store dir in
    the primary workspace; the primary's `.jj/repo` is the store itself.
    """
    root = repo_root(cwd)
    repo_ptr = root / ".jj" / "repo"
    if repo_ptr.is_dir():
        return root
    store = (root / ".jj" / repo_ptr.read_text().strip()).resolve()
    return store.parent.parent


def add_workspace(
    dest: Path, name: str, cwd: Path, revision: str | None = None
) -> None:
    args = ["workspace", "add", str(dest), "--name", name]
    if revision is not None:
        args.extend(["--revision", revision])
    jj(*args, cwd=cwd)


def workspaces(cwd: Path) -> list[Workspace]:
    template = 'self.name() ++ "\\t" ++ self.root() ++ "\\n"'
    out = jj("workspace", "list", "-T", template, cwd=cwd)
    result = []
    for line in out.splitlines():
        name, separator, root = line.partition("\t")
        if name and separator and root:
            result.append(Workspace(name=name, root=Path(root)))
    return result


def workspace(cwd: Path, name: str) -> Workspace:
    found = next((item for item in workspaces(cwd) if item.name == name), None)
    if found is None:
        raise JjError(f"'{name}' is not a jj workspace")
    return found


def current_workspace(cwd: Path) -> Workspace:
    root = repo_root(cwd).resolve()
    found = next(
        (item for item in workspaces(cwd) if item.root.resolve() == root), None
    )
    if found is None:
        raise JjError(f"could not identify jj workspace at {root}")
    return found


def workspace_names(cwd: Path) -> list[str]:
    try:
        return [item.name for item in workspaces(cwd)]
    except JjError:
        out = jj("workspace", "list", cwd=cwd)
        return [
            line.split(":", 1)[0].strip() for line in out.splitlines() if line.strip()
        ]


def forget_workspace(name: str, cwd: Path) -> None:
    jj("workspace", "forget", name, cwd=cwd)


def status_token(cwd: Path, rev: str = "@") -> str:
    """Sidebar token: short change id plus ✓ (empty) or ● (dirty)."""
    template = 'change_id.shortest() ++ " " ++ if(empty, "✓", "●")'
    return jj("log", "--no-graph", "-r", rev, "-T", template, cwd=cwd).strip()
