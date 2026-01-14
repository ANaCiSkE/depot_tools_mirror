#!/usr/bin/env vpython3
# Copyright (c) 2024 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import io
import os
import shlex
import sys
import pytest
import subprocess
import itertools
from pathlib import Path
from typing import Any, Dict, List, Tuple, Generator, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
import siso

# These are required for fixtures to work.
# pylint: disable=redefined-outer-name,unused-argument


@pytest.fixture
def siso_test_fixture(tmp_path: Path,
                      mocker: Any) -> Generator[None, None, None]:
    # Replace trial dir functionality with tmp_parth.
    previous_dir = os.getcwd()
    os.chdir(tmp_path)
    mocker.patch("siso.getpass.getuser", return_value="testuser")
    yield
    os.chdir(previous_dir)


def test_load_sisorc_no_file(siso_test_fixture: Any) -> None:
    global_flags, subcmd_flags = siso.load_sisorc(
        os.path.join("build", "config", "siso", ".sisorc"))
    assert global_flags == []
    assert subcmd_flags == {}


def test_load_sisorc(siso_test_fixture: Any) -> None:
    sisorc = os.path.join("build", "config", "siso", ".sisorc")
    os.makedirs(os.path.dirname(sisorc))
    with open(sisorc, "w") as f:
        f.write("""
# comment
-credential_helper=gcloud
ninja --failure_verbose=false -k=0
        """)
    global_flags, subcmd_flags = siso.load_sisorc(sisorc)
    assert global_flags == ["-credential_helper=gcloud"]
    assert subcmd_flags == {"ninja": ["--failure_verbose=false", "-k=0"]}


def test_apply_sisorc_none(siso_test_fixture: Any) -> None:
    new_args = siso.apply_sisorc([], {}, ["ninja", "-C", "out/Default"],
                                 "ninja")
    assert new_args == ["ninja", "-C", "out/Default"]


def test_apply_sisorc_nosubcmd(siso_test_fixture: Any) -> None:
    new_args = siso.apply_sisorc([], {"ninja": ["-k=0"]}, ["-version"], "")
    assert new_args == ["-version"]


def test_apply_sisorc(siso_test_fixture: Any) -> None:
    new_args = siso.apply_sisorc(
        ["-credential_helper=luci-auth"],
        {"ninja": ["-k=0"]},
        ["-log_dir=/tmp", "ninja", "-C", "out/Default"],
        "ninja",
    )
    assert new_args == [
        "-credential_helper=luci-auth",
        "-log_dir=/tmp",
        "ninja",
        "-k=0",
        "-C",
        "out/Default",
    ]


@pytest.mark.parametrize(
    "args, want",
    [
        pytest.param(
            ["ninja", "-C", "out/Default"],
            [
                "ninja",
                "-C",
                "out/Default",
                "--metrics_labels",
                f"type=developer,tool=siso,host_os={siso._SYSTEM_DICT.get(sys.platform, sys.platform)}",
            ],
            id="no_labels",
        ),
        pytest.param(
            ["ninja", "-C", "out/Default", "--metrics_labels=foo=bar"],
            ["ninja", "-C", "out/Default", "--metrics_labels=foo=bar"],
            id="labels_exist",
        ),
    ],
)
def test_apply_metrics_labels(args: List[str], want: List[str]) -> None:
    got = siso.apply_metrics_labels(args)
    assert got == want


@pytest.mark.parametrize(
    "args, env, want",
    [
        pytest.param(
            ["ninja", "-C", "out/Default"],
            {},
            ["ninja", "-C", "out/Default"],
            id="no_env_flags",
        ),
        pytest.param(
            [
                "ninja",
                "-C",
                "out/Default",
                "--enable_cloud_monitoring",
                "--enable_cloud_profiler",
            ],
            {},
            [
                "ninja",
                "-C",
                "out/Default",
                "--enable_cloud_monitoring",
                "--enable_cloud_profiler",
            ],
            id="some_already_applied_no_env_flags",
        ),
        pytest.param(
            ["ninja", "-C", "out/Default", "--metrics_project", "some_project"],
            {},
            [
                "ninja",
                "-C",
                "out/Default",
                "--metrics_project",
                "some_project",
                "--enable_cloud_monitoring",
                "--enable_cloud_profiler",
                "--enable_cloud_trace",
                "--enable_cloud_logging",
            ],
            id="metrics_project_set",
        ),
        pytest.param(
            ["ninja", "-C", "out/Default"],
            {"RBE_metrics_project": "some_project"},
            [
                "ninja",
                "-C",
                "out/Default",
                "--enable_cloud_monitoring",
                "--enable_cloud_profiler",
                "--enable_cloud_trace",
                "--enable_cloud_logging",
            ],
            id="metrics_project_set_thru_env",
        ),
        pytest.param(
            ["ninja", "-C", "out/Default", "--project", "some_project"],
            {},
            [
                "ninja",
                "-C",
                "out/Default",
                "--project",
                "some_project",
                "--enable_cloud_monitoring",
                "--enable_cloud_profiler",
                "--enable_cloud_trace",
                "--enable_cloud_logging",
                "--metrics_project=some_project",
            ],
            id="cloud_project_set",
        ),
        pytest.param(
            ["ninja", "-C", "out/Default"],
            {"SISO_PROJECT": "some_project"},
            [
                "ninja",
                "-C",
                "out/Default",
                "--enable_cloud_monitoring",
                "--enable_cloud_profiler",
                "--enable_cloud_trace",
                "--enable_cloud_logging",
                "--metrics_project=some_project",
            ],
            id="cloud_project_set_thru_env",
        ),
        pytest.param(
            ["ninja", "-C", "out/Default", "--enable_cloud_profiler=false"],
            {"SISO_PROJECT": "some_project"},
            [
                "ninja",
                "-C",
                "out/Default",
                "--enable_cloud_profiler=false",
                "--enable_cloud_monitoring",
                "--enable_cloud_trace",
                "--enable_cloud_logging",
                "--metrics_project=some_project",
            ],
            id="respects_set_flags",
        ),
        pytest.param(
            ["ninja", "--help"],
            {},
            ["ninja", "--help"],
            id="help_flag",
        ),
        pytest.param(
            ["ninja", "-h"],
            {},
            ["ninja", "-h"],
            id="short_help_flag",
        ),
    ],
)
def test_apply_telemetry_flags(args: List[str], env: Dict[str, str],
                               want: List[str]) -> None:
    got = siso.apply_telemetry_flags(args, env, "siso_path")
    assert got == want


