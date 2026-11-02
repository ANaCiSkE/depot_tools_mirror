#!/usr/bin/env vpython3
# coding=utf-8
# Copyright 2012 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import io
import os
import stat
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gclient_utils
import subprocess2
from testing_support import trial_dir


class CheckCallAndFilterTestCase(unittest.TestCase):
    class ProcessIdMock(object):
        def __init__(self, test_string, return_code=0):
            self.stdout = test_string.encode("utf-8")
            self.pid = 9284
            self.return_code = return_code

        def wait(self):
            return self.return_code

    def PopenMock(self, *args, **kwargs):
        kid = self.kids.pop(0)
        stdout = kwargs.get("stdout")
        os.write(stdout, kid.stdout)
        return kid

    def setUp(self):
        super(CheckCallAndFilterTestCase, self).setUp()
        self.printfn = io.StringIO()
        self.stdout = io.BytesIO()
        self.kids = []
        mock.patch("sys.stdout", mock.Mock()).start()
        mock.patch("sys.stdout.buffer", self.stdout).start()
        mock.patch("sys.stdout.isatty", return_value=False).start()
        mock.patch("builtins.print", self.printfn.write).start()
        mock.patch("sys.stdout.flush", lambda: None).start()
        self.addCleanup(mock.patch.stopall)

    @mock.patch("subprocess2.Popen")
    def testCheckCallAndFilter(self, mockPopen):
        cwd = "bleh"
        args = ["boo", "foo", "bar"]
        test_string = "ahah\naccb\nallo\naddb\n✔"

        self.kids = [self.ProcessIdMock(test_string)]
        mockPopen.side_effect = self.PopenMock

        line_list = []
        result = gclient_utils.CheckCallAndFilter(
            args,
            cwd=cwd,
            show_header=True,
            always_show_header=True,
            filter_fn=line_list.append,
        )

        self.assertEqual(result, test_string.encode("utf-8"))
        self.assertEqual(
            line_list,
            [
                "________ running 'boo foo bar' in 'bleh'\n",
                "ahah",
                "accb",
                "allo",
                "addb",
                "✔",
            ],
        )
        self.assertEqual(self.stdout.getvalue(), b"")

        kall = mockPopen.call_args
        self.assertEqual(kall.args, (args,))
        self.assertEqual(kall.kwargs["cwd"], cwd)
        self.assertEqual(kall.kwargs["stdout"], mock.ANY)
        self.assertEqual(kall.kwargs["stderr"], subprocess2.STDOUT)
        self.assertEqual(kall.kwargs["bufsize"], 0)
        self.assertIn("env", kall.kwargs)
        self.assertIn("COLUMNS", kall.kwargs["env"])
        self.assertIn("LINES", kall.kwargs["env"])

    @mock.patch("time.sleep")
    @mock.patch("subprocess2.Popen")
    def testCheckCallAndFilter_RetryOnce(self, mockPopen, mockTime):
        cwd = "bleh"
        args = ["boo", "foo", "bar"]
        test_string = "ahah\naccb\nallo\naddb\n✔"

        self.kids = [
            self.ProcessIdMock(test_string, 1),
            self.ProcessIdMock(test_string, 0),
        ]
        mockPopen.side_effect = self.PopenMock

        line_list = []
        result = gclient_utils.CheckCallAndFilter(
            args,
            cwd=cwd,
            show_header=True,
            always_show_header=True,
            filter_fn=line_list.append,
            retry=True,
        )

        self.assertEqual(result, test_string.encode("utf-8"))

        self.assertEqual(
            line_list,
            [
                "________ running 'boo foo bar' in 'bleh'\n",
                "ahah",
                "accb",
                "allo",
                "addb",
                "✔",
                "________ running 'boo foo bar' in 'bleh' attempt 2 / 2\n",
                "ahah",
                "accb",
                "allo",
                "addb",
                "✔",
            ],
        )

        mockTime.assert_called_with(gclient_utils.RETRY_INITIAL_SLEEP)

        for i in range(2):
            kall = mockPopen.mock_calls[i]
            self.assertEqual(kall.args, (args,))
            self.assertEqual(kall.kwargs["cwd"], cwd)
            self.assertEqual(kall.kwargs["stdout"], mock.ANY)
            self.assertEqual(kall.kwargs["stderr"], subprocess2.STDOUT)
            self.assertEqual(kall.kwargs["bufsize"], 0)
            self.assertIn("env", kall.kwargs)
            self.assertIn("COLUMNS", kall.kwargs["env"])
            self.assertIn("LINES", kall.kwargs["env"])

        self.assertEqual(self.stdout.getvalue(), b"")
        self.assertEqual(
            self.printfn.getvalue(),
            'WARNING: subprocess \'"boo" "foo" "bar"\' in bleh failed; will retry '
            "after a short nap...",
        )

    @mock.patch("subprocess2.Popen")
    def testCheckCallAndFilter_PrintStdout(self, mockPopen):
        cwd = "bleh"
        args = ["boo", "foo", "bar"]
        test_string = "ahah\naccb\nallo\naddb\n✔"

        self.kids = [self.ProcessIdMock(test_string)]
        mockPopen.side_effect = self.PopenMock

        result = gclient_utils.CheckCallAndFilter(
            args,
            cwd=cwd,
            show_header=True,
            always_show_header=True,
            print_stdout=True,
        )

        self.assertEqual(result, test_string.encode("utf-8"))
        self.assertEqual(
            self.stdout.getvalue().splitlines(),
            [
                b"________ running 'boo foo bar' in 'bleh'",
                b"ahah",
                b"accb",
                b"allo",
                b"addb",
                b"\xe2\x9c\x94",
            ],
        )


