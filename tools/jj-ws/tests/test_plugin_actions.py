import json

from jjws.herdr import actions as actions_module
from jjws.herdr import state
from jjws.lib.jj import JjError


def run_action(monkeypatch, tmp_path, action, cwd=None, jj_ok=True):
    calls = {"herdr": [], "ensure": []}
    cwd = cwd or tmp_path
    env = {
        "HERDR_PLUGIN_CONTEXT_JSON": json.dumps({"cwd": str(cwd)}),
        "HERDR_PLUGIN_STATE_DIR": str(tmp_path / "state"),
    }

    if jj_ok:
        monkeypatch.setattr(actions_module, "primary_root", lambda c: tmp_path)
    else:

        def fail(c):
            raise JjError("jj root failed (1): not a repo")

        monkeypatch.setattr(actions_module, "primary_root", fail)

    monkeypatch.setattr(
        actions_module, "herdr", lambda *a: calls["herdr"].append(a) or {}
    )
    monkeypatch.setattr(
        actions_module, "ensure", lambda e: calls["ensure"].append(e) or 0
    )

    rc = action(env)
    return rc, env, calls


class TestNew:
    def test_writes_context_opens_wizard_pane_and_arms_reporter(
        self, monkeypatch, tmp_path
    ):
        rc, env, calls = run_action(monkeypatch, tmp_path, actions_module.new)

        assert rc == 0
        assert state.read_context(env) == {"cwd": str(tmp_path)}
        assert calls["herdr"] == [
            (
                "plugin",
                "pane",
                "open",
                "--plugin",
                "aamini.jj",
                "--entrypoint",
                "name-wizard",
            )
        ]
        assert calls["ensure"] == [env]

    def test_fails_outside_jj_repo(self, monkeypatch, tmp_path, capsys):
        rc, _env, calls = run_action(
            monkeypatch, tmp_path, actions_module.new, jj_ok=False
        )

        assert rc == 1
        assert calls["herdr"] == []
        assert "not a repo" in capsys.readouterr().err


class TestPick:
    def test_opens_picker_pane(self, monkeypatch, tmp_path):
        rc, _env, calls = run_action(monkeypatch, tmp_path, actions_module.pick)

        assert rc == 0
        assert calls["herdr"] == [
            (
                "plugin",
                "pane",
                "open",
                "--plugin",
                "aamini.jj",
                "--entrypoint",
                "picker",
            )
        ]
