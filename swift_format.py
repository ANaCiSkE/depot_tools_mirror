#!/usr/bin/env python3
# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Redirects to the version of swift-format present in the Chrome tree.

Swift format binaries are pulled down from CIPD whenever you sync Chrome.
This script knows how to locate those tools, assuming the script is
invoked from inside a Chromium checkout."""

import detect_host_arch
import gclient_paths
import os
import subprocess
import sys


class NotFoundError(Exception):
    """A file could not be found."""

    def __init__(self, e):
        Exception.__init__(
            self,
            "Problem while looking for swift-format in Chromium source tree:\n"
            "%s" % e,
        )


def _GetHostPlatformSubdir():
    """Returns the CIPD platform subdirectory for the current host, or None."""
    arch = detect_host_arch.HostArch()
    if sys.platform == "darwin":
        if arch == "x64":
            return "mac-amd64"
        if arch == "arm64":
            return "mac-arm64"
    return None


def FindSwiftFormatToolInChromiumTree():
    """Return a path to the swift-format executable, or die trying."""
    chromium_src_path = gclient_paths.GetChromiumSrcPath()
    if not chromium_src_path:
        raise NotFoundError(
            "Could not find checkout in any parent of the current path.\n"
            "Set CHROMIUM_BUILDTOOLS_PATH to use outside of a chromium "
            "checkout."
        )

    old_tool_path = os.path.join(
        chromium_src_path,
        "third_party",
        "swift-toolchain",
        "usr",
        "bin",
        "swift-format",
    )

    possible_paths = []
    platform_subdir = _GetHostPlatformSubdir()
    if platform_subdir:
        possible_paths.append(
            os.path.join(
                chromium_src_path,
                "third_party",
                "swift-toolchain",
                platform_subdir,
                "usr",
                "bin",
                "swift-format",
            )
        )
    possible_paths.append(old_tool_path)

    for path in possible_paths:
        if os.path.exists(path):
            return path
    raise NotFoundError(
        "File does not exist in either path: %s" % possible_paths
    )


def IsSwiftFormatSupported():
    if sys.platform != "darwin":
        return False
    try:
        FindSwiftFormatToolInChromiumTree()
        return True
    except NotFoundError:
        return False


def main(args):
    try:
        tool = FindSwiftFormatToolInChromiumTree()
    except NotFoundError as e:
        sys.stderr.write("%s\n" % str(e))
        return 1

    # Add some visibility to --help showing where the tool lives, since this
    # redirection can be a little opaque.
    help_syntax = ("-h", "--help", "-help", "-help-list", "--help-list")
    if any(match in args for match in help_syntax):
        print(
            "\nDepot tools redirects you to the swift-format at:\n    %s\n"
            % tool
        )

    return subprocess.call([tool] + args)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write("interrupted\n")
        sys.exit(1)
