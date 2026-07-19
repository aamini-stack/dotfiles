import unittest
from unittest.mock import patch

from herdr_ws import close as close_module
from herdr_ws import open as open_module


class LabelForTests(unittest.TestCase):
    def test_repo_and_name(self):
        self.assertEqual(
            open_module.herdr_label_for("dotfiles", "plugin"), "ws-dotfiles-plugin"
        )

    def test_sanitizes_slashes_like_dojjo(self):
        self.assertEqual(
            open_module.herdr_label_for("dotfiles", "feat/login"),
            "ws-dotfiles-feat-login",
        )
        self.assertEqual(
            open_module.herdr_label_for("dotfiles", "feat\\login"),
            "ws-dotfiles-feat-login",
        )


class CloseWorkspaceTests(unittest.TestCase):
    def test_closes_matching_workspace(self):
        calls = []

        def fake_herdr(*args):
            calls.append(args)
            if args[:2] == ("workspace", "list"):
                return {
                    "workspaces": [
                        {"label": "ui", "workspace_id": "w1"},
                        {"label": "ws-dotfiles-plugin", "workspace_id": "w2"},
                    ]
                }
            return {}

        with (
            patch.object(close_module, "herdr", side_effect=fake_herdr),
            patch.object(open_module, "herdr", side_effect=fake_herdr),
            patch.object(close_module.guard, "disarm") as disarm,
            patch.object(close_module.guard, "prune") as prune,
        ):
            self.assertEqual(close_module.close_workspace("dotfiles", "plugin"), 0)

        self.assertEqual(calls, [("workspace", "list"), ("workspace", "close", "w2")])
        disarm.assert_called_once_with("w2")
        prune.assert_called_once_with({"w1"})

    def test_noop_when_workspace_absent(self):
        calls = []

        def fake_herdr(*args):
            calls.append(args)
            return {"workspaces": []}

        with (
            patch.object(close_module, "herdr", side_effect=fake_herdr),
            patch.object(open_module, "herdr", side_effect=fake_herdr),
            patch.object(close_module.guard, "disarm") as disarm,
            patch.object(close_module.guard, "prune") as prune,
        ):
            self.assertEqual(close_module.close_workspace("dotfiles", "ghost"), 0)

        self.assertEqual(calls, [("workspace", "list")])
        disarm.assert_not_called()
        prune.assert_called_once_with(set())


if __name__ == "__main__":
    unittest.main()
