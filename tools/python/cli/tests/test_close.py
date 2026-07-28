import unittest
from pathlib import Path
from unittest.mock import patch

from cli import close as close_module
from cli import herdr as herdr_module
from cli import open as open_module


class LabelForTests(unittest.TestCase):
    def test_repo_and_name(self):
        self.assertEqual(
            open_module.herdr_label_for("dotfiles", "plugin"), "ws-dotfiles-plugin"
        )

    def test_sanitizes_slashes(self):
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
            patch.object(herdr_module, "herdr", side_effect=fake_herdr),
            patch.object(close_module.guard, "disarm") as disarm,
            patch.object(close_module.guard, "prune") as prune,
        ):
            self.assertEqual(close_module.close_workspace("dotfiles", "plugin"), 0)

        self.assertEqual(calls, [("workspace", "list"), ("workspace", "close", "w2")])
        disarm.assert_called_once_with("w2")
        prune.assert_called_once_with({"w1"})

    def test_closes_by_worktree_path_when_label_differs(self):
        calls = []
        path = Path("/home/u/.herdr/workspaces/dotfiles/feat")

        def fake_herdr(*args):
            calls.append(args)
            if args[:2] == ("workspace", "list"):
                return {
                    "workspaces": [
                        {
                            "label": "feat",
                            "workspace_id": "w3",
                            "worktree": {"checkout_path": str(path)},
                        },
                    ]
                }
            return {}

        with (
            patch.object(herdr_module, "herdr", side_effect=fake_herdr),
            patch.object(close_module.guard, "disarm") as disarm,
            patch.object(close_module.guard, "prune"),
        ):
            self.assertEqual(close_module.close_workspace("dotfiles", "feat", path), 0)

        self.assertEqual(calls, [("workspace", "list"), ("workspace", "close", "w3")])
        disarm.assert_called_once_with("w3")

    def test_noop_when_workspace_absent(self):
        calls = []

        def fake_herdr(*args):
            calls.append(args)
            return {"workspaces": []}

        with (
            patch.object(herdr_module, "herdr", side_effect=fake_herdr),
            patch.object(close_module.guard, "disarm") as disarm,
            patch.object(close_module.guard, "prune") as prune,
        ):
            self.assertEqual(close_module.close_workspace("dotfiles", "ghost"), 0)

        self.assertEqual(calls, [("workspace", "list")])
        disarm.assert_not_called()
        prune.assert_called_once_with(set())


if __name__ == "__main__":
    unittest.main()
