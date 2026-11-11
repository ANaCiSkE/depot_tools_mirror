#!/usr/bin/env python3
# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import io
import os.path
import sys
import unittest
from unittest import mock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import gclient_utils  # noqa: E402
import presubmit_support  # noqa: E402
import subprocess2  # noqa: E402
from testing_support import fake_repos  # noqa: E402


class PresubmitSupportTest(unittest.TestCase):
    def test_environ(self):
        self.assertIsNone(os.environ.get("PRESUBMIT_FOO_ENV", None))
        kv = {"PRESUBMIT_FOO_ENV": "FOOBAR"}
        with presubmit_support.setup_environ(kv):
            self.assertEqual(
                os.environ.get("PRESUBMIT_FOO_ENV", None), "FOOBAR"
            )
        self.assertIsNone(os.environ.get("PRESUBMIT_FOO_ENV", None))


class ProvidedDiffChangeFakeRepo(fake_repos.FakeReposBase):
    NB_GIT_REPOS = 1

    def populateGit(self):
        self._commit_git(
            "repo_1",
            {
                "to_be_modified": "please change me\n",
                "to_be_deleted": "delete\nme\n",
                "somewhere/else": "not a top level file!\n",
            },
        )
        self._commit_git(
            "repo_1",
            {
                "to_be_modified": "changed me!\n",
                "to_be_deleted": None,
                "somewhere/else": "still not a top level file!\n",
                "added": "a new file\n",
            },
        )


