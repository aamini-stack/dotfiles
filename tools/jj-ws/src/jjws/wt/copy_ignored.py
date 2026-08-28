"""Copy ignored files from the primary workspace to another workspace."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from pathspec import GitIgnoreSpec

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


def copy_ignored(
    source: Path,
    target: Path,
    excludes: tuple[str, ...] = (),
    includes: tuple[str, ...] | None = None,
    *,
    force: bool = False,
) -> int:
    source = source.resolve()
    target = target.resolve()
    if source == target:
        raise CopyIgnoredError("source and target workspace are the same")

    ignored = _ignored_files(source)
    include_file = _read_patterns(source / ".worktreeinclude")
    include_spec = _selection_spec(include_file)
    config_include_spec = _selection_spec(includes)
    exclude_spec = GitIgnoreSpec.from_lines(BUILTIN_EXCLUDES + excludes)
    copied = 0

    workspace_tree = None
    if target.is_relative_to(source):
        workspace_tree = target.relative_to(source).parts[0]

    for relative_posix in ignored:
        if workspace_tree and (
            relative_posix == workspace_tree
            or relative_posix.startswith(f"{workspace_tree}/")
        ):
            continue
        if include_spec is not None and not include_spec.match_file(relative_posix):
            continue
        if config_include_spec is not None and not config_include_spec.match_file(
            relative_posix
        ):
            continue
        if exclude_spec.match_file(relative_posix):
            continue

        relative = Path(relative_posix)
        source_path = source / relative
        target_path = target / relative
        if not source_path.is_symlink() and not source_path.is_file():
            continue
        if (target_path.exists() or target_path.is_symlink()) and not force:
            continue
        _reject_symlinked_parent(target, relative)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        _replace_file(source_path, target_path)
        copied += 1
    return copied


def _ignored_files(source: Path) -> list[str]:
    if (source / ".git").exists():
        return _git_ignored_files(source)
    return _jj_ignored_files(source)


def _git_ignored_files(source: Path) -> list[str]:
    result = _run(
        ["git", "ls-files", "-z", "--others", "--ignored", "--exclude-standard"],
        source,
        "git ls-files",
    )
    return _nul_paths(result.stdout)


def _jj_ignored_files(source: Path) -> list[str]:
    tracked_result = _run(
        ["jj", "file", "list", "-T", 'path ++ "\\0"'],
        source,
        "jj file list",
    )
    tracked = set(_nul_paths(tracked_result.stdout))
    specs = []
    ignored = []
    for root, directory_names, file_names in os.walk(source, followlinks=False):
        root_path = Path(root)
        relative_root = root_path.relative_to(source)
        patterns = _read_patterns(root_path / ".gitignore")
        if patterns is not None:
            specs.append((relative_root, GitIgnoreSpec.from_lines(patterns)))
        directory_names[:] = [
            name
            for name in directory_names
            if name not in {".jj", ".git"} and not (root_path / name).is_symlink()
        ]
        for name in file_names:
            relative_path = relative_root / name
            relative = relative_path.as_posix()
            if relative not in tracked and _is_ignored(relative_path, specs):
                ignored.append(relative)
    return ignored


def _is_ignored(path: Path, specs: list[tuple[Path, GitIgnoreSpec]]) -> bool:
    ignored = False
    for scope, spec in specs:
        if not path.is_relative_to(scope):
            continue
        result = spec.check_file(path.relative_to(scope).as_posix())
        if result.include is not None:
            ignored = result.include
    return ignored


def _run(
    command: list[str], cwd: Path, label: str
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, check=False)
    except OSError as error:
        raise CopyIgnoredError(f"could not run {label}: {error}") from error
    if result.returncode:
        message = result.stderr.decode(errors="replace").strip()
        raise CopyIgnoredError(f"{label} failed: {message}")
    return result


def _nul_paths(raw: bytes) -> list[str]:
    return [
        value.decode(errors="surrogateescape") for value in raw.split(b"\0") if value
    ]


def _selection_spec(patterns: tuple[str, ...] | None) -> GitIgnoreSpec | None:
    if patterns is None:
        return None
    return GitIgnoreSpec.from_lines(patterns)


def _read_patterns(path: Path) -> tuple[str, ...] | None:
    if not path.is_file():
        return None
    try:
        return tuple(path.read_text().splitlines())
    except OSError as error:
        raise CopyIgnoredError(f"could not read {path}: {error}") from error


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
