import subprocess

from cli.wt.config import Config, Hook
from cli.wt.hooks import run_hooks


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