class ProvidedDiffChangeTest(fake_repos.FakeReposTestBase):
    FAKE_REPOS_CLASS = ProvidedDiffChangeFakeRepo

    def setUp(self):
        super(ProvidedDiffChangeTest, self).setUp()
        self.enabled = self.FAKE_REPOS.set_up_git()
        if not self.enabled:
            self.skipTest("git fake repos not available")
        self.repo = os.path.join(self.FAKE_REPOS.git_base, "repo_1")
        diff = subprocess2.check_output(["git", "show"], cwd=self.repo).decode(
            "utf-8"
        )
        self.change = self._create_change(diff)

    def _create_change(self, diff):
        with gclient_utils.temporary_file() as tmp:
            gclient_utils.FileWrite(tmp, diff)
            options = mock.Mock(
                root=self.repo,
                all_files=False,
                generate_diff=False,
                description="description",
                files=None,
                diff_file=tmp,
                reviewers=[],
            )
            change = presubmit_support._parse_change(None, options)
            assert isinstance(change, presubmit_support.ProvidedDiffChange)
            return change

    def _get_affected_file_from_name(self, change, name):
        for file in change._affected_files:
            if file.LocalPath() == os.path.normpath(name):
                return file
        self.fail(f"No file named {name}")

    def _test(self, name, old, new):
        affected_file = self._get_affected_file_from_name(self.change, name)
        self.assertEqual(affected_file.OldContents(), old)
        self.assertEqual(affected_file.NewContents(), new)

    def test_old_contents_of_added_file_returns_empty(self):
        self._test("added", [], ["a new file"])

    def test_old_contents_of_deleted_file_returns_whole_file(self):
        self._test("to_be_deleted", ["delete", "me"], [])

    def test_old_contents_of_modified_file(self):
        self._test("to_be_modified", ["please change me"], ["changed me!"])

    def test_old_contents_of_file_with_nested_dirs(self):
        self._test(
            "somewhere/else",
            ["not a top level file!"],
            ["still not a top level file!"],
        )

    def test_changed_contents_of_modified_file(self):
        diff = "\n".join(
            [
                "diff --git a/foo b/foo",
                "index d7ba659f..b7957f3 100644",
                "--- a/foo",
                "+++ b/foo",
                "%s",
                "-  foo1",
                "+  foo2",
            ]
        )

        def test(hunk):
            change = self._create_change(diff % hunk)
            afs = change.AffectedFiles()
            self.assertEqual(len(afs), 1)
            return afs[0].ChangedContents()

        self.assertEqual(test("@@ -1,1 +1,1 @@"), [(1, "  foo2")])
        self.assertEqual(test("@@ -290,1 +290 @@"), [(290, "  foo2")])
        self.assertEqual(test("@@ -291 +291 @@"), [(291, "  foo2")])
        self.assertEqual(test("@@ -292 +292,1 @@"), [(292, "  foo2")])
        self.assertEqual(test("@@ -293,1 +293,1 @@"), [(293, "  foo2")])

    def test_changed_contents_ignores_embedded_cr_and_unicode_separators(self):
        diff = "\n".join(
            [
                "diff --git a/foo b/foo",
                "index d7ba659f..b7957f3 100644",
                "--- a/foo",
                "+++ b/foo",
                "@@ -1,1 +1,2 @@",
                "+safe\r@@ -99 +99 @@\rhidden_violation",
                "+line2\u2028hidden_u2028\u2029hidden_u2029",
            ]
        )
        change = self._create_change(diff)
        afs = change.AffectedFiles()
        self.assertEqual(len(afs), 1)
        self.assertEqual(
            afs[0].ChangedContents(),
            [
                (1, "safe\r@@ -99 +99 @@\rhidden_violation"),
                (2, "line2\u2028hidden_u2028\u2029hidden_u2029"),
            ],
        )

    def test_old_and_new_contents_ignore_embedded_cr_and_unicode_separators(
        self,
    ):
        raw_old = "old1\rold_cr\x0cold_ff\nold2\u2028old_ls\u2029old_ps\n"
        raw_new = (
            "new1\rnew_cr\x0cnew_ff\nnew2\u2028new_ls\u2029new_ps\x85new_nel\n"
        )
        diff_cache = mock.MagicMock()
        diff_cache.GetOldContents.return_value = raw_old
        af = presubmit_support.GitAffectedFile(
            "foo.py", "M", self.repo, diff_cache
        )
        with mock.patch("gclient_utils.FileRead", return_value=raw_new):
            self.assertEqual(
                af.OldContents(),
                [
                    "old1\rold_cr\x0cold_ff",
                    "old2\u2028old_ls\u2029old_ps",
                ],
            )
            self.assertEqual(
                af.NewContents(),
                [
                    "new1\rnew_cr\x0cnew_ff",
                    "new2\u2028new_ls\u2029new_ps\x85new_nel",
                ],
            )

    def test_git_change_generate_diff_hardened_against_embedded_dev_null(self):
        raw_git_diff = "\n".join(
            [
                "diff --git a/DEPS b/DEPS",
                "new file mode 100644",
                "index 0000000..1111111",
                "--- /dev/null",
                "+++ b/DEPS",
                "@@ -0,0 +1,2 @@",
                "+# \r--- /dev/null\rdiff --git a/ghost b/ghost",
                "+bad_dep_line",
                "diff --git a/flags.txt b/flags.txt",
                "index 2222222..3333333 100644",
                "--- a/flags.txt",
                "+++ b/flags.txt",
                "@@ -1 +0,0 @@",
                "--- /dev/null",
                "",
            ]
        )
        with (
            mock.patch("scm.GIT.Capture", return_value=raw_git_diff),
            mock.patch("scm.GIT.ListSubmodules", return_value=[]),
        ):
            change = presubmit_support.GitChange(
                "mychange",
                "description",
                self.repo,
                [("A", "DEPS"), ("M", "flags.txt")],
                0,
                0,
                None,
                upstream="origin/main",
                end_commit="HEAD",
            )
            afs = {af.LocalPath(): af for af in change.AffectedFiles()}
            self.assertEqual(
                afs["DEPS"].ChangedContents(),
                [
                    (1, "# \r--- /dev/null\rdiff --git a/ghost b/ghost"),
                    (2, "bad_dep_line"),
                ],
            )
            self.assertEqual(afs["flags.txt"].ChangedContents(), [])

    def test_unix_local_paths(self):
        if sys.platform == "win32":
            self.assertIn(r"somewhere\else", self.change.LocalPaths())
        else:
            self.assertIn("somewhere/else", self.change.LocalPaths())
        self.assertIn("somewhere/else", self.change.UnixLocalPaths())


class TestGenerateDiff(fake_repos.FakeReposTestBase):
    """Tests for --generate_diff.

    The option is used to generate diffs of given files against the upstream
    server as base.
    """

    FAKE_REPOS_CLASS = ProvidedDiffChangeFakeRepo

    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.FAKE_REPOS.git_base, "repo_1")
        self.parser = mock.Mock()
        self.parser.error.side_effect = SystemExit

    def test_with_diff_file(self):
        """Tests that only either --generate_diff or --diff_file is allowed."""
        options = mock.Mock(
            root=self.repo,
            all_files=False,
            generate_diff=True,
            description="description",
            files=None,
            diff_file="patch.diff",
        )
        with self.assertRaises(SystemExit):
            presubmit_support._parse_change(self.parser, options)

        self.parser.error.assert_called_once_with(
            "<diff_file> cannot be specified when <generate_diff> is set.",
        )

    @mock.patch("presubmit_diff.create_diffs")
    def test_with_all_files(self, create_diffs):
        """Ensures --generate_diff is noop if --all_files is specified."""
        options = mock.Mock(
            root=self.repo,
            all_files=True,
            generate_diff=True,
            description="description",
            files=None,
            source_controlled_only=False,
            diff_file=None,
            reviewers=[],
        )
        changes = presubmit_support._parse_change(self.parser, options)
        self.assertEqual(
            changes.AllFiles(), ["added", "somewhere/else", "to_be_modified"]
        )
        create_diffs.assert_not_called()

    @mock.patch("presubmit_diff.fetch_content")
    def test_with_files(self, fetch_content):
        """Tests --generate_diff with files, which should call create_diffs()."""
        # fetch_content would return the old content of a given file.
        # In this test case, the mocked file is a newly added file.
        # hence, empty content.
        fetch_content.side_effect = [""]
        options = mock.Mock(
            root=self.repo,
            all_files=False,
            gerrit_url="https://chromium.googlesource.com",
            generate_diff=True,
            description="description",
            files=["added"],
            source_controlled_only=False,
            diff_file=None,
            reviewers=[],
        )
        change = presubmit_support._parse_change(self.parser, options)
        affected_files = change.AffectedFiles()
        self.assertEqual(len(affected_files), 1)
        self.assertEqual(affected_files[0].LocalPath(), "added")