def test_apply_telemetry_flags_sets_expected_env_var(mocker: Any) -> None:
    mocker.patch.dict("os.environ", {})
    args = [
        "ninja",
        "-C",
        "out/Default",
    ]
    env = {}
    _ = siso.apply_telemetry_flags(args, env, "siso_path")
    assert env.get("GOOGLE_API_USE_CLIENT_CERTIFICATE") == "false"


@pytest.mark.parametrize(
    "args, env, want",
    [
        pytest.param(
            ["--metrics_project", "proj1"],
            {},
            "proj1",
            id="metrics_project_arg",
        ),
        pytest.param(["--project", "proj2"], {}, "proj2", id="project_arg"),
        pytest.param(
            ["--metrics_project", "proj1", "--project", "proj2"],
            {},
            "proj1",
            id="metrics_project_and_project_args",
        ),
        pytest.param(
            [],
            {"RBE_metrics_project": "proj3"},
            "proj3",
            id="rbe_metrics_project_env",
        ),
        pytest.param(
            [], {"SISO_PROJECT": "proj4"}, "proj4", id="siso_project_env"),
        pytest.param(
            [],
            {
                "RBE_metrics_project": "proj3",
                "SISO_PROJECT": "proj4"
            },
            "proj3",
            id="rbe_and_siso_project_env",
        ),
        pytest.param(
            ["--project", "proj2"],
            {"RBE_metrics_project": "proj3"},
            "proj2",
            id="project_arg_and_rbe_env",
        ),
        pytest.param(
            ["--metrics_project", "proj1"],
            {"RBE_metrics_project": "proj3"},
            "proj1",
            id="metrics_project_arg_and_rbe_env",
        ),
        pytest.param([], {}, "", id="no_project"),
        pytest.param(
            ["-metrics_project", "proj1"],
            {},
            "proj1",
            id="short_metrics_project_arg",
        ),
        pytest.param(["-project", "proj2"], {}, "proj2",
                     id="short_project_arg"),
        pytest.param(["--help"], {}, "", id="help_flag"),
        pytest.param(["-h"], {}, "", id="short_help_flag"),
    ],
)
def test_fetch_metrics_project(args: List[str], env: Dict[str, str],
                               want: str) -> None:
    got = siso._fetch_metrics_project(args, env)
    assert got == want


@pytest.mark.parametrize(
    "platform, env_vars, want_path_template",
    [
        (
            "Linux",
            {
                "XDG_RUNTIME_DIR": os.path.join("{root_dir}", "run", "user",
                                                "1000")
            },
            os.path.join("{root_dir}", "run", "user", "1000", "{user}", "siso"),
        ),
        ("Linux", {}, os.path.join("/tmp", "{user}", "siso")),
        (
            "Darwin",
            {
                "TMPDIR":
                os.path.join("{root_dir}", "var", "folders", "12", "345..."),
            },
            os.path.join("{root_dir}", "var", "folders", "12", "345...",
                         "{user}", "siso"),
        ),
        ("Darwin", {}, os.path.join("/tmp", "{user}", "siso")),
        (
            "Linux",
            {
                "XDG_RUNTIME_DIR": "a" * 100
            },
            os.path.join("/tmp", "{user}", "siso"),
        ),
    ],
)
def test_resolve_sockets_folder(
    siso_test_fixture: Any,
    tmp_path: Path,
    platform: str,
    env_vars: Dict[str, str],
    want_path_template: str,
    mocker: Any,
) -> None:
    user = "testuser"
    # Replace placeholders in paths
    for key, value in env_vars.items():
        env_vars[key] = value.format(root_dir=str(tmp_path))
    want_path = want_path_template.format(root_dir=str(tmp_path), user=user)
    mocker.patch("sys.platform", new=platform.lower())
    path, length = siso._resolve_sockets_folder(env_vars)
    # If the desired path is too long, the function will fall back to /tmp/<user>/siso
    if (104 - len(want_path) - 6) < 1:
        expected_path = os.path.join("/tmp", user, "siso")
    else:
        expected_path = want_path
    expected_len = 104 - len(expected_path) - 6
    # Windows.
    assert path == expected_path
    assert length == expected_len
    assert os.path.isdir(path)


