#!/usr/bin/env python3
# Copyright 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script is a wrapper to run command in virtual path."""

import os
import shlex
import subprocess
import sys
from typing import Callable, Optional

import gclient_paths


def fetch_out_dir(args: list[str]) -> str:
    out_dir = "."
    for i, arg in enumerate(args):
        if arg == "-C":
            if i + 1 < len(args):
                out_dir = args[i + 1]
        elif arg.startswith("-C"):
            out_dir = arg[2:]
    return out_dir


def main(
    args: list[str],
    env: Optional[dict[str, str]] = None,
    runner: Callable = subprocess.call,
) -> int:
    if sys.platform != "linux":
        print(
            "Error: virtual path is only supported on Linux",
            file=sys.stderr,
        )
        return 1

    cmd_args = args[1:]
    if not cmd_args:
        print("Usage: run_in_virtual_path <command> [args...]", file=sys.stderr)
        return 1

    env = (os.environ if env is None else env).copy()

    out_dir = fetch_out_dir(cmd_args)
    primary_solution_path = gclient_paths.GetPrimarySolutionPath(out_dir)
    if not primary_solution_path:
        print(
            "Error: Could not find gclient primary solution path.",
            file=sys.stderr,
        )
        return 1

    virtual_path = env.get(
        "DEPOT_TOOLS_VIRTUAL_BUILD_PATH", "/tmp/depot_tools_virtual_build_path"
    )
    print(
        f"Virtualizing paths from {primary_solution_path} to {virtual_path}. All file paths in log output will show the virtual path.",
        file=sys.stderr,
    )

    os.makedirs(virtual_path, exist_ok=True)

    # TODO(b/528372534): run `siso proxy` outside namespace
    uid = os.getuid()
    bash_cmd = f"mount --rbind {shlex.quote(primary_solution_path)} {shlex.quote(virtual_path)} && cd {shlex.quote(virtual_path)} && unshare --map-user={uid} {shlex.join(cmd_args)}"
    unshare_cmd = [
        "luci-auth",
        "context",
        "--",
        "unshare",
        "--mount",
        "--map-root-user",
        "bash",
        "-c",
        bash_cmd,
    ]
    env["SISO_CREDENTIAL_HELPER"] = "google-application-default"

    return runner(unshare_cmd, env=env)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
