"""Storage and discovery for SSH development boxes."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class BoxError(Exception):
    """A development box operation failed."""


@dataclass(frozen=True)
class Box:
    name: str
    hostname: str
    source: str
    path: Path


NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
RESERVED_NAMES = {"add", "connect", "edit", "list", "ls", "remove", "rm", "test"}


def default_box_dir() -> Path:
    return Path.home() / ".ssh/devboxes.d"


def list_boxes(box_dir: Path | None = None, lima_dir: Path | None = None) -> list[Box]:
    managed = list_managed_boxes(box_dir)
    lima = list_lima_boxes(lima_dir)
    names = {box.name for box in managed}
    return sorted(
        managed + [box for box in lima if box.name not in names],
        key=lambda box: box.name,
    )


def list_managed_boxes(box_dir: Path | None = None) -> list[Box]:
    directory = box_dir or default_box_dir()
    if not directory.exists():
        return []
    return [
        read_box(path, expected_name=path.stem)
        for path in sorted(directory.glob("*.conf"))
        if not path.name.startswith(".")
    ]


def list_lima_boxes(lima_dir: Path | None = None) -> list[Box]:
    directory = lima_dir or Path.home() / ".lima"
    if not directory.exists():
        return []
    boxes = []
    for path in sorted(directory.glob("*/ssh.config")):
        try:
            boxes.append(read_box(path, source="lima"))
        except BoxError:
            continue
    return boxes


def get_box(
    name: str, box_dir: Path | None = None, lima_dir: Path | None = None
) -> Box:
    validate_name(name)
    managed_path = (box_dir or default_box_dir()) / f"{name}.conf"
    if managed_path.is_file():
        return read_box(managed_path, expected_name=name)
    for box in list_lima_boxes(lima_dir):
        if box.name == name:
            return box
    raise BoxError(f"box {name!r} does not exist")


def read_box(
    path: Path, *, expected_name: str | None = None, source: str = "managed"
) -> Box:
    try:
        contents = path.read_text()
    except OSError as error:
        raise BoxError(f"could not read {path}: {error}") from error

    hosts = []
    hostnames = []
    for raw_line in contents.splitlines():
        try:
            parts = shlex.split(raw_line, comments=True)
        except ValueError as error:
            raise BoxError(f"invalid SSH syntax in {path}: {error}") from error
        if not parts:
            continue
        if "=" in parts[0]:
            key, value = parts[0].split("=", 1)
            parts = [key, value, *parts[1:]]
        key = parts[0].lower()
        values = parts[1:]
        if key == "host":
            hosts.append(values)
        elif key == "hostname":
            hostnames.append(values)
        elif key == "match":
            raise BoxError(f"{path} cannot contain Match blocks")

    if len(hosts) != 1 or len(hosts[0]) != 1:
        raise BoxError(f"{path} must contain one concrete Host")
    name = hosts[0][0]
    validate_name(name)
    if expected_name is not None and name != expected_name:
        raise BoxError(f"Host {name!r} must match file name {expected_name!r}")
    if len(hostnames) != 1 or len(hostnames[0]) != 1:
        raise BoxError(f"{path} must contain one HostName")
    return Box(name=name, hostname=hostnames[0][0], source=source, path=path)


def add_box(name: str, box_dir: Path | None = None) -> Box:
    validate_name(name)
    directory = box_dir or default_box_dir()
    destination = directory / f"{name}.conf"
    if destination.exists():
        raise BoxError(f"box {name!r} already exists")
    template = f"Host {name}\n    HostName \n    User {os.environ.get('USER', '')}\n"
    return _edit_into_place(destination, name, template, create=True)


def edit_box(name: str, box_dir: Path | None = None) -> Box:
    path = box_path(name, box_dir)
    try:
        contents = path.read_text()
    except OSError as error:
        raise BoxError(f"could not read {path}: {error}") from error
    return _edit_into_place(path, name, contents)


def remove_box(name: str, box_dir: Path | None = None) -> None:
    path = box_path(name, box_dir)
    try:
        path.unlink()
    except OSError as error:
        raise BoxError(f"could not remove {path}: {error}") from error


def box_path(name: str, box_dir: Path | None = None) -> Path:
    validate_name(name)
    path = (box_dir or default_box_dir()) / f"{name}.conf"
    if not path.is_file():
        raise BoxError(f"managed box {name!r} does not exist")
    return path


def validate_name(name: str) -> None:
    if not NAME_PATTERN.fullmatch(name):
        raise BoxError(
            "box names must start with a letter or number and contain only letters, "
            "numbers, dots, underscores, or hyphens"
        )
    if name in RESERVED_NAMES:
        raise BoxError(f"box name {name!r} is reserved by the dev command")


def _edit_into_place(
    destination: Path, name: str, contents: str, *, create: bool = False
) -> Box:
    temporary = None
    try:
        destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{name}.", suffix=".tmp", dir=destination.parent, text=True
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w") as file:
            file.write(contents)
        os.chmod(temporary, 0o600)
    except OSError as error:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise BoxError(f"could not prepare {destination}: {error}") from error

    try:
        editor = shlex.split(
            os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
        )
        result = subprocess.run([*editor, str(temporary)], check=False)
        if result.returncode:
            raise BoxError(f"editor exited with status {result.returncode}")
        box = read_box(temporary, expected_name=name)
        _validate_ssh_config(temporary, name)
        if create:
            try:
                os.link(temporary, destination)
            except FileExistsError as error:
                raise BoxError(
                    f"box {name!r} was created by another process"
                ) from error
        else:
            os.replace(temporary, destination)
        return Box(
            name=box.name, hostname=box.hostname, source="managed", path=destination
        )
    except OSError as error:
        raise BoxError(f"could not update {destination}: {error}") from error
    finally:
        temporary.unlink(missing_ok=True)


def _validate_ssh_config(path: Path, name: str) -> None:
    ssh = shutil.which("ssh")
    if ssh is None:
        raise BoxError("ssh is not installed")
    result = subprocess.run(
        [ssh, "-G", "-F", str(path), name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or "invalid SSH configuration"
        raise BoxError(detail)