def test_handle_collector_args_disabled(start_collector_mocks: Dict[str, Any],
                                        mocker: Any) -> None:
    mock_fetch = mocker.patch("siso._fetch_metrics_project", return_value="")
    m = start_collector_mocks
    mocker.patch("sys.platform", new="linux")
    siso_path = "path/to/siso"
    out_dir = "out/Default"
    env = {"SISO_PROJECT": "test-project"}
    args = ["ninja", "-C", out_dir]
    res_env = siso._handle_collector(siso_path, args, "ninja", env)
    assert "SISO_COLLECTOR_ADDRESS" not in res_env
    mock_fetch.assert_called_once_with(args, env)
    m["subprocess_popen"].assert_not_called()


@pytest.mark.parametrize(
    "args, subcmd, project_val",
    [
        (["-h"], "ninja", "test-project"),
        (["--help"], "ninja", "test-project"),
        (["-help"], "ninja", "test-project"),
        ([], "other", "test-project"),
        ([], "ninja", ""),
    ],
)
def test_handle_collector_skipped(
    siso_test_fixture: Any,
    start_collector_mocks: Dict[str, Any],
    mocker: Any,
    args: List[str],
    subcmd: str,
    project_val: str,
) -> None:
    mocker.patch("sys.platform", new="linux")
    mocker.patch("siso._fetch_metrics_project", return_value=project_val)
    siso_path = "siso_path"
    env = {}

    res_env = siso._handle_collector(siso_path, args, subcmd, env)

    assert "SISO_COLLECTOR_ADDRESS" not in res_env
    start_collector_mocks["subprocess_popen"].assert_not_called()


@pytest.fixture
def start_collector_mocks(mocker: Any) -> Dict[str, Any]:
    mocks = {
        "subprocess_run":
        mocker.patch("siso.subprocess.run"),
        "kill_collector":
        mocker.patch("siso._kill_collector"),
        "time_sleep":
        mocker.patch("siso.time.sleep"),
        "time_time":
        mocker.patch("siso.time.time",
                     side_effect=(1000 + i * 0.1 for i in range(100))),
        "http_connection":
        mocker.patch("siso.http.client.HTTPConnection"),
        "subprocess_popen":
        mocker.patch("siso.subprocess.Popen"),
        "os_path_exists":
        mocker.patch("os.path.exists", return_value=True),
        "os_remove":
        mocker.patch("os.remove"),
    }
    mock_conn = mocker.Mock()
    mocks["http_connection"].return_value = mock_conn
    mocks["mock_conn"] = mock_conn
    return mocks


def _configure_http_responses(
    mocker: Any,
    mock_conn: Any,
    status_responses: List[Tuple[int, Any]],
    config_responses: Optional[List[Tuple[int, Any]]] = None,
) -> None:
    if config_responses is None:
        config_responses = []

    request_path_history = []

    def request_side_effect(method, path):
        request_path_history.append(path)

    def getresponse_side_effect():
        path = request_path_history[-1]
        if path == "/health/status":
            if not status_responses:
                return mocker.Mock(status=404,
                                   read=mocker.Mock(return_value=b""))
            status_code, _ = status_responses.pop(0)
            return mocker.Mock(status=status_code,
                               read=mocker.Mock(return_value=b""))
        if path == "/health/config":
            if not config_responses:
                return mocker.Mock(status=200,
                                   read=mocker.Mock(return_value=b"{}"))
            status_code, _ = config_responses.pop(0)
            return mocker.Mock(status=status_code,
                               read=mocker.Mock(return_value=b""))
        return mocker.Mock(status=404)

    mock_conn.request.side_effect = request_side_effect
    mock_conn.getresponse.side_effect = getresponse_side_effect


def test_handle_collector_removes_existing_socket_file(
        siso_test_fixture: Any, start_collector_mocks: Dict[str, Any],
        mocker: Any) -> None:
    mocker.patch("sys.platform", new="linux")
    mock_os_path_exists = mocker.patch("os.path.exists", return_value=True)
    mock_os_remove = mocker.patch("os.remove")
    mocker.patch("siso._fetch_metrics_project", return_value="test-project")
    siso_path = "siso_path"
    sockets_file = os.path.join("/tmp", "testuser", "siso", "test-project.sock")
    siso._handle_collector(siso_path, ["ninja"], "ninja", {})
    mock_os_path_exists.assert_called_with(sockets_file)
    mock_os_remove.assert_called_with(sockets_file)