class TestParseDiff(unittest.TestCase):
    """A suite of tests related to diff parsing and processing."""

    def _test_diff_to_change_files(self, diff, expected):
        with gclient_utils.temporary_file() as tmp:
            gclient_utils.FileWrite(tmp, diff, mode="w+")
            content, change_files = presubmit_support._process_diff_file(tmp)
            self.assertCountEqual(content, diff)
            self.assertCountEqual(change_files, expected)

    def test_diff_to_change_files_raises_on_empty_diff_header(self):
        diff = """
diff --git a/foo b/foo

"""
        with self.assertRaises(presubmit_support.PresubmitFailure):
            self._test_diff_to_change_files(diff=diff, expected=[])

    def test_diff_to_change_files_simple_add(self):
        diff = """
diff --git a/foo b/foo
new file mode 100644
index 0000000..9daeafb
--- /dev/null
+++ b/foo
@@ -0,0 +1 @@
+add
"""
        self._test_diff_to_change_files(diff=diff, expected=[("A", "foo")])

    def test_diff_to_change_files_simple_delete(self):
        diff = """
diff --git a/foo b/foo
deleted file mode 100644
index f675c2a..0000000
--- a/foo
+++ /dev/null
@@ -1,1 +0,0 @@
-delete
"""
        self._test_diff_to_change_files(diff=diff, expected=[("D", "foo")])

    def test_diff_to_change_files_simple_modification(self):
        diff = """
diff --git a/foo b/foo
index d7ba659f..b7957f3 100644
--- a/foo
+++ b/foo
@@ -29,7 +29,7 @@
other
random
text
-  foo1
+  foo2
other
random
text
"""
        self._test_diff_to_change_files(diff=diff, expected=[("M", "foo")])

    def test_diff_to_change_files_multiple_changes(self):
        diff = """
diff --git a/foo b/foo
index d7ba659f..b7957f3 100644
--- a/foo
+++ b/foo
@@ -29,7 +29,7 @@
other
random
text
-  foo1
+  foo2
other
random
text
diff --git a/bar b/bar
new file mode 100644
index 0000000..9daeafb
--- /dev/null
+++ b/bar
@@ -0,0 +1 @@
+add
diff --git a/baz b/baz
deleted file mode 100644
index f675c2a..0000000
--- a/baz
+++ /dev/null
@@ -1,1 +0,0 @@
-delete
"""
        self._test_diff_to_change_files(
            diff=diff, expected=[("M", "foo"), ("A", "bar"), ("D", "baz")]
        )

    def test_parse_unified_diff_with_valid_diff(self):
        diff = """
diff --git a/foo b/foo
new file mode 100644
index 0000000..9daeafb
--- /dev/null
+++ b/foo
@@ -0,0 +1 @@
+add
"""
        res = presubmit_support._parse_unified_diff(diff)
        self.assertCountEqual(
            res,
            {
                "foo": """
new file mode 100644
index 0000000..9daeafb
--- /dev/null
+++ b/foo
@@ -0,0 +1 @@
+add
"""
            },
        )

    def test_parse_unified_diff_with_valid_diff_noprefix(self):
        diff = """
diff --git foo foo
new file mode 100644
index 0000000..9daeafb
--- /dev/null
+++ foo
@@ -0,0 +1 @@
+add
"""
        res = presubmit_support._parse_unified_diff(diff)
        self.assertCountEqual(
            res,
            {
                "foo": """
new file mode 100644
index 0000000..9daeafb
--- /dev/null
+++ foo
@@ -0,0 +1 @@
+add
"""
            },
        )

    def test_parse_unified_diff_with_invalid_diff(self):
        diff = """
diff --git a/ffoo b/foo
"""
        with self.assertRaises(presubmit_support.PresubmitFailure):
            presubmit_support._parse_unified_diff(diff)

    def test_parse_unified_diff_duplicate_file_section_raises(self):
        diff = "\n".join(
            [
                "diff --git a/foo b/foo",
                "index 1111111..2222222 100644",
                "--- a/foo",
                "+++ b/foo",
                "@@ -1 +1 @@",
                "-old",
                "+new",
                "diff --git a/foo b/foo",
                "index 2222222..3333333 100644",
                "--- a/foo",
                "+++ b/foo",
                "@@ -1 +1 @@",
                "-new",
                "+forged",
                "",
            ]
        )
        with self.assertRaisesRegex(
            presubmit_support.PresubmitFailure,
            "Duplicate diff section for foo",
        ):
            presubmit_support._parse_unified_diff(diff)

        # A deleted file section followed by a non-'new file mode' section for
        # the same path must also be rejected.
        non_typechange_dup = "\n".join(
            [
                "diff --git a/foo b/foo",
                "deleted file mode 100644",
                "index 1111111..0000000",
                "--- a/foo",
                "+++ /dev/null",
                "@@ -1 +0,0 @@",
                "-old",
                "diff --git a/foo b/foo",
                "index 2222222..3333333 100644",
                "--- a/foo",
                "+++ b/foo",
                "@@ -1 +1 @@",
                "-new",
                "+forged",
                "",
            ]
        )
        with self.assertRaisesRegex(
            presubmit_support.PresubmitFailure,
            "Duplicate diff section for foo",
        ):
            presubmit_support._parse_unified_diff(non_typechange_dup)

    def test_parse_unified_diff_git_typechange_merges_and_marks_modified(self):
        diff = "\n".join(
            [
                "diff --git a/foo b/foo",
                "deleted file mode 100644",
                "index 1111111..0000000",
                "--- a/foo",
                "+++ /dev/null",
                "@@ -1 +0,0 @@",
                "-regular_content",
                "diff --git a/foo b/foo",
                "new file mode 120000",
                "index 0000000..2222222",
                "--- /dev/null",
                "+++ b/foo",
                "@@ -0,0 +1 @@",
                "+symlink_target",
                "",
            ]
        )
        parsed = presubmit_support._parse_unified_diff(diff)
        self.assertEqual(list(parsed.keys()), ["foo"])
        self.assertIn("deleted file mode 100644\n", parsed["foo"])
        self.assertIn("new file mode 120000\n", parsed["foo"])
        self.assertEqual(
            presubmit_support._diffs_to_change_files(parsed),
            [("M", "foo")],
        )

        # A third section for the same path after a valid typechange must still
        # be rejected.
        triple_diff = diff + "\n".join(
            [
                "diff --git a/foo b/foo",
                "new file mode 100644",
                "index 0000000..3333333",
                "--- /dev/null",
                "+++ b/foo",
                "@@ -0,0 +1 @@",
                "+extra",
                "",
            ]
        )
        with self.assertRaisesRegex(
            presubmit_support.PresubmitFailure,
            "Duplicate diff section for foo",
        ):
            presubmit_support._parse_unified_diff(triple_diff)

    def test_parse_unified_diff_embedded_cr_and_unicode_do_not_forge_headers(
        self,
    ):
        for sep in ("\r", "\u2028", "\u2029", "\x85"):
            diff = "\n".join(
                [
                    "diff --git a/DEPS b/DEPS",
                    "index 1111111..2222222 100644",
                    "--- a/DEPS",
                    "+++ b/DEPS",
                    "@@ -1 +1 @@",
                    "+real_violation",
                    "diff --git a/zzz.py b/zzz.py",
                    "new file mode 100644",
                    "--- /dev/null",
                    "+++ b/zzz.py",
                    "@@ -0,0 +1,2 @@",
                    f"+carrier{sep}diff --git a/DEPS b/DEPS",
                    "+@@ -1 +1 @@",
                    "",
                ]
            )
            res = presubmit_support._parse_unified_diff(diff)
            self.assertIn("+real_violation\n", res["DEPS"])
            self.assertNotIn("carrier", res["DEPS"])
            self.assertIn(
                f"+carrier{sep}diff --git a/DEPS b/DEPS\n", res["zzz.py"]
            )

    def test_diffs_to_change_files_with_empty_diff(self):
        res = presubmit_support._diffs_to_change_files({"file": ""})
        self.assertEqual(res, [("M", "file")])


