import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from cli import open as open_module
from cli import herdr as herdr_module
from cli.herdr import HerdrError


def completed(stdout: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


class LabelTests(unittest.TestCase):
    def test_label_uses_workspace_dir(self):
        path = Path("/home/u/.herdr/workspaces/dotfiles/plugin")
        self.assertEqual(open_module.herdr_label(path), "plugin")


class FindWorkspaceTests(unittest.TestCase):
    def test_matches_by_label(self):
        payload = {
            "workspaces": [
                {"label": "ui", "workspace_id": "w1"},
                {"label": "plugin", "workspace_id": "w2"},
            ]
        }
        with patch.object(herdr_module, "herdr", return_value=payload):
            found = herdr_module.find_workspace("plugin")
        self.assertEqual(found["workspace_id"], "w2")

    def test_returns_none_without_match(self):
        with patch.object(herdr_module, "herdr", return_value={"workspaces": []}):
            self.assertIsNone(herdr_module.find_workspace("nope"))


class BootstrapDetectionTests(unittest.TestCase):
    def test_detects_plain_and_monorepo_task_names(self):
        tasks = json.dumps([{"name": "bootstrap"}, {"name": "//:check"}])
        with patch.object(subprocess, "run", return_value=completed(tasks)):
            self.assertTrue(open_module.has_bootstrap_task(Path("/tmp")))

        tasks = json.dumps([{"name": "//tools/x:bootstrap"}])
        with patch.object(subprocess, "run", return_value=completed(tasks)):
            self.assertTrue(open_module.has_bootstrap_task(Path("/tmp")))

    def test_absent_or_broken_mise_means_no_task(self):
        with patch.object(subprocess, "run", return_value=completed("[]")):
            self.assertFalse(open_module.has_bootstrap_task(Path("/tmp")))
        with patch.object(subprocess, "run", return_value=completed("", 1)):
            self.assertFalse(open_module.has_bootstrap_task(Path("/tmp")))
        with patch.object(subprocess, "run", side_effect=OSError):
            self.assertFalse(open_module.has_bootstrap_task(Path("/tmp")))


class OpenWorkspaceTests(unittest.TestCase):
    def test_uses_explicit_workspace_name_for_custom_path(self):
        path = Path("/workspaces/feat/checkout")
        with (
            patch.object(
                open_module,
                "ensure_open",
                return_value=({"workspace": {"workspace_id": "w2"}}, False, []),
            ) as ensure_open,
            patch.object(open_module, "focus_workspace"),
            patch.object(open_module.guard, "arm"),
        ):
            self.assertEqual(
                open_module.open_workspace(
                    path, Path("/src/dotfiles"), workspace_name="feat"
                ),
                0,
            )
        ensure_open.assert_called_once_with(
            "feat", path, project_path=Path("/src/dotfiles")
        )

    def test_focuses_existing_without_layout(self):
        calls = []

        def fake_herdr(*args):
            calls.append(args)
            if args[:2] == ("workspace", "list"):
                return {"workspaces": [{"label": "plugin", "workspace_id": "w2"}]}
            return {}

        path = Path("/home/u/.herdr/workspaces/dotfiles/plugin")
        with (
            patch.object(open_module, "herdr", side_effect=fake_herdr),
            patch.object(herdr_module, "herdr", side_effect=fake_herdr),
            patch.object(open_module.guard, "arm") as arm,
        ):
            self.assertEqual(open_module.open_workspace(path), 0)

        self.assertEqual(calls, [("workspace", "list"), ("workspace", "focus", "w2")])
        arm.assert_called_once_with("w2", path, {"w2"})

    def test_creates_layout_and_runs_agent(self):
        calls = []

        def fake_herdr(*args):
            calls.append(args)
            if args[:2] == ("workspace", "list"):
                return {"workspaces": []}
            if args[:2] == ("workspace", "create"):
                return {
                    "root_pane": {"pane_id": "p1"},
                    "workspace": {"workspace_id": "w9"},
                }
            if args[:2] == ("pane", "split"):
                return {"pane": {"pane_id": "p2"}}
            return {}

        path = Path("/home/u/.herdr/workspaces/dotfiles/plugin")
        with (
            patch.object(open_module, "herdr", side_effect=fake_herdr),
            patch.object(herdr_module, "herdr", side_effect=fake_herdr),
            patch.object(open_module, "has_bootstrap_task", return_value=True),
            patch.object(open_module.guard, "arm") as arm,
        ):
            self.assertEqual(open_module.open_workspace(path), 0)

        self.assertEqual(
            calls,
            [
                ("workspace", "list"),
                (
                    "workspace",
                    "create",
                    "--cwd",
                    str(path),
                    "--label",
                    "plugin",
                    "--no-focus",
                ),
                ("pane", "split", "p1", "--direction", "right", "--no-focus"),
                ("pane", "run", "p1", "mise run bootstrap"),
                ("pane", "run", "p2", "opencode"),
                ("workspace", "focus", "w9"),
            ],
        )
        arm.assert_called_once_with("w9", path, {"w9"})

    def test_skips_bootstrap_when_task_absent(self):
        calls = []

        def fake_herdr(*args):
            calls.append(args)
            if args[:2] == ("workspace", "list"):
                return {"workspaces": []}
            if args[:2] == ("workspace", "create"):
                return {
                    "root_pane": {"pane_id": "p1"},
                    "workspace": {"workspace_id": "w9"},
                }
            if args[:2] == ("pane", "split"):
                return {"pane": {"pane_id": "p2"}}
            return {}

        path = Path("/home/u/.herdr/workspaces/dotfiles/plugin")
        with (
            patch.object(open_module, "herdr", side_effect=fake_herdr),
            patch.object(herdr_module, "herdr", side_effect=fake_herdr),
            patch.object(open_module, "has_bootstrap_task", return_value=False),
            patch.object(open_module.guard, "arm"),
        ):
            self.assertEqual(open_module.open_workspace(path), 0)

        run_calls = [call for call in calls if call[:2] == ("pane", "run")]
        self.assertEqual(run_calls, [("pane", "run", "p2", "opencode")])

    def test_opens_via_worktree_open_when_project_path_given(self):
        calls = []

        def fake_herdr(*args):
            calls.append(args)
            if args[:2] == ("workspace", "list"):
                return {"workspaces": []}
            if args[:2] == ("worktree", "open"):
                return {
                    "already_open": False,
                    "root_pane": {"pane_id": "p1"},
                    "workspace": {"workspace_id": "w9"},
                }
            if args[:2] == ("pane", "split"):
                return {"pane": {"pane_id": "p2"}}
            return {}

        path = Path("/home/u/.herdr/workspaces/dotfiles/plugin")
        primary = Path("/home/u/dotfiles")
        with (
            patch.object(open_module, "herdr", side_effect=fake_herdr),
            patch.object(herdr_module, "herdr", side_effect=fake_herdr),
            patch.object(open_module, "has_bootstrap_task", return_value=False),
            patch.object(open_module.guard, "arm"),
        ):
            self.assertEqual(open_module.open_workspace(path, primary), 0)

        self.assertEqual(
            calls[:2],
            [
                ("workspace", "list"),
                (
                    "worktree",
                    "open",
                    "--cwd",
                    str(primary),
                    "--path",
                    str(path),
                    "--label",
                    "plugin",
                    "--no-focus",
                ),
            ],
        )
        self.assertNotIn(("workspace", "create"), [call[:2] for call in calls])
        self.assertEqual(calls[-1], ("workspace", "focus", "w9"))

    def test_falls_back_to_create_when_worktree_open_fails(self):
        calls = []

        def fake_herdr(*args):
            calls.append(args)
            if args[:2] == ("workspace", "list"):
                return {"workspaces": []}
            if args[:2] == ("worktree", "open"):
                raise herdr_module.HerdrError("not a worktree")
            if args[:2] == ("workspace", "create"):
                return {
                    "root_pane": {"pane_id": "p1"},
                    "workspace": {"workspace_id": "w9"},
                }
            if args[:2] == ("pane", "split"):
                return {"pane": {"pane_id": "p2"}}
            return {}

        path = Path("/home/u/.herdr/workspaces/dotfiles/plugin")
        primary = Path("/home/u/dotfiles")
        with (
            patch.object(open_module, "herdr", side_effect=fake_herdr),
            patch.object(herdr_module, "herdr", side_effect=fake_herdr),
            patch.object(open_module, "has_bootstrap_task", return_value=False),
            patch.object(open_module.guard, "arm"),
        ):
            self.assertEqual(open_module.open_workspace(path, primary), 0)

        kinds = [call[:2] for call in calls]
        self.assertIn(("worktree", "open"), kinds)
        self.assertIn(("workspace", "create"), kinds)


class HerdrWrapperTests(unittest.TestCase):
    def test_raises_on_nonzero_exit(self):
        from cli import herdr as herdr_module

        with patch.object(subprocess, "run", return_value=completed("", 2)):
            with self.assertRaises(HerdrError):
                herdr_module.herdr("workspace", "list")


if __name__ == "__main__":
    unittest.main()