def test_handle_collector_remove_socket_file_fails(siso_test_fixture: Any,
                                                   start_collector_mocks: Dict[
                                                       str, Any],
                                                   mocker: Any) -> None:
    mocker.patch("sys.platform", new="linux")
    mock_os_path_exists = mocker.patch("os.path.exists", return_value=True)
    mock_os_remove = mocker.patch("os.remove",
                                  side_effect=OSError("Permission denied"))
    mock_stderr = mocker.patch("sys.stderr", new_callable=io.StringIO)
    mocker.patch("siso._fetch_metrics_project", return_value="test-project")
    siso_path = "siso_path"
    sockets_file = os.path.join("/tmp", "testuser", "siso", "test-project.sock")
    siso._handle_collector(siso_path, ["ninja"], "ninja", {})
    mock_os_path_exists.assert_called_with(sockets_file)
    mock_os_remove.assert_called_with(sockets_file)
    assert f"Failed to remove {sockets_file}" in mock_stderr.getvalue()


@pytest.mark.parametrize(
    "global_flags, subcmd_flags, args, subcmd, should_collect_logs, env, want, want_stderr",
    [
        pytest.param(
            [],
            {},
            ["other", "-C", "out/Default"],
            "other",
            True,
            {},
            ["other", "-C", "out/Default"],
            "",
            id="no_ninja",
        ),
        pytest.param(
            [],
            {},
            ["ninja", "-C", "out/Default"],
            "ninja",
            False,
            {},
            [
                "ninja",
                "-C",
                "out/Default",
                "--metrics_labels",
                f"type=developer,tool=siso,host_os={siso._SYSTEM_DICT.get(sys.platform, sys.platform)}",
            ],
            "",
            id="ninja_no_logs",
        ),
        pytest.param(
            [],
            {},
            ["ninja", "-C", "out/Default"],
            "ninja",
            True,
            {},
            [
                "ninja",
                "-C",
                "out/Default",
                "--metrics_labels",
                f"type=developer,tool=siso,host_os={siso._SYSTEM_DICT.get(sys.platform, sys.platform)}",
            ],
            "",
            id="ninja_with_logs_no_project",
        ),
        pytest.param(
            [],
            {},
            ["ninja", "-C", "out/Default", "--project=test-project"],
            "ninja",
            True,
            {},
            [
                "ninja",
                "-C",
                "out/Default",
                "--project=test-project",
                "--metrics_labels",
                f"type=developer,tool=siso,host_os={siso._SYSTEM_DICT.get(sys.platform, sys.platform)}",
                "--enable_cloud_monitoring",
                "--enable_cloud_profiler",
                "--enable_cloud_trace",
                "--enable_cloud_logging",
                "--metrics_project=test-project",
            ],
            "",
            id="ninja_with_logs_with_project_in_args",
        ),
        pytest.param(
            [],
            {},
            ["ninja", "-C", "out/Default"],
            "ninja",
            True,
            {"SISO_PROJECT": "test-project"},
            [
                "ninja",
                "-C",
                "out/Default",
                "--metrics_labels",
                f"type=developer,tool=siso,host_os={siso._SYSTEM_DICT.get(sys.platform, sys.platform)}",
                "--enable_cloud_monitoring",
                "--enable_cloud_profiler",
                "--enable_cloud_trace",
                "--enable_cloud_logging",
                "--metrics_project=test-project",
            ],
            "",
            id="ninja_with_logs_with_project_in_env",
        ),
        pytest.param(
            ["-gflag"],
            {"ninja": ["-sflag"]},
            ["ninja", "-C", "out/Default"],
            "ninja",
            False,
            {},
            [
                "-gflag",
                "ninja",
                "-sflag",
                "-C",
                "out/Default",
                "--metrics_labels",
                f"type=developer,tool=siso,host_os={siso._SYSTEM_DICT.get(sys.platform, sys.platform)}",
            ],
            "depot_tools/siso.py: %s\n" %
            shlex.join(["-gflag", "ninja", "-sflag", "-C", "out/Default"]),
            id="with_sisorc",
        ),
        pytest.param(
            ["-gflag_only"],
            {},
            ["ninja", "-C", "out/Default"],
            "ninja",
            False,
            {},
            [
                "-gflag_only",
                "ninja",
                "-C",
                "out/Default",
                "--metrics_labels",
                f"type=developer,tool=siso,host_os={siso._SYSTEM_DICT.get(sys.platform, sys.platform)}",
            ],
            "depot_tools/siso.py: %s\n" %
            shlex.join(["-gflag_only", "ninja", "-C", "out/Default"]),
            id="with_sisorc_global_flags_only",
        ),
        pytest.param(
            [],
            {"ninja": ["-sflag_only"]},
            ["ninja", "-C", "out/Default"],
            "ninja",
            False,
            {},
            [
                "ninja",
                "-sflag_only",
                "-C",
                "out/Default",
                "--metrics_labels",
                f"type=developer,tool=siso,host_os={siso._SYSTEM_DICT.get(sys.platform, sys.platform)}",
            ],
            "depot_tools/siso.py: %s\n" %
            shlex.join(["ninja", "-sflag_only", "-C", "out/Default"]),
            id="with_sisorc_subcmd_flags_only",
        ),
        pytest.param(
            ["-gflag_tel"],
            {"ninja": ["-sflag_tel"]},
            ["ninja", "-C", "out/Default"],
            "ninja",
            True,
            {"SISO_PROJECT": "telemetry-project"},
            [
                "-gflag_tel",
                "ninja",
                "-sflag_tel",
                "-C",
                "out/Default",
                "--metrics_labels",
                f"type=developer,tool=siso,host_os={siso._SYSTEM_DICT.get(sys.platform, sys.platform)}",
                "--enable_cloud_monitoring",
                "--enable_cloud_profiler",
                "--enable_cloud_trace",
                "--enable_cloud_logging",
                "--metrics_project=telemetry-project",
            ],
            "depot_tools/siso.py: %s\n" % shlex.join(
                ["-gflag_tel", "ninja", "-sflag_tel", "-C", "out/Default"]),
            id="with_sisorc_global_and_subcmd_flags_and_telemetry",
        ),
        pytest.param(
            ["-gflag_non_ninja"],
            {"other_subcmd": ["-sflag_non_ninja"]},
            ["other_subcmd", "-C", "out/Default"],
            "other_subcmd",
            True,
            {"SISO_PROJECT": "telemetry-project"},
            [
                "-gflag_non_ninja",
                "other_subcmd",
                "-sflag_non_ninja",
                "-C",
                "out/Default",
            ],
            "depot_tools/siso.py: %s\n" % shlex.join([
                "-gflag_non_ninja",
                "other_subcmd",
                "-sflag_non_ninja",
                "-C",
                "out/Default",
            ]),
            id="with_sisorc_non_ninja_subcmd",
        ),
    ],
)
def test_process_args(
    global_flags: List[str],
    subcmd_flags: Dict[str, List[str]],
    args: List[str],
    subcmd: str,
    should_collect_logs: bool,
    env: Dict[str, str],
    want: List[str],
    want_stderr: str,
    siso_test_fixture: Any,
    mocker: Any,
) -> None:
    mock_stderr = mocker.patch("sys.stderr", new_callable=io.StringIO)
    got = siso._process_args(
        global_flags,
        subcmd_flags,
        args,
        subcmd,
        should_collect_logs,
        "siso_path",
        env,
    )
    assert got == want
    assert mock_stderr.getvalue() == want_stderr


