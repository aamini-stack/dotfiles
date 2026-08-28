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


def test_copies_only_included_files_and_honors_excludes(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text(".env*.local\n.venv/\n")
    (source / ".env.local").write_text("root\n")
    (source / "app").mkdir()
    (source / "app" / ".env.test.local").write_text("nested\n")
    (source / ".venv").mkdir()
    (source / ".venv" / "state").write_text("generated\n")

    count = copy_ignored(
        source,
        target,
        ("app/.env.test.local",),
        (".env*.local",),
    )

    assert count == 1
    assert (target / ".env.local").read_text() == "root\n"
    assert not (target / "app").exists()
    assert not (target / ".venv").exists()


def test_path_include_does_not_cross_directory_boundaries(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text("app/")
    (source / "app").mkdir()
    (source / "app" / ".env.local").write_text("included\n")
    (source / "app" / "private").mkdir()
    (source / "app" / "private" / ".env.local").write_text("excluded\n")

    count = copy_ignored(source, target, includes=("app/*.local",))

    assert count == 1
    assert (target / "app" / ".env.local").read_text() == "included\n"
    assert not (target / "app" / "private").exists()


def test_directory_include_copies_its_contents(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text("secrets/\ncache/\n")
    (source / "secrets" / "nested").mkdir(parents=True)
    (source / "secrets" / "nested" / "config").write_text("included\n")
    (source / "cache").mkdir()
    (source / "cache" / "state").write_text("excluded\n")

    count = copy_ignored(source, target, includes=("secrets/",))

    assert count == 1
    assert (target / "secrets" / "nested" / "config").read_text() == "included\n"
    assert not (target / "cache").exists()


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

    copy_ignored(source, target, force=True)

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

    copy_ignored(source, target, force=True)

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


def test_worktreeinclude_selects_ignored_files_with_comments_and_negation(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text(".env*.local\nsecrets/\ncache/\n")
    (source / ".worktreeinclude").write_text(
        "# local setup\n.env*.local\nsecrets/\n!secrets/private/\n"
    )
    (source / ".env.local").touch()
    (source / "secrets" / "public").mkdir(parents=True)
    (source / "secrets" / "public" / "token").touch()
    (source / "secrets" / "private").mkdir()
    (source / "secrets" / "private" / "token").touch()
    (source / "cache").mkdir()
    (source / "cache" / "state").touch()

    count = copy_ignored(source, target)

    assert count == 2
    assert (target / ".env.local").is_file()
    assert (target / "secrets" / "public" / "token").is_file()
    assert not (target / "secrets" / "private").exists()
    assert not (target / "cache").exists()


def test_worktreeinclude_and_config_include_intersect_and_excludes_win(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text(".env*.local\n")
    (source / ".worktreeinclude").write_text(".env*.local\n")
    (source / ".env.local").touch()
    (source / ".env.test.local").touch()

    count = copy_ignored(
        source,
        target,
        excludes=(".env.test.local",),
        includes=(".env.local", ".env.test.local"),
    )

    assert count == 1
    assert (target / ".env.local").is_file()
    assert not (target / ".env.test.local").exists()


def test_skips_existing_destination_unless_forced(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text(".env.local\n")
    (source / ".env.local").write_text("source\n")
    (target / ".env.local").write_text("workspace\n")

    assert copy_ignored(source, target) == 0
    assert (target / ".env.local").read_text() == "workspace\n"
    assert copy_ignored(source, target, force=True) == 1
    assert (target / ".env.local").read_text() == "source\n"


def test_gitignore_wildmatch_for_include_and_exclude(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / ".gitignore").write_text("**/*.local\ncache/\n")
    (source / ".worktreeinclude").write_text(
        "# all local files\n**/*.local\n!private/**\n/cache/\n"
    )
    (source / "app").mkdir()
    (source / "app" / "a.local").touch()
    (source / "private").mkdir()
    (source / "private" / "b.local").touch()
    (source / "cache" / "nested").mkdir(parents=True)
    (source / "cache" / "nested" / "state").touch()

    count = copy_ignored(source, target, excludes=("**/state",))

    assert count == 1
    assert (target / "app" / "a.local").is_file()
    assert not (target / "private").exists()
    assert not (target / "cache").exists()


def test_native_jj_copies_gitignored_untracked_file_without_git(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    subprocess.run(
        ["jj", "git", "init", "--no-colocate", str(source)],
        check=True,
        capture_output=True,
    )
    target.mkdir()
    (source / ".gitignore").write_text(".env.local\n")
    (source / ".env.local").touch()

    count = copy_ignored(source, target)

    assert count == 1
    assert (target / ".env.local").is_file()


def test_native_jj_applies_nested_gitignore_relative_to_its_directory(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    subprocess.run(
        ["jj", "git", "init", "--no-colocate", str(source)],
        check=True,
        capture_output=True,
    )
    target.mkdir()
    nested = source / "services" / "api"
    nested.mkdir(parents=True)
    (nested / ".gitignore").write_text("cache/\n*.local\n")
    (nested / "cache").mkdir()
    (nested / "cache" / "state").touch()
    (nested / ".env.local").touch()
    outside = source / "cache"
    outside.mkdir()
    (outside / "state").touch()

    count = copy_ignored(source, target)

    assert count == 2
    assert (target / "services" / "api" / "cache" / "state").is_file()
    assert (target / "services" / "api" / ".env.local").is_file()
    assert not (target / "cache").exists()


def test_native_jj_nested_negation_overrides_parent_ignore(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    subprocess.run(
        ["jj", "git", "init", "--no-colocate", str(source)],
        check=True,
        capture_output=True,
    )
    target.mkdir()
    (source / ".gitignore").write_text("*.local\n")
    nested = source / "services"
    nested.mkdir()
    (nested / ".gitignore").write_text("!keep.local\n")
    (nested / "keep.local").touch()
    (nested / "drop.local").touch()

    count = copy_ignored(source, target)

    assert count == 1
    assert not (target / "services" / "keep.local").exists()
    assert (target / "services" / "drop.local").is_file()
