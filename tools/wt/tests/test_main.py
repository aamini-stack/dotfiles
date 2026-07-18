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

        switch.assert_called_once_with("project/feature", False)

    def test_switch_dispatches_create(self):
        with (
            patch.object(sys, "argv", ["wt", "switch", "-c", "feature"]),
            patch.object(__main__, "switch_workspace", return_value=0) as switch,
        ):
            self.assertEqual(__main__.main(), 0)

        switch.assert_called_once_with("feature", True)

    def test_remove_dispatches_workspace(self):
        with (
            patch.object(sys, "argv", ["wt", "remove", "project/feature"]),
            patch.object(__main__, "remove_workspace", return_value=0) as remove,
        ):
            self.assertEqual(__main__.main(), 0)

        remove.assert_called_once_with("project/feature", False)

    def test_remove_dispatches_force(self):
        with (
            patch.object(sys, "argv", ["wt", "remove", "feature", "--force"]),
            patch.object(__main__, "remove_workspace", return_value=0) as remove,
        ):
            self.assertEqual(__main__.main(), 0)

        remove.assert_called_once_with("feature", True)

    def test_switch_create_requires_workspace_name(self):
        with patch("builtins.print") as print_result:
            self.assertEqual(__main__.switch_workspace(None, create=True), 1)

        self.assertIn("--create", print_result.call_args.args[0])

    @patch.object(__main__.subprocess, "run")
    def test_switch_create_uses_existing_workspace(self, run):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            destination = root / "project" / "feature"
            (destination / ".jj").mkdir(parents=True)

            with patch("builtins.print") as print_result:
                self.assertEqual(
                    __main__.switch_workspace("feature", create=True, root=root), 0
                )

            run.assert_not_called()
            print_result.assert_called_once_with(destination)

    def test_switch_create_rejects_ambiguous_workspace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "first" / "feature" / ".jj").mkdir(parents=True)
            (root / "second" / "feature" / ".jj").mkdir(parents=True)

            with patch("builtins.print") as print_result:
                self.assertEqual(
                    __main__.switch_workspace("feature", create=True, root=root), 1
                )

            self.assertIn("ambiguous", print_result.call_args.args[0])

    @patch.object(__main__.subprocess, "run")
    def test_switch_create_adds_missing_workspace(self, run):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            run.side_effect = [
                subprocess.CompletedProcess(["jj", "root"], 0, "/repo/project\n", ""),
                subprocess.CompletedProcess(["jj", "workspace", "add"], 0),
            ]
            destination = root / "project" / "feature"

            with patch("builtins.print") as print_result:
                self.assertEqual(
                    __main__.switch_workspace("feature", create=True, root=root), 0
                )

            self.assertEqual(
                run.call_args_list[1].args[0],
                ["jj", "workspace", "add", str(destination)],
            )
            print_result.assert_called_once_with(destination)

    @patch.object(__main__.subprocess, "run")
    def test_main_checkout_follows_workspace_pointer(self, run):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            main = root / "project"
            (main / ".jj" / "repo").mkdir(parents=True)
            workspace = root / "workspaces" / "project" / "feature"
            (workspace / ".jj").mkdir(parents=True)
            (workspace / ".jj" / "repo").write_text(
                (main / ".jj" / "repo").absolute().as_posix()
            )
            run.return_value = subprocess.CompletedProcess(
                ["jj", "root"], 0, f"{workspace}\n", ""
            )

            self.assertEqual(__main__.main_checkout(), main)

    @patch.object(__main__.subprocess, "run")
    def test_main_checkout_errors_outside_jj_repo(self, run):
        run.return_value = subprocess.CompletedProcess(
            ["jj", "root"], 1, "", "Error: no repo\n"
        )

        self.assertIsNone(__main__.main_checkout())

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
                self.assertEqual(__main__.switch_workspace("feature", root=root), 0)

            print_result.assert_called_once_with(destination)

    def test_switch_requires_project_for_ambiguous_workspace_name(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "first" / "feature" / ".jj").mkdir(parents=True)
            (root / "second" / "feature" / ".jj").mkdir(parents=True)

            with patch("builtins.print") as print_result:
                self.assertEqual(__main__.switch_workspace("feature", root=root), 1)

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
                self.assertEqual(__main__.switch_workspace(None, root=root), 0)

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

    def test_remove_defaults_to_current_workspace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            destination = root / "project" / "feature"
            (destination / ".jj").mkdir(parents=True)
            (destination / ".jj" / "repo").write_text("../../../project/.jj/repo")

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree") as rmtree,
            ):
                run.side_effect = [
                    subprocess.CompletedProcess(
                        ["jj", "root"], 0, f"{destination}\n", ""
                    ),
                    subprocess.CompletedProcess(["jj", "log"], 0, "", ""),
                    subprocess.CompletedProcess(["jj", "workspace", "forget"], 0),
                ]

                self.assertEqual(__main__.remove_workspace(None, root=root), 0)

                rmtree.assert_called_once_with(destination)

    def test_remove_prints_main_checkout_after_removing_current(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            main = root / "project"
            (main / ".jj" / "repo").mkdir(parents=True)
            destination = root / "workspaces" / "project" / "feature"
            (destination / ".jj").mkdir(parents=True)
            (destination / ".jj" / "repo").write_text(
                (main / ".jj" / "repo").as_posix()
            )

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree"),
                patch.object(__main__.Path, "cwd", return_value=destination),
                patch("builtins.print") as print_result,
            ):
                run.side_effect = [
                    subprocess.CompletedProcess(
                        ["jj", "root"], 0, f"{destination}\n", ""
                    ),
                    subprocess.CompletedProcess(["jj", "log"], 0, "", ""),
                    subprocess.CompletedProcess(["jj", "workspace", "forget"], 0),
                ]

                self.assertEqual(__main__.remove_workspace(None, root=root), 0)

                print_result.assert_called_once_with(main)

    def test_remove_prints_nothing_when_removing_other_workspace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "project" / "feature" / ".jj").mkdir(parents=True)

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree"),
                patch("builtins.print") as print_result,
            ):
                run.side_effect = [
                    subprocess.CompletedProcess(["jj", "log"], 0, "", ""),
                    subprocess.CompletedProcess(["jj", "workspace", "forget"], 0),
                ]

                self.assertEqual(__main__.remove_workspace("feature", root=root), 0)

                print_result.assert_not_called()

    def test_remove_refuses_default_checkout(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            main = Path(temporary_directory) / "project"
            (main / ".jj" / "repo").mkdir(parents=True)

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree") as rmtree,
                patch("builtins.print") as print_result,
            ):
                run.return_value = subprocess.CompletedProcess(
                    ["jj", "root"], 0, f"{main}\n", ""
                )

                self.assertEqual(__main__.remove_workspace(None), 1)

                run.assert_called_once()
                self.assertIn("refusing", print_result.call_args.args[0])
                rmtree.assert_not_called()

    @patch.object(__main__.subprocess, "run")
    def test_remove_errors_outside_jj_repo(self, run):
        run.return_value = subprocess.CompletedProcess(
            ["jj", "root"], 1, "", "Error: no repo\n"
        )

        self.assertEqual(__main__.remove_workspace(None), 1)

        run.assert_called_once()

    def test_remove_forgets_and_deletes_clean_workspace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            destination = root / "project" / "feature"
            (destination / ".jj").mkdir(parents=True)

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree") as rmtree,
            ):
                run.side_effect = [
                    subprocess.CompletedProcess(["jj", "log"], 0, "", ""),
                    subprocess.CompletedProcess(["jj", "workspace", "forget"], 0),
                ]

                self.assertEqual(__main__.remove_workspace("feature", root=root), 0)

                self.assertEqual(run.call_args_list[0].kwargs["cwd"], destination)
                self.assertEqual(
                    run.call_args_list[1].args[0], ["jj", "workspace", "forget"]
                )
                rmtree.assert_called_once_with(destination)

    def test_remove_confirms_before_deleting_dirty_workspace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            destination = root / "project" / "feature"
            (destination / ".jj").mkdir(parents=True)

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree") as rmtree,
                patch.object(sys, "stdin") as stdin,
                patch("builtins.input", return_value="y"),
            ):
                run.side_effect = [
                    subprocess.CompletedProcess(["jj", "log"], 0, "abc123\n", ""),
                    subprocess.CompletedProcess(["jj", "workspace", "forget"], 0),
                ]
                stdin.isatty.return_value = True

                self.assertEqual(__main__.remove_workspace("feature", root=root), 0)

                rmtree.assert_called_once_with(destination)

    def test_remove_keeps_dirty_workspace_when_declined(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "project" / "feature" / ".jj").mkdir(parents=True)

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree") as rmtree,
                patch.object(sys, "stdin") as stdin,
                patch("builtins.input", return_value="n"),
            ):
                run.return_value = subprocess.CompletedProcess([], 0, "abc123\n", "")
                stdin.isatty.return_value = True

                self.assertEqual(__main__.remove_workspace("feature", root=root), 1)

                run.assert_called_once()
                rmtree.assert_not_called()

    def test_remove_keeps_dirty_workspace_without_tty(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "project" / "feature" / ".jj").mkdir(parents=True)

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree") as rmtree,
                patch.object(sys, "stdin") as stdin,
            ):
                run.return_value = subprocess.CompletedProcess([], 0, "abc123\n", "")
                stdin.isatty.return_value = False

                self.assertEqual(__main__.remove_workspace("feature", root=root), 1)

                run.assert_called_once()
                rmtree.assert_not_called()

    def test_remove_force_skips_confirmation(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            destination = root / "project" / "feature"
            (destination / ".jj").mkdir(parents=True)

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree") as rmtree,
            ):
                run.return_value = subprocess.CompletedProcess([], 0)

                self.assertEqual(
                    __main__.remove_workspace("feature", force=True, root=root), 0
                )

                run.assert_called_once()
                self.assertEqual(run.call_args.args[0], ["jj", "workspace", "forget"])
                rmtree.assert_called_once_with(destination)

    def test_remove_keeps_workspace_when_forget_fails(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "project" / "feature" / ".jj").mkdir(parents=True)

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree") as rmtree,
            ):
                run.side_effect = [
                    subprocess.CompletedProcess(["jj", "log"], 0, "", ""),
                    subprocess.CompletedProcess(["jj", "workspace", "forget"], 1),
                ]

                self.assertEqual(__main__.remove_workspace("feature", root=root), 1)

                rmtree.assert_not_called()

    def test_remove_retries_delete_after_race(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "project" / "feature" / ".jj").mkdir(parents=True)

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree") as rmtree,
                patch.object(__main__.time, "sleep"),
            ):
                run.side_effect = [
                    subprocess.CompletedProcess(["jj", "log"], 0, "", ""),
                    subprocess.CompletedProcess(["jj", "workspace", "forget"], 0),
                ]
                rmtree.side_effect = [OSError(39, "Directory not empty"), None]

                self.assertEqual(__main__.remove_workspace("feature", root=root), 0)

                self.assertEqual(rmtree.call_count, 2)

    def test_remove_reports_undeletable_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "project" / "feature" / ".jj").mkdir(parents=True)

            with (
                patch.object(__main__.subprocess, "run") as run,
                patch.object(__main__.shutil, "rmtree") as rmtree,
                patch.object(__main__.time, "sleep"),
                patch("builtins.print") as print_result,
            ):
                run.side_effect = [
                    subprocess.CompletedProcess(["jj", "log"], 0, "", ""),
                    subprocess.CompletedProcess(["jj", "workspace", "forget"], 0),
                ]
                rmtree.side_effect = OSError(39, "Directory not empty")

                self.assertEqual(__main__.remove_workspace("feature", root=root), 1)

                self.assertIn(
                    "could not delete", print_result.call_args_list[0].args[0]
                )
                self.assertIn("manually", print_result.call_args_list[1].args[0])

    @patch.object(__main__.subprocess, "run")
    def test_current_bookmark_uses_local_bookmarks_only(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "env\n", "")

        self.assertEqual(__main__.current_bookmark(), "env")
        self.assertIn("local_bookmarks", run.call_args.args[0][-1])


if __name__ == "__main__":
    unittest.main()
