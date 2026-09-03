import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from jjws.herdr import adopt as adopt_module
from jjws.lib.jj import JjError, Workspace

PRIMARY = Path("/repo")
PATH = Path("/wt/feat")
EVENT = {
    "workspace": {"workspace_id": "w1"},
    "worktree": {"path": str(PATH), "branch": "feat"},
}


@pytest.fixture()
def base():
    with (
        patch.object(adopt_module, "_jj_primary", return_value=PRIMARY),
        patch.object(adopt_module, "workspaces", return_value=[]),
        patch.object(adopt_module, "_git") as git,
        patch.object(adopt_module, "jj") as jj,
        patch.object(adopt_module, "herdr") as herdr,
    ):
        git.return_value = "abc123"
        herdr.return_value = {"panes": [{"pane_id": "w1:p1", "workspace_id": "w1"}]}
        yield git, jj, herdr


class TestRun:
    def test_unwraps_data_envelope(self, monkeypatch):
        seen = []
        monkeypatch.setenv(
            "HERDR_PLUGIN_EVENT_JSON",
            '{"event": "worktree_created", "data": {"worktree": {"path": "/wt/x"}}}',
        )
        with patch.object(adopt_module, "_jj_primary", return_value=None):
            rc = adopt_module._run(argparse.Namespace(), seen.append)
        assert rc == 0
        assert seen == [{"worktree": {"path": "/wt/x"}}]

    def test_tolerates_missing_event(self, monkeypatch):
        monkeypatch.delenv("HERDR_PLUGIN_EVENT_JSON", raising=False)
        with patch.object(adopt_module, "_jj_primary", return_value=None):
            rc = adopt_module._run(argparse.Namespace(), lambda event: None)
        assert rc == 0


class TestAdopt:
    def test_skips_non_jj_repo(self):
        with (
            patch.object(adopt_module, "_jj_primary", return_value=None),
            patch.object(adopt_module, "_git") as git,
        ):
            adopt_module.adopt(EVENT)
        git.assert_not_called()

    def test_aborts_on_name_collision(self, base):
        git, jj, _ = base
        with (
            patch.object(
                adopt_module,
                "workspaces",
                return_value=[Workspace(name="feat", root=PATH)],
            ),
            pytest.raises(adopt_module.AdoptError),
        ):
            adopt_module.adopt(EVENT)
        assert not any(
            call.args[1:3] == ("worktree", "remove") for call in git.call_args_list
        )
        jj.assert_not_called()

    def test_recreates_checkout_as_jj_workspace(self, base):
        git, jj, herdr = base
        adopt_module.adopt(EVENT)

        assert git.call_args_list[0].args == (PATH, "rev-parse", "HEAD")
        assert git.call_args_list[1].args == (
            PRIMARY,
            "worktree",
            "remove",
            "--force",
            str(PATH),
        )
        jj.assert_called_once_with(
            "workspace",
            "add",
            str(PATH),
            "--name",
            "feat",
            "--revision",
            "abc123",
            cwd=PRIMARY,
        )
        herdr.assert_any_call("pane", "send-text", "w1:p1", f"cd {PATH} && clear")
        herdr.assert_any_call("pane", "send-keys", "w1:p1", "enter")

    def test_rolls_back_git_worktree_on_jj_failure(self, base):
        _git, jj, _ = base
        jj.side_effect = JjError("boom")
        with (
            patch.object(adopt_module, "subprocess") as subprocess,
            pytest.raises(JjError),
        ):
            adopt_module.adopt(EVENT)
        subprocess.run.assert_called_once_with(
            ["git", "-C", str(PRIMARY), "worktree", "add", str(PATH), "feat"],
            capture_output=True,
            check=False,
        )


class TestForget:
    def test_forgets_matching_jj_workspace(self, tmp_path):
        (tmp_path / ".jj").mkdir()
        event = {
            "workspace": {
                "workspace_id": "w1",
                "worktree": {"repo_root": str(tmp_path)},
            },
            "worktree": {"path": "/wt/feat"},
        }
        with patch.object(adopt_module, "jj") as jj:
            adopt_module.forget(event)
        jj.assert_called_once_with("workspace", "forget", "feat", cwd=tmp_path)

    def test_skips_without_repo_info(self):
        with patch.object(adopt_module, "jj") as jj:
            adopt_module.forget({"worktree": {"path": "/wt/feat"}})
        jj.assert_not_called()

    def test_tolerates_missing_jj_workspace(self, tmp_path):
        (tmp_path / ".jj").mkdir()
        event = {"worktree": {"path": "/wt/feat", "repo_root": str(tmp_path)}}
        with patch.object(adopt_module, "jj", side_effect=JjError("no such workspace")):
            adopt_module.forget(event)
