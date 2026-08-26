"""Copy ignored files from the primary workspace to another workspace."""

import fnmatch
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

BUILTIN_EXCLUDES = (
    ".bzr/",
    ".git/",
    ".hg/",
    ".jj/",
    ".pijul/",
    ".sl/",
    ".svn/",
    ".worktrees/",
)


class CopyIgnoredError(RuntimeError):
    pass


def copy_ignored(source: Path, target: Path, excludes: tuple[str, ...] = ()) -> int:
    source = source.resolve()
    target = target.resolve()
    if source == target:
        raise CopyIgnoredError("source and target workspace are the same")

    try:
        result = subprocess.run(
            [
                "git",
                "ls-files",
                "-z",
                "--others",
                "--ignored",
                "--exclude-standard",
            ],
            cwd=source,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise CopyIgnoredError(f"could not list ignored files: {error}") from error
    if result.returncode:
        message = result.stderr.decode(errors="replace").strip()
        raise CopyIgnoredError(f"git ls-files failed: {message}")

    copied = 0
    patterns = BUILTIN_EXCLUDES + excludes
    if target.is_relative_to(source):
        workspace_tree = target.relative_to(source).parts[0]
        patterns += (f"{workspace_tree}/",)
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(raw.decode(errors="surrogateescape"))
        relative_posix = relative.as_posix()
        if _excluded(relative_posix, patterns):
            continue
        source_path = source / relative
        target_path = target / relative
        _reject_symlinked_parent(target, relative)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not source_path.is_symlink() and not source_path.is_file():
            continue
        _replace_file(source_path, target_path)
        copied += 1
    return copied


def _reject_symlinked_parent(target: Path, relative: Path) -> None:
    current = target
    for part in relative.parts[:-1]:
        current /= part
        if current.is_symlink():
            raise CopyIgnoredError(
                f"refusing to copy through symlinked directory {current}"
            )


def _replace_file(source: Path, target: Path) -> None:
    if target.is_dir() and not target.is_symlink():
        raise CopyIgnoredError(f"refusing to replace directory {target}")

    descriptor, temporary_name = tempfile.mkstemp(prefix=".wt-copy-", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.unlink()
        if source.is_symlink():
            temporary.symlink_to(source.readlink())
        else:
            shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _excluded(path: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        normalized = pattern.removeprefix("./")
        if normalized.endswith("/"):
            root = normalized.rstrip("/")
            if path == root or path.startswith(f"{root}/"):
                return True
        elif fnmatch.fnmatch(path, normalized):
            return True
    return False
