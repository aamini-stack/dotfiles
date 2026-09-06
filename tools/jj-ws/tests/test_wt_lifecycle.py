import errno
import subprocess

import pytest

from jjws.lib.jj import JjError, Workspace
from jjws.wt import lifecycle
from jjws.wt.config import Config
from jjws.wt.hooks import HookError
from jjws.wt.lifecycle import WtError


def test_create_runs_worktrunk_hooks_in_order(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    caller = tmp_path / "workspaces" / "repo" / "parent"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [])
    monkeypatch.setattr(
        lifecycle,
        "add_workspace",
        lambda dest, name, cwd, revision=None: calls.append(
            ("add", dest, name, cwd, revision)
        ),
    )
    monkeypatch.setattr(
        lifecycle,
        "run_hooks",
        lambda config, phase, name, path, primary, **kwargs: calls.append(
            ("hooks", phase, name, path, primary)
        ),
    )

    created = lifecycle.create_workspace(
        caller,
        "feat",
        revision="trunk()",
        env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
    )

    assert created == Workspace("feat", destination)
    assert calls == [
        ("hooks", "pre-switch", "feat", destination, primary),
        ("add", destination, "feat", caller, "trunk()"),
        ("hooks", "pre-start", "feat", destination, primary),
        ("hooks", "post-start", "feat", destination, primary),
        ("hooks", "post-switch", "feat", destination, primary),
    ]


def test_create_registers_git_worktree_when_primary_is_colocated(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    primary.mkdir()
    (primary / ".git").mkdir()
    caller = tmp_path / "workspaces" / "repo" / "parent"
    registered = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [])
    monkeypatch.setattr(lifecycle, "add_workspace", lambda *args, **kwargs: None)
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        lifecycle,
        "_register_git_worktree",
        lambda primary, target: registered.append(target),
    )

    created = lifecycle.create_workspace(
        caller,
        "feat",
        env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
    )

    assert registered == [created]


def test_create_skips_registration_when_destination_already_colocated(
    monkeypatch, tmp_path
):
    primary = tmp_path / "repo"
    primary.mkdir()
    (primary / ".git").mkdir()
    caller = tmp_path / "workspaces" / "repo" / "parent"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    registered = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [])
    monkeypatch.setattr(
        lifecycle,
        "add_workspace",
        lambda *args, **kwargs: (
            destination.mkdir(parents=True),
            (destination / ".git").write_text("gitdir: x\n"),
        ),
    )
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        lifecycle,
        "_register_git_worktree",
        lambda primary, target: registered.append(target),
    )

    lifecycle.create_workspace(
        caller,
        "feat",
        env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
    )

    assert registered == []


def test_create_survives_git_worktree_registration_failure(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    primary.mkdir()
    (primary / ".git").mkdir()
    caller = tmp_path / "workspaces" / "repo" / "parent"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [])
    monkeypatch.setattr(lifecycle, "add_workspace", lambda *args, **kwargs: None)
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: None)

    def explode(primary, target):
        raise WtError("no git store")

    monkeypatch.setattr(lifecycle, "_register_git_worktree", explode)

    created = lifecycle.create_workspace(
        caller,
        "feat",
        env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
    )

    assert created == Workspace("feat", destination)


def test_create_skips_hooks_when_disabled(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    caller = tmp_path / "workspaces" / "repo" / "parent"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [])
    monkeypatch.setattr(
        lifecycle,
        "add_workspace",
        lambda dest, name, cwd, revision=None: calls.append(
            ("add", dest, name, cwd, revision)
        ),
    )
    monkeypatch.setattr(
        lifecycle,
        "run_hooks",
        lambda *args, **kwargs: calls.append(("hooks", args)),
    )

    created = lifecycle.create_workspace(
        caller,
        "feat",
        env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
        run_post_create=False,
    )

    assert created == Workspace("feat", destination)
    assert calls[0][0] == "hooks"
    assert calls[1] == ("add", destination, "feat", caller, "@")
    assert len(calls) == 2


