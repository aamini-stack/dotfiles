import subprocess

import pytest
from jjws.wt.copy_ignored import CopyIgnoredError, copy_ignored


def test_copies_ignored_files_and_honors_excludes(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text(".env\nnode_modules/\n.cache/\n")
    (source / ".env").write_text("secret\n")
    (source / "node_modules" / "pkg").mkdir(parents=True)
    (source / "node_modules" / "pkg" / "index.js").write_text("module\n")
    (source / ".cache").mkdir()
    (source / ".cache" / "state").write_text("cache\n")

    count = copy_ignored(source, target, (".cache/",))

    assert count == 2
    assert (target / ".env").read_text() == "secret\n"
    assert (target / "node_modules" / "pkg" / "index.js").is_file()
    assert not (target / ".cache").exists()


def test_replaces_destination_symlink_without_following_it(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text(".env\n")
    (source / ".env").write_text("new\n")
    external = tmp_path / "external"
    external.write_text("safe\n")
    (target / ".env").symlink_to(external)

    copy_ignored(source, target)

    assert external.read_text() == "safe\n"
    assert not (target / ".env").is_symlink()
    assert (target / ".env").read_text() == "new\n"


def test_rejects_symlinked_destination_parent(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    external = tmp_path / "external"
    source.mkdir()
    target.mkdir()
    external.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text("cache/\n")
    (source / "cache").mkdir()
    (source / "cache" / "state").write_text("new\n")
    (target / "cache").symlink_to(external, target_is_directory=True)

    with pytest.raises(CopyIgnoredError, match="symlinked directory"):
        copy_ignored(source, target)
    assert not (external / "state").exists()


def test_replaces_hardlink_without_overwriting_external_file(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text(".env\n")
    (source / ".env").write_text("new\n")
    external = tmp_path / "external"
    external.write_text("safe\n")
    (target / ".env").hardlink_to(external)

    copy_ignored(source, target)

    assert external.read_text() == "safe\n"
    assert (target / ".env").read_text() == "new\n"


def test_excludes_workspace_tree_when_target_is_inside_primary(tmp_path):
    source = tmp_path / "source"
    target = source / ".ws" / "feat"
    source.mkdir()
    target.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text(".env\n.ws/\n")
    (source / ".env").write_text("new\n")
    (target / "old").write_text("do not nest\n")

    copy_ignored(source, target)

    assert (target / ".env").read_text() == "new\n"
    assert not (target / ".ws").exists()
