#!/usr/bin/env vpython3
# Copyright (c) 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import io
import os
import sys
from typing import Any
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import run_in_virtual_path  # noqa: E402

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="Virtual path is not supported on Windows"
)


def test_main_non_linux(mocker: Any) -> None:
    mocker.patch("sys.platform", new="win32")
    mock_stderr = mocker.patch("sys.stderr", new_callable=io.StringIO)

    ret = run_in_virtual_path.main(["run_in_virtual_path.py", "siso", "ninja"])
    assert ret == 1
    assert "virtual path is only supported on Linux" in mock_stderr.getvalue()


def test_main_no_args(mocker: Any) -> None:
    mocker.patch("sys.platform", new="linux")
    mock_stderr = mocker.patch("sys.stderr", new_callable=io.StringIO)

    ret = run_in_virtual_path.main(["run_in_virtual_path.py"])
    assert ret == 1
    assert (
        "Usage: run_in_virtual_path <command> [args...]"
        in mock_stderr.getvalue()
    )


def test_main_no_primary_solution_path(mocker: Any) -> None:
    mocker.patch("sys.platform", new="linux")
    mocker.patch("gclient_paths.GetPrimarySolutionPath", return_value=None)
    mock_stderr = mocker.patch("sys.stderr", new_callable=io.StringIO)

    ret = run_in_virtual_path.main(["run_in_virtual_path.py", "siso", "ninja"])
    assert ret == 1
    assert (
        "Could not find gclient primary solution path" in mock_stderr.getvalue()
    )


def test_main_runs_in_virtual_path(mocker: Any) -> None:
    mocker.patch("sys.platform", new="linux")
    mocker.patch(
        "gclient_paths.GetPrimarySolutionPath", return_value="/workspace/src"
    )
    mocker.patch("os.getuid", return_value=1001)
    mocker.patch("os.makedirs")
    mock_stderr = mocker.patch("sys.stderr", new_callable=io.StringIO)
    runner = mocker.Mock(return_value=0)

    ret = run_in_virtual_path.main(
        ["run_in_virtual_path.py", "autoninja", "-C", "out/Release", "chrome"],
        env={},
        runner=runner,
    )
    assert ret == 0

    assert runner.call_count == 1
    called_cmd, called_kwargs = runner.call_args
    cmd = called_cmd[0]
    called_env = called_kwargs.get("env", {})

    expected_bash_cmd = (
        "mount --rbind /workspace/src /tmp/depot_tools_virtual_build_path && "
        "cd /tmp/depot_tools_virtual_build_path && "
        "unshare --map-user=1001 autoninja -C out/Release chrome"
    )
    expected_unshare_cmd = [
        "luci-auth",
        "context",
        "--",
        "unshare",
        "--mount",
        "--map-root-user",
        "bash",
        "-c",
        expected_bash_cmd,
    ]

    assert cmd == expected_unshare_cmd
    assert (
        called_env.get("SISO_CREDENTIAL_HELPER") == "google-application-default"
    )
    assert (
        "Virtualizing paths from /workspace/src to /tmp/depot_tools_virtual_build_path"
        in mock_stderr.getvalue()
    )


def test_main_custom_virtual_path(mocker: Any) -> None:
    mocker.patch("sys.platform", new="linux")
    mocker.patch(
        "gclient_paths.GetPrimarySolutionPath", return_value="/workspace/src"
    )
    mocker.patch("os.getuid", return_value=1001)
    mocker.patch("os.makedirs")
    runner = mocker.Mock(return_value=0)

    env = {"DEPOT_TOOLS_VIRTUAL_BUILD_PATH": "/custom/virtual_path"}

    ret = run_in_virtual_path.main(
        ["run_in_virtual_path.py", "siso", "ninja"],
        env=env,
        runner=runner,
    )
    assert ret == 0

    cmd = runner.call_args[0][0]
    expected_bash_cmd = (
        "mount --rbind /workspace/src /custom/virtual_path && "
        "cd /custom/virtual_path && "
        "unshare --map-user=1001 siso ninja"
    )
    assert cmd[-1] == expected_bash_cmd


if __name__ == "__main__":
    sys.exit(pytest.main([__file__] + sys.argv[1:]))
