#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for git_cl_core.py."""

import io
import os
import sys
import tempfile
import unittest
from unittest import mock

# Add parent directory to sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import git_cl_core  # noqa: E402


class GitClCoreTest(unittest.TestCase):
    def testSettingsDefaults(self):
        s = git_cl_core.Settings()
        self.assertIsNone(s.cc)
        self.assertIsNone(s.root)
        self.assertFalse(s.updated)

    @mock.patch("scm.GIT.GetCheckoutRoot", return_value="/fake/root")
    def testGetRoot(self, mock_root):
        s = git_cl_core.Settings()
        self.assertEqual(os.path.realpath("/fake/root"), s.GetRoot())

    def testSplitArgsByCmdLineLimit(self):
        args = ["a" * 100 for _ in range(500)]
        chunks = list(git_cl_core._SplitArgsByCmdLineLimit(args))
        self.assertTrue(len(chunks) >= 1)
        self.assertEqual(sum(len(c) for c in chunks), 500)

    @mock.patch("scm.GIT.SetConfig")
    def testLoadCodereviewSettingsFromFileWithExplicitRoot(
        self, mock_set_config
    ):
        content = "CODE_REVIEW_SERVER: https://example.com\nCC_LIST: a@b.com"
        file_obj = io.StringIO(content)
        git_cl_core.LoadCodereviewSettingsFromFile(
            file_obj, root="/custom/root"
        )
        mock_set_config.assert_any_call(
            "/custom/root", "rietveld.server", "https://example.com"
        )
        mock_set_config.assert_any_call(
            "/custom/root", "rietveld.cc", "a@b.com"
        )

    def testFindCodereviewSettingsFileUtf8(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = os.path.join(tmp_dir, "codereview.settings")
            with open(settings_path, "w", encoding="utf-8") as f:
                f.write(
                    "# UTF-8 test: café 🚀\nCODE_REVIEW_SERVER: https://example.com\n"
                )
            sub_dir = os.path.join(tmp_dir, "subdir")
            os.makedirs(sub_dir)
            orig_cwd = os.getcwd()
            try:
                os.chdir(sub_dir)
                fileobj = git_cl_core.FindCodereviewSettingsFile(root=tmp_dir)
                self.assertIsNotNone(fileobj)
                with fileobj:
                    self.assertEqual(
                        "utf-8", getattr(fileobj, "encoding", "").lower()
                    )
                    content = fileobj.read()
                    self.assertIn("café 🚀", content)
            finally:
                os.chdir(orig_cwd)

    @mock.patch("scm.GIT.SetConfig")
    def testLoadCodereviewSettingsFromFileWithGerritSkipEnsureAuthenticated(
        self, mock_set_config
    ):
        content = "GERRIT_SKIP_ENSURE_AUTHENTICATED: True\n"
        file_obj = io.StringIO(content)
        git_cl_core.LoadCodereviewSettingsFromFile(
            file_obj, root="/custom/root"
        )
        mock_set_config.assert_any_call(
            "/custom/root", "gerrit.skip-ensure-authenticated", "True"
        )

    @mock.patch("scm.GIT.SetConfig")
    def testLoadCodereviewSettingsFromFileWithPushUrlConfig(
        self, mock_set_config
    ):
        content = (
            "PUSH_URL_CONFIG: url.ssh://gitrw.chromium.org.pushinsteadof\n"
            "ORIGIN_URL_CONFIG: http://src.chromium.org/git\n"
        )
        file_obj = io.StringIO(content)
        git_cl_core.LoadCodereviewSettingsFromFile(
            file_obj, root="/custom/root"
        )
        mock_set_config.assert_any_call(
            "/custom/root",
            "url.ssh://gitrw.chromium.org.pushinsteadof",
            "http://src.chromium.org/git",
        )

    @mock.patch("scm.GIT.GetConfig", return_value="false")
    @mock.patch("git_cl_core.FindCodereviewSettingsFile")
    def testLazyUpdateAutoupdateDisabled(self, mock_find, mock_get_config):
        s = git_cl_core.Settings()
        s.root = "/fake/root"
        s._LazyUpdateIfNeeded()
        mock_find.assert_not_called()
        self.assertTrue(s.updated)

    @mock.patch("git_cl_core.SaveDescriptionBackup")
    def testDieWithErrorSavesBackup(self, mock_backup):
        mock_desc = mock.Mock(description="backup description")
        with self.assertRaises(SystemExit):
            git_cl_core.DieWithError("error msg", change_desc=mock_desc)
        mock_backup.assert_called_once_with(mock_desc)


if __name__ == "__main__":
    unittest.main()