def test_run_configured_phase_runs_all_phase_hooks(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    current = tmp_path / "workspaces" / "repo" / "feat"
    calls = []
    monkeypatch.setattr(
        lifecycle, "current_workspace", lambda cwd: Workspace("feat", current)
    )
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(
        lifecycle,
        "run_hooks",
        lambda config, phase, name, path, primary: calls.append(
            (phase, name, path, primary)
        ),
    )

    lifecycle.run_configured_phase(current, "post-create")

    assert calls == [("post-create", "feat", current, primary)]


def test_run_configured_phase_rejects_unknown_phase(monkeypatch, tmp_path):
    with pytest.raises(WtError, match="unknown hook phase"):
        lifecycle.run_configured_phase(tmp_path, "post-createe")


def test_create_leaves_workspace_when_hook_fails(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())

    def fake_add(dest, name, cwd, revision=None):
        destination.mkdir(parents=True)

    monkeypatch.setattr(lifecycle, "add_workspace", fake_add)

    def fail_post_start(config, phase, *args, **kwargs):
        if phase == "post-start":
            raise HookError("install failed")

    monkeypatch.setattr(lifecycle, "run_hooks", fail_post_start)

    with pytest.raises(lifecycle.CreateHookError, match="install failed") as caught:
        lifecycle.create_workspace(
            primary,
            "feat",
            env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
        )
    assert caught.value.workspace == Workspace("feat", destination)
    assert destination.is_dir()


def test_create_runs_post_switch_when_post_start_fails(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "add_workspace", lambda *args, **kwargs: None)

    def fail_post_start(config, phase, *args, **kwargs):
        calls.append(phase)
        if phase == "post-start":
            raise HookError("start failed")

    monkeypatch.setattr(lifecycle, "run_hooks", fail_post_start)

    with pytest.raises(lifecycle.CreateHookError, match="start failed"):
        lifecycle.create_workspace(
            primary,
            "feat",
            env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
        )

    assert calls == ["pre-switch", "pre-start", "post-start", "post-switch"]


def test_create_refuses_leftover_destination_without_force(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    (destination / ".vite").mkdir(parents=True)
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())

    with pytest.raises(WtError, match="already exists and is not empty"):
        lifecycle.create_workspace(
            primary,
            "feat",
            env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
        )
    assert (destination / ".vite").is_dir()


def test_create_force_moves_leftover_aside(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    caller = tmp_path / "parent"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    (destination / ".vite").mkdir(parents=True)
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [])
    monkeypatch.setattr(
        lifecycle,
        "add_workspace",
        lambda dest, name, cwd, revision=None: calls.append((dest, name)),
    )
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: True)

    lifecycle.create_workspace(
        caller,
        "feat",
        env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
        force=True,
    )

    assert calls == [(destination, "feat")]
    assert not destination.exists()


def test_create_force_restores_destination_when_add_fails(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    destination.mkdir(parents=True)
    original = destination / "important"
    original.write_text("preserve\n")
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: True)
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [])
    monkeypatch.setattr(
        lifecycle,
        "add_workspace",
        lambda *args, **kwargs: (_ for _ in ()).throw(JjError("add failed")),
    )

    with pytest.raises(JjError, match="add failed"):
        lifecycle.create_workspace(
            primary,
            "feat",
            env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
            force=True,
        )

    assert original.read_text() == "preserve\n"
    assert list(destination.parent.glob(".feat.trash-*")) == []


def test_create_force_preserves_partial_workspace_when_add_fails(
    monkeypatch, tmp_path, capsys
):
    primary = tmp_path / "repo"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    destination.mkdir(parents=True)
    (destination / "important").write_text("preserve\n")
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: True)
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [])

    def partial_add(*args, **kwargs):
        destination.mkdir()
        (destination / "partial").write_text("diagnose\n")
        raise JjError("add failed")

    monkeypatch.setattr(lifecycle, "add_workspace", partial_add)

    with pytest.raises(JjError, match="add failed"):
        lifecycle.create_workspace(
            primary,
            "feat",
            env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
            force=True,
        )

    assert (destination / "important").read_text() == "preserve\n"
    leftovers = list(destination.parent.glob(".feat.trash-*"))
    assert len(leftovers) == 1
    assert (leftovers[0] / "partial").read_text() == "diagnose\n"
    assert str(leftovers[0]) in capsys.readouterr().err


def test_create_force_forgets_registration_created_before_add_failure(
    monkeypatch, tmp_path
):
    primary = tmp_path / "repo"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    destination.mkdir(parents=True)
    (destination / "important").write_text("preserve\n")
    registrations = []
    forgotten = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: True)
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: list(registrations))

    def fail_after_registration(*args, **kwargs):
        registrations.append(Workspace("feat", destination))
        destination.mkdir()
        (destination / ".jj").mkdir()
        raise OSError("pointer rewrite failed")

    def forget(name, cwd):
        forgotten.append((name, cwd))
        registrations.clear()

    monkeypatch.setattr(lifecycle, "add_workspace", fail_after_registration)
    monkeypatch.setattr(lifecycle, "forget_workspace", forget)

    with pytest.raises(OSError, match="pointer rewrite failed"):
        lifecycle.create_workspace(
            primary,
            "feat",
            env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
            force=True,
        )

    assert forgotten == [("feat", primary)]
    assert registrations == []
    assert (destination / "important").read_text() == "preserve\n"


