import argparse
import subprocess
import sys
import unittest
from unittest.mock import patch

from jjws.wt import main, pr


def completed(stdout: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


class DispatchTests(unittest.TestCase):
    def test_forwards_gh_options(self):
        with (
            patch.object(sys, "argv", ["wt", "pr", "env", "--base", "main"]),
            patch.object(pr, "create_pr", return_value=0) as create_pr,
        ):
            self.assertEqual(main.main(), 0)

        create_pr.assert_called_once_with("env", ["--base", "main"])

    def test_defaults_bookmark(self):
        with (
            patch.object(sys, "argv", ["wt", "pr"]),
            patch.object(pr, "create_pr", return_value=0) as create_pr,
        ):
            self.assertEqual(main.main(), 0)

        create_pr.assert_called_once_with(None, [])

    def test_run_calls_create_pr(self):
        args = argparse.Namespace(bookmark="env", gh_args=["--base", "main"])
        with patch.object(pr, "create_pr", return_value=0) as create_pr:
            self.assertEqual(pr.run(args), 0)

        create_pr.assert_called_once_with("env", ["--base", "main"])


class CurrentBookmarkTests(unittest.TestCase):
    def test_returns_sole_bookmark(self):
        with patch.object(subprocess, "run", return_value=completed("feature\n")):
            self.assertEqual(pr.current_bookmark(), "feature")

    def test_requires_exactly_one_bookmark(self):
        with patch.object(subprocess, "run", return_value=completed("a\nb\n")):
            self.assertIsNone(pr.current_bookmark())

    def test_propagates_jj_failure(self):
        with patch.object(subprocess, "run", return_value=completed("", 1)):
            self.assertIsNone(pr.current_bookmark())


if __name__ == "__main__":
    unittest.main()
