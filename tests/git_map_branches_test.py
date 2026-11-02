#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for `git_map_branches`."""

import os
import re
import shutil
import sys
import unittest

DEPOT_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEPOT_TOOLS_ROOT)

import git_common  # noqa: E402
import git_map_branches  # noqa: E402
from testing_support import git_test_utils  # noqa: E402


class GitMapBranchesTest(git_test_utils.GitRepoReadWriteTestBase):
    """Tests for `git_map_branches` execution and `--show-worktrees` option."""

    REPO_SCHEMA = """
    A B C
      B D
    """

    @classmethod
    def getRepoContent(cls, commit):
        return {commit: {"data": commit.encode("utf-8")}}

    @classmethod
    def setUpClass(cls):
        super(GitMapBranchesTest, cls).setUpClass()
        git_common.TEST_MODE = True

    def setUp(self):
        super(GitMapBranchesTest, self).setUp()
        self.repo.git("checkout", "branch_C")

    def tearDown(self):
        try:
            self.repo.git("worktree", "prune")
        except Exception:
            pass
        super(GitMapBranchesTest, self).tearDown()

    def _assert_has_worktree(self, line, expected_path):
        match = re.search(r"\(([^)]+)\)", line)
        self.assertIsNotNone(match, f"No worktree found in line: {line}")
        self.assertEqual(
            os.path.normcase(os.path.normpath(match.group(1))),
            os.path.normcase(os.path.normpath(expected_path)),
        )

    def testDefaultOutput(self):
        """Verifies default output without worktree option."""
        stdout, _ = self.repo.capture_stdio(
            git_map_branches.main, ["--no-color"]
        )
        lines = stdout.splitlines()
        self.assertTrue(any("branch_C *" in line for line in lines))
        self.assertTrue(any("branch_D" in line for line in lines))
        self.assertNotIn(os.path.normpath(self.repo.repo_path), stdout)
        self.assertNotIn(self.repo.repo_path.replace("\\", "/"), stdout)

    def testShowWorktreeSingle(self):
        """Verifies `--show-worktrees` displays path for checked out branch."""
        stdout, _ = self.repo.capture_stdio(
            git_map_branches.main, ["-w", "--no-color"]
        )
        lines = stdout.splitlines()
        c_line = next(line for line in lines if "branch_C *" in line)
        self._assert_has_worktree(c_line, self.repo.repo_path)

        d_line = next(line for line in lines if "branch_D" in line)
        self.assertNotIn("(", d_line)

    def testShowWorktreeLinked(self):
        """Verifies `--show-worktrees` displays path for linked worktrees."""
        linked_wt = self.repo.repo_path + "_linked"
        self.addCleanup(shutil.rmtree, linked_wt, ignore_errors=True)
        self.repo.git("worktree", "add", linked_wt, "branch_D")

        stdout, _ = self.repo.capture_stdio(
            git_map_branches.main, ["--show-worktrees", "--no-color"]
        )
        lines = stdout.splitlines()
        c_line = next(line for line in lines if "branch_C *" in line)
        self._assert_has_worktree(c_line, self.repo.repo_path)

        d_line = next(line for line in lines if "branch_D" in line)
        self._assert_has_worktree(d_line, linked_wt)

    def testShowWorktreesFlags(self):
        """Verifies `-w` and `--show-worktrees` produce identical output."""
        out_short, _ = self.repo.capture_stdio(
            git_map_branches.main, ["-w", "--no-color"]
        )
        out_long, _ = self.repo.capture_stdio(
            git_map_branches.main, ["--show-worktrees", "--no-color"]
        )
        self.assertEqual(out_short, out_long)

    def testShowWorktreeWithSubject(self):
        """Verifies worktree column appears before subject column."""
        linked_wt = self.repo.repo_path + "_linked"
        self.addCleanup(shutil.rmtree, linked_wt, ignore_errors=True)
        self.repo.git("worktree", "add", linked_wt, "branch_D")

        stdout, _ = self.repo.capture_stdio(
            git_map_branches.main,
            ["-w", "--show-subject", "--no-color"],
        )
        lines = stdout.splitlines()
        d_line = next(line for line in lines if "branch_D" in line)
        self._assert_has_worktree(d_line, linked_wt)
        self.assertIn("D", d_line)
        wt_match = re.search(r"\(([^)]+)\)", d_line)
        self.assertIsNotNone(wt_match)
        wt_index = wt_match.start()
        subject_index = d_line.index("D", wt_match.end())
        self.assertGreater(subject_index, wt_index)


if __name__ == "__main__":
    unittest.main()