# Else it won"t even compile on Windows.
if sys.platform != "win32":
    SIGKILL = siso.signal.SIGKILL  # pylint: disable=no-member
else:
    SIGKILL = None


@pytest.mark.skipif(sys.platform == "win32", reason="Not applicable on Windows")
@pytest.mark.parametrize(
    "stdout, stderr, returncode, kill_side_effect, expected_result, expected_kill_args",
    [
        pytest.param(
            b"123\n", b"", 0, None, True,
            (123, SIGKILL), id="found_and_killed"),
        pytest.param(
            b"",
            b"lsof: no process found\n",
            1,
            None,
            False,
            None,
            id="process_not_found",
        ),
        pytest.param(
            b"123\n",
            b"",
            0,
            OSError("Operation not permitted"),
            False,
            (123, SIGKILL),
            id="kill_fails",
        ),
        pytest.param(b"\n", b"", 0, None, False, None, id="no_pids_found"),
        pytest.param(
            b"0\n123\n456\n",
            b"",
            0,
            None,
            True,
            (123, SIGKILL),
            id="multiple_pids_found",
        ),
    ],
)
def test_kill_collector_posix(
    stdout: bytes,
    stderr: bytes,
    returncode: int,
    kill_side_effect: Optional[OSError],
    expected_result: bool,
    expected_kill_args: Optional[Tuple[int, Any]],
    mocker: Any,
) -> None:
    mocker.patch("sys.platform", new="linux")
    mock_os_kill = mocker.patch("siso.os.kill")
    mock_subprocess_run = mocker.patch("siso.subprocess.run")
    mock_subprocess_run.return_value = mocker.Mock(stdout=stdout,
                                                   stderr=stderr,
                                                   returncode=returncode)
    mock_os_kill.side_effect = kill_side_effect
    result = siso._kill_collector()
    assert result == expected_result
    mock_subprocess_run.assert_called_once_with(
        ["lsof", "-t", f"-i:{siso._OTLP_HEALTH_PORT}"], capture_output=True)
    if expected_kill_args:
        mock_os_kill.assert_called_once_with(*expected_kill_args)
    else:
        mock_os_kill.assert_not_called()


