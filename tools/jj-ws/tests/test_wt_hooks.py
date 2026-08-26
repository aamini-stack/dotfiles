import subprocess

from jjws.wt.config import Config, Hook
from jjws.wt.hooks import run_hooks


def test_pre_remove_os_error_warns_and_continues(monkeypatch, tmp_path, capsys):
    config = Config(pre_remove=(Hook("pre-remove", "cleanup", "docker compose down"),))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("missing cwd")),
    )

    succeeded = run_hooks(
        config,
        "pre-remove",
        "feat",
        tmp_path / "missing",
        tmp_path,
        continue_on_error=True,
    )

    assert succeeded is False
    assert "warning" in capsys.readouterr().err


def test_run_hooks_cwd_overrides_workspace_path(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    primary.mkdir()
    gone = tmp_path / "workspaces" / "repo" / "feat"
    seen = {}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (
            seen.update(kwargs) or subprocess.CompletedProcess(args, 0)
        ),
    )
    config = Config(post_remove=(Hook("post-remove", "close", "true"),))

    succeeded = run_hooks(config, "post-remove", "feat", gone, primary, cwd=primary)

    assert succeeded is True
    assert seen["cwd"] == primary
