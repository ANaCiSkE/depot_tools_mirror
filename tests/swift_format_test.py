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

import swift_format  # noqa: E402
from testing_support import trial_dir  # noqa: E402


def write_file(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class SwiftFormatTest(trial_dir.TestCase):
    def setUp(self):
        super().setUp()
        self.src_dir = os.path.join(self.root_dir, "src")

    def test_finds_arch_specific_binary(self):
        cases = [
            ("darwin", "arm64", "mac-arm64"),
            ("darwin", "x64", "mac-amd64"),
        ]
        for platform, arch, subdir in cases:
            with self.subTest(platform=platform, arch=arch):
                expected = os.path.join(
                    self.src_dir,
                    "third_party",
                    "swift-toolchain",
                    subdir,
                    "usr",
                    "bin",
                    "swift-format",
                )
                write_file(expected, "binary")
                with (
                    mock.patch("sys.platform", platform),
                    mock.patch("detect_host_arch.HostArch", return_value=arch),
                    mock.patch(
                        "gclient_paths.GetChromiumSrcPath",
                        return_value=self.src_dir,
                    ),
                ):
                    self.assertEqual(
                        swift_format.FindSwiftFormatToolInChromiumTree(),
                        expected,
                    )
                    self.assertTrue(swift_format.IsSwiftFormatSupported())

    def test_prefers_arch_specific_over_fallback(self):
        arch_tool = os.path.join(
            self.src_dir,
            "third_party",
            "swift-toolchain",
            "mac-arm64",
            "usr",
            "bin",
            "swift-format",
        )
        fallback_tool = os.path.join(
            self.src_dir,
            "third_party",
            "swift-toolchain",
            "usr",
            "bin",
            "swift-format",
        )
        write_file(arch_tool, "arch")
        write_file(fallback_tool, "fallback")

        with (
            mock.patch("sys.platform", "darwin"),
            mock.patch("detect_host_arch.HostArch", return_value="arm64"),
            mock.patch(
                "gclient_paths.GetChromiumSrcPath", return_value=self.src_dir
            ),
        ):
            self.assertEqual(
                swift_format.FindSwiftFormatToolInChromiumTree(), arch_tool
            )

    def test_falls_back_to_legacy_location(self):
        fallback_tool = os.path.join(
            self.src_dir,
            "third_party",
            "swift-toolchain",
            "usr",
            "bin",
            "swift-format",
        )
        write_file(fallback_tool, "fallback")

        with (
            mock.patch("sys.platform", "darwin"),
            mock.patch("detect_host_arch.HostArch", return_value="arm64"),
            mock.patch(
                "gclient_paths.GetChromiumSrcPath", return_value=self.src_dir
            ),
        ):
            self.assertEqual(
                swift_format.FindSwiftFormatToolInChromiumTree(), fallback_tool
            )

    def test_raises_not_found_when_missing(self):
        with (
            mock.patch("sys.platform", "darwin"),
            mock.patch("detect_host_arch.HostArch", return_value="arm64"),
            mock.patch(
                "gclient_paths.GetChromiumSrcPath", return_value=self.src_dir
            ),
        ):
            with self.assertRaises(swift_format.NotFoundError):
                swift_format.FindSwiftFormatToolInChromiumTree()
            self.assertFalse(swift_format.IsSwiftFormatSupported())

    def test_not_supported_on_windows(self):
        with mock.patch("sys.platform", "win32"):
            self.assertFalse(swift_format.IsSwiftFormatSupported())


if __name__ == "__main__":
    unittest.main()