def test_create_force_does_not_forget_preexisting_registration(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    destination.mkdir(parents=True)
    (destination / "important").touch()
    existing = Workspace("feat", destination)
    forgotten = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: True)
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [existing])
    monkeypatch.setattr(
        lifecycle,
        "add_workspace",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("failed")),
    )
    monkeypatch.setattr(
        lifecycle,
        "forget_workspace",
        lambda name, cwd: forgotten.append((name, cwd)),
    )

    with pytest.raises(OSError, match="failed"):
        lifecycle.create_workspace(
            primary,
            "feat",
            env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
            force=True,
        )

    assert forgotten == []
    assert (destination / "important").is_file()


def test_create_pre_switch_receives_computed_destination(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    seen = {}
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "add_workspace", lambda *args, **kwargs: None)

    def record(config, phase, name, path, primary, **kwargs):
        if phase == "pre-switch":
            seen["path"] = path

    monkeypatch.setattr(lifecycle, "run_hooks", record)

    lifecycle.create_workspace(
        primary,
        "feature/auth",
        env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
    )

    assert seen["path"].parent == tmp_path / "workspaces" / "repo"
    assert seen["path"].name.startswith("feature-auth-")


def test_create_explicitly_bases_default_on_caller_at(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    caller = tmp_path / "parent"
    seen = {}
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(
        lifecycle,
        "add_workspace",
        lambda dest, name, cwd, revision=None: seen.update(cwd=cwd, revision=revision),
    )
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: True)

    lifecycle.create_workspace(
        caller,
        "feat",
        env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
    )

    assert seen == {"cwd": caller, "revision": "@"}


def test_switch_existing_runs_switch_hooks_only(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    target = Workspace("feat", tmp_path / "workspaces" / "feat")
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "workspace", lambda cwd, name: target)
    monkeypatch.setattr(
        lifecycle,
        "run_hooks",
        lambda config, phase, name, path, primary, **kwargs: calls.append(phase),
    )

    assert lifecycle.switch_to_workspace(tmp_path, "feat") == target
    assert calls == ["pre-switch", "post-switch"]


@pytest.mark.parametrize(
    "name",
    ["", ".", "..", "a/../b", "/absolute", "a//b", "$(touch owned)", "a;true"],
)
def test_create_rejects_unsafe_names_before_repo_or_hooks(monkeypatch, tmp_path, name):
    calls = []
    monkeypatch.setattr(
        lifecycle, "primary_root", lambda cwd: calls.append("repo") or tmp_path
    )
    monkeypatch.setattr(
        lifecycle, "run_hooks", lambda *args, **kwargs: calls.append("hook")
    )

    with pytest.raises(WtError, match="workspace name"):
        lifecycle.create_workspace(tmp_path, name, force=True)

    assert calls == []


def test_create_supports_safe_slash_name_and_sanitizes_destination(
    monkeypatch, tmp_path
):
    primary = tmp_path / "repo"
    seen = {}
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        lifecycle,
        "add_workspace",
        lambda destination, name, **kwargs: seen.update(
            destination=destination, name=name
        ),
    )

    lifecycle.create_workspace(
        primary,
        "feature/auth.v2",
        env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
    )

    assert seen["name"] == "feature/auth.v2"
    assert seen["destination"].parent == tmp_path / "workspaces" / "repo"
    assert seen["destination"].name.startswith("feature-auth.v2-")


def test_slash_and_hyphen_names_have_distinct_default_destinations(tmp_path):
    primary = tmp_path / "repo"
    config = Config()
    env = {"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")}

    slash = lifecycle.workspace_destination(primary, "feature/auth", config, env)
    hyphen = lifecycle.workspace_destination(primary, "feature-auth", config, env)

    assert slash != hyphen
    assert slash.name.startswith("feature-auth-")
    assert hyphen.name == "feature-auth"


