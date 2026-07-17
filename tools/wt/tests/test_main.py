import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wt import __main__


class MainTests(unittest.TestCase):
    def test_pr_create_forwards_gh_options(self):
        with (
            patch.object(sys, "argv", ["wt", "pr", "create", "env", "--base", "main"]),
            patch.object(__main__, "create_pr", return_value=0) as create_pr,
        ):
            self.assertEqual(__main__.main(), 0)

        create_pr.assert_called_once_with("env", ["--base", "main"])

    def test_pr_create_uses_working_copy_bookmark_by_default(self):
        with (
            patch.object(sys, "argv", ["wt", "pr", "create"]),
            patch.object(__main__, "create_pr", return_value=0) as create_pr,
        ):
            self.assertEqual(__main__.main(), 0)

        create_pr.assert_called_once_with(None, [])

    def test_switch_dispatches_workspace(self):
        with (
            patch.object(sys, "argv", ["wt", "switch", "project/feature"]),
            patch.object(__main__, "switch_workspace", return_value=0) as switch,
        ):
            self.assertEqual(__main__.main(), 0)

        switch.assert_called_once_with("project/feature")

    def test_discover_workspaces_finds_jj_directories(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "project" / "feature" / ".jj").mkdir(parents=True)
            (root / "project" / "not-a-workspace").mkdir()

            self.assertEqual(
                __main__.discover_workspaces(root), [root / "project" / "feature"]
            )

    def test_switch_resolves_unique_workspace_name(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            destination = root / "project" / "feature"
            (destination / ".jj").mkdir(parents=True)

            with patch("builtins.print") as print_result:
                self.assertEqual(__main__.switch_workspace("feature", root), 0)

            print_result.assert_called_once_with(destination)

    def test_switch_requires_project_for_ambiguous_workspace_name(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "first" / "feature" / ".jj").mkdir(parents=True)
            (root / "second" / "feature" / ".jj").mkdir(parents=True)

            with patch("builtins.print") as print_result:
                self.assertEqual(__main__.switch_workspace("feature", root), 1)

            self.assertIn("ambiguous", print_result.call_args.args[0])

    @patch.object(__main__.shutil, "which", return_value="/usr/bin/fzf")
    @patch.object(__main__.subprocess, "run")
    def test_switch_uses_fzf_when_workspace_is_omitted(self, run, _which):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            destination = root / "project" / "feature"
            (destination / ".jj").mkdir(parents=True)
            run.return_value = subprocess.CompletedProcess([], 0, "project/feature\n")

            with patch("builtins.print") as print_result:
                self.assertEqual(__main__.switch_workspace(None, root), 0)

            self.assertEqual(run.call_args.kwargs["input"], "project/feature")
            print_result.assert_called_once_with(destination)

    @patch.object(__main__.shutil, "which", return_value="/usr/bin/tool")
    @patch.object(__main__.Path, "is_dir", return_value=True)
    @patch.object(__main__.subprocess, "run")
    def test_pr_create_uses_jj_git_dir(self, run, _is_dir, _which):
        run.side_effect = [
            subprocess.CompletedProcess(["jj", "git", "root"], 0, "/repo/.git\n", ""),
            subprocess.CompletedProcess(["jj", "git", "push", "--bookmark", "env"], 0),
            subprocess.CompletedProcess(["gh", "pr", "create"], 0),
        ]

        self.assertEqual(__main__.create_pr("env", ["--base", "main"]), 0)

        self.assertEqual(
            run.call_args_list[1].args[0], ["jj", "git", "push", "--bookmark", "env"]
        )
        self.assertEqual(
            run.call_args_list[2].args[0],
            ["gh", "pr", "create", "--head", "env", "--base", "main"],
        )
        self.assertEqual(run.call_args_list[2].kwargs["env"]["GIT_DIR"], "/repo/.git")
        self.assertEqual(
            run.call_args_list[2].kwargs["env"]["PATH"], os.environ["PATH"]
        )

    @patch.object(__main__.subprocess, "run")
    def test_current_bookmark_uses_local_bookmarks_only(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "env\n", "")

        self.assertEqual(__main__.current_bookmark(), "env")
        self.assertIn("local_bookmarks", run.call_args.args[0][-1])


if __name__ == "__main__":
    unittest.main()
