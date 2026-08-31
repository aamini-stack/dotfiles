import argparse
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from devcli.boxes import Box, BoxError
from devcli.main import _connect, _select_box, main

BOX = Box("staging", "staging.example.com", "managed", Path("staging.conf"))


class MainTests(unittest.TestCase):
    def test_direct_box_name_connects_with_herdr(self):
        completed = subprocess.CompletedProcess([], 0)
        with (
            patch("devcli.main.get_box", return_value=BOX),
            patch("devcli.main.subprocess.run", return_value=completed) as run,
        ):
            result = main(["staging"])

        self.assertEqual(result, 0)
        run.assert_called_once_with(
            ["herdr", "--remote", "staging", "--remote-keybindings", "server"],
            check=False,
        )

    def test_connect_returns_herdr_status(self):
        args = argparse.Namespace(name="staging")
        with (
            patch("devcli.main.get_box", return_value=BOX),
            patch(
                "devcli.main.subprocess.run",
                return_value=subprocess.CompletedProcess([], 7),
            ),
        ):
            self.assertEqual(_connect(args), 7)

    def test_missing_named_box_is_an_error(self):
        with patch("devcli.main.get_box", side_effect=BoxError("missing")):
            self.assertEqual(main(["missing"]), 1)

    def test_selector_returns_selected_box(self):
        completed = subprocess.CompletedProcess(
            [], 0, stdout="staging\tstaging.example.com\tmanaged\n", stderr=""
        )
        with patch("devcli.main.subprocess.run", return_value=completed):
            self.assertEqual(_select_box([BOX]), BOX)

    def test_selector_cancel_returns_none(self):
        completed = subprocess.CompletedProcess([], 130, stdout="", stderr="")
        with patch("devcli.main.subprocess.run", return_value=completed):
            self.assertIsNone(_select_box([BOX]))

    def test_selector_reports_fzf_failure(self):
        completed = subprocess.CompletedProcess(
            [], 2, stdout="", stderr="invalid option"
        )
        with (
            patch("devcli.main.subprocess.run", return_value=completed),
            self.assertRaisesRegex(BoxError, "invalid option"),
        ):
            _select_box([BOX])


if __name__ == "__main__":
    unittest.main()
