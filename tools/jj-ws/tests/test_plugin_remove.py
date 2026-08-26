from pathlib import Path

from jjws.herdr import remove as remove_module
from jjws.lib.jj import JjError, Workspace
from jjws.wt.lifecycle import WtError


def test_remove_delegates_lifecycle_then_closes_herdr(monkeypatch, tmp_path):
    primary = tmp_path / "dotfiles"
    target = tmp_path / "workspaces" / "dotfiles" / "feat"
    calls = []

    monkeypatch.setattr(remove_module, "repo_root", lambda cwd: target)
    monkeypatch.setattr(remove_module, "primary_root", lambda cwd: primary)

    def fake_remove(cwd, name=None, **kwargs):
        calls.append(("remove", cwd, name, kwargs))
        return Workspace("feat", target)

    monkeypatch.setattr(remove_module, "wt_remove_workspace", fake_remove)
    monkeypatch.setattr(
        remove_module,
        "close_workspace",
        lambda name, path=None: calls.append(("close", name, path)) or 0,
    )

    env = {"JJ_WORKSPACE_ROOT": str(tmp_path / "workspaces")}
    rc = remove_module.remove_current(env, assume_yes=True)

    assert rc == 0
    assert calls[0][0:3] == ("remove", target, None)
    assert calls[0][3]["assume_yes"] is True
    assert calls[0][3]["env"] == env
    assert calls[1] == ("close", "feat", target)


def test_remove_does_not_close_when_lifecycle_aborts(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(remove_module, "repo_root", lambda cwd: tmp_path / "feat")
    monkeypatch.setattr(remove_module, "primary_root", lambda cwd: tmp_path / "repo")
    monkeypatch.setattr(
        remove_module,
        "wt_remove_workspace",
        lambda *args, **kwargs: (_ for _ in ()).throw(WtError("aborted")),
    )
    closed = []
    monkeypatch.setattr(
        remove_module,
        "close_workspace",
        lambda *args: closed.append(args) or 0,
    )

    assert remove_module.remove_current({}, input_fn=lambda prompt: "n") == 1
    assert closed == []
    assert "aborted" in capsys.readouterr().err


def test_remove_fails_when_cwd_not_in_jj_repo(monkeypatch, tmp_path, capsys):
    def fail(cwd: Path):
        raise JjError("jj root failed (1): not a repo")

    monkeypatch.setattr(remove_module, "repo_root", fail)

    assert remove_module.remove_current({}, assume_yes=True) == 1
    assert "not a repo" in capsys.readouterr().err