@pytest.mark.skipif(sys.platform != "win32", reason="Only for Windows")
@pytest.mark.parametrize(
    "run_effects, expected_result, expected_calls",
    [
        pytest.param(
            [
                (
                    f"  TCP    127.0.0.1:{siso._OTLP_HEALTH_PORT}        [::]:0                 LISTENING       1234\r\n"
                    .encode("utf-8"),
                    b"",
                    0,
                ),
                (b"", b"", 0),
            ],
            True,
            [
                ["netstat", "-aon"],
                ["taskkill", "/F", "/T", "/PID", "1234"],
            ],
            id="found_and_killed",
        ),
        pytest.param(
            [
                (
                    b"  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       868\r\n",
                    b"",
                    0,
                ),
            ],
            False,
            [["netstat", "-aon"]],
            id="process_not_found",
        ),
        pytest.param(
            [
                (
                    f"  TCP    127.0.0.1:{siso._OTLP_HEALTH_PORT}        [::]:0                 LISTENING       1234\r\n  TCP    127.0.0.1:{siso._OTLP_HEALTH_PORT}        [::]:0                 LISTENING       5678\r\n"
                    .encode("utf-8"),
                    b"",
                    0,
                ),
                (b"", b"", 0),
            ],
            True,
            [
                ["netstat", "-aon"],
                ["taskkill", "/F", "/T", "/PID", "1234"],
            ],
            id="multiple_pids_found",
        ),
        pytest.param(
            [
                (b"", b"netstat error\n", 1),
            ],
            False,
            [["netstat", "-aon"]],
            id="netstat_fails",
        ),
        pytest.param(
            [
                (
                    f"  TCP    127.0.0.1:{siso._OTLP_HEALTH_PORT}        [::]:0                 LISTENING       1234\r\n"
                    .encode("utf-8"),
                    b"",
                    0,
                ),
                (b"", b"ERROR: Cannot terminate process.", 1),
            ],
            False,
            [
                ["netstat", "-aon"],
                ["taskkill", "/F", "/T", "/PID", "1234"],
            ],
            id="taskkill_fails",
        ),
    ],
)
def test_kill_collector_windows(
    run_effects: List[Tuple[bytes, bytes, int]],
    expected_result: bool,
    expected_calls: List[List[str]],
    mocker: Any,
) -> None:
    mock_subprocess_run = mocker.patch("siso.subprocess.run")
    mock_subprocess_run.side_effect = [
        mocker.Mock(stdout=stdout, stderr=stderr, returncode=returncode)
        for stdout, stderr, returncode in run_effects
    ]
    result = siso._kill_collector()
    assert result == expected_result
    calls = [mocker.call(c, capture_output=True) for c in expected_calls]
    mock_subprocess_run.assert_has_calls(calls)
    assert mock_subprocess_run.call_count == len(calls)


@pytest.mark.parametrize(
    "platform, creationflags",
    [
        ("linux", 0),
        ("win32", 512),  # subprocess.CREATE_NEW_PROCESS_GROUP
    ],
)
def test_handle_collector_dead_then_healthy(
    siso_test_fixture: Any,
    platform: str,
    creationflags: int,
    start_collector_mocks: Dict[str, Any],
    mocker: Any,
) -> None:
    mocker.patch("sys.platform", new=platform)
    mocker.patch("subprocess.CREATE_NEW_PROCESS_GROUP",
                 creationflags,
                 create=True)
    mock_json_loads = mocker.patch("siso.json.loads")
    m = start_collector_mocks
    siso_path = "siso_path"
    project = "test-project"
    _configure_http_responses(
        mocker,
        m["mock_conn"],
        status_responses=[(404, None), (200, None)],
        config_responses=[(200, None)],
    )
    status_healthy = {"healthy": True, "status": "StatusOK"}
    if platform == "linux":
        endpoint = os.path.join("/tmp", "testuser", "siso", f"{project}.sock")
    else:
        endpoint = siso._OTLP_DEFAULT_TCP_ENDPOINT
    config = {
        "receivers": {
            "otlp": {
                "protocols": {
                    "grpc": {
                        "endpoint": endpoint
                    }
                }
            }
        }
    }
    mock_json_loads.side_effect = [status_healthy, config]
    env = {}
    args = ["--project", project]
    res_env = siso._handle_collector(siso_path, args, "ninja", env)
    assert res_env.get("SISO_COLLECTOR_ADDRESS")
    if platform == "linux":
        assert res_env["SISO_COLLECTOR_ADDRESS"] == f"unix://{endpoint}"
    else:
        assert res_env["SISO_COLLECTOR_ADDRESS"] == endpoint

    m["subprocess_popen"].assert_called_once_with(
        [siso_path, "collector", "--project", project],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=res_env,
        creationflags=creationflags,
    )
    m["kill_collector"].assert_not_called()