def test_force_refuses_destination_owned_by_another_workspace(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    destination = tmp_path / "workspaces" / "repo" / "feature-auth"
    destination.mkdir(parents=True)
    (destination / "important").touch()
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(
        lifecycle,
        "workspaces",
        lambda cwd: [Workspace("feature/auth", destination)],
    )
    monkeypatch.setattr(
        lifecycle, "run_hooks", lambda *args, **kwargs: calls.append("hook")
    )
    monkeypatch.setattr(
        lifecycle, "add_workspace", lambda *args, **kwargs: calls.append("add")
    )

    with pytest.raises(WtError, match="belongs to jj workspace 'feature/auth'"):
        lifecycle.create_workspace(
            primary,
            "feature-auth",
            env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
            force=True,
        )

    assert calls == []
    assert (destination / "important").is_file()


def test_hostile_name_executes_nothing_on_production_path(tmp_path):
    repo = tmp_path / "repo"
    subprocess.run(
        ["jj", "git", "init", "--no-colocate", str(repo)],
        check=True,
        capture_output=True,
    )
    config_dir = repo / ".config"
    config_dir.mkdir()
    marker = tmp_path / "hook-ran"
    (config_dir / "wt.toml").write_text(f'[pre-switch]\nmarker = "touch {marker}"\n')
    hostile_marker = tmp_path / "hostile-ran"

    with pytest.raises(WtError, match="workspace name"):
        lifecycle.create_workspace(
            repo,
            f"safe;touch {hostile_marker}",
            env={"XDG_CONFIG_HOME": str(tmp_path / "xdg")},
        )

    assert not marker.exists()
    assert not hostile_marker.exists()


def test_existing_typo_resolves_before_pre_switch(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(
        lifecycle,
        "workspace",
        lambda cwd, name: (_ for _ in ()).throw(JjError("not found")),
    )
    monkeypatch.setattr(
        lifecycle, "run_hooks", lambda *args, **kwargs: calls.append("hook")
    )

    with pytest.raises(JjError, match="not found"):
        lifecycle.switch_to_workspace(tmp_path, "typo")

    assert calls == []


def test_remove_confirms_runs_hooks_forgets_and_deletes(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    primary.mkdir()
    target = tmp_path / "workspaces" / "repo" / "feat"
    target.mkdir(parents=True)
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(
        lifecycle, "workspace", lambda cwd, name: Workspace(name, target)
    )
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(
        lifecycle,
        "run_hooks",
        lambda *args, **kwargs: calls.append(("hooks", args[1], kwargs)) or True,
    )
    monkeypatch.setattr(
        lifecycle,
        "forget_workspace",
        lambda name, cwd: calls.append(("forget", name, cwd)),
    )

    removed = lifecycle.remove_workspace(primary, "feat", input_fn=lambda prompt: "yes")

    assert removed == Workspace("feat", target)
    assert calls[0][0:2] == ("hooks", "pre-remove")
    assert calls[0][2]["continue_on_error"] is True
    assert calls[1] == ("forget", "feat", primary)
    assert calls[2][0:2] == ("hooks", "post-remove")
    assert calls[2][2]["continue_on_error"] is True
    assert calls[2][2]["cwd"] == primary
    assert not target.exists()


def test_remove_leaves_workspace_registered_when_move_aside_fails(
    monkeypatch, tmp_path
):
    primary = tmp_path / "repo"
    primary.mkdir()
    target = tmp_path / "workspaces" / "repo" / "feat"
    target.mkdir(parents=True)
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(
        lifecycle, "workspace", lambda cwd, name: Workspace(name, target)
    )
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        lifecycle,
        "forget_workspace",
        lambda name, cwd: calls.append((name, cwd)),
    )

    def failing_rename(self, other):
        raise OSError(errno.EACCES, "Permission denied", str(self))

    monkeypatch.setattr(lifecycle.Path, "rename", failing_rename)

    with pytest.raises(WtError, match="workspace remains registered"):
        lifecycle.remove_workspace(primary, "feat", assume_yes=True)

    assert target.is_dir()
    assert calls == []


def test_remove_moves_aside_and_forgets_even_when_files_remain(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    primary.mkdir()
    target = tmp_path / "workspaces" / "repo" / "feat"
    target.mkdir(parents=True)
    (target / ".vite").mkdir()
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(
        lifecycle, "workspace", lambda cwd, name: Workspace(name, target)
    )
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
    monkeypatch.setattr(lifecycle, "run_hooks", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        lifecycle,
        "forget_workspace",
        lambda name, cwd: calls.append((name, cwd)),
    )

    def failing_rmtree(path, ignore_errors=False):
        assert ignore_errors

    monkeypatch.setattr(lifecycle.shutil, "rmtree", failing_rmtree)

    removed = lifecycle.remove_workspace(primary, "feat", assume_yes=True)

    assert removed == Workspace("feat", target)
    assert calls == [("feat", primary)]
    assert not target.exists()
    leftovers = list(target.parent.glob(".feat.trash-*"))
    assert len(leftovers) == 1
    assert (leftovers[0] / ".vite").is_dir()


def test_remove_refuses_primary_and_decline(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    primary.mkdir()
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(
        lifecycle, "workspace", lambda cwd, name: Workspace(name, primary)
    )
    with pytest.raises(WtError, match="primary"):
        lifecycle.remove_workspace(primary, "default", assume_yes=True)

    target = tmp_path / "feat"
    target.mkdir()
    monkeypatch.setattr(
        lifecycle, "workspace", lambda cwd, name: Workspace(name, target)
    )
    with pytest.raises(WtError, match="aborted"):
        lifecycle.remove_workspace(primary, "feat", input_fn=lambda prompt: "n")
    assert target.is_dir()
