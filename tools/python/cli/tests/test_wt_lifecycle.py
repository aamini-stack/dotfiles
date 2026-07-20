import pytest

from cli.jj import Workspace
from cli.wt import lifecycle
from cli.wt.config import Config
from cli.wt.hooks import HookError
from cli.wt.lifecycle import WtError


def test_create_adds_workspace_then_runs_hooks(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    caller = tmp_path / "workspaces" / "repo" / "parent"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    calls = []
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())
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
        lambda config, phase, name, path, primary: calls.append(
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
        ("add", destination, "feat", caller, "trunk()"),
        ("hooks", "post-create", "feat", destination, primary),
    ]


def test_create_leaves_workspace_when_hook_fails(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    destination = tmp_path / "workspaces" / "repo" / "feat"
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle.config_module, "load", lambda primary, env: Config())

    def fake_add(dest, name, cwd, revision=None):
        destination.mkdir(parents=True)

    monkeypatch.setattr(lifecycle, "add_workspace", fake_add)
    monkeypatch.setattr(
        lifecycle,
        "run_hooks",
        lambda *args, **kwargs: (_ for _ in ()).throw(HookError("install failed")),
    )

    with pytest.raises(HookError, match="install failed"):
        lifecycle.create_workspace(
            primary,
            "feat",
            env={"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")},
        )
    assert destination.is_dir()


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
    assert not target.exists()


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
