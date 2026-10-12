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

import gclient_paths  # noqa: E402
import gn  # noqa: E402
from testing_support import trial_dir  # noqa: E402


def write_file(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class GnTest(trial_dir.TestCase):
    def setUp(self):
        super().setUp()
        self.previous_dir = os.getcwd()
        os.chdir(self.root_dir)

    def tearDown(self):
        os.chdir(self.previous_dir)
        super().tearDown()

    def test_prefers_buildtools_over_third_party_gn(self):
        suffix = gclient_paths.GetExeSuffix()
        src_dir = os.path.join(self.root_dir, "src")
        buildtools_bin = os.path.join(src_dir, "buildtools", "linux64")
        buildtools_gn = os.path.join(buildtools_bin, "gn", f"gn{suffix}")
        third_party_gn = os.path.join(
            src_dir, "third_party", "gn", f"gn{suffix}"
        )
        write_file(buildtools_gn, "legit")
        write_file(third_party_gn, "planted")

        with (
            mock.patch(
                "gclient_paths.GetBuildtoolsPlatformBinaryPath",
                return_value=buildtools_bin,
            ),
            mock.patch(
                "gclient_paths.GetChromiumSrcPath", return_value=src_dir
            ),
        ):
            self.assertEqual(gn.FindGnTool(), buildtools_gn)

    def test_falls_back_to_third_party_gn_when_buildtools_missing(self):
        suffix = gclient_paths.GetExeSuffix()
        src_dir = os.path.join(self.root_dir, "src")
        third_party_gn = os.path.join(
            src_dir, "third_party", "gn", f"gn{suffix}"
        )
        write_file(third_party_gn, "fallback")

        with (
            mock.patch(
                "gclient_paths.GetBuildtoolsPlatformBinaryPath",
                return_value=None,
            ),
            mock.patch(
                "gclient_paths.GetChromiumSrcPath", return_value=src_dir
            ),
        ):
            self.assertEqual(gn.FindGnTool(), third_party_gn)

    def test_path_lookup_ignores_empty_dot_and_cwd(self):
        suffix = gclient_paths.GetExeSuffix()
        cwd_gn = os.path.join(self.root_dir, f"gn{suffix}")
        sys_bin = os.path.join(self.root_dir, "sys_bin")
        sys_gn = os.path.join(sys_bin, f"gn{suffix}")
        write_file(cwd_gn, "planted-cwd")
        write_file(sys_gn, "system-gn")

        path_val = os.pathsep.join(["", ".", self.root_dir, sys_bin])
        with (
            mock.patch.dict(os.environ, {"PATH": path_val}),
            mock.patch(
                "gclient_paths.GetBuildtoolsPlatformBinaryPath",
                return_value=None,
            ),
            mock.patch("gclient_paths.GetChromiumSrcPath", return_value=None),
        ):
            self.assertEqual(gn.FindGnTool(), sys_gn)

    def test_main_sets_no_default_cwd_on_windows(self):
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("sys.platform", "win32"),
            mock.patch(
                "gn.FindGnTool",
                return_value=os.path.join(self.root_dir, "gn.exe"),
            ),
            mock.patch("subprocess.call", return_value=0) as mock_call,
        ):
            rc = gn.main(["gn.py", "--version"])
            self.assertEqual(rc, 0)
            self.assertEqual(
                os.environ.get("NoDefaultCurrentDirectoryInExePath"), "1"
            )
            mock_call.assert_called_once_with(
                [os.path.join(self.root_dir, "gn.exe"), "--version"]
            )


if __name__ == "__main__":
    unittest.main()