class AnnotatedTestCase(unittest.TestCase):
    def setUp(self):
        self.out = gclient_utils.MakeFileAnnotated(io.BytesIO())
        self.annotated = gclient_utils.MakeFileAnnotated(
            io.BytesIO(), include_zero=True
        )

    def testWrite(self):
        test_cases = [
            ("test string\n", b"test string\n"),
            (b"test string\n", b"test string\n"),
            ("✔\n", b"\xe2\x9c\x94\n"),
            (b"\xe2\x9c\x94\n", b"\xe2\x9c\x94\n"),
            ("first line\nsecondline\n", b"first line\nsecondline\n"),
            (b"first line\nsecondline\n", b"first line\nsecondline\n"),
        ]

        for test_input, expected_output in test_cases:
            out = gclient_utils.MakeFileAnnotated(io.BytesIO())
            out.write(test_input)
            self.assertEqual(out.getvalue(), expected_output)

    def testWrite_Annotated(self):
        test_cases = [
            ("test string\n", b"0>test string\n"),
            (b"test string\n", b"0>test string\n"),
            ("✔\n", b"0>\xe2\x9c\x94\n"),
            (b"\xe2\x9c\x94\n", b"0>\xe2\x9c\x94\n"),
            ("first line\nsecondline\n", b"0>first line\n0>secondline\n"),
            (b"first line\nsecondline\n", b"0>first line\n0>secondline\n"),
        ]

        for test_input, expected_output in test_cases:
            out = gclient_utils.MakeFileAnnotated(
                io.BytesIO(), include_zero=True
            )
            out.write(test_input)
            self.assertEqual(out.getvalue(), expected_output)

    def testByteByByteInput(self):
        self.out.write(b"\xe2")
        self.out.write(b"\x9c")
        self.out.write(b"\x94")
        self.out.write(b"\n")
        self.out.write(b"\xe2")
        self.out.write(b"\n")
        self.assertEqual(self.out.getvalue(), b"\xe2\x9c\x94\n\xe2\n")

    def testByteByByteInput_Annotated(self):
        self.annotated.write(b"\xe2")
        self.annotated.write(b"\x9c")
        self.annotated.write(b"\x94")
        self.annotated.write(b"\n")
        self.annotated.write(b"\xe2")
        self.annotated.write(b"\n")
        self.assertEqual(self.annotated.getvalue(), b"0>\xe2\x9c\x94\n0>\xe2\n")

    def testFlush_Annotated(self):
        self.annotated.write(b"first line\nsecond line")
        self.assertEqual(self.annotated.getvalue(), b"0>first line\n")
        self.annotated.flush()
        self.assertEqual(
            self.annotated.getvalue(), b"0>first line\n0>second line\n"
        )


