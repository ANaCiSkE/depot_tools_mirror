#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest
from unittest import mock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import compile_single_file  # noqa: E402
from testing_support import trial_dir  # noqa: E402


class CompileSingleFileTest(trial_dir.TestCase):
    def setUp(self):
        super().setUp()
        self.previous_dir = os.getcwd()
        self.src_dir = os.path.join(self.root_dir, "src")
        for fp in ["chrome", "net", "v8", "build", "skia"]:
            os.makedirs(os.path.join(self.src_dir, fp), exist_ok=True)
        os.chdir(self.src_dir)

    def tearDown(self):
        os.chdir(self.previous_dir)
        super().tearDown()

    def test_invokes_autoninja_without_shell_on_win32(self):
        file_path = os.path.join(self.src_dir, "base", "render&evil.bat&x.cc")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("")

        abs_build_dir = os.path.join(self.src_dir, "out", "Default")
        expected_rel = os.path.relpath(file_path, abs_build_dir)

        with (
            mock.patch("sys.platform", "win32"),
            mock.patch("subprocess.call", return_value=0) as mock_call,
        ):
            rc = compile_single_file.main(
                [
                    "--file-path",
                    file_path,
                    "--build-dir",
                    os.path.join("out", "Default"),
                ]
            )
            self.assertEqual(rc, 0)
            mock_call.assert_called_once_with(
                [
                    sys.executable,
                    os.path.join(
                        compile_single_file.DEPOT_TOOLS_DIR, "autoninja.py"
                    ),
                    "-C",
                    abs_build_dir,
                    f"{expected_rel}^",
                ],
                shell=False,
            )

    def test_invokes_autoninja_without_shell_on_posix(self):
        file_path = os.path.join(self.src_dir, "base", "foo.cc")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("")

        abs_build_dir = os.path.join(self.src_dir, "out", "Default")
        expected_rel = os.path.relpath(file_path, abs_build_dir)

        with (
            mock.patch("sys.platform", "linux"),
            mock.patch("subprocess.call", return_value=0) as mock_call,
        ):
            rc = compile_single_file.main(
                [
                    "--file-path",
                    file_path,
                    "--build-dir",
                    os.path.join("out", "Default"),
                ]
            )
            self.assertEqual(rc, 0)
            mock_call.assert_called_once_with(
                [
                    sys.executable,
                    os.path.join(
                        compile_single_file.DEPOT_TOOLS_DIR, "autoninja.py"
                    ),
                    "-C",
                    abs_build_dir,
                    f"{expected_rel}^",
                ],
                shell=False,
            )


if __name__ == "__main__":
    unittest.main()