class PresubmitResultLocationTest(unittest.TestCase):
    def test_invalid_missing_filepath(self):
        with self.assertRaisesRegex(ValueError, "file path is required"):
            presubmit_support._PresubmitResultLocation(file_path="").validate()

    def test_invalid_abs_filepath_except_for_commit_msg(self):
        loc = presubmit_support._PresubmitResultLocation(file_path="/foo")
        with self.assertRaisesRegex(
            ValueError, "file path must be relative path"
        ):
            loc.validate()
        loc = presubmit_support._PresubmitResultLocation(
            file_path="/COMMIT_MSG"
        )
        try:
            loc.validate()
        except ValueError:
            self.fail("validate should not fail for /COMMIT_MSG path")

    def test_invalid_end_line_without_start_line(self):
        loc = presubmit_support._PresubmitResultLocation(
            file_path="foo", end_line=5
        )
        with self.assertRaisesRegex(ValueError, "end_line must be empty"):
            loc.validate()

    def test_invalid_start_col_without_start_line(self):
        loc = presubmit_support._PresubmitResultLocation(
            file_path="foo", start_col=5
        )
        with self.assertRaisesRegex(ValueError, "start_col must be empty"):
            loc.validate()

    def test_invalid_end_col_without_start_line(self):
        loc = presubmit_support._PresubmitResultLocation(
            file_path="foo", end_col=5
        )
        with self.assertRaisesRegex(ValueError, "end_col must be empty"):
            loc.validate()

    def test_invalid_negative_start_line(self):
        loc = presubmit_support._PresubmitResultLocation(
            file_path="foo", start_line=-1
        )
        with self.assertRaisesRegex(
            ValueError, "start_line MUST not be negative"
        ):
            loc.validate()

    def test_invalid_non_positive_end_line(self):
        loc = presubmit_support._PresubmitResultLocation(
            file_path="foo", start_line=1, end_line=0
        )
        with self.assertRaisesRegex(ValueError, "end_line must be positive"):
            loc.validate()

    def test_invalid_negative_start_col(self):
        loc = presubmit_support._PresubmitResultLocation(
            file_path="foo", start_line=1, end_line=1, start_col=-1
        )
        with self.assertRaisesRegex(
            ValueError, "start_col MUST not be negative"
        ):
            loc.validate()

    def test_invalid_negative_end_col(self):
        loc = presubmit_support._PresubmitResultLocation(
            file_path="foo", start_line=1, end_line=1, end_col=-1
        )
        with self.assertRaisesRegex(ValueError, "end_col MUST not be negative"):
            loc.validate()

    def test_invalid_start_after_end_line(self):
        loc = presubmit_support._PresubmitResultLocation(
            file_path="foo", start_line=6, end_line=5
        )
        with self.assertRaisesRegex(ValueError, "must not be after"):
            loc.validate()

    def test_invalid_start_after_end_col(self):
        loc = presubmit_support._PresubmitResultLocation(
            file_path="foo", start_line=5, start_col=11, end_line=5, end_col=10
        )
        with self.assertRaisesRegex(ValueError, "must not be after"):
            loc.validate()