class SplitUrlRevisionTestCase(unittest.TestCase):
    def testSSHUrl(self):
        url = "ssh://test@example.com/test.git"
        rev = "ac345e52dc"
        out_url, out_rev = gclient_utils.SplitUrlRevision(url)
        self.assertEqual(out_rev, None)
        self.assertEqual(out_url, url)
        out_url, out_rev = gclient_utils.SplitUrlRevision("%s@%s" % (url, rev))
        self.assertEqual(out_rev, rev)
        self.assertEqual(out_url, url)
        url = "ssh://example.com/test.git"
        out_url, out_rev = gclient_utils.SplitUrlRevision(url)
        self.assertEqual(out_rev, None)
        self.assertEqual(out_url, url)
        out_url, out_rev = gclient_utils.SplitUrlRevision("%s@%s" % (url, rev))
        self.assertEqual(out_rev, rev)
        self.assertEqual(out_url, url)
        url = "ssh://example.com/git/test.git"
        out_url, out_rev = gclient_utils.SplitUrlRevision(url)
        self.assertEqual(out_rev, None)
        self.assertEqual(out_url, url)
        out_url, out_rev = gclient_utils.SplitUrlRevision("%s@%s" % (url, rev))
        self.assertEqual(out_rev, rev)
        self.assertEqual(out_url, url)
        rev = "test-stable"
        out_url, out_rev = gclient_utils.SplitUrlRevision("%s@%s" % (url, rev))
        self.assertEqual(out_rev, rev)
        self.assertEqual(out_url, url)
        url = "ssh://user-name@example.com/~/test.git"
        out_url, out_rev = gclient_utils.SplitUrlRevision(url)
        self.assertEqual(out_rev, None)
        self.assertEqual(out_url, url)
        out_url, out_rev = gclient_utils.SplitUrlRevision("%s@%s" % (url, rev))
        self.assertEqual(out_rev, rev)
        self.assertEqual(out_url, url)
        url = "ssh://user-name@example.com/~username/test.git"
        out_url, out_rev = gclient_utils.SplitUrlRevision(url)
        self.assertEqual(out_rev, None)
        self.assertEqual(out_url, url)
        out_url, out_rev = gclient_utils.SplitUrlRevision("%s@%s" % (url, rev))
        self.assertEqual(out_rev, rev)
        self.assertEqual(out_url, url)
        url = "git@github.com:dart-lang/spark.git"
        out_url, out_rev = gclient_utils.SplitUrlRevision(url)
        self.assertEqual(out_rev, None)
        self.assertEqual(out_url, url)
        out_url, out_rev = gclient_utils.SplitUrlRevision("%s@%s" % (url, rev))
        self.assertEqual(out_rev, rev)
        self.assertEqual(out_url, url)

    def testSVNUrl(self):
        url = "svn://example.com/test"
        rev = "ac345e52dc"
        out_url, out_rev = gclient_utils.SplitUrlRevision(url)
        self.assertEqual(out_rev, None)
        self.assertEqual(out_url, url)
        out_url, out_rev = gclient_utils.SplitUrlRevision("%s@%s" % (url, rev))
        self.assertEqual(out_rev, rev)
        self.assertEqual(out_url, url)

    def testRevisionStartingWithHyphenAllowed(self):
        url, rev = gclient_utils.SplitUrlRevision(
            "https://example.com/repo.git@-b"
        )
        self.assertEqual(url, "https://example.com/repo.git")
        self.assertEqual(rev, "-b")
        url, rev = gclient_utils.SplitUrlRevision(
            "https://chrome-infra-packages.appspot.com/pkg@-uRXiZeA4Yl-Nv-6jP69DyDs5cGroZgGsa1NHnVySQwC"
        )
        self.assertEqual(url, "https://chrome-infra-packages.appspot.com/pkg")
        self.assertEqual(rev, "-uRXiZeA4Yl-Nv-6jP69DyDs5cGroZgGsa1NHnVySQwC")

    def testInvalidUrlStartingWithHyphen(self):
        with self.assertRaises(gclient_utils.Error):
            gclient_utils.SplitUrlRevision("--upload-pack=foo@main")
        with self.assertRaises(gclient_utils.Error):
            gclient_utils.SplitUrlRevision("-u")


