#!/usr/bin/env vpython3
# Copyright 2014 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test gsutil.py."""

import base64
import hashlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from types import FrameType
from typing import Any, Callable, Optional
import unittest
from unittest import mock
import urllib.request
import zipfile

# Add depot_tools to path
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEPOT_TOOLS_DIR = os.path.dirname(THIS_DIR)
sys.path.append(DEPOT_TOOLS_DIR)

import gsutil  # noqa: E402


class TestError(Exception):
    pass


class FakeCall(object):
    def __init__(self):
        self.expectations = []

    def add_expectation(self, *args, **kwargs):
        returns = kwargs.pop("_returns", None)
        self.expectations.append((args, kwargs, returns))

    def __call__(self, *args, **kwargs):
        if not self.expectations:
            raise TestError("Got unexpected\n%s\n%s" % (args, kwargs))
        exp_args, exp_kwargs, exp_returns = self.expectations.pop(0)
        if args != exp_args or kwargs != exp_kwargs:
            message = "Expected:\n  args: %s\n  kwargs: %s\n" % (
                exp_args,
                exp_kwargs,
            )
            message += "Got:\n  args: %s\n  kwargs: %s\n" % (args, kwargs)
            raise TestError(message)
        return exp_returns


class MockResponse(io.BytesIO):
    def info(self):
        # urlretrieve expects info() to return a dictionary.
        return {}


class GsutilUnitTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeCall()
        self.tempdir = tempfile.mkdtemp()
        self.old_urlopen = getattr(urllib.request, "urlopen")
        self.old_call = getattr(subprocess, "call")
        setattr(urllib.request, "urlopen", self.fake)
        setattr(subprocess, "call", self.fake)

    def tearDown(self):
        self.assertEqual(self.fake.expectations, [])
        shutil.rmtree(self.tempdir)
        setattr(urllib.request, "urlopen", self.old_urlopen)
        setattr(subprocess, "call", self.old_call)

    def add_md5_expectation(self, url, data):
        md5_calc = hashlib.md5()
        md5_calc.update(data)
        b64_md5 = base64.b64encode(md5_calc.digest()).decode("utf-8")
        response_data = json.dumps({"md5Hash": b64_md5}).encode("utf-8")
        self.fake.add_expectation(url, _returns=MockResponse(response_data))

    def add_file_expectation(self, url, data):
        self.fake.add_expectation(url, None, _returns=MockResponse(data))

    def test_download_gsutil(self):
        version = gsutil.VERSION
        filename = "gsutil_%s.zip" % version
        full_filename = os.path.join(self.tempdir, filename)
        fake_file = b"This is gsutil.zip"
        fake_file2 = b"This is other gsutil.zip"
        metadata_url = gsutil.API_URL + filename
        url = gsutil.GSUTIL_URL + filename

        # The md5 is valid, so download_gsutil should download the file.
        self.add_md5_expectation(metadata_url, fake_file)
        self.add_file_expectation(url, fake_file)
        self.assertEqual(
            gsutil.download_gsutil(version, self.tempdir), full_filename
        )
        with open(full_filename, "rb") as f:
            self.assertEqual(fake_file, f.read())
        self.assertEqual(self.fake.expectations, [])

        # The md5 is valid, so download_gsutil should use the existing file.
        self.add_md5_expectation(metadata_url, fake_file)
        self.assertEqual(
            gsutil.download_gsutil(version, self.tempdir), full_filename
        )
        with open(full_filename, "rb") as f:
            self.assertEqual(fake_file, f.read())
        self.assertEqual(self.fake.expectations, [])

        # The md5 is invalid for a new file, so download_gsutil should raise an
        # error.
        self.add_md5_expectation(metadata_url, b"aaaaaaa")
        self.add_file_expectation(url, fake_file2)
        self.assertRaises(
            gsutil.InvalidGsutilError,
            gsutil.download_gsutil,
            version,
            self.tempdir,
        )
        self.assertEqual(self.fake.expectations, [])

        # The md5 is valid and the new file is already downloaded, so it should
        # be used without downloading again.
        self.add_md5_expectation(metadata_url, fake_file2)
        self.assertEqual(
            gsutil.download_gsutil(version, self.tempdir), full_filename
        )
        with open(full_filename, "rb") as f:
            self.assertEqual(fake_file2, f.read())
        self.assertEqual(self.fake.expectations, [])

    def test_ensure_gsutil_full(self):
        version = gsutil.VERSION
        gsutil_dir = os.path.join(self.tempdir, "gsutil_%s" % version, "gsutil")
        gsutil_bin = os.path.join(gsutil_dir, "gsutil")
        gsutil_flag = os.path.join(gsutil_dir, "install.flag")
        os.makedirs(gsutil_dir)

        zip_filename = "gsutil_%s.zip" % version
        metadata_url = gsutil.API_URL + zip_filename
        url = gsutil.GSUTIL_URL + zip_filename
        _, tempzip = tempfile.mkstemp()
        fake_gsutil = "Fake gsutil"
        with zipfile.ZipFile(tempzip, "w") as zf:
            zf.writestr("gsutil/gsutil", fake_gsutil)
        with open(tempzip, "rb") as f:
            fake_file = f.read()
            self.add_md5_expectation(metadata_url, fake_file)
            self.add_file_expectation(url, fake_file)

        # This should write the gsutil_bin with 'Fake gsutil'
        gsutil.ensure_gsutil(version, self.tempdir, False)
        self.assertTrue(os.path.exists(gsutil_bin))
        with open(gsutil_bin, "r") as f:
            self.assertEqual(f.read(), fake_gsutil)
        self.assertTrue(os.path.exists(gsutil_flag))
        self.assertEqual(self.fake.expectations, [])

    def test_ensure_gsutil_short(self):
        version = gsutil.VERSION
        gsutil_dir = os.path.join(self.tempdir, "gsutil_%s" % version, "gsutil")
        gsutil_bin = os.path.join(gsutil_dir, "gsutil")
        gsutil_flag = os.path.join(gsutil_dir, "install.flag")
        os.makedirs(gsutil_dir)

        with open(gsutil_bin, "w") as f:
            f.write("Foobar")
        with open(gsutil_flag, "w") as f:
            f.write("Barbaz")
        self.assertEqual(
            gsutil.ensure_gsutil(version, self.tempdir, False), gsutil_bin
        )

    @mock.patch("sys.platform", "linux")
    def test__is_supported_platform_returns_true_for_supported_platform(self):
        self.assertTrue(gsutil._is_luci_auth_supported_platform())

    @mock.patch("sys.platform", "aix")
    def test__is_supported_platform_returns_false_for_unsupported_platform(
        self,
    ):
        self.assertFalse(gsutil._is_luci_auth_supported_platform())

    @mock.patch("signal.SIGKILL", 9, create=True)
    @mock.patch("gsutil.IS_WINDOWS", False)
    def test__run_subprocess_forwards_sigterm(self) -> None:
        mock_proc = mock.MagicMock()
        mock_proc.__enter__.return_value = mock_proc
        mock_proc.pid = 12345
        mock_proc.returncode = -signal.SIGKILL

        captured_handler: dict[
            str, Callable[[int, Optional[FrameType]], Any]
        ] = {}

        def fake_communicate() -> tuple[bytes, bytes]:
            captured_handler["handler"](signal.SIGTERM, None)
            return (b"out", b"err")

        mock_proc.communicate.side_effect = fake_communicate

        orig_signal = signal.getsignal(signal.SIGTERM)

        def fake_signal(sig: int, handler: Any) -> Any:
            if sig == signal.SIGTERM and callable(handler):
                captured_handler["handler"] = handler
            return orig_signal

        with (
            mock.patch(
                "subprocess.Popen", return_value=mock_proc
            ) as mock_popen,
            mock.patch("os.killpg", create=True) as mock_killpg,
            mock.patch("signal.signal", side_effect=fake_signal) as mock_sig,
            self.assertRaises(SystemExit) as cm,
        ):
            gsutil._run_subprocess(["fake_cmd"])

        self.assertEqual(cm.exception.code, 128 + signal.SIGTERM)
        mock_popen.assert_called_once_with(
            ["fake_cmd"],
            shell=False,
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        mock_killpg.assert_called_once_with(12345, signal.SIGKILL)
        self.assertEqual(mock_sig.call_count, 2)
        self.assertEqual(
            mock_sig.call_args_list[1], mock.call(signal.SIGTERM, orig_signal)
        )


def _mock_popen(returncode: int = 0) -> Any:
    """Returns a patcher for subprocess.Popen that doesn't run anything."""
    proc = mock.MagicMock()
    proc.__enter__.return_value = proc
    proc.communicate.return_value = (b"", b"")
    proc.returncode = returncode
    return mock.patch("subprocess.Popen", return_value=proc)


class CipdExeTest(unittest.TestCase):
    """Tests running depot_tools' CIPD tools without their .bat wrappers."""

    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)
        self.cipd_bin = os.path.join(self.tempdir, ".cipd_bin")
        os.mkdir(self.cipd_bin)
        self._write_cipd_manifests()
        for patcher in (
            mock.patch("gsutil.THIS_DIR", self.tempdir),
            # Avoid platform-specific gsutil options in run_gsutil().
            mock.patch("sys.platform", "win32"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _write_cipd_manifests(self, version_suffix: str = "v1") -> None:
        cache_dir = os.path.join(self.cipd_bin, ".cipd", "tmp")
        os.makedirs(cache_dir, exist_ok=True)
        for filename in (
            "cipd_manifest.txt",
            "cipd_manifest.versions",
            "cipd_client_version",
        ):
            content = f"{filename}:{version_suffix}\n".encode("utf-8")
            with open(os.path.join(self.tempdir, filename), "wb") as f:
                f.write(content)
            with open(os.path.join(cache_dir, f".{filename}"), "wb") as f:
                f.write(content)

    def _create_exe(self, name: str) -> str:
        path = os.path.join(self.cipd_bin, name + ".exe")
        with open(path, "wb"):
            pass
        return path

    def _luci_auth_cmd(self, luci_auth: str, subcommand: str) -> list[str]:
        """Returns the command gsutil.py should build to run luci-auth."""
        scopes = " ".join(gsutil.LUCI_AUTH_SCOPES)
        return [luci_auth, subcommand, "-scopes", scopes]

    def _gsutil_cmd(self, vpython3: str, *args: str) -> list[str]:
        """Returns the command run_gsutil() should build to run gsutil."""
        return [
            vpython3,
            "-vpython-spec",
            os.path.join(self.tempdir, "gsutil.vpython.toml"),
            "--",
            "gsutil_bin",
            "-o",
            "GSUtil:software_update_check_period=0",
        ] + list(args)

    def _run_gsutil(self, args: list[str], luci_context: bool = False) -> Any:
        """Calls run_gsutil() without boto, returning the mocked Popen."""
        with (
            mock.patch("gsutil.ensure_gsutil", return_value="gsutil_bin"),
            mock.patch("gsutil.get_boto_path", return_value=""),
            mock.patch("gsutil._is_luci_context", return_value=luci_context),
            mock.patch(
                "gsutil._is_luci_auth_supported_platform", return_value=True
            ),
            _mock_popen() as mock_popen,
        ):
            self.assertEqual(gsutil.run_gsutil(self.tempdir, args), 0)
        return mock_popen

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test_resolve_depot_tools_exe_windows(self) -> None:
        vpython3 = self._create_exe("vpython3")
        luci_auth = self._create_exe("luci-auth")
        self.assertEqual(gsutil._resolve_depot_tools_exe("vpython3"), vpython3)
        self.assertEqual(
            gsutil._resolve_depot_tools_exe("luci-auth"), luci_auth
        )

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test_resolve_depot_tools_exe_windows_missing_exe(self) -> None:
        # Only the requested tool is resolved.
        self._create_exe("luci-auth")
        self.assertEqual(
            gsutil._resolve_depot_tools_exe("vpython3"), "vpython3"
        )

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test_resolve_depot_tools_exe_windows_missing_cipd_bin(self) -> None:
        # e.g. a fresh checkout that hasn't run cipd_bin_setup.bat yet.
        shutil.rmtree(self.cipd_bin)
        self.assertEqual(
            gsutil._resolve_depot_tools_exe("vpython3"), "vpython3"
        )

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test_resolve_depot_tools_exe_windows_stale_manifest_cache(self) -> None:
        self._create_exe("vpython3")
        with open(
            os.path.join(self.tempdir, "cipd_manifest.versions"), "wb"
        ) as f:
            f.write(b"updated\n")
        self.assertEqual(
            gsutil._resolve_depot_tools_exe("vpython3"), "vpython3"
        )

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test_resolve_depot_tools_exe_windows_missing_manifest_cache(
        self,
    ) -> None:
        self._create_exe("vpython3")
        shutil.rmtree(os.path.join(self.cipd_bin, ".cipd"))
        self.assertEqual(
            gsutil._resolve_depot_tools_exe("vpython3"), "vpython3"
        )

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test_resolve_depot_tools_exe_windows_ignores_directory(self) -> None:
        os.mkdir(os.path.join(self.cipd_bin, "vpython3.exe"))
        self.assertEqual(
            gsutil._resolve_depot_tools_exe("vpython3"), "vpython3"
        )

    @mock.patch("gsutil.IS_WINDOWS", False)
    def test_resolve_depot_tools_exe_non_windows(self) -> None:
        self._create_exe("vpython3")
        self.assertEqual(
            gsutil._resolve_depot_tools_exe("vpython3"), "vpython3"
        )

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test__run_subprocess_windows_exe_without_shell(self) -> None:
        for exe in (
            r"C:\depot_tools\.cipd_bin\vpython3.exe",
            r"C:\depot tools\.cipd_bin\LUCI-AUTH.EXE",
            "python.exe",
        ):
            with self.subTest(exe=exe), _mock_popen() as mock_popen:
                p = gsutil._run_subprocess([exe, "arg"])
                mock_popen.assert_called_once_with(
                    [exe, "arg"],
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(p.returncode, 0)

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test__run_subprocess_windows_interactive_exe_without_shell(
        self,
    ) -> None:
        exe = r"C:\depot_tools\.cipd_bin\luci-auth.exe"
        with _mock_popen() as mock_popen:
            gsutil._run_subprocess([exe, "login"], interactive=True)
        mock_popen.assert_called_once_with([exe, "login"], shell=False)

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test__run_subprocess_windows_non_exe_uses_shell(self) -> None:
        for cmd0 in (
            "vpython3",
            "luci-auth",
            "vpython3.bat",
            "luci-auth.cmd",
            r"C:\depot_tools.exe\vpython3",
            "vpython3.exe.bat",
        ):
            with self.subTest(cmd0=cmd0), _mock_popen() as mock_popen:
                gsutil._run_subprocess([cmd0, "arg"])
                mock_popen.assert_called_once_with(
                    [cmd0, "arg"],
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

    @mock.patch("gsutil.IS_WINDOWS", False)
    def test__run_subprocess_non_windows_never_uses_shell(self) -> None:
        for cmd0 in ("vpython3", "/depot_tools/.cipd_bin/vpython3.exe"):
            with self.subTest(cmd0=cmd0), _mock_popen() as mock_popen:
                gsutil._run_subprocess([cmd0, "arg"])
                mock_popen.assert_called_once_with(
                    [cmd0, "arg"],
                    shell=False,
                    start_new_session=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test_run_gsutil_windows_runs_cipd_exes_directly(self) -> None:
        vpython3 = self._create_exe("vpython3")
        luci_auth = self._create_exe("luci-auth")
        mock_popen = self._run_gsutil(["ls", "gs://b"])
        mock_popen.assert_called_once_with(
            self._luci_auth_cmd(luci_auth, "context")
            + ["--"]
            + self._gsutil_cmd(vpython3, "ls", "gs://b"),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test_run_gsutil_windows_in_luci_context_runs_vpython3_exe(
        self,
    ) -> None:
        vpython3 = self._create_exe("vpython3")
        mock_popen = self._run_gsutil(["ls"], luci_context=True)
        mock_popen.assert_called_once_with(
            self._gsutil_cmd(vpython3, "ls"), shell=False
        )

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test_run_gsutil_windows_falls_back_to_bat_wrappers(self) -> None:
        # Without .cipd_bin, the .bat wrappers are run via the shell so they
        # can bootstrap .cipd_bin.
        shutil.rmtree(self.cipd_bin)
        mock_popen = self._run_gsutil(["ls"])
        mock_popen.assert_called_once_with(
            self._luci_auth_cmd("luci-auth", "context")
            + ["--"]
            + self._gsutil_cmd("vpython3", "ls"),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    @mock.patch("gsutil.IS_WINDOWS", True)
    def test_run_gsutil_windows_config_runs_luci_auth_exe(self) -> None:
        luci_auth = self._create_exe("luci-auth")
        mock_popen = self._run_gsutil(["config"])
        mock_popen.assert_called_once_with(
            self._luci_auth_cmd(luci_auth, "login"), shell=False
        )


if __name__ == "__main__":
    unittest.main()
