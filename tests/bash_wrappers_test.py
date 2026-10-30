#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for bash wrappers that exec CIPD binaries installed in .cipd_bin.

In git-bash (MinGW) and Cygwin, these wrappers must exec the CIPD binary
directly rather than routing "$@" through cmd.exe or a .bat file, which would
re-parse the command line with cmd.exe shell grammar (b/557826663).
"""

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Wrappers that exec "$CIPD_ROOT/<name>" after running `cipd_bin_setup`.
CIPD_WRAPPERS = (
    "crowbar",
    "git-credential-luci",
    "luci-auth-ssh-helper",
    "luci-auth-ssh-plugin",
    "vpython3",
)

# `uname -s` output of the emulated platforms.
UNAME_S = {
    "linux": "Linux",
    "darwin": "Darwin",
    "mingw": "MINGW64_NT-10.0-19045",
    "cygwin": "CYGWIN_NT-10.0-19045",
}

# Arguments with characters that cmd.exe interprets. MSYS and Cygwin only quote
# arguments that are empty or contain whitespace or `"`, so most of these would
# reach cmd.exe unquoted if routed through a .bat wrapper.
ARGS = [
    "docs/notes&evil.bat&x.md",
    "a|b",
    "a^b",
    "<in",
    ">out",
    "(x)",
    "%PATH%",
    "!PATH!",
    "*",
    "a;b",
    "$(id)",
    "`id`",
    "with space",
    'with"quote',
    "",
]


def _write_file(path: str, content: str, *, executable: bool = True) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    if executable:
        os.chmod(path, 0o755)


def _fake_program(label: str) -> str:
    """Returns a script that prints `label`, DEPOT_TOOLS_DIR, and its args."""
    return (
        "#!/usr/bin/env bash\n"
        f"printf '%s\\0' {shlex.quote(label)} "
        '"${DEPOT_TOOLS_DIR-<unset>}" "$@"\n'
        'exit "${FAKE_EXIT:-0}"\n'
    )


@unittest.skipIf(sys.platform == "win32", "POSIX bash wrapper test")
class BashWrappersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="depot_tools_wrappers_")
        self.addCleanup(shutil.rmtree, self.tmpdir)
        # Include a space in the directory name to catch unquoted paths.
        self.dt_dir = os.path.join(self.tmpdir, "depot tools")
        self.cipd_bin = os.path.join(self.dt_dir, ".cipd_bin")
        self.fake_bin = os.path.join(self.tmpdir, "fake_bin")
        self.cmd_exe_log = os.path.join(self.tmpdir, "cmd_exe.log")
        self.cipd_log = os.path.join(self.tmpdir, "cipd.log")
        os.makedirs(self.cipd_bin)
        os.makedirs(self.fake_bin)

        for name in (*CIPD_WRAPPERS, "cipd_bin_setup.sh"):
            shutil.copy2(os.path.join(ROOT_DIR, name), self.dt_dir)
        for name in CIPD_WRAPPERS:
            _write_file(
                os.path.join(self.cipd_bin, name), _fake_program("default")
            )

        # Populate inputs for `cipd_bin_setup` and a fake `cipd` script so
        # `cipd_bin_setup` never touches the network. Like the real client on
        # Cygwin (which echoes its command line), the fake writes to stdout,
        # which must not leak into the CIPD root that `cipd_bin_setup` prints.
        for name in (
            "cipd_manifest.txt",
            "cipd_manifest.versions",
            "cipd_client_version",
        ):
            _write_file(
                os.path.join(self.dt_dir, name),
                f"{name}\n",
                executable=False,
            )
        _write_file(
            os.path.join(self.dt_dir, "cipd"),
            f'echo "$*" >> {shlex.quote(self.cipd_log)}\n'
            "echo cipd-ensure-stdout\n"
            "exit 0\n",
            executable=False,
        )

        # Plant canary `cmd.exe`, `evil.bat`, and `<wrapper>.bat` scripts that
        # record and fail if they are ever invoked.
        record_and_fail = (
            "#!/bin/sh\n"
            f'echo "$0 $*" >> {shlex.quote(self.cmd_exe_log)}\n'
            "exit 99\n"
        )
        _write_file(os.path.join(self.fake_bin, "cmd.exe"), record_and_fail)
        _write_file(os.path.join(self.fake_bin, "evil.bat"), record_and_fail)
        for name in CIPD_WRAPPERS:
            _write_file(
                os.path.join(self.dt_dir, f"{name}.bat"), record_and_fail
            )
            _write_file(
                os.path.join(self.fake_bin, f"{name}.bat"), record_and_fail
            )

        # On Cygwin, `cipd_bin_setup` converts paths with `cygpath -w`. Like
        # the real one, print each argument on its own line, so an unquoted
        # (word-split) path containing a space yields a multi-line result.
        _write_file(
            os.path.join(self.fake_bin, "cygpath"),
            '#!/bin/sh\n[ "$1" = -w ] && shift\nprintf "%s\\n" "$@"\n',
        )

    def _run(
        self,
        name: str,
        args: list[str],
        platform: str = "mingw",
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        """Runs depot_tools wrapper `name` (or an absolute path) with `args`."""
        if os.path.exists(self.cmd_exe_log):
            os.remove(self.cmd_exe_log)
        _write_file(
            os.path.join(self.fake_bin, "uname"),
            f"#!/bin/sh\necho {shlex.quote(UNAME_S[platform])}\n",
        )
        run_env = os.environ.copy()
        # Clear variables exported by depot_tools wrappers (e.g. if this test
        # itself is run via vpython3).
        for var in ("DEPOT_TOOLS_DIR", "DEPOT_TOOLS_UNAME_S", "VPYTHON_BYPASS"):
            run_env.pop(var, None)
        run_env["PATH"] = os.pathsep.join(
            [self.fake_bin, self.dt_dir, run_env.get("PATH", "")]
        )
        if env:
            run_env.update(env)
        return subprocess.run(
            [os.path.join(self.dt_dir, name), *args],
            capture_output=True,
            env=run_env,
            cwd=self.tmpdir,
            check=False,
        )

    def _assert_no_cmd_exe(self) -> None:
        log = ""
        if os.path.exists(self.cmd_exe_log):
            with open(self.cmd_exe_log, encoding="utf-8") as f:
                log = f.read()
        self.assertEqual(log, "", f"arguments were passed to cmd.exe: {log}")

    def _assert_ran(
        self,
        res: subprocess.CompletedProcess[bytes],
        expected_label: str,
        expected_args: list[str],
    ) -> None:
        self._assert_no_cmd_exe()
        stderr = res.stderr.decode("utf-8", "replace")
        self.assertEqual(res.returncode, 0, stderr)
        fields = res.stdout.decode("utf-8").split("\0")
        self.assertEqual(
            fields,
            [expected_label, "<unset>", *expected_args, ""],
            stderr,
        )

    def test_cipd_wrappers_pass_args_verbatim(self) -> None:
        for name in CIPD_WRAPPERS:
            for platform in UNAME_S:
                with self.subTest(name=name, platform=platform):
                    res = self._run(name, ARGS, platform)
                    self._assert_ran(res, "default", ARGS)

    def test_exit_code_is_propagated(self) -> None:
        for name in CIPD_WRAPPERS:
            for platform in ("mingw", "cygwin"):
                with self.subTest(name=name, platform=platform):
                    res = self._run(
                        name, ["x"], platform=platform, env={"FAKE_EXIT": "42"}
                    )
                    self.assertEqual(res.returncode, 42, res.stderr)
                    self._assert_no_cmd_exe()

    def test_missing_binary_does_not_fall_back_to_cmd_exe(self) -> None:
        for name in CIPD_WRAPPERS:
            with self.subTest(name=name):
                os.remove(os.path.join(self.cipd_bin, name))
                res = self._run(name, ARGS)
                self.assertNotEqual(res.returncode, 0)
                self._assert_no_cmd_exe()

    def test_cipd_client_root_override(self) -> None:
        alt_root = os.path.join(self.tmpdir, "alt root")
        for name in CIPD_WRAPPERS:
            _write_file(os.path.join(alt_root, name), _fake_program("override"))
        _write_file(
            os.path.join(self.dt_dir, ".cipd_client_root"),
            f"{alt_root}\n",
            executable=False,
        )
        for name in CIPD_WRAPPERS:
            for platform in UNAME_S:
                with self.subTest(name=name, platform=platform):
                    res = self._run(name, ARGS, platform)
                    self._assert_ran(res, "override", ARGS)

    def test_windows_style_path_in_argv0(self) -> None:
        # git.exe launches these scripts with a Windows-style path in $0 (e.g.
        # `C:\depot_tools\git-credential-luci`, b/410753790). Emulate this with
        # a symlink whose file name contains backslashes, run from outside
        # depot_tools, so `dirname` only finds depot_tools if `\` is handled.
        for name in CIPD_WRAPPERS:
            with self.subTest(name=name):
                link = os.path.join(self.tmpdir, f"depot tools\\{name}")
                os.symlink(os.path.join(self.dt_dir, name), link)
                res = self._run(link, ARGS)
                self._assert_ran(res, "default", ARGS)

    def test_cipd_bin_setup_sourced_via_windows_style_path(self) -> None:
        # Without DEPOT_TOOLS_DIR, `cipd_bin_setup` falls back to its own
        # ${BASH_SOURCE[0]}; its stdout must be exactly the CIPD root.
        link = os.path.join(self.tmpdir, "depot tools\\cipd_bin_setup.sh")
        os.symlink(os.path.join(self.dt_dir, "cipd_bin_setup.sh"), link)
        driver = os.path.join(self.tmpdir, "driver")
        _write_file(
            driver,
            "#!/usr/bin/env bash\n"
            f"source {shlex.quote(link)} && cipd_bin_setup\n",
        )
        res = self._run(driver, [])
        self.assertEqual(res.stdout, f"{self.cipd_bin}\n".encode(), res.stderr)

    def test_cipd_ensure_result_is_cached(self) -> None:
        cache_dir = os.path.join(self.cipd_bin, ".cipd")
        for platform in UNAME_S:
            with self.subTest(platform=platform):
                shutil.rmtree(cache_dir, ignore_errors=True)
                _write_file(self.cipd_log, "", executable=False)
                for _ in range(2):
                    res = self._run("vpython3", ["x"], platform)
                    self._assert_ran(res, "default", ["x"])
                with open(self.cipd_log, encoding="utf-8") as f:
                    cipd_runs = f.read().splitlines()
                self.assertEqual(len(cipd_runs), 1, cipd_runs)

    def test_vpython3_appends_depot_tools_to_path(self) -> None:
        _write_file(
            os.path.join(self.cipd_bin, "vpython3"),
            '#!/usr/bin/env bash\nprintf "%s" "$PATH"\n',
        )
        rel_vpython3 = os.path.relpath(
            os.path.join(self.dt_dir, "vpython3"), self.tmpdir
        )
        run_env = os.environ.copy()
        for var in ("DEPOT_TOOLS_DIR", "DEPOT_TOOLS_UNAME_S", "VPYTHON_BYPASS"):
            run_env.pop(var, None)
        run_env["PATH"] = os.pathsep.join([self.fake_bin, "/usr/bin", "/bin"])
        res = subprocess.run(
            [rel_vpython3],
            capture_output=True,
            env=run_env,
            cwd=self.tmpdir,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        path_entries = res.stdout.decode("utf-8").split(os.pathsep)
        self.assertEqual(path_entries[0], self.fake_bin)
        self.assertEqual(path_entries[-1], os.path.realpath(self.dt_dir))


class NoCmdExeArgvForwardingTest(unittest.TestCase):
    """Guards against bash scripts passing "$@" to cmd.exe or a .bat file."""

    # TODO(b/557826663): evaluate and fix these remaining build wrappers, then
    # remove them from this allowlist.
    KNOWN_OFFENDERS = frozenset({"autoninja", "gn"})

    SHEBANG_RE = re.compile(rb"^#!.*\b(ba)?sh\b")
    # Matches a non-comment line passing the script's arguments ($@, $*, ${@},
    # ...) to a .bat/.cmd file or to cmd.exe.
    FORWARDING_RE = re.compile(
        r"^[^#\n]*(\.(bat|cmd)\b|\bcmd(\.exe)?\s+//?c\b)[^\n]*\$\{?[@*]",
        re.MULTILINE | re.IGNORECASE,
    )

    def test_no_bash_wrapper_forwards_argv_through_cmd_exe(self) -> None:
        offenders = set()
        for name in sorted(os.listdir(ROOT_DIR)):
            path = os.path.join(ROOT_DIR, name)
            if not os.path.isfile(path):
                continue
            with open(path, "rb") as f:
                # Sourced helpers like python_runner.sh have no shebang.
                first_line = f.readline(256)
                if not (
                    name.endswith(".sh") or self.SHEBANG_RE.match(first_line)
                ):
                    continue
                content = (first_line + f.read()).decode(
                    "utf-8", errors="replace"
                )
            if self.FORWARDING_RE.search(content):
                offenders.add(name)
        self.assertEqual(
            offenders,
            self.KNOWN_OFFENDERS,
            'Bash wrappers must exec the target binary directly; passing "$@" '
            "to cmd.exe or a .bat file lets cmd.exe re-parse it as shell "
            "syntax (b/557826663). Update KNOWN_OFFENDERS only when fixing "
            "one of them.",
        )


if __name__ == "__main__":
    unittest.main()