class ExtracRefNameTest(unittest.TestCase):
    def testMatchFound(self):
        self.assertEqual(
            "main",
            gclient_utils.ExtractRefName("origin", "refs/remote/origin/main"),
        )
        self.assertEqual(
            "1234", gclient_utils.ExtractRefName("origin", "refs/tags/1234")
        )
        self.assertEqual(
            "chicken",
            gclient_utils.ExtractRefName("origin", "refs/heads/chicken"),
        )

    def testNoMatch(self):
        self.assertIsNone(gclient_utils.ExtractRefName("origin", "abcbbb1234"))


class GClientUtilsTest(trial_dir.TestCase):
    def testHardToDelete(self):
        # Use the fact that tearDown will delete the directory to make it hard
        # to do so.
        l1 = os.path.join(self.root_dir, "l1")
        l2 = os.path.join(l1, "l2")
        l3 = os.path.join(l2, "l3")
        f3 = os.path.join(l3, "f3")
        os.mkdir(l1)
        os.mkdir(l2)
        os.mkdir(l3)
        gclient_utils.FileWrite(f3, "foo")
        os.chmod(f3, 0)
        os.chmod(l3, 0)
        os.chmod(l2, 0)
        os.chmod(l1, 0)

    def testRmtreeWithoutCmdExe(self) -> None:
        # On Windows, a tree whose path cmd.exe would interpret is removed in
        # Python, including read-only files such as git objects.
        tree = os.path.join(self.root_dir, "a&b%c^d")
        readonly = os.path.join(tree, "sub", "readonly")
        os.makedirs(os.path.dirname(readonly))
        gclient_utils.FileWrite(readonly, "foo")
        os.chmod(readonly, stat.S_IREAD)
        with (
            mock.patch("sys.platform", "win32"),
            mock.patch("gclient_utils.subprocess.call") as mock_call,
        ):
            gclient_utils.rmtree(tree)
        mock_call.assert_not_called()
        self.assertFalse(os.path.exists(tree))

    @unittest.skipUnless(sys.platform == "win32", "needs cmd.exe")
    def testRmtreeWithRdOnWindows(self) -> None:
        # Names that `rd` must still receive intact through the real cmd.exe.
        for name in ("with space", "parens (x86)", "bang!"):
            with self.subTest(name=name):
                tree = os.path.join(self.root_dir, name)
                os.makedirs(os.path.join(tree, "sub"))
                gclient_utils.FileWrite(os.path.join(tree, "sub", "f"), "foo")
                gclient_utils.rmtree(tree)
                self.assertFalse(os.path.exists(tree))

    @unittest.skipIf(sys.platform == "win32", "needs POSIX file names")
    def testRmtreePosixDoesNotUseCmdExeOrShutil(self) -> None:
        for name in (
            "ordinary",
            *[
                f"a{c}b"
                for c in sorted(subprocess2.CMD_EXE_METACHARACTERS)
                if c not in "\r\n"
            ],
        ):
            with self.subTest(name=name):
                tree = os.path.join(self.root_dir, name)
                leaf = os.path.join(tree, "sub")
                nested = os.path.join(leaf, "file")
                os.makedirs(leaf)
                gclient_utils.FileWrite(nested, "foo")
                os.chmod(nested, 0)
                os.chmod(leaf, 0)
                os.chmod(tree, 0)
                with (
                    mock.patch("sys.platform", "linux"),
                    mock.patch("gclient_utils.subprocess.call") as mock_call,
                    mock.patch(
                        "gclient_utils.shutil.rmtree"
                    ) as mock_shutil_rmtree,
                ):
                    gclient_utils.rmtree(tree)
                self.assertFalse(os.path.exists(tree))
                mock_call.assert_not_called()
                mock_shutil_rmtree.assert_not_called()

    def testUpgradeToHttps(self):
        values = [
            ["", ""],
            [None, None],
            ["foo", "https://foo"],
            ["http://foo", "https://foo"],
            ["foo/", "https://foo/"],
            ["ssh-svn://foo", "ssh-svn://foo"],
            ["ssh-svn://foo/bar/", "ssh-svn://foo/bar/"],
            ["codereview.chromium.org", "https://codereview.chromium.org"],
            ["codereview.chromium.org/", "https://codereview.chromium.org/"],
            [
                "chromium-review.googlesource.com",
                "https://chromium-review.googlesource.com",
            ],
            [
                "chromium-review.googlesource.com/",
                "https://chromium-review.googlesource.com/",
            ],
            ["http://foo:10000", "http://foo:10000"],
            ["http://foo:10000/bar", "http://foo:10000/bar"],
            ["foo:10000", "http://foo:10000"],
            ["foo:", "https://foo:"],
        ]
        for content, expected in values:
            self.assertEqual(expected, gclient_utils.UpgradeToHttps(content))

    def testParseCodereviewSettingsContent(self):
        values = [
            ["# bleh\n", {}],
            ["\t# foo : bar\n", {}],
            ["Foo:bar", {"Foo": "bar"}],
            ["Foo:bar:baz\n", {"Foo": "bar:baz"}],
            [" Foo : bar ", {"Foo": "bar"}],
            [" Foo : bar \n", {"Foo": "bar"}],
            ["a:b\n\rc:d\re:f", {"a": "b", "c": "d", "e": "f"}],
            ["an_url:http://value/", {"an_url": "http://value/"}],
            [
                "CODE_REVIEW_SERVER : http://r/s",
                {"CODE_REVIEW_SERVER": "https://r/s"},
            ],
            ["VIEW_VC:http://r/s", {"VIEW_VC": "https://r/s"}],
        ]
        for content, expected in values:
            self.assertEqual(
                expected, gclient_utils.ParseCodereviewSettingsContent(content)
            )

    def testFileRead_Bytes(self):
        with gclient_utils.temporary_file() as tmp:
            gclient_utils.FileWrite(
                tmp, b"foo \xe2\x9c bar", mode="wb", encoding=None
            )
            self.assertEqual("foo \ufffd bar", gclient_utils.FileRead(tmp))

    def testFileRead_Unicode(self):
        with gclient_utils.temporary_file() as tmp:
            gclient_utils.FileWrite(tmp, "foo ✔ bar")
            self.assertEqual("foo ✔ bar", gclient_utils.FileRead(tmp))

    def testTemporaryFile(self):
        with gclient_utils.temporary_file() as tmp:
            gclient_utils.FileWrite(tmp, "test")
            self.assertEqual("test", gclient_utils.FileRead(tmp))
        self.assertFalse(os.path.exists(tmp))

    def testMergeConditions(self):
        self.assertEqual(None, gclient_utils.merge_conditions(None, None))

        self.assertEqual("foo", gclient_utils.merge_conditions("foo", None))

        self.assertEqual("foo", gclient_utils.merge_conditions(None, "foo"))

        self.assertEqual(
            "(foo) and (bar)", gclient_utils.merge_conditions("foo", "bar")
        )

        self.assertEqual(
            "(foo or bar) and (baz)",
            gclient_utils.merge_conditions("foo or bar", "baz"),
        )

    def testIsEnvAi(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(gclient_utils.IsEnvAi())
            self.assertEqual(gclient_utils.GetAiAgentEnvVars(), [])
        with mock.patch.dict(os.environ, {"GEMINI_CLI": "1"}, clear=True):
            self.assertTrue(gclient_utils.IsEnvAi())
            self.assertEqual(gclient_utils.GetAiAgentEnvVars(), ["GEMINI_CLI"])
        with mock.patch.dict(os.environ, {"COPILOT_CLI": "1"}, clear=True):
            self.assertTrue(gclient_utils.IsEnvAi())
            self.assertEqual(gclient_utils.GetAiAgentEnvVars(), ["COPILOT_CLI"])
        with mock.patch.dict(os.environ, {"AI_AGENT": "true"}, clear=True):
            self.assertTrue(gclient_utils.IsEnvAi())
            self.assertEqual(gclient_utils.GetAiAgentEnvVars(), ["AI_AGENT"])

        for falsey_val in ("", "0", "false", "FALSE"):
            with mock.patch.dict(
                os.environ, {"GEMINI_CLI": falsey_val}, clear=True
            ):
                self.assertFalse(gclient_utils.IsEnvAi())
                self.assertEqual(gclient_utils.GetAiAgentEnvVars(), [])

        self.assertFalse(gclient_utils.IsEnvAi({"GEMINI_CLI": None}))
        self.assertFalse(
            gclient_utils.IsEnvAi({"GEMINI_CLI": "0", "AI_AGENT": "false"})
        )
        self.assertTrue(
            gclient_utils.IsEnvAi({"GEMINI_CLI": "0", "AI_AGENT": "1"})
        )
        self.assertEqual(
            gclient_utils.GetAiAgentEnvVars(
                {"GEMINI_CLI": "0", "AI_AGENT": "1"}
            ),
            ["AI_AGENT"],
        )


class RmtreeWin32Test(unittest.TestCase):
    """Tests the Windows branch of rmtree() with sys.platform patched."""

    CMD_EXE = r"C:\Windows\System32\cmd.exe"

    def setUp(self) -> None:
        self.addCleanup(mock.patch.stopall)
        mock.patch("sys.platform", "win32").start()
        mock.patch.dict(os.environ, {"COMSPEC": self.CMD_EXE}).start()
        self.mock_sleep = mock.patch("time.sleep").start()
        self.mock_call = mock.patch(
            "gclient_utils.subprocess.call", return_value=0
        ).start()
        self.mock_shutil_rmtree = mock.patch(
            "gclient_utils.shutil.rmtree"
        ).start()
        # Make every path look like an existing directory.
        mock.patch("os.path.exists", return_value=True).start()
        mock.patch("os.path.isdir", return_value=True).start()
        mock.patch("os.path.islink", return_value=False).start()

    def _rd_cmd(self, path: str, cmd_exe: str = CMD_EXE) -> list[str]:
        return [cmd_exe, "/d", "/v:off", "/c", "rd", "/q", "/s", path]

    def testOrdinaryPathsUseRd(self) -> None:
        # Spaces, parentheses and `!` (with delayed expansion off) are not
        # special on a plain cmd.exe command line, so such paths must keep
        # going through `rd`.
        for path, expected in (
            # The case is kept, and only `/` is converted.
            (r"C:\src\third_party\Foo", r"C:\src\third_party\Foo"),
            (r"C:\Program Files (x86)\Foo", r"C:\Program Files (x86)\Foo"),
            (r"C:\src\some dir\wow!", r"C:\src\some dir\wow!"),
            ("relative/dep", r"relative\dep"),
        ):
            with self.subTest(path=path):
                self.mock_call.reset_mock()
                gclient_utils.rmtree(path)
                self.mock_call.assert_called_once_with(self._rd_cmd(expected))
        self.mock_shutil_rmtree.assert_not_called()

    def testCmdExePath(self) -> None:
        for env, expected in (
            (
                {"COMSPEC": r"D:\Win\System32\cmd.exe"},
                r"D:\Win\System32\cmd.exe",
            ),
            # A missing, empty, relative or drive-relative COMSPEC is not used,
            # so that a cmd.exe in the current directory is never run.
            ({"SYSTEMROOT": r"D:\Win"}, r"D:\Win\System32\cmd.exe"),
            (
                {"COMSPEC": "", "SYSTEMROOT": r"D:\Win"},
                r"D:\Win\System32\cmd.exe",
            ),
            ({"COMSPEC": "cmd.exe"}, r"C:\Windows\System32\cmd.exe"),
            ({"COMSPEC": r"\cmd.exe"}, r"C:\Windows\System32\cmd.exe"),
            ({"SYSTEMROOT": "win"}, r"C:\Windows\System32\cmd.exe"),
            ({"COMSPEC": "D:cmd.exe"}, r"C:\Windows\System32\cmd.exe"),
            (
                {"COMSPEC": r"\\server\share\cmd.exe"},
                r"\\server\share\cmd.exe",
            ),
        ):
            with (
                self.subTest(env=env),
                mock.patch.dict(os.environ, env, clear=True),
            ):
                self.mock_call.reset_mock()
                gclient_utils.rmtree(r"C:\src\foo")
                self.mock_call.assert_called_once_with(
                    self._rd_cmd(r"C:\src\foo", expected)
                )

    def testRdIsRetriedBeforeGivingUp(self) -> None:
        self.mock_call.return_value = 1
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            with self.assertRaisesRegex(Exception, "Failed to remove path"):
                gclient_utils.rmtree(r"C:\src\foo")
        self.assertEqual(3, self.mock_call.call_count)
        self.assertEqual(3, self.mock_sleep.call_count)
        self.assertIn("rd exited with code 1", stderr.getvalue())

    def testPathsRdWouldNotGetIntactNeverReachCmdExe(self) -> None:
        # cmd.exe metacharacters, `rd` argument separators, and any control or
        # non-ASCII character, e.g. the ideographic space U+3000 or U+212A,
        # which lowercases to `k`.
        for char in '&|<>^%",;=\r\n\t\x0b\x0c\xa0\xff\u3000\u00e9\u212a':
            path = rf"C:\src\dep{char}x"
            with self.subTest(char=char):
                self.mock_shutil_rmtree.reset_mock()
                gclient_utils.rmtree(path)
                self.mock_shutil_rmtree.assert_called_once_with(
                    path, onerror=gclient_utils._clear_readonly_and_retry
                )
        # Byte paths are decoded first.
        self.mock_shutil_rmtree.reset_mock()
        gclient_utils.rmtree(b"C:\\src\\dep&x")
        self.mock_shutil_rmtree.assert_called_once_with(
            r"C:\src\dep&x", onerror=gclient_utils._clear_readonly_and_retry
        )
        self.mock_call.assert_not_called()

    def testPythonRemovalIsRetriedBeforeGivingUp(self) -> None:
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            self.mock_shutil_rmtree.side_effect = [
                PermissionError("busy"),
                None,
            ]
            gclient_utils.rmtree(r"C:\src\a&b")
            self.assertEqual(2, self.mock_shutil_rmtree.call_count)
            self.assertEqual(1, self.mock_sleep.call_count)

            self.mock_shutil_rmtree.reset_mock()
            self.mock_shutil_rmtree.side_effect = PermissionError("busy")
            self.mock_sleep.reset_mock()
            with self.assertRaisesRegex(Exception, "Failed to remove path"):
                gclient_utils.rmtree(r"C:\src\a&b")
            self.assertEqual(3, self.mock_shutil_rmtree.call_count)
            self.assertEqual(3, self.mock_sleep.call_count)
        self.assertIn("busy", stderr.getvalue())
        self.mock_call.assert_not_called()

    def testClearReadonlyAndRetry(self) -> None:
        subpath = r"C:\src\a&b\.git\objects\pack\readonly.pack"
        error = PermissionError("read-only")
        exc_info = (PermissionError, error, None)
        with mock.patch("os.chmod") as mock_chmod:
            # Removals are retried after clearing the read-only attribute.
            for func in (os.unlink, os.remove, os.rmdir):
                with (
                    self.subTest(func=func.__name__),
                    mock.patch.object(os, func.__name__) as mock_func,
                ):
                    mock_chmod.reset_mock()
                    gclient_utils._clear_readonly_and_retry(
                        mock_func, subpath, exc_info
                    )
                    mock_chmod.assert_called_once_with(subpath, stat.S_IWRITE)
                    mock_func.assert_called_once_with(subpath)
            # An entry that is already gone is fine, whatever noticed it.
            gone = (FileNotFoundError, FileNotFoundError("gone"), None)
            for name in ("unlink", "rmdir", "lstat", "scandir"):
                with (
                    self.subTest(gone=name),
                    mock.patch.object(os, name) as mock_func,
                ):
                    mock_chmod.reset_mock()
                    gclient_utils._clear_readonly_and_retry(
                        mock_func, subpath, gone
                    )
                    mock_chmod.assert_not_called()
                    mock_func.assert_not_called()
            # Other errors, e.g. a junction or an unreadable directory, are
            # re-raised.
            mock_chmod.reset_mock()
            for name, func in (
                ("islink", os.path.islink),
                ("scandir", os.scandir),
                ("lstat", os.lstat),
            ):
                with self.subTest(func=name):
                    with self.assertRaises(PermissionError):
                        gclient_utils._clear_readonly_and_retry(
                            func, subpath, exc_info
                        )
            mock_chmod.assert_not_called()


class IsGitShaTest(unittest.TestCase):
    def testIsFullGitSha(self):
        # A full object name is 40 hex chars for SHA-1 or 64 for SHA-256.
        self.assertTrue(gclient_utils.IsFullGitSha("a" * 40))
        self.assertTrue(gclient_utils.IsFullGitSha("0" * 64))
        self.assertTrue(
            gclient_utils.IsFullGitSha(
                "0123456789abcdef0123456789abcdef01234567"
            )
        )

    def testIsFullGitShaRejectsInvalid(self):
        # Abbreviated, invalid-length (41-63), over-length, and non-hex values
        # are not full shas.
        self.assertFalse(gclient_utils.IsFullGitSha("a" * 39))
        self.assertFalse(gclient_utils.IsFullGitSha("a" * 41))
        self.assertFalse(gclient_utils.IsFullGitSha("a" * 63))
        self.assertFalse(gclient_utils.IsFullGitSha("a" * 65))
        self.assertFalse(gclient_utils.IsFullGitSha("z" * 40))

    def testIsGitSha(self):
        # Abbreviated (>=6 hex) through a full SHA-256 (64) are accepted.
        self.assertTrue(gclient_utils.IsGitSha("abcdef"))
        self.assertTrue(gclient_utils.IsGitSha("a" * 40))
        self.assertTrue(gclient_utils.IsGitSha("a" * 64))

    def testIsGitShaRejectsInvalid(self):
        self.assertFalse(gclient_utils.IsGitSha("abc"))
        self.assertFalse(gclient_utils.IsGitSha("a" * 65))
        self.assertFalse(gclient_utils.IsGitSha("z" * 40))


if __name__ == "__main__":
    unittest.main()


class SafeReplaceTest(unittest.TestCase):
    def setUp(self):
        self.mock_os = mock.patch("gclient_utils.os").start()
        self.addCleanup(mock.patch.stopall)

    def testReplace(self):
        gclient_utils.safe_replace("old", "new")
        self.mock_os.replace.assert_called_with("old", "new")

    def testReplaceRetry(self):
        self.mock_os.replace.side_effect = [OSError, OSError, None]
        with mock.patch("time.sleep") as mock_sleep:
            gclient_utils.safe_replace("old", "new")
            self.assertEqual(self.mock_os.replace.call_count, 3)
            self.assertEqual(mock_sleep.call_count, 2)

    def testReplaceFailure(self):
        self.mock_os.replace.side_effect = OSError
        with mock.patch("time.sleep"):
            with self.assertRaises(OSError):
                gclient_utils.safe_replace("old", "new")


# vim: ts=2:sw=2:tw=80:et:
