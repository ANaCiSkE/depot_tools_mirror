#!/usr/bin/env python3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Redirects to the version of ktfmt checked into the Chrome tree."""

import gclient_paths
import os
import subprocess
import sys


def FindKtfmt():
    """Returns the path to the ktfmt executable."""
    primary_solution_path = gclient_paths.GetPrimarySolutionPath()
    if not primary_solution_path:
        return None

    override = os.environ.get("KTFMT_PATH")
    if override:
        return os.path.join(primary_solution_path, override)

    bin_path = os.path.join(
        primary_solution_path, "third_party", "ktfmt", "ktfmt"
    )
    jar_path = os.path.join(
        primary_solution_path, "third_party", "ktfmt", "cipd", "ktfmt.jar"
    )
    if os.path.exists(bin_path) and os.path.exists(jar_path):
        return bin_path
    return None


def main(args):
    tool = FindKtfmt()
    if tool is None:
        print(
            'ktfmt not found. Please run "gclient sync" to download build tools.',
            file=sys.stderr,
        )
        return 2

    return subprocess.call([tool] + args)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write("interrupted\n")
        sys.exit(1)