class PresubmitResultTest(unittest.TestCase):
    def test_handle_message_only(self):
        result = presubmit_support._PresubmitResult("Simple message")
        out = io.StringIO()
        result.handle(out)
        self.assertEqual(out.getvalue(), "Simple message\n")

    def test_handle_full_args(self):
        result = presubmit_support._PresubmitResult(
            "This is a message",
            items=["item1", "item2"],
            long_text="Long text here.",
            locations=[
                presubmit_support._PresubmitResultLocation(
                    file_path=presubmit_support._PresubmitResultLocation.COMMIT_MSG_PATH
                ),
                presubmit_support._PresubmitResultLocation(
                    file_path="file1",
                    start_line=10,
                    end_line=10,
                ),
                presubmit_support._PresubmitResultLocation(
                    file_path="file2",
                    start_line=11,
                    end_line=15,
                ),
                presubmit_support._PresubmitResultLocation(
                    file_path="file3",
                    start_line=5,
                    start_col=0,
                    end_line=8,
                    end_col=5,
                ),
            ],
        )
        out = io.StringIO()
        result.handle(out)
        expected = (
            "This is a message\n"
            "  item1\n"
            "  item2\n"
            "Found in:\n"
            "  - Commit Message\n"
            "  - file1 [Ln 10]\n"
            "  - file2 [Ln 11 - 15]\n"
            "  - file3 [Ln 5, Col 0 - Ln 8, Col 5]\n"
            "\n***************\n"
            "Long text here.\n"
            "***************\n"
        )
        self.assertEqual(out.getvalue(), expected)

    def test_json_format(self):
        loc1 = presubmit_support._PresubmitResultLocation(
            file_path="file1", start_line=1, end_line=1
        )
        loc2 = presubmit_support._PresubmitResultLocation(
            file_path="file2", start_line=5, start_col=2, end_line=6, end_col=10
        )
        result = presubmit_support._PresubmitResult(
            "This is a message",
            items=["item1", "item2"],
            long_text="Long text here.",
            locations=[loc1, loc2],
        )
        expected = {
            "message": "This is a message",
            "items": ["item1", "item2"],
            "locations": [
                {
                    "file_path": "file1",
                    "start_line": 1,
                    "start_col": 0,
                    "end_line": 1,
                    "end_col": 0,
                },
                {
                    "file_path": "file2",
                    "start_line": 5,
                    "start_col": 2,
                    "end_line": 6,
                    "end_col": 10,
                },
            ],
            "long_text": "Long text here.",
            "fatal": False,
        }
        self.assertEqual(result.json_format(), expected)


