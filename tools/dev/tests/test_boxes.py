import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from devcli.boxes import (
    BoxError,
    add_box,
    edit_box,
    get_box,
    list_boxes,
    list_managed_boxes,
    read_box,
)


class BoxTests(unittest.TestCase):
    def test_lists_managed_boxes(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / ".staging.abandoned.conf").write_text("incomplete")
            (directory / "staging.conf").write_text(
                "Host staging\n    HostName staging.example.com\n    User aria\n"
            )

            boxes = list_managed_boxes(directory)

            self.assertEqual(
                [(box.name, box.hostname, box.source) for box in boxes],
                [("staging", "staging.example.com", "managed")],
            )

    def test_rejects_file_name_that_differs_from_host(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "staging.conf"
            path.write_text("Host production\n    HostName example.com\n")

            with self.assertRaisesRegex(BoxError, "must match file name"):
                read_box(path, expected_name="staging")

    def test_rejects_wildcard_hosts(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "staging.conf"
            path.write_text("Host staging *\n    HostName example.com\n")

            with self.assertRaisesRegex(BoxError, "one concrete Host"):
                read_box(path, expected_name="staging")

    def test_lists_lima_boxes_without_shadowing_managed_boxes(self):
        with (
            TemporaryDirectory() as boxes_temporary,
            TemporaryDirectory() as lima_temporary,
        ):
            boxes_dir = Path(boxes_temporary)
            lima_dir = Path(lima_temporary)
            (boxes_dir / "lima-default.conf").write_text(
                "Host lima-default\n    HostName managed.example.com\n"
            )
            lima_instance = lima_dir / "default"
            lima_instance.mkdir()
            (lima_instance / "ssh.config").write_text(
                "Host lima-default\n    HostName 127.0.0.1\n"
            )

            boxes = list_boxes(boxes_dir, lima_dir)

            self.assertEqual(len(boxes), 1)
            self.assertEqual(boxes[0].hostname, "managed.example.com")

    def test_get_box_reads_only_the_named_managed_file(self):
        with TemporaryDirectory() as temporary, TemporaryDirectory() as lima_temporary:
            directory = Path(temporary)
            (directory / "broken.conf").write_text("not an SSH host\n")
            (directory / "work.conf").write_text(
                "Host work\n    HostName work.example.com\n"
            )

            box = get_box("work", directory, Path(lima_temporary))

            self.assertEqual(box.hostname, "work.example.com")

    def test_add_uses_editor_and_installs_valid_file(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)

            def edit(command, **_kwargs):
                Path(command[-1]).write_text(
                    "Host staging\n    HostName staging.example.com\n    User aria\n"
                )
                return type("Result", (), {"returncode": 0})()

            with (
                patch.dict(os.environ, {"EDITOR": "editor", "VISUAL": ""}),
                patch("devcli.boxes.subprocess.run", side_effect=edit),
                patch("devcli.boxes._validate_ssh_config"),
            ):
                box = add_box("staging", directory)

            self.assertEqual(box.hostname, "staging.example.com")
            self.assertEqual(
                (directory / "staging.conf").read_text(),
                "Host staging\n    HostName staging.example.com\n    User aria\n",
            )

    def test_failed_edit_preserves_original_file(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / "staging.conf"
            original = "Host staging\n    HostName old.example.com\n"
            path.write_text(original)

            def edit(command, **_kwargs):
                Path(command[-1]).write_text(
                    "Host production\n    HostName new.example.com\n"
                )
                return type("Result", (), {"returncode": 0})()

            with (
                patch.dict(os.environ, {"EDITOR": "editor", "VISUAL": ""}),
                patch("devcli.boxes.subprocess.run", side_effect=edit),
                self.assertRaisesRegex(BoxError, "must match file name"),
            ):
                edit_box("staging", directory)

            self.assertEqual(path.read_text(), original)

    def test_concurrent_add_does_not_overwrite_new_file(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            destination = directory / "staging.conf"
            concurrent = "Host staging\n    HostName concurrent.example.com\n"

            def edit(command, **_kwargs):
                Path(command[-1]).write_text(
                    "Host staging\n    HostName edited.example.com\n"
                )
                destination.write_text(concurrent)
                return type("Result", (), {"returncode": 0})()

            with (
                patch.dict(os.environ, {"EDITOR": "editor", "VISUAL": ""}),
                patch("devcli.boxes.subprocess.run", side_effect=edit),
                patch("devcli.boxes._validate_ssh_config"),
                self.assertRaisesRegex(BoxError, "created by another process"),
            ):
                add_box("staging", directory)

            self.assertEqual(destination.read_text(), concurrent)