def test_handle_collector_unhealthy_then_healthy(siso_test_fixture: Any,
                                                 start_collector_mocks: Dict[
                                                     str, Any],
                                                 mocker: Any) -> None:
    mocker.patch("sys.platform", new="linux")
    mock_json_loads = mocker.patch("siso.json.loads")
    m = start_collector_mocks
    siso_path = "siso_path"
    project = "test-project"
    _configure_http_responses(
        mocker,
        m["mock_conn"],
        status_responses=[(200, None), (200, None)],
        config_responses=[(200, None), (200, None)],
    )
    status_unhealthy = {"healthy": False, "status": "NotOK"}
    status_healthy = {"healthy": True, "status": "StatusOK"}
    endpoint = os.path.join("/tmp", "testuser", "siso", f"{project}.sock")
    config_project_full = {
        "exporters": {
            "googlecloud": {
                "project": project
            }
        },
        "receivers": {
            "otlp": {
                "protocols": {
                    "grpc": {
                        "endpoint": endpoint
                    }
                }
            }
        },
    }
    mock_json_loads.side_effect = [
        status_unhealthy,
        status_healthy,
        config_project_full,
        config_project_full,
    ]
    env = {}
    args = ["--project", project]
    res_env = siso._handle_collector(siso_path, args, "ninja", env)
    assert res_env.get("SISO_COLLECTOR_ADDRESS") == f"unix://{endpoint}"

    m["subprocess_popen"].assert_called_once_with(
        [siso_path, "collector", "--project", project],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=res_env,
        creationflags=0,
    )
    m["kill_collector"].assert_called_once()


def test_handle_collector_already_healthy(siso_test_fixture: Any,
                                          start_collector_mocks: Dict[str, Any],
                                          mocker: Any) -> None:
    mocker.patch("sys.platform", new="linux")
    mock_json_loads = mocker.patch("siso.json.loads")
    m = start_collector_mocks
    siso_path = "siso_path"
    project = "test-project"
    _configure_http_responses(
        mocker,
        m["mock_conn"],
        status_responses=[(200, None)],
        config_responses=[(200, None), (200, None)],
    )
    status_healthy = {"healthy": True, "status": "StatusOK"}
    endpoint = os.path.join("/tmp", "testuser", "siso", f"{project}.sock")
    config_project_full = {
        "exporters": {
            "googlecloud": {
                "project": project
            }
        },
        "receivers": {
            "otlp": {
                "protocols": {
                    "grpc": {
                        "endpoint": endpoint
                    }
                }
            }
        },
    }
    mock_json_loads.side_effect = [
        status_healthy,
        config_project_full,
        config_project_full,
    ]
    env = {}
    args = ["--project", project]
    res_env = siso._handle_collector(siso_path, args, "ninja", env)
    assert res_env.get("SISO_COLLECTOR_ADDRESS") == f"unix://{endpoint}"
    m["subprocess_popen"].assert_not_called()
    m["kill_collector"].assert_not_called()


def test_handle_collector_never_healthy(siso_test_fixture: Any,
                                        start_collector_mocks: Dict[str, Any],
                                        mocker: Any) -> None:
    mocker.patch("sys.platform", new="linux")
    m = start_collector_mocks

    captured_env = {}

    def popen_side_effect(*args, **kwargs):
        nonlocal captured_env
        if "env" in kwargs:
            captured_env = kwargs["env"].copy()
        return mocker.Mock()

    m["subprocess_popen"].side_effect = popen_side_effect

    siso_path = "siso_path"
    project = "test-project"
    _configure_http_responses(mocker,
                              m["mock_conn"],
                              status_responses=[(404, None)])
    env = {}
    args = ["--project", project]
    res_env = siso._handle_collector(siso_path, args, "ninja", env)
    # If never healthy, handle_collector removes the address from env
    assert "SISO_COLLECTOR_ADDRESS" not in res_env

    endpoint = os.path.join("/tmp", "testuser", "siso", f"{project}.sock")
    expected_env = env.copy()
    expected_env["SISO_COLLECTOR_ADDRESS"] = f"unix://{endpoint}"

    assert captured_env == expected_env

    m["subprocess_popen"].assert_called_once()
    m["kill_collector"].assert_not_called()