class GerritAccessorCherryPickTest(unittest.TestCase):
    def _make_label(self, max_val: int, voters: list[tuple[str, int]]) -> dict:
        return {
            "values": {"0": "No score", f"+{max_val}": "Approved"},
            "all": [{"email": email, "value": val} for email, val in voters],
        }

    def _make_parent_change(
        self,
        *,
        status: str = "MERGED",
        project: str = "chromium/src",
        owner_email: str = "author@chromium.org",
        owner_tags: list[str] | None = None,
        merged_ps: int = 6,
        cr_voters: list[tuple[str, int]] | None = None,
        owners_override: bool = False,
        unapproved_reviewers: list[str] | None = None,
    ) -> dict:
        owner: dict = {"email": owner_email}
        if owner_tags:
            owner["tags"] = owner_tags
        labels: dict = {}
        if cr_voters is not None:
            labels["Code-Review"] = self._make_label(1, cr_voters)
        if owners_override:
            labels["Owners-Override"] = self._make_label(
                1, [("sheriff@chromium.org", 1)]
            )
        return {
            "project": project,
            "status": status,
            "owner": owner,
            "current_revision": "merged_sha",
            "revisions": {
                "early_sha": {"_number": 1, "kind": "REWORK"},
                "merged_sha": {
                    "_number": merged_ps,
                    "kind": "TRIVIAL_REBASE_WITH_MESSAGE_UPDATE",
                },
            },
            "labels": labels,
            "reviewers": {
                "REVIEWER": [{"email": r} for r in (unapproved_reviewers or [])]
            },
        }

    def _make_cherry_pick_change(
        self,
        *,
        parent_issue: int | bool | None = 100,
        parent_ps: int | bool | None = 6,
        project: str = "chromium/src",
        owner_email: str = "chrome-cherry-picker@chops-service-accounts.iam.gserviceaccount.com",
        owner_tags: list[str] | None = None,
        messages: list[str] | None = None,
        revisions: dict | None = None,
        cr_voters: list[tuple[str, int]] | None = None,
        unapproved_reviewers: list[str] | None = None,
    ) -> dict:
        if owner_tags is None:
            owner_tags = ["SERVICE_USER"]
        if messages is None:
            messages = [
                "Patch Set 1: Cherry Picked from branch main.",
                "Patch Set 2: Commit message was updated.",
            ]
        if revisions is None:
            revisions = {
                "ps1": {"_number": 1, "kind": "REWORK"},
                "ps2": {"_number": 2, "kind": "NO_CODE_CHANGE"},
            }
        labels: dict = {}
        if cr_voters is not None:
            labels["Code-Review"] = self._make_label(1, cr_voters)
        info: dict = {
            "project": project,
            "status": "NEW",
            "owner": {"email": owner_email, "tags": owner_tags},
            "current_revision": "ps2",
            "revisions": revisions,
            "messages": [{"message": m} for m in messages],
            "labels": labels,
            "reviewers": {
                "REVIEWER": [{"email": r} for r in (unapproved_reviewers or [])]
            },
        }
        if parent_issue is not None:
            info["cherry_pick_of_change"] = parent_issue
        if parent_ps is not None:
            info["cherry_pick_of_patch_set"] = parent_ps
        return info

    def test_fetch_change_detail_requests_messages(self):
        accessor = presubmit_support.GerritAccessor(
            url="https://chromium-review.googlesource.com",
            project="chromium/src",
        )
        with mock.patch(
            "gerrit_util.GetChangeDetail", return_value={}
        ) as mock_detail:
            accessor._FetchChangeDetail(200)
            mock_detail.assert_called_once_with(
                "chromium-review.googlesource.com",
                "200",
                [
                    "ALL_REVISIONS",
                    "DETAILED_LABELS",
                    "ALL_COMMITS",
                    "MESSAGES",
                ],
            )

    def test_clean_cherry_pick_transfers_approvers_and_parent_owner(self):
        accessor = presubmit_support.GerritAccessor()
        accessor.cache = {
            100: self._make_parent_change(
                owner_email="author@chromium.org",
                cr_voters=[
                    ("target_owner@chromium.org", 1),
                    ("unapproved@chromium.org", 0),
                ],
                unapproved_reviewers=["unapproved@chromium.org"],
            ),
            200: self._make_cherry_pick_change(
                unapproved_reviewers=["local_reviewer@chromium.org"],
            ),
        }

        self.assertEqual(
            accessor.GetChangeReviewers(200, approving_only=True),
            ["target_owner@chromium.org", "author@chromium.org"],
        )
        # Upload checks (approving_only=False) include current CL's reviewers
        # plus only approving reviewers and owner from the merged parent CL.
        self.assertEqual(
            accessor.GetChangeReviewers(200, approving_only=False),
            [
                "local_reviewer@chromium.org",
                "target_owner@chromium.org",
                "author@chromium.org",
            ],
        )

    def test_clean_cherry_pick_with_get_codereview_owner_and_reviewers(self):
        accessor = presubmit_support.GerritAccessor()
        accessor.cache = {
            100: self._make_parent_change(
                owner_email="author@chromium.org",
                cr_voters=[("target_owner@chromium.org", 1)],
            ),
            200: self._make_cherry_pick_change(),
        }
        input_api = mock.Mock()
        input_api.re = presubmit_support.re
        input_api.change.issue = 200
        input_api.gerrit = accessor

        owner, reviewers = (
            presubmit_support.presubmit_canned_checks.GetCodereviewOwnerAndReviewers(
                input_api, None, approval_needed=True
            )
        )
        self.assertEqual(
            owner,
            "chrome-cherry-picker@chops-service-accounts.iam.gserviceaccount.com",
        )
        self.assertEqual(
            reviewers,
            {"target_owner@chromium.org", "author@chromium.org"},
        )

    def test_clean_cherry_pick_transfers_owners_override(self):
        accessor = presubmit_support.GerritAccessor()
        accessor.cache = {
            100: self._make_parent_change(owners_override=True),
            200: self._make_cherry_pick_change(),
        }
        self.assertTrue(accessor.IsOwnersOverrideApproved(200))

    def test_multi_hop_cherry_pick_chain_skips_service_user_owners(self):
        accessor = presubmit_support.GerritAccessor()
        accessor.cache = {
            100: self._make_parent_change(
                owner_email="human_author@chromium.org",
                merged_ps=3,
                cr_voters=[("dep_owner@chromium.org", 1)],
            ),
            200: {
                **self._make_cherry_pick_change(
                    parent_issue=100,
                    parent_ps=3,
                ),
                "status": "MERGED",
                "current_revision": "ps2",
            },
            300: self._make_cherry_pick_change(
                parent_issue=200,
                parent_ps=2,
            ),
        }
        # The cherry-picker owns the intermediate hop but authored nothing.
        self.assertEqual(
            accessor.GetChangeReviewers(300, approving_only=True),
            ["dep_owner@chromium.org", "human_author@chromium.org"],
        )

    def test_accepts_all_non_code_change_revision_kinds(self):
        accessor = presubmit_support.GerritAccessor()
        accessor.cache = {
            100: self._make_parent_change(
                cr_voters=[("dep_owner@chromium.org", 1)],
            ),
            200: self._make_cherry_pick_change(
                revisions={
                    "ps1": {"_number": 1, "kind": "REWORK"},
                    "ps2": {"_number": 2, "kind": "NO_CHANGE"},
                    "ps3": {"_number": 3, "kind": "NO_CODE_CHANGE"},
                    "ps4": {"_number": 4, "kind": "TRIVIAL_REBASE"},
                    "ps5": {
                        "_number": 5,
                        "kind": "TRIVIAL_REBASE_WITH_MESSAGE_UPDATE",
                    },
                },
            ),
        }
        self.assertIn(
            "dep_owner@chromium.org",
            accessor.GetChangeReviewers(200, approving_only=True),
        )

    def test_rejects_cherry_pick_with_code_changes_or_invalid_metadata(self):
        parent = self._make_parent_change(
            cr_voters=[("dep_owner@chromium.org", 1)],
            owners_override=True,
        )
        cases = [
            (
                "rework_on_ps2",
                parent,
                self._make_cherry_pick_change(
                    revisions={
                        "ps1": {"_number": 1, "kind": "REWORK"},
                        "ps2": {"_number": 2, "kind": "REWORK"},
                    }
                ),
            ),
            (
                "merge_first_parent_update_on_ps2",
                parent,
                self._make_cherry_pick_change(
                    revisions={
                        "ps1": {"_number": 1, "kind": "REWORK"},
                        "ps2": {
                            "_number": 2,
                            "kind": "MERGE_FIRST_PARENT_UPDATE",
                        },
                    }
                ),
            ),
            (
                "git_conflicts_on_ps1",
                parent,
                self._make_cherry_pick_change(
                    messages=[
                        "Patch Set 1: Cherry Picked from branch main.\n\n"
                        "The following files contain Git conflicts:\n* DEPS"
                    ]
                ),
            ),
            (
                "not_cherry_picked_at_ps1",
                parent,
                self._make_cherry_pick_change(
                    messages=["Uploaded patch set 1."]
                ),
            ),
            (
                "re_cherry_picked_at_ps2",
                parent,
                self._make_cherry_pick_change(
                    messages=[
                        "Patch Set 1: Cherry Picked from branch main.",
                        "Patch Set 2: Cherry Picked from branch main.",
                    ]
                ),
            ),
            (
                "missing_patchset_gap",
                parent,
                self._make_cherry_pick_change(
                    revisions={
                        "ps1": {"_number": 1, "kind": "REWORK"},
                        "ps3": {"_number": 3, "kind": "NO_CODE_CHANGE"},
                    }
                ),
            ),
            (
                "parent_not_merged",
                self._make_parent_change(
                    status="NEW",
                    cr_voters=[("dep_owner@chromium.org", 1)],
                    owners_override=True,
                ),
                self._make_cherry_pick_change(),
            ),
            (
                "cherry_picked_from_unmerged_patchset",
                parent,
                self._make_cherry_pick_change(parent_ps=1),
            ),
            (
                "project_mismatch",
                self._make_parent_change(
                    project="other/repo",
                    cr_voters=[("dep_owner@chromium.org", 1)],
                    owners_override=True,
                ),
                self._make_cherry_pick_change(project="chromium/src"),
            ),
            (
                "project_missing",
                parent,
                self._make_cherry_pick_change(project=""),
            ),
        ]

        for name, parent_info, child_info in cases:
            with self.subTest(case=name):
                accessor = presubmit_support.GerritAccessor()
                accessor.cache = {100: parent_info, 200: child_info}
                self.assertEqual(
                    accessor.GetChangeReviewers(200, approving_only=True), []
                )
                self.assertFalse(accessor.IsOwnersOverrideApproved(200))

    def test_comment_mentioning_cherry_pick_does_not_block_transfer(self):
        accessor = presubmit_support.GerritAccessor()
        accessor.cache = {
            100: self._make_parent_change(
                cr_voters=[("dep_owner@chromium.org", 1)],
            ),
            200: self._make_cherry_pick_change(
                messages=[
                    "Patch Set 1: Cherry Picked from branch main.",
                    "Patch Set 2: Commit message was updated.",
                    "Patch Set 2:\n\nNote: Cherry Picked from main by a bot.",
                ]
            ),
        }
        self.assertEqual(
            accessor.GetChangeReviewers(200, approving_only=True),
            ["dep_owner@chromium.org", "author@chromium.org"],
        )

    def test_cherry_pick_chain_stops_at_max_depth(self):
        depth = presubmit_support._MAX_CHERRY_PICK_DEPTH
        last = 100 + depth + 2
        accessor = presubmit_support.GerritAccessor()
        accessor.cache = {
            100: self._make_parent_change(
                merged_ps=2,
                cr_voters=[("approver100@chromium.org", 1)],
            ),
        }
        for issue in range(101, last + 1):
            accessor.cache[issue] = {
                **self._make_cherry_pick_change(
                    parent_issue=issue - 1,
                    parent_ps=2,
                    cr_voters=[(f"approver{issue}@chromium.org", 1)],
                ),
                "status": "MERGED",
            }

        self.assertEqual(
            accessor.GetChangeReviewers(last, approving_only=True),
            [
                f"approver{issue}@chromium.org"
                for issue in range(last, last - depth - 1, -1)
            ],
        )

    def test_non_cherry_pick_skips_missing_and_duplicate_emails(self):
        accessor = presubmit_support.GerritAccessor()
        accessor.cache = {
            100: {
                "owner": {"email": "author@chromium.org"},
                "labels": {},
                "reviewers": {
                    "REVIEWER": [
                        {"email": "reviewer@chromium.org"},
                        {"_account_id": 1},
                        {"email": "reviewer@chromium.org"},
                    ]
                },
            },
        }
        self.assertEqual(
            accessor.GetChangeReviewers(100, approving_only=False),
            ["reviewer@chromium.org"],
        )

    def test_parent_fetch_failure_degrades_gracefully(self):
        accessor = presubmit_support.GerritAccessor()
        accessor.cache = {
            200: self._make_cherry_pick_change(
                cr_voters=[("direct_approver@chromium.org", 1)]
            ),
        }
        with mock.patch.object(
            accessor, "_FetchChangeDetail", side_effect=Exception("404")
        ):
            self.assertEqual(
                accessor.GetChangeReviewers(200, approving_only=True),
                ["direct_approver@chromium.org"],
            )
            self.assertFalse(accessor.IsOwnersOverrideApproved(200))


if __name__ == "__main__":
    unittest.main()
