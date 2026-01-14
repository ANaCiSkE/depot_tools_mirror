#!/usr/bin/env python3
# Copyright 2024 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script is a wrapper around the siso binary that is pulled to
third_party as part of gclient sync. It will automatically find the siso
binary when run inside a gclient source tree, so users can just type
"siso" on the command line."""

import argparse
import getpass
import json
import http.client
import os
import sys
import shlex
import shutil
import signal
import subprocess
import time
from enum import Enum
from typing import Optional

import build_telemetry
import caffeinate
import gclient_paths


_SYSTEM_DICT = {"win32": "windows", "darwin": "mac", "linux": "linux"}
_OTLP_DEFAULT_TCP_ENDPOINT = "127.0.0.1:4317"
_OTLP_HEALTH_PORT = 13133


def parse_args(args: list[str]) -> tuple[str, str]:
    subcmd = ''
    out_dir = "."
    for i, arg in enumerate(args):
        if not arg.startswith("-") and not subcmd:
            subcmd = arg
            continue
        if arg == "-C":
            out_dir = args[i + 1]
        elif arg.startswith("-C"):
            out_dir = arg[2:]
    return subcmd, out_dir


# Fetch PID platform independently of possibly running collector
# and kill it.
# Return boolean whether the kill was successful or not.
def _kill_collector() -> bool:
    output: Optional[subprocess.CompletedProcess] = None
    pids = []
    if sys.platform in ["linux", "darwin"]:
        # Use lsof to find the PID of the process listening on the port.
        # The -t flag causes lsof to produce terse output with process
        # identifiers only.
        output = subprocess.run(['lsof', '-t', f'-i:{_OTLP_HEALTH_PORT}'],
                                capture_output=True)
        if output.returncode != 0:
            print(f"Warning: failed to fetch processes: {output.stderr}",
                  file=sys.stderr)
            return False
        # The output of lsof is a list of PIDs, separated by newlines.
        pids = [int(p) for p in output.stdout.decode('utf-8').strip().split()]
    elif sys.platform == "win32":
        output = subprocess.run(['netstat', '-aon'], capture_output=True)
        if output.returncode != 0:
            print(f"Warning: failed to fetch processes: {output.stderr}",
                  file=sys.stderr)
            return False
        result = output.stdout.decode('utf-8', errors='ignore')
        for line in result.splitlines():
            #  Result example:
            #  Proto  Local Address   Foreign Address     State        PID
            #  TCP    127.0.0.1:13133   0.0.0.0:0       LISTENING     34228
            parts = line.strip().split()
            if len(parts) < 4:
                continue
            if parts[1] != f'127.0.0.1:{_OTLP_HEALTH_PORT}':
                continue
            pids.append(int(parts[-1]))
    # Windows may return processes with PID 0, which is definitely not what we want.
    pids = [pid for pid in pids if pid != 0]
    if not pids:
        print(f"Warning: no processes detected taking {_OTLP_HEALTH_PORT}.",
              file=sys.stderr)
        return False
    # Take first process running on the given port - that's normally the only one.
    if len(pids) > 1:
        print(
            f"Warning: detected multiple processed taking {_OTLP_HEALTH_PORT}: {pids}. Stopping the first one fetched.",
            file=sys.stderr)
    pid = pids[0]
    if sys.platform in ["linux", "darwin"]:
        try:
            os.kill(pid, signal.SIGKILL)
            print(
                f"Killed the {pid} collector that takes {_OTLP_HEALTH_PORT} port."
            )
            return True
        except OSError as e:
            print(
                f"Warning: Failed to kill the {pid} collector that takes {_OTLP_HEALTH_PORT} port: {e}",
                file=sys.stderr)
            return False
    elif sys.platform == "win32":
        res = subprocess.run(['taskkill', '/F', '/T', '/PID', f"{pid}"],
                             capture_output=True)
        if res.returncode != 0:
            print(
                f"Warning: Failed to kill the {pid} collector that takes {_OTLP_HEALTH_PORT} port: {res.stderr}",
                file=sys.stderr)
            return False
        print(
            f"Killed the {pid} collector that takes {_OTLP_HEALTH_PORT} port.")
        return True
    return False


# Start collector when present.
# Returns boolean whether collector has started successfully.
def _start_collector(siso_path: str, expected_endpoint: str, project: str,
                     env: dict[str, str]) -> bool:
    class Status(Enum):
        HEALTHY = 1
        WRONG_ENDPOINT = 2
        UNHEALTHY = 3
        DEAD = 4
        MISSING_SOCKETS_FILE = 5

    def collector_status() -> Status:
        conn = http.client.HTTPConnection(f"localhost:{_OTLP_HEALTH_PORT}")
        try:
            conn.request("GET", "/health/status")
            response = conn.getresponse()
        except ConnectionError:
            return Status.DEAD

        if response.status != 200:
            return Status.DEAD

        status = json.loads(response.read())
        if not status["healthy"] or status["status"] != "StatusOK":
            return Status.UNHEALTHY
        endpoint = fetch_receiver_endpoint(conn)

        # Collector is liable to drop unix:// part from socks.
        if not expected_endpoint.endswith(endpoint):
            return Status.WRONG_ENDPOINT

        if expected_endpoint.startswith(
                "unix://") and not os.path.exists(endpoint):
            return Status.MISSING_SOCKETS_FILE
        return Status.HEALTHY

    def fetch_receiver_endpoint(conn: http.client.HTTPConnection) -> str:
        try:
            conn.request("GET", "/health/config")
            response = conn.getresponse()
        except ConnectionError:
            return ""
        resp_json = json.loads(response.read())
        try:
            return resp_json["receivers"]["otlp"]["protocols"]["grpc"][
                "endpoint"]
        except KeyError:
            return ""

    def start_collector() -> None:
        # Use Popen as it's non blocking.
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        cmd = [siso_path, "collector", "--project", project]
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
            creationflags=creationflags,
        )

    start = time.time()
    status = collector_status()
    if status == Status.HEALTHY:
        return True
    if status != Status.DEAD:
        if not _kill_collector():
            return False
    if os.path.exists(
            sockets_file := expected_endpoint.removeprefix("unix://")):
        try:
            os.remove(sockets_file)
        except OSError as e:
            print(f"Failed to remove {sockets_file} due to {e}. " +
                  "Having existing sockets file is known to cause " +
                  "permission issues among others. Not using collector.",
                  file=sys.stderr)
            return False

    start_collector()

    while time.time() - start < 1:
        status = collector_status()
        if status == Status.HEALTHY:
            return True
        # Non retriable error.
        if status == Status.WRONG_ENDPOINT:
            return False
        time.sleep(0.05)
    return False


def check_outdir(out_dir: str) -> None:
    ninja_marker = os.path.join(out_dir, ".ninja_deps")
    if os.path.exists(ninja_marker):
        print("depot_tools/siso.py: %s contains Ninja state file.\n"
              "Use `autoninja` to use reclient,\n"
              "or run `gn clean %s` to switch from ninja to siso\n" %
              (out_dir, out_dir),
              file=sys.stderr)
        sys.exit(1)


def apply_metrics_labels(args: list[str]) -> list[str]:
    user_system = _SYSTEM_DICT.get(sys.platform, sys.platform)

    # TODO(ovsienko) - add targets to the processing. For this, the Siso needs to understand lists.
    for arg in args[1:]:
        # Respect user provided labels, abort.
        if arg.startswith("--metrics_labels") or arg.startswith(
                "-metrics_labels"):
            return args

    result = []
    result.append("type=developer")
    result.append("tool=siso")
    result.append(f"host_os={user_system}")
    return args + ["--metrics_labels", ",".join(result)]


def apply_telemetry_flags(args: list[str], env: dict[str, str],
                          siso_path: str) -> list[str]:
    telemetry_flags = [
        "enable_cloud_monitoring", "enable_cloud_profiler",
        "enable_cloud_trace", "enable_cloud_logging"
    ]
    # Despite go.dev/issue/68312 being fixed, the issue is still reproducible
    # for googlers. Due to this, the flag is still applied while the
    # issue is being investigated.
    env.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
    flags_to_add = []
    for flag in telemetry_flags:
        found = False
        for arg in args:
            if (arg == f"-{flag}" or arg == f"--{flag}"
                    or arg.startswith(f"-{flag}=")
                    or arg.startswith(f"--{flag}=")):
                found = True
                break
        if not found:
            flags_to_add.append(f"--{flag}")

    # This is a temporary measure as on new siso versions metrics_project
    # gets set the same as project by default.
    # TODO: remove this code after we make sure all clients are using new siso versions.

    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-metrics_project", "--metrics_project")
    parser.add_argument("-project", "--project")
    metrics_env_var = "RBE_metrics_project"
    project_env_var = "SISO_PROJECT"
    # If metrics env variable is set, add flags and return.
    if metrics_env_var in env:
        return args + flags_to_add
    # Check if metrics project is set. If so, then add flags and return.
    known_args, _ = parser.parse_known_args(args)
    if known_args.metrics_project:
        return args + flags_to_add
    if known_args.project:
        return args + flags_to_add + [f"--metrics_project={known_args.project}"]
    if project_env_var in env:
        return args + flags_to_add + [f"--metrics_project={env[project_env_var]}"]
    # Default case - no flags are set, so don't add any
    return args


def _fetch_metrics_project(args: list[str], env: dict[str, str]) -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-metrics_project", "--metrics_project")
    parser.add_argument("-project", "--project")
    metrics_env_var = "RBE_metrics_project"
    project_env_var = "SISO_PROJECT"
    known_args, _ = parser.parse_known_args(args)
    if known_args.metrics_project:
        return known_args.metrics_project
    if known_args.project:
        return known_args.project
    if metrics_env_var in env:
        return env[metrics_env_var]
    if project_env_var in env:
        return env[project_env_var]
    return ""


def _resolve_sockets_folder(env: dict[str, str]) -> tuple[str, int]:
    path = "/tmp"
    user = getpass.getuser()
    if sys.platform == "linux":
        path = env.get("XDG_RUNTIME_DIR", "/tmp")
    elif sys.platform == "darwin":
        path = env.get("TMPDIR", "/tmp")
    path = os.path.join(path, user, "siso")
    # socks path sizes are severely limited.
    # Linux SHOULD be 108 but we will got with conservative MacOS number.
    # 6 is for .sock + /
    allowed_length = 104 - len(path) - 6
    if allowed_length < 1:
        path = os.path.join("/tmp", user, "siso")
        allowed_length = 104 - len(path) - 6
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path, allowed_length


def _handle_collector(siso_path: str, args: list[str],
                      env: dict[str, str]) -> dict[str, str]:
    project = _fetch_metrics_project(args, env)
    lenv = env.copy()
    if not project:
        return lenv
    if sys.platform in ["darwin", "linux"]:
        path, remainder_len = _resolve_sockets_folder(env)
        sockets_file = os.path.join(path, f"{project[:remainder_len]}.sock")
        expected_endpoint = f"unix://{sockets_file}"
    else:
        expected_endpoint = _OTLP_DEFAULT_TCP_ENDPOINT
    lenv["SISO_COLLECTOR_ADDRESS"] = expected_endpoint
    started = _start_collector(siso_path, expected_endpoint, project, lenv)
    if not started:
        print("Collector never came to life", file=sys.stderr)
        lenv.pop("SISO_COLLECTOR_ADDRESS", None)
    return lenv


def load_sisorc(rcfile: str) -> tuple[list[str], dict[str, list[str]]]:
    if not os.path.exists(rcfile):
        return [], {}
    global_flags = []
    subcmd_flags = {}
    with open(rcfile) as file:
        for line in file:
            line = line.strip()
            if line.startswith("#"):
                continue
            args = shlex.split(line)
            if len(args) == 0:
                continue
            if line.startswith("-"):
                global_flags.extend(args)
                continue
            subcmd_flags[args[0]] = args[1:]
    return global_flags, subcmd_flags


def apply_sisorc(global_flags: list[str], subcmd_flags: dict[str, list[str]],
                 args: list[str], subcmd: str) -> list[str]:
    new_args = []
    for arg in args:
        if not new_args:
            new_args.extend(global_flags)
        if arg == subcmd:
            new_args.append(arg)
            new_args.extend(subcmd_flags.get(arg, []))
            continue
        new_args.append(arg)
    return new_args


def _fix_system_limits() -> None:
    # On macOS and most Linux distributions, the default limit of open file
    # descriptors is too low (256 and 1024, respectively).
    # This causes a large j value to result in 'Too many open files' errors.
    # Check whether the limit can be raised to a large enough value. If yes,
    # use `resource.setrlimit` to increase the limit when running ninja.
    if sys.platform in ["darwin", "linux"]:
        import resource

        # Increase the number of allowed open file descriptors to the maximum.
        fileno_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        if fileno_limit < hard_limit:
            try:
                resource.setrlimit(resource.RLIMIT_NOFILE,
                                   (hard_limit, hard_limit))
            except Exception:
                pass


# Utility function to produce actual command line flags for Siso.
def _process_args(global_flags: list[str], subcmd_flags: dict[str, list[str]],
                  args: list[str], subcmd: str, should_collect_logs: bool,
                  siso_path: str, env: dict[str, str]) -> list[str]:
    new_args = apply_sisorc(global_flags, subcmd_flags, args, subcmd)
    if args != new_args:
        print('depot_tools/siso.py: %s' % shlex.join(new_args), file=sys.stderr)
    # Add ninja specific flags.
    if subcmd == "ninja":
        new_args = apply_metrics_labels(new_args)
        if should_collect_logs:
            new_args = apply_telemetry_flags(new_args, env, siso_path)
    return new_args


def _is_google_corp_machine() -> bool:
    """This assumes that corp machine has gcert binary in known location."""
    return shutil.which("gcert") is not None


def main(args: list[str],
         telemetry_cfg: Optional[build_telemetry.Config] = None):
    # Do not raise KeyboardInterrupt on SIGINT so as to give siso time to run
    # cleanup tasks. Siso will be terminated immediately after the second
    # Ctrl-C.
    original_sigint_handler = signal.getsignal(signal.SIGINT)
    if not telemetry_cfg:
        telemetry_cfg = build_telemetry.load_config()
    should_collect_logs = telemetry_cfg.enabled()

    _fix_system_limits()

    def _ignore(signum, frame):
        try:
            # Call the original signal handler.
            original_sigint_handler(signum, frame)  # type: ignore
        except KeyboardInterrupt:
            # Do not reraise KeyboardInterrupt so as to not kill siso too early.
            pass

    signal.signal(signal.SIGINT, _ignore)

    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, lambda signum, frame: None)

    # On Windows the siso.bat script passes along the arguments enclosed in
    # double quotes. This prevents multiple levels of parsing of the special '^'
    # characters needed when compiling a single file.  When this case is
    # detected, we need to split the argument. This means that arguments
    # containing actual spaces are not supported by siso.bat, but that is not a
    # real limitation.
    if sys.platform == "win32" and len(args) == 2:
        args = args[:1] + args[1].split()

    # macOS's python sets CPATH, LIBRARY_PATH, SDKROOT implicitly.
    # https://openradar.appspot.com/radar?id=5608755232243712
    #
    # Removing those environment variables to avoid affecting clang's behaviors.
    if sys.platform == 'darwin':
        os.environ.pop("CPATH", None)
        os.environ.pop("LIBRARY_PATH", None)
        os.environ.pop("SDKROOT", None)

    # if user doesn't set PYTHONPYCACHEPREFIX and PYTHONDONTWRITEBYTECODE
    # set PYTHONDONTWRITEBYTECODE=1 not to create many *.pyc in workspace
    # and keep workspace clean.
    if not os.environ.get("PYTHONPYCACHEPREFIX"):
        os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

    env = os.environ.copy()

    subcmd, out_dir = parse_args(args[1:])

    # Get gclient root + src.
    primary_solution_path = gclient_paths.GetPrimarySolutionPath(out_dir)
    gclient_root_path = gclient_paths.FindGclientRoot(out_dir)
    gclient_src_root_path = None
    if gclient_root_path:
        gclient_src_root_path = os.path.join(gclient_root_path, 'src')

    siso_override_path = os.environ.get('SISO_PATH')
    if siso_override_path:
        print('depot_tools/siso.py: Using Siso binary from SISO_PATH: %s.' %
              siso_override_path,
              file=sys.stderr)
        if not os.path.isfile(siso_override_path):
            print(
                'depot_tools/siso.py: Could not find Siso at provided '
                'SISO_PATH.',
                file=sys.stderr)
            return 1

    for base_path in set(
        [primary_solution_path, gclient_root_path, gclient_src_root_path]):
        if not base_path:
            continue
        sisoenv_path = os.path.join(base_path, 'build', 'config', 'siso',
                                    '.sisoenv')
        if not os.path.exists(sisoenv_path):
            continue
        with open(sisoenv_path) as f:
            for line in f.readlines():
                k, v = line.rstrip().split('=', 1)
                env[k] = v
        backend_config_dir = os.path.join(base_path, 'build', 'config', 'siso',
                                          'backend_config')
        if os.path.exists(backend_config_dir) and not os.path.exists(
                os.path.join(backend_config_dir, 'backend.star')):
            if _is_google_corp_machine():
                print(
                    'build/config/siso/backend_config/backend.star does not '
                    'exist.\n'
                    'backend.star is configured by gclient hook '
                    'build/config/siso/configure_siso.py.\n'
                    'Make sure `rbe_instance` gclient custom vars is correct.\n'
                    'Did you run `gclient runhooks` ?',
                    file=sys.stderr)
            else:
                print(
                    'build/config/siso/backend_config/backend.star does not '
                    'exist.\n'
                    'See build/config/siso/backend_config/README.md',
                    file=sys.stderr)
            return 1
        global_flags, subcmd_flags = load_sisorc(
            os.path.join(base_path, 'build', 'config', 'siso', '.sisorc'))
        siso_paths = [
            siso_override_path,
            os.path.join(base_path, 'third_party', 'siso', 'cipd',
                         'siso' + gclient_paths.GetExeSuffix()),
            os.path.join(base_path, 'third_party', 'siso',
                         'siso' + gclient_paths.GetExeSuffix()),
        ]
        for siso_path in siso_paths:
            if siso_path and os.path.isfile(siso_path):
                processed_args = _process_args(global_flags, subcmd_flags,
                                               args[1:], subcmd,
                                               should_collect_logs, siso_path,
                                               env)
                if should_collect_logs and {"-h", "--help", "-help"
                                            }.isdisjoint(processed_args):
                    env = _handle_collector(siso_path, processed_args, env)
                check_outdir(out_dir)
                return caffeinate.call([siso_path] + processed_args, env=env)
        print(
            'depot_tools/siso.py: Could not find siso in third_party/siso '
            'of the current project. Did you run gclient sync?',
            file=sys.stderr)
        return 1
    if siso_override_path:
        return caffeinate.call([siso_override_path] + args[1:], env=env)

    print(
        'depot_tools/siso.py: Could not find .sisoenv under build/config/siso '
        'of the current project. Did you run gclient sync?',
        file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