@pytest.mark.parametrize(
    "expected_result, http_status_responses, json_loads_side_effect_values",
    [
        (
            True,
            [(404, None), (200, None)],
            ["status_healthy", "config_with_socket"],
        ),
        (
            True,
            [(404, None)] + [(404, None)] * 5 + [(200, None)],
            ["status_healthy", "config_with_socket"],
        ),
        (False, [(404, None)] * 30, []),
    ],
    ids=["healthy_immediately", "healthy_later", "never_healthy"],
)
def test_handle_collector_lifecycle(
    siso_test_fixture: Any,
    start_collector_mocks: Dict[str, Any],
    mocker: Any,
    expected_result: bool,
    http_status_responses: List[Tuple[int, Any]],
    json_loads_side_effect_values: List[str],
) -> None:
    mocker.patch("sys.platform", new="linux")
    mock_json_loads = mocker.patch("siso.json.loads")
    siso_path = "siso_path"
    project = "test-project"
    endpoint = os.path.join("/tmp", "testuser", "siso", f"{project}.sock")
    status_healthy = {"healthy": True, "status": "StatusOK"}
    config_with_socket = {
        "receivers": {
            "otlp": {
                "protocols": {
                    "grpc": {
                        "endpoint": endpoint
                    }
                }
            }
        }
    }
    json_loads_map = {
        "status_healthy": status_healthy,
        "config_with_socket": config_with_socket,
    }
    json_loads_side_effect = [
        json_loads_map[v] for v in json_loads_side_effect_values
    ]
    m = start_collector_mocks
    mock_json_loads.side_effect = json_loads_side_effect
    _configure_http_responses(
        mocker,
        m["mock_conn"],
        status_responses=list(http_status_responses),
        config_responses=[(200, None)] * 20,
    )

    captured_env = {}

    def popen_side_effect(*args, **kwargs):
        nonlocal captured_env
        if "env" in kwargs:
            captured_env = kwargs["env"].copy()
        return mocker.Mock()

    m["subprocess_popen"].side_effect = popen_side_effect

    env = {}
    args = ["--project", project]
    res_env = siso._handle_collector(siso_path, args, "ninja", env)

    if expected_result:
        assert res_env.get("SISO_COLLECTOR_ADDRESS") == f"unix://{endpoint}"
    else:
        assert "SISO_COLLECTOR_ADDRESS" not in res_env

    expected_env = env.copy()
    expected_env["SISO_COLLECTOR_ADDRESS"] = f"unix://{endpoint}"

    m["subprocess_popen"].assert_called_once()
    assert captured_env == expected_env

    if not expected_result:
        m["kill_collector"].assert_not_called()


@pytest.mark.skipif(sys.platform == "win32", reason="Not applicable on Windows")
def test_handle_collector_missing_sockets_file_appears_later(
    siso_test_fixture: Any,
    start_collector_mocks: Dict[str, Any],
    mocker: Any,
) -> None:
    mocker.patch("sys.platform", new="linux")

    socket_exists_vals = iter([False, False, True])

    def socket_file_sideeff(path: str) -> bool:
        if path.endswith(".sock"):
            return next(socket_exists_vals)
        return True

    mocker.patch("os.path.exists", side_effect=socket_file_sideeff)

    m = start_collector_mocks
    siso_path = "siso_path"
    project = "test-project"
    endpoint = os.path.join("/tmp", "testuser", "siso", f"{project}.sock")

    # Status: DEAD -> (Start) -> Loop 1 (200) -> Loop 2 (200)
    _configure_http_responses(
        mocker,
        m["mock_conn"],
        status_responses=[(404, None), (200, None), (200, None)],
        config_responses=[(200, None), (200, None)],
    )

    status_healthy = {"healthy": True, "status": "StatusOK"}
    config_with_socket = {
        "receivers": {
            "otlp": {
                "protocols": {
                    "grpc": {
                        "endpoint": endpoint
                    }
                }
            }
        }
    }

    mock_json_loads = mocker.patch("siso.json.loads")
    mock_json_loads.side_effect = [
        status_healthy, config_with_socket, status_healthy, config_with_socket
    ]

    env = {}
    args = ["--project", project]

    res_env = siso._handle_collector(siso_path, args, "ninja", env)

    assert res_env.get("SISO_COLLECTOR_ADDRESS") == f"unix://{endpoint}"


@pytest.mark.skipif(sys.platform == "win32", reason="Not applicable on Windows")
def test_handle_collector_missing_sockets_file_never_appears(
    siso_test_fixture: Any,
    start_collector_mocks: Dict[str, Any],
    mocker: Any,
) -> None:
    mocker.patch("sys.platform", new="linux")

    mocker.patch("os.path.exists", return_value=False)

    m = start_collector_mocks
    siso_path = "siso_path"
    project = "test-project"
    endpoint = os.path.join("/tmp", "testuser", "siso", f"{project}.sock")

    # Status: DEAD -> (Start) -> Loop 1..N (200)
    status_responses = [(404, None)] + [(200, None)] * 20
    config_responses = [(200, None)] * 20

    _configure_http_responses(
        mocker,
        m["mock_conn"],
        status_responses=status_responses,
        config_responses=config_responses,
    )

    status_healthy = {"healthy": True, "status": "StatusOK"}
    config_with_socket = {
        "receivers": {
            "otlp": {
                "protocols": {
                    "grpc": {
                        "endpoint": endpoint
                    }
                }
            }
        }
    }

    mock_json_loads = mocker.patch("siso.json.loads")
    mock_json_loads.side_effect = itertools.cycle(
        [status_healthy, config_with_socket])

    env = {}
    args = ["--project", project]

    res_env = siso._handle_collector(siso_path, args, "ninja", env)

    # Should fail to find socket file, so no address in env.
    assert "SISO_COLLECTOR_ADDRESS" not in res_env


# Stanza to have pytest be executed.
if __name__ == "__main__":
    sys.exit(pytest.main([__file__] + sys.argv[1:]))
