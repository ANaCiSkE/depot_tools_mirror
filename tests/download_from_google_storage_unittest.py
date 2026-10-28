#!/usr/bin/env vpython3
# Copyright 2012 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for download_from_google_storage.py."""

import io
import ntpath
import optparse
import os
import queue

import shutil
import stat
import sys
import tarfile
import tempfile
import threading
from typing import Optional
import unittest
from unittest import mock
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import upload_to_google_storage
import download_from_google_storage

# ../third_party/gsutil/gsutil
GSUTIL_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gsutil.py"
)
TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class GsutilMock(object):
    def __init__(self, path, boto_path, timeout=None):
        self.path = path
        self.timeout = timeout
        self.boto_path = boto_path
        self.expected = []
        self.history = []
        self.lock = threading.Lock()

    def add_expected(self, return_code, out, err, fn=None):
        self.expected.append((return_code, out, err, fn))

    def append_history(self, method, args):
        self.history.append((method, args))

    def call(self, *args):
        with self.lock:
            self.append_history("call", args)
            if self.expected:
                code, _out, _err, fn = self.expected.pop(0)
                if fn:
                    fn()
                return code

            return 0

    def check_call(self, *args):
        with self.lock:
            self.append_history("check_call", args)
            if self.expected:
                code, out, err, fn = self.expected.pop(0)
                if fn:
                    fn()
                return code, out, err

            return (0, "", "")

    def check_call_with_retries(self, *args):
        return self.check_call(*args)


class ChangedWorkingDirectory(object):
    def __init__(self, working_directory):
        self._old_cwd = ""
        self._working_directory = working_directory

    def __enter__(self):
        self._old_cwd = os.getcwd()
        print("Enter directory = ", self._working_directory)
        os.chdir(self._working_directory)

    def __exit__(self, *_):
        print("Enter directory = ", self._old_cwd)
        os.chdir(self._old_cwd)


class GstoolsUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gstools_test")
        self.base_path = os.path.join(self.temp_dir, "test_files")
        shutil.copytree(os.path.join(TEST_DIR, "gstools"), self.base_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_validate_tar_file(self):
        lorem_ipsum = os.path.join(self.base_path, "lorem_ipsum.txt")
        with ChangedWorkingDirectory(self.base_path):
            # Sanity ok check.
            tar_dir = "ok_dir"
            os.makedirs(os.path.join(self.base_path, tar_dir))
            tar = "good.tar.gz"
            lorem_ipsum_copy = os.path.join(tar_dir, "lorem_ipsum.txt")
            shutil.copyfile(lorem_ipsum, lorem_ipsum_copy)
            with tarfile.open(tar, "w:gz") as tar:
                tar.add(lorem_ipsum_copy)
                self.assertTrue(
                    download_from_google_storage._validate_tar_file(
                        tar, tar_dir
                    )
                )

            # os.symlink doesn't exist on Windows.
            if sys.platform != "win32":
                # Test no links.
                tar_dir_link = "for_tar_link"
                os.makedirs(tar_dir_link)
                link = os.path.join(tar_dir_link, "link")
                os.symlink(lorem_ipsum, link)
                tar_with_links = "with_links.tar.gz"
                with tarfile.open(tar_with_links, "w:gz") as tar:
                    tar.add(link)
                    self.assertFalse(
                        download_from_google_storage._validate_tar_file(
                            tar, tar_dir_link
                        )
                    )

            # Test not outside.
            tar_dir_outside = "outside_tar"
            os.makedirs(tar_dir_outside)
            tar_with_outside = "with_outside.tar.gz"
            with tarfile.open(tar_with_outside, "w:gz") as tar:
                tar.add(lorem_ipsum)
                self.assertFalse(
                    download_from_google_storage._validate_tar_file(
                        tar, tar_dir_outside
                    )
                )
            # Test no ../
            tar_with_dotdot = "with_dotdot.tar.gz"
            dotdot_file = os.path.join(
                tar_dir, "..", tar_dir, "lorem_ipsum.txt"
            )
            with tarfile.open(tar_with_dotdot, "w:gz") as tar:
                tar.add(dotdot_file)
                self.assertFalse(
                    download_from_google_storage._validate_tar_file(
                        tar, tar_dir
                    )
                )
            # Test normal file with .. in name okay
            tar_with_hidden = "with_normal_dotdot.tar.gz"
            hidden_file = os.path.join(tar_dir, "..hidden_file.txt")
            shutil.copyfile(lorem_ipsum, hidden_file)
            with tarfile.open(tar_with_hidden, "w:gz") as tar:
                tar.add(hidden_file)
                self.assertTrue(
                    download_from_google_storage._validate_tar_file(
                        tar, tar_dir
                    )
                )

    def test_gsutil(self):
        # This will download a real gsutil package from Google Storage.
        gsutil = download_from_google_storage.Gsutil(GSUTIL_DEFAULT_PATH, None)
        self.assertEqual(gsutil.path, GSUTIL_DEFAULT_PATH)
        code, _, err = gsutil.check_call()
        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")

    def test_get_sha1(self):
        lorem_ipsum = os.path.join(self.base_path, "lorem_ipsum.txt")
        self.assertEqual(
            download_from_google_storage.get_sha1(lorem_ipsum),
            "7871c8e24da15bad8b0be2c36edc9dc77e37727f",
        )

    def test_get_md5(self):
        lorem_ipsum = os.path.join(self.base_path, "lorem_ipsum.txt")
        self.assertEqual(
            upload_to_google_storage.get_md5(lorem_ipsum),
            "634d7c1ed3545383837428f031840a1e",
        )

    def test_get_md5_cached_read(self):
        lorem_ipsum = os.path.join(self.base_path, "lorem_ipsum.txt")
        # Use a fake 'stale' MD5 sum.  Expected behavior is to return stale sum.
        self.assertEqual(
            upload_to_google_storage.get_md5_cached(lorem_ipsum),
            "734d7c1ed3545383837428f031840a1e",
        )

    def test_get_md5_cached_write(self):
        lorem_ipsum2 = os.path.join(self.base_path, "lorem_ipsum2.txt")
        lorem_ipsum2_md5 = os.path.join(self.base_path, "lorem_ipsum2.txt.md5")
        if os.path.exists(lorem_ipsum2_md5):
            os.remove(lorem_ipsum2_md5)
        # Use a fake 'stale' MD5 sum.  Expected behavior is to return stale sum.
        self.assertEqual(
            upload_to_google_storage.get_md5_cached(lorem_ipsum2),
            "4c02d1eb455a0f22c575265d17b84b6d",
        )
        self.assertTrue(os.path.exists(lorem_ipsum2_md5))
        self.assertEqual(
            open(lorem_ipsum2_md5, "rb").read().decode(),
            "4c02d1eb455a0f22c575265d17b84b6d",
        )
        os.remove(lorem_ipsum2_md5)  # Clean up.
        self.assertFalse(os.path.exists(lorem_ipsum2_md5))


class GsutilCommandTests(unittest.TestCase):
    """Tests how Gsutil launches gsutil (see Gsutil._get_python_cmd)."""

    DEFAULT_PATH = download_from_google_storage.GSUTIL_DEFAULT_PATH
    VPYTHON3 = download_from_google_storage.Gsutil.VPYTHON3
    PIPE = download_from_google_storage.subprocess2.PIPE

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gsutil_cmd_test")
        self.addCleanup(shutil.rmtree, self.temp_dir)
        self.custom_path = os.path.join(self.temp_dir, "gsutil.py")
        with open(self.custom_path, "w"):
            pass
        self.python = os.path.join(self.temp_dir, "bin", "python3")

        # Don't depend on the interpreter or platform running the tests.
        self._patch(mock.patch.object(sys, "executable", self.python))
        self._patch(mock.patch.object(sys, "platform", "linux"))
        self.mock_call = self._patch(
            mock.patch("subprocess2.call", return_value=0)
        )
        self.mock_communicate = self._patch(
            mock.patch("subprocess2.communicate", return_value=((b"", b""), 0))
        )

    def _patch(self, patcher):
        mocked = patcher.start()
        self.addCleanup(patcher.stop)
        return mocked

    def _gsutil(self, path=None, boto_path=None):
        return download_from_google_storage.Gsutil(
            path or self.DEFAULT_PATH, boto_path
        )

    def assertUsesCurrentInterpreter(self, gsutil, path=None):
        path = path or self.DEFAULT_PATH
        self.mock_call.reset_mock()
        self.mock_communicate.reset_mock()

        self.assertEqual(gsutil.call("cp", "gs://b/o", "out"), 0)
        self.mock_call.assert_called_once_with(
            [self.python, path, "cp", "gs://b/o", "out"],
            env=mock.ANY,
            shell=False,
        )
        self.assertEqual(gsutil.check_call("ls", "gs://b"), (0, "", ""))
        self.mock_communicate.assert_called_once_with(
            [self.python, path, "ls", "gs://b"],
            stdout=self.PIPE,
            stderr=self.PIPE,
            env=mock.ANY,
            shell=False,
        )

    def assertUsesVpython3(self, gsutil, vpython3=None, path=None):
        vpython3 = vpython3 or self.VPYTHON3
        path = path or self.DEFAULT_PATH
        self.mock_call.reset_mock()
        self.mock_communicate.reset_mock()

        # No shell= argument, so that subprocess2 keeps defaulting to
        # shell=True on Windows, which is needed to run vpython3.bat.
        self.assertEqual(gsutil.call("cp", "gs://b/o", "out"), 0)
        self.mock_call.assert_called_once_with(
            [vpython3, path, "cp", "gs://b/o", "out"], env=mock.ANY
        )
        self.assertEqual(gsutil.check_call("ls", "gs://b"), (0, "", ""))
        self.mock_communicate.assert_called_once_with(
            [vpython3, path, "ls", "gs://b"],
            stdout=self.PIPE,
            stderr=self.PIPE,
            env=mock.ANY,
        )

    def test_default_path_uses_current_interpreter(self):
        for platform in ("linux", "darwin", "win32"):
            with (
                self.subTest(platform=platform),
                mock.patch.object(sys, "platform", platform),
            ):
                self.assertUsesCurrentInterpreter(self._gsutil())

    def test_current_interpreter_gets_sub_env(self):
        boto_path = os.path.join(self.temp_dir, ".boto")
        self._gsutil(boto_path=boto_path).call("ls")
        env = self.mock_call.call_args.kwargs["env"]
        self.assertEqual(env["BOTO_CONFIG"], boto_path)
        self.assertEqual(env["AWS_CREDENTIAL_FILE"], boto_path)

    def test_check_call_parses_output_from_current_interpreter(self):
        self.mock_communicate.return_value = (
            (b"out", b"CommandException: No URLs matched: gs://b/o"),
            1,
        )
        code, out, err = self._gsutil().check_call("ls", "gs://b/o")
        self.assertEqual((code, out), (404, "out"))
        self.assertIn("No URLs matched", err)
        self.assertIs(self.mock_communicate.call_args.kwargs["shell"], False)

    def test_equivalent_default_paths_use_current_interpreter(self):
        # A non-normalized path still refers to depot_tools' gsutil.py. The
        # path is passed through unchanged.
        dotted = os.path.join(
            os.path.dirname(self.DEFAULT_PATH), "tests", "..", "gsutil.py"
        )
        self.assertUsesCurrentInterpreter(self._gsutil(dotted), dotted)

        old_cwd = os.getcwd()
        os.chdir(os.path.dirname(self.DEFAULT_PATH))
        self.addCleanup(os.chdir, old_cwd)
        self.assertUsesCurrentInterpreter(
            self._gsutil("gsutil.py"), "gsutil.py"
        )

    def test_default_path_comparison_uses_normcase(self):
        # Simulate Windows' case-insensitive paths on any platform.
        gsutil = self._gsutil()
        gsutil.path = self.DEFAULT_PATH.upper()
        with mock.patch("os.path.normcase", ntpath.normcase):
            cmd = gsutil._get_python_cmd()
        self.assertEqual(cmd, [self.python, gsutil.path])

    def test_custom_path_uses_vpython3(self):
        self.assertUsesVpython3(
            self._gsutil(self.custom_path), path=self.custom_path
        )

    def test_cygwin_uses_vpython3(self):
        with mock.patch.object(sys, "platform", "cygwin"):
            self.assertUsesVpython3(self._gsutil())

    def test_overridden_vpython3_on_instance_is_respected(self):
        gsutil = self._gsutil()
        gsutil.VPYTHON3 = "custom-vpython3"
        self.assertUsesVpython3(gsutil, vpython3="custom-vpython3")

    def test_overridden_vpython3_in_subclass_is_respected(self):
        class CustomGsutil(download_from_google_storage.Gsutil):
            VPYTHON3 = "custom-vpython3"

        self.assertUsesVpython3(
            CustomGsutil(self.DEFAULT_PATH), vpython3="custom-vpython3"
        )

    def test_overridden_vpython3_on_class_is_respected(self):
        with mock.patch.object(
            download_from_google_storage.Gsutil,
            "VPYTHON3",
            "class-vpython3",
        ):
            self.assertUsesVpython3(self._gsutil(), vpython3="class-vpython3")

    def test_unknown_executable_uses_vpython3(self):
        # sys.executable is "" or None if Python can't determine it.
        for executable in ("", None):
            with (
                self.subTest(executable=executable),
                mock.patch.object(sys, "executable", executable),
            ):
                self.assertUsesVpython3(self._gsutil())

    def test_python_cmd_is_a_new_list_each_time(self):
        gsutil = self._gsutil()
        cmd = gsutil._get_python_cmd()
        cmd.append("mutated")
        self.assertEqual(
            gsutil._get_python_cmd(), [self.python, self.DEFAULT_PATH]
        )

    def test_concurrent_calls_build_independent_commands(self):
        # download_from_google_storage shares one Gsutil between threads.
        gsutil = self._gsutil()
        lock = threading.Lock()
        commands = []

        def fake_communicate(cmd, **_kwargs):
            with lock:
                commands.append(list(cmd))
            return ((b"", b""), 0)

        self.mock_communicate.side_effect = fake_communicate
        threads = [
            threading.Thread(
                target=gsutil.check_call, args=("cp", "gs://b/%d" % i, str(i))
            )
            for i in range(16)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertCountEqual(
            commands,
            [
                [self.python, self.DEFAULT_PATH, "cp", "gs://b/%d" % i, str(i)]
                for i in range(16)
            ],
        )


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.gsutil = GsutilMock(GSUTIL_DEFAULT_PATH, None)
        self.temp_dir = tempfile.mkdtemp(prefix="gstools_test")
        self.checkout_test_files = os.path.join(
            TEST_DIR, "gstools", "download_test_data"
        )
        self.base_path = os.path.join(self.temp_dir, "download_test_data")
        shutil.copytree(self.checkout_test_files, self.base_path)
        self.base_url = "gs://sometesturl"
        self.parser = optparse.OptionParser()
        self.queue = queue.Queue()
        self.ret_codes = queue.Queue()
        self.lorem_ipsum = os.path.join(TEST_DIR, "gstools", "lorem_ipsum.txt")
        self.lorem_ipsum_sha1 = "7871c8e24da15bad8b0be2c36edc9dc77e37727f"
        self.maxDiff = None

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_enumerate_files_non_recursive(self):
        for item in download_from_google_storage.enumerate_input(
            self.base_path, True, False, False, None, False, False
        ):
            self.queue.put(item)
        expected_queue = [
            (
                "e6c4fbd4fe7607f3e6ebf68b2ea4ef694da7b4fe",
                os.path.join(self.base_path, "rootfolder_text.txt"),
            ),
            (
                "7871c8e24da15bad8b0be2c36edc9dc77e37727f",
                os.path.join(self.base_path, "uploaded_lorem_ipsum.txt"),
            ),
        ]
        self.assertEqual(sorted(expected_queue), sorted(self.queue.queue))

    def test_enumerate_files_recursive(self):
        for item in download_from_google_storage.enumerate_input(
            self.base_path, True, True, False, None, False, False
        ):
            self.queue.put(item)
        expected_queue = [
            (
                "e6c4fbd4fe7607f3e6ebf68b2ea4ef694da7b4fe",
                os.path.join(self.base_path, "rootfolder_text.txt"),
            ),
            (
                "7871c8e24da15bad8b0be2c36edc9dc77e37727f",
                os.path.join(self.base_path, "uploaded_lorem_ipsum.txt"),
            ),
            (
                "b5415aa0b64006a95c0c409182e628881d6d6463",
                os.path.join(self.base_path, "subfolder", "subfolder_text.txt"),
            ),
            (
                "b5415aa0b64006a95c0c409182e628881d6d6463",
                os.path.join(
                    self.base_path, "subfolder2", "subfolder_text.txt"
                ),
            ),
        ]
        self.assertEqual(sorted(expected_queue), sorted(self.queue.queue))

    def test_download_worker_single_file(self):
        sha1_hash = self.lorem_ipsum_sha1
        input_filename = "%s/%s" % (self.base_url, sha1_hash)
        output_filename = os.path.join(
            self.base_path, "uploaded_lorem_ipsum.txt"
        )
        self.gsutil.add_expected(
            0,
            "",
            "",
            lambda: shutil.copyfile(self.lorem_ipsum, output_filename),
        )  # cp
        self.queue.put((sha1_hash, output_filename))
        self.queue.put((None, None))
        stdout_queue = queue.Queue()
        download_from_google_storage._downloader_worker_thread(
            0,
            self.queue,
            False,
            self.base_url,
            self.gsutil,
            stdout_queue,
            self.ret_codes,
            True,
            False,
        )
        expected_calls = [
            ("check_call", ("cp", input_filename, output_filename))
        ]
        sha1_hash = "7871c8e24da15bad8b0be2c36edc9dc77e37727f"
        if sys.platform != "win32":
            expected_calls.append(
                ("check_call", ("stat", "gs://sometesturl/" + sha1_hash))
            )
        expected_output = [
            "0> Downloading %s@%s..." % (output_filename, sha1_hash)
        ]
        expected_ret_codes = []
        self.assertEqual(list(stdout_queue.queue), expected_output)
        self.assertEqual(self.gsutil.history, expected_calls)
        self.assertEqual(list(self.ret_codes.queue), expected_ret_codes)

    def test_download_worker_skips_file(self):
        sha1_hash = "e6c4fbd4fe7607f3e6ebf68b2ea4ef694da7b4fe"
        output_filename = os.path.join(self.base_path, "rootfolder_text.txt")
        self.queue.put((sha1_hash, output_filename))
        self.queue.put((None, None))
        stdout_queue = queue.Queue()
        download_from_google_storage._downloader_worker_thread(
            0,
            self.queue,
            False,
            self.base_url,
            self.gsutil,
            stdout_queue,
            self.ret_codes,
            True,
            False,
        )
        # dfgs does not output anything in the no-op case.
        self.assertEqual(list(stdout_queue.queue), [])
        self.assertEqual(self.gsutil.history, [])

    def test_download_extract_archive(self):
        # Generate a gzipped tarfile
        output_filename = os.path.join(self.base_path, "subfolder.tar.gz")
        output_dirname = os.path.join(self.base_path, "subfolder")
        extracted_filename = os.path.join(output_dirname, "subfolder_text.txt")
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(output_dirname, arcname="subfolder")
        shutil.rmtree(output_dirname)
        sha1_hash = download_from_google_storage.get_sha1(output_filename)
        input_filename = "%s/%s" % (self.base_url, sha1_hash)

        # Initial download
        self.queue.put((sha1_hash, output_filename))
        self.queue.put((None, None))
        stdout_queue = queue.Queue()
        download_from_google_storage._downloader_worker_thread(
            0,
            self.queue,
            True,
            self.base_url,
            self.gsutil,
            stdout_queue,
            self.ret_codes,
            True,
            True,
            delete=False,
        )
        expected_calls = [
            ("check_call", ("cp", input_filename, output_filename))
        ]
        if sys.platform != "win32":
            expected_calls.append(
                ("check_call", ("stat", "gs://sometesturl/%s" % sha1_hash))
            )
        expected_output = [
            "0> Downloading %s@%s..." % (output_filename, sha1_hash)
        ]
        expected_output.extend(
            [
                "0> Extracting 3 entries from %s to %s"
                % (output_filename, output_dirname)
            ]
        )
        expected_ret_codes = []
        self.assertEqual(list(stdout_queue.queue), expected_output)
        self.assertEqual(self.gsutil.history, expected_calls)
        self.assertEqual(list(self.ret_codes.queue), expected_ret_codes)
        self.assertTrue(os.path.exists(output_dirname))
        self.assertTrue(os.path.exists(extracted_filename))

        # Test noop download
        self.queue.put((sha1_hash, output_filename))
        self.queue.put((None, None))
        stdout_queue = queue.Queue()
        download_from_google_storage._downloader_worker_thread(
            0,
            self.queue,
            False,
            self.base_url,
            self.gsutil,
            stdout_queue,
            self.ret_codes,
            True,
            True,
            delete=False,
        )

        self.assertEqual(list(stdout_queue.queue), [])
        self.assertEqual(self.gsutil.history, expected_calls)
        self.assertEqual(list(self.ret_codes.queue), [])
        self.assertTrue(os.path.exists(output_dirname))
        self.assertTrue(os.path.exists(extracted_filename))

        # With dirty flag file, previous extraction wasn't complete
        with open(os.path.join(self.base_path, "subfolder.tmp"), "a"):
            pass

        self.queue.put((sha1_hash, output_filename))
        self.queue.put((None, None))
        stdout_queue = queue.Queue()
        download_from_google_storage._downloader_worker_thread(
            0,
            self.queue,
            False,
            self.base_url,
            self.gsutil,
            stdout_queue,
            self.ret_codes,
            True,
            True,
            delete=False,
        )
        expected_calls += [
            ("check_call", ("cp", input_filename, output_filename))
        ]
        if sys.platform != "win32":
            expected_calls.append(
                ("check_call", ("stat", "gs://sometesturl/%s" % sha1_hash))
            )
        expected_output = [
            "0> Detected tmp flag file for %s, re-downloading..."
            % (output_filename),
            "0> Downloading %s@%s..." % (output_filename, sha1_hash),
            "0> Removed %s..." % (output_dirname),
            "0> Extracting 3 entries from %s to %s"
            % (output_filename, output_dirname),
        ]
        expected_ret_codes = []
        self.assertEqual(list(stdout_queue.queue), expected_output)
        self.assertEqual(self.gsutil.history, expected_calls)
        self.assertEqual(list(self.ret_codes.queue), expected_ret_codes)
        self.assertTrue(os.path.exists(output_dirname))
        self.assertTrue(os.path.exists(extracted_filename))

    def test_download_worker_skips_not_found_file(self):
        sha1_hash = "7871c8e24da15bad8b0be2c36edc9dc77e37727f"
        input_filename = "%s/%s" % (self.base_url, sha1_hash)
        output_filename = os.path.join(
            self.base_path, "uploaded_lorem_ipsum.txt"
        )
        self.queue.put((sha1_hash, output_filename))
        self.queue.put((None, None))
        stdout_queue = queue.Queue()
        self.gsutil.add_expected(1, "", "")  # Return error when 'cp' is called.
        download_from_google_storage._downloader_worker_thread(
            0,
            self.queue,
            False,
            self.base_url,
            self.gsutil,
            stdout_queue,
            self.ret_codes,
            True,
            False,
        )
        expected_output = [
            "0> Downloading %s@%s..." % (output_filename, sha1_hash),
            "0> Failed to fetch file %s for %s, skipping. [Err: ]"
            % (input_filename, output_filename),
        ]
        expected_calls = [
            ("check_call", ("cp", input_filename, output_filename))
        ]
        expected_ret_codes = [
            (
                1,
                "Failed to fetch file %s for %s. [Err: ]"
                % (input_filename, output_filename),
            )
        ]
        self.assertEqual(list(stdout_queue.queue), expected_output)
        self.assertEqual(self.gsutil.history, expected_calls)
        self.assertEqual(list(self.ret_codes.queue), expected_ret_codes)

    def test_download_cp_fails(self):
        sha1_hash = "7871c8e24da15bad8b0be2c36edc9dc77e37727f"
        input_filename = "%s/%s" % (self.base_url, sha1_hash)
        output_filename = os.path.join(
            self.base_path, "uploaded_lorem_ipsum.txt"
        )
        self.gsutil.add_expected(101, "", "Test error message.")  # cp
        code = download_from_google_storage.download_from_google_storage(
            input_filename=sha1_hash,
            base_url=self.base_url,
            gsutil=self.gsutil,
            num_threads=1,
            directory=False,
            recursive=False,
            force=True,
            output=output_filename,
            ignore_errors=False,
            sha1_file=False,
            verbose=True,
            auto_platform=False,
            extract=False,
        )
        expected_calls = [
            ("check_call", ("cp", input_filename, output_filename))
        ]
        self.assertEqual(self.gsutil.history, expected_calls)
        self.assertEqual(code, 101)

    def test_corrupt_download(self):
        q = queue.Queue()
        out_q = queue.Queue()
        ret_codes = queue.Queue()
        tmp_dir = tempfile.mkdtemp()
        sha1_hash = "7871c8e24da15bad8b0be2c36edc9dc77e37727f"
        output_filename = os.path.join(tmp_dir, "lorem_ipsum.txt")
        q.put(("7871c8e24da15bad8b0be2c36edc9dc77e37727f", output_filename))
        q.put((None, None))

        def _write_bad_file():
            with open(output_filename, "w") as f:
                f.write("foobar")

        self.gsutil.add_expected(0, "", "", _write_bad_file)  # cp
        download_from_google_storage._downloader_worker_thread(
            1,
            q,
            True,
            self.base_url,
            self.gsutil,
            out_q,
            ret_codes,
            True,
            False,
        )
        self.assertTrue(q.empty())
        msg = "1> ERROR remote sha1 (%s) does not match expected sha1 (%s)." % (
            "8843d7f92416211de9ebb963ff4ce28125932878",
            sha1_hash,
        )
        self.assertEqual(
            out_q.get(),
            "1> Downloading %s@%s..." % (output_filename, sha1_hash),
        )
        self.assertEqual(out_q.get(), msg)
        self.assertEqual(ret_codes.get(), (20, msg))
        self.assertTrue(out_q.empty())
        self.assertTrue(ret_codes.empty())

    def test_download_directory_no_recursive_non_force(self):
        sha1_hash = "7871c8e24da15bad8b0be2c36edc9dc77e37727f"
        input_filename = "%s/%s" % (self.base_url, sha1_hash)
        output_filename = os.path.join(
            self.base_path, "uploaded_lorem_ipsum.txt"
        )
        self.gsutil.add_expected(0, "", "")  # version
        self.gsutil.add_expected(
            0,
            "",
            "",
            lambda: shutil.copyfile(self.lorem_ipsum, output_filename),
        )  # cp
        code = download_from_google_storage.download_from_google_storage(
            input_filename=self.base_path,
            base_url=self.base_url,
            gsutil=self.gsutil,
            num_threads=1,
            directory=True,
            recursive=False,
            force=False,
            output=None,
            ignore_errors=False,
            sha1_file=False,
            verbose=True,
            auto_platform=False,
            extract=False,
        )
        expected_calls = [
            ("check_call", ("version",)),
            ("check_call", ("cp", input_filename, output_filename)),
        ]
        if sys.platform != "win32":
            expected_calls.append(
                (
                    "check_call",
                    (
                        "stat",
                        "gs://sometesturl/7871c8e24da15bad8b0be2c36edc9dc77e37727f",
                    ),
                )
            )
        self.assertEqual(self.gsutil.history, expected_calls)
        self.assertEqual(code, 0)


SYM, LNK, REG, DIR = (
    tarfile.SYMTYPE,
    tarfile.LNKTYPE,
    tarfile.REGTYPE,
    tarfile.DIRTYPE,
)

# (name, type, linkname for links or content for regular files, mode)
MemberSpec = tuple[str, bytes, Optional[str], int]


def _member(
    name: str, kind: bytes = REG, arg: Optional[str] = "x", mode: int = 0o644
) -> MemberSpec:
    return (name, kind, arg, mode)


def _write_tar(path: str, members: list[MemberSpec]) -> None:
    """Writes a tar.gz with the given members."""
    with tarfile.open(path, "w:gz") as tar:
        for name, kind, arg, mode in members:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.mode = mode
            data = None
            if kind in (SYM, LNK):
                info.linkname = arg
            elif kind == REG:
                content = arg.encode()
                data = io.BytesIO(content)
                info.size = len(content)
            tar.addfile(info, data)


class ExtractTests(unittest.TestCase):
    """Tests that --extract cannot write outside the extract dir."""

    # Levels between the extract dir and temp_dir.
    DEPTH = 5

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="dfgs_extract_test")
        self.addCleanup(shutil.rmtree, self.temp_dir)
        # Nest the work dir so that escapes stay inside temp_dir.
        self.work_dir = os.path.join(self.temp_dir, "a", "b", "c", "work")
        os.makedirs(self.work_dir)
        self.tar_path = os.path.join(self.work_dir, "node.tar.gz")
        self.extract_dir = os.path.join(self.work_dir, "node")
        self.secret = os.path.join(self.temp_dir, "secret")
        with open(self.secret, "w") as f:
            f.write("secret")
        with open(f"{self.tar_path}.sha1", "w") as f:
            f.write("pin")

    def _validate(
        self, members: list[MemberSpec], prefix: str = "node"
    ) -> bool:
        _write_tar(self.tar_path, members)
        with tarfile.open(self.tar_path, "r:gz") as tar:
            return download_from_google_storage._validate_tar_file(tar, prefix)

    def _run_worker(
        self, members: Optional[list[MemberSpec]]
    ) -> list[tuple[int, str]]:
        """Downloads and extracts an archive; returns the reported errors.

        If members is None, the archive at tar_path is used as is.
        """
        if members is not None:
            _write_tar(self.tar_path, members)
        work_queue = queue.Queue()
        work_queue.put(
            (
                download_from_google_storage.get_sha1(self.tar_path),
                self.tar_path,
            )
        )
        work_queue.put((None, None))
        ret_codes = queue.Queue()
        download_from_google_storage._downloader_worker_thread(
            0,
            work_queue,
            True,
            "gs://bucket",
            GsutilMock(GSUTIL_DEFAULT_PATH, None),
            queue.Queue(),
            ret_codes,
            False,
            True,
            delete=False,
        )
        return [r for r in ret_codes.queue if r[0]]

    def _outside_files(self) -> list[str]:
        """Returns all paths under temp_dir except the extract dir."""
        paths = []
        for root, dirs, files in os.walk(self.temp_dir):
            if root == self.work_dir and "node" in dirs:
                dirs.remove("node")
            for name in dirs + files:
                paths.append(
                    os.path.relpath(os.path.join(root, name), self.temp_dir)
                )
        return sorted(paths)

    def _data_exists(self) -> bool:
        return download_from_google_storage._data_exists(
            download_from_google_storage.get_sha1(self.tar_path),
            self.tar_path,
            True,
        )

    def assertFailsSafely(
        self, members: Optional[list[MemberSpec]], error: str
    ) -> None:
        """Asserts that extracting members fails without escaping."""
        if members is not None:
            _write_tar(self.tar_path, members)
        tmp_flag = f"{self.extract_dir}.tmp"
        if os.path.exists(tmp_flag):
            os.remove(tmp_flag)
        outside = self._outside_files()
        errors = self._run_worker(None)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn(error, errors[0][1])
        # Nothing was written outside the extract dir, apart from the flag
        # file marking the extraction as incomplete so that it is retried.
        self.assertEqual(
            self._outside_files(),
            sorted(outside + [os.path.relpath(tmp_flag, self.temp_dir)]),
        )
        with open(self.secret) as f:
            self.assertEqual(f.read(), "secret")
        self.assertEqual(os.stat(self.secret).st_nlink, 1)
        with open(f"{self.tar_path}.sha1") as f:
            self.assertEqual(f.read(), "pin")
        # No partial tree is left behind, and the next run retries.
        self.assertFalse(os.path.lexists(self.extract_dir))
        self.assertFalse(self._data_exists())

    def test_validate_tar_file_rejects(self) -> None:
        depth = self.DEPTH
        chain = f"node/{'x/' * depth}evil"
        cases: dict[str, list[MemberSpec]] = {
            "prefix without separator": [_member("node.tar.gz.sha1")],
            "sibling dir sharing prefix": [_member("nodeevil/x")],
            "parent component": [_member("node/../node/x")],
            "backslash": [_member("node\\x")],
            "absolute": [_member("/node/x")],
            "drive": [_member("C:/node/x")],
            "colon": [_member("node/x:stream")],
            "dot component in file name": [_member("node/y/.")],
            "dotdot with trailing space": [_member("node/.. /x")],
            "unc": [_member("//server/share/node/x")],
            "empty name": [_member("")],
            "archive root": [_member(".", DIR, None)],
            "file as extract dir": [_member("node")],
            "fifo": [_member("node/f", tarfile.FIFOTYPE, None)],
            "duplicate": [_member("node/x"), _member("node/x")],
            "absolute symlink": [_member("node/s", SYM, "/etc/passwd")],
            "drive symlink": [_member("node/s", SYM, "C:/x")],
            "dot prefixed drive symlink": [_member("node/s", SYM, "./C:/x")],
            "symlink dotdot with trailing space": [
                _member("node/a/s", SYM, ".. /.. /x")
            ],
            "backslash symlink": [_member("node/s", SYM, "a\\..\\..\\x")],
            "symlink to sibling": [_member("node/s", SYM, "../nodeevil")],
            "symlink to parent": [_member("node/s", SYM, "..")],
            "symlink with inner dotdot": [_member("node/s", SYM, "a/../x")],
            # Earlier symlinks redirect later members out of the extract dir.
            "chained symlink depth": [
                _member("node/x", SYM, "."),
                _member(chain, SYM, f"{'../' * depth}secret"),
                _member(chain),
            ],
            "write through symlink": [
                _member("node/s", SYM, "x"),
                _member("node/s"),
            ],
            "member under symlink": [
                _member("node/s", SYM, "."),
                _member("node/s/x"),
            ],
            "member under later symlink": [
                _member("node/s/x"),
                _member("node/s", SYM, "."),
            ],
            "member under symlink differing in case": [
                _member("node/S", SYM, "."),
                _member("node/s/x"),
            ],
            "member under symlink with trailing dot": [
                _member("node/s.", SYM, "."),
                _member("node/s/x"),
            ],
            "symlink replacing dir": [
                _member("node/d", DIR, None),
                _member("node/d", SYM, "x"),
            ],
            "symlink as extract dir": [_member("node", SYM, "node/x")],
            # tarfile resolves hardlinks relative to the archive root, not to
            # the hardlink's directory.
            "hardlink relative to member": [
                _member("node/a"),
                _member("node/b/h", LNK, "../a"),
            ],
            "hardlink outside": [_member("node/a/b/h", LNK, "../../../secret")],
            "hardlink with dotdot": [
                _member("node/a"),
                _member("node/b/h", LNK, "node/x/../a"),
            ],
            "hardlink to sibling": [_member("node/h", LNK, "node.tar.gz.sha1")],
            "hardlink to later file": [
                _member("node/h", LNK, "node/a"),
                _member("node/a"),
            ],
            "hardlink to symlink": [
                _member("node/s", SYM, "a"),
                _member("node/h", LNK, "node/s"),
            ],
            "hardlink with dot": [
                _member("node/a"),
                _member("node/h", LNK, "node/a/."),
            ],
            "hardlink to dir": [
                _member("node/d", DIR, None),
                _member("node/h", LNK, "node/d"),
            ],
        }
        for desc, members in cases.items():
            with self.subTest(desc):
                self.assertFalse(self._validate(members))

    def test_validate_tar_file_rejects_degenerate_prefix(self) -> None:
        for prefix in ("", ".", "..", "node/sub", "/node", "C:node", "a\\b"):
            with self.subTest(prefix=prefix):
                self.assertFalse(self._validate([], prefix=prefix))

    def test_validate_tar_file_accepts(self) -> None:
        cases: dict[str, list[MemberSpec]] = {
            "extract dir": [_member("node", DIR, None)],
            "extract dir with slash": [_member("node/", DIR, None)],
            "file": [_member("node/x")],
            "dot prefixed": [_member("./node/x")],
            "dotdot in file name": [_member("node/..hidden")],
            "names differing in case": [_member("node/x"), _member("node/X")],
            "duplicate dir": [
                _member("node/d", DIR, None),
                _member("node/d", DIR, None),
            ],
            "relative symlink": [
                _member(
                    "node/bin/npm",
                    SYM,
                    "../lib/node_modules/npm/bin/npm-cli.js",
                )
            ],
            "symlink to symlink": [
                _member("node/lib/libfoo.so.1", SYM, "libfoo.so.1.2"),
                _member("node/lib/libfoo.so", SYM, "libfoo.so.1"),
            ],
            "symlink to extract dir": [_member("node/bin/self", SYM, "..")],
            "symlink to own dir": [_member("node/self", SYM, ".")],
            "hardlink": [_member("node/a"), _member("node/b", LNK, "node/a")],
            "hardlink chain": [
                _member("node/a"),
                _member("node/b", LNK, "node/a"),
                _member("node/c", LNK, "node/b"),
            ],
        }
        for desc, members in cases.items():
            with self.subTest(desc):
                self.assertTrue(self._validate(members))

    def test_extract_rejects_invalid_archive(self) -> None:
        for desc, members in {
            "sibling file": [_member("node/x"), _member("node.tar.gz.sha1")],
            "chained symlink depth": [
                _member("node/x", SYM, "."),
                _member("node/x/x/evil", SYM, "../../x"),
                _member("node/x/x/evil"),
            ],
        }.items():
            with self.subTest(desc):
                self.assertFailsSafely(members, "contains invalid entries")

    def test_extract_rejects_corrupt_archive(self) -> None:
        _write_tar(
            self.tar_path,
            [_member("node/x", REG, os.urandom(1 << 16).hex())],
        )
        with open(self.tar_path, "rb") as f:
            data = f.read()
        cases = {
            "truncated header": data[:30],
            "truncated stream": data[: len(data) // 2],
        }
        for desc, corrupt in cases.items():
            with self.subTest(desc):
                with open(self.tar_path, "wb") as f:
                    f.write(corrupt)
                self.assertFailsSafely(None, "Failed to extract")

    @unittest.skipIf(
        sys.platform == "win32", "os.symlink requires elevation on Windows"
    )
    @unittest.skipUnless(
        download_from_google_storage._HAS_DATA_FILTER,
        "requires PEP 706 tarfile filters",
    )
    def test_extract_data_filter_is_defense_in_depth(self) -> None:
        # Even if the lexical check were bypassed, the data filter refuses
        # members that resolve outside the work dir on disk.
        depth = self.DEPTH
        chain = f"node/{'x/' * depth}evil"
        cases: dict[str, list[MemberSpec]] = {
            "chained symlink depth": [
                _member("node/x", SYM, "."),
                _member(chain, SYM, f"{'../' * depth}secret"),
                _member(chain, REG, "evil"),
            ],
            "hardlink outside": [
                _member("node/a/b/h", LNK, f"{'../' * (depth - 1)}secret")
            ],
        }
        with mock.patch.object(
            download_from_google_storage,
            "_validate_tar_file",
            return_value=True,
        ):
            for desc, members in cases.items():
                with self.subTest(desc):
                    self.assertFailsSafely(members, "Failed to extract")

    @unittest.skipIf(
        sys.platform == "win32", "os.symlink requires elevation on Windows"
    )
    def test_extract_legitimate_archive(self) -> None:
        npm_cli = "node/lib/node_modules/npm/bin/npm-cli.js"
        members = [
            _member("node", DIR, None, 0o755),
            _member("node/bin", DIR, None, 0o755),
            _member("node/bin/node", REG, "node", 0o755),
            _member(npm_cli, REG, "npm", 0o755),
            _member(
                "node/bin/npm", SYM, "../lib/node_modules/npm/bin/npm-cli.js"
            ),
            _member("node/bin/self", SYM, ".."),
            _member("node/a", REG, "a"),
            _member("node/b", LNK, "node/a"),
        ]
        for data_filter in (
            (True, False)
            if download_from_google_storage._HAS_DATA_FILTER
            else (False,)
        ):
            with self.subTest(data_filter=data_filter):
                with (
                    mock.patch.object(
                        download_from_google_storage,
                        "_HAS_DATA_FILTER",
                        data_filter,
                    ),
                    warnings.catch_warnings(),
                ):
                    warnings.simplefilter("ignore", DeprecationWarning)
                    self.assertEqual(self._run_worker(members), [])
                self.assertFalse(os.path.exists(f"{self.extract_dir}.tmp"))
                npm = os.path.join(self.extract_dir, "bin", "npm")
                self.assertEqual(
                    os.readlink(npm), "../lib/node_modules/npm/bin/npm-cli.js"
                )
                with open(npm) as f:
                    self.assertEqual(f.read(), "npm")
                self.assertTrue(
                    os.path.samefile(
                        os.path.join(self.extract_dir, "a"),
                        os.path.join(self.extract_dir, "b"),
                    )
                )
                for exe in ("node/bin/node", npm_cli):
                    mode = os.stat(os.path.join(self.work_dir, exe)).st_mode
                    self.assertTrue(mode & stat.S_IXUSR, exe)
                mode = os.stat(os.path.join(self.extract_dir, "a")).st_mode
                self.assertFalse(mode & stat.S_IXUSR)
                self.assertTrue(self._data_exists())

    def test_failed_update_is_retried(self) -> None:
        # An existing extract dir from a previous version...
        os.mkdir(self.extract_dir)
        # ...followed by an update to an archive that is rejected.
        self.assertEqual(len(self._run_worker([_member("nodeevil/x")])), 1)
        self.assertTrue(os.path.isdir(self.extract_dir))
        self.assertTrue(os.path.exists(f"{self.extract_dir}.tmp"))
        self.assertFalse(self._data_exists())


if __name__ == "__main__":
    unittest.main()
