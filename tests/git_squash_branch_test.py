#!/usr/bin/env vpython3
# coding=utf-8
# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for git_squash_branch."""

import os
import sys
import unittest
from unittest import mock

DEPOT_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEPOT_TOOLS_ROOT)

from testing_support import git_test_utils

import git_squash_branch
import git_common
import subprocess2

git_common.TEST_MODE = True


class GitSquashBranchTest(git_test_utils.GitRepoReadWriteTestBase):
    REPO_SCHEMA = """
  """

    def setUp(self):
        super(GitSquashBranchTest, self).setUp()

        # Create a repo with the following schema:
        #
        # main <- branchA <- branchB <- branchC
        #            ^
        #            \ branchD
        #
        # where each branch has 2 commits.
        self.repo.git("commit", "-m", "First commit", "--allow-empty")

        self.repo.git("checkout", "-B", "branchA", "--track", "main")
        self._createFileAndCommit("fileA1")
        self._createFileAndCommit("fileA2")

        self.repo.git("checkout", "-B", "branchB", "--track", "branchA")
        self._createFileAndCommit("fileB1")
        self._createFileAndCommit("fileB2")

        self.repo.git("checkout", "-B", "branchC", "--track", "branchB")
        self._createFileAndCommit("fileC1")
        self._createFileAndCommit("fileC2")

        self.repo.git("checkout", "-B", "branchD", "--track", "branchA")
        self._createFileAndCommit("fileD1")
        self._createFileAndCommit("fileD2")

    # =========================================================================
    # Core Functionality Tests
    # =========================================================================

    def testSquashRoot(self):
        self._assertCounts(
            {"branchA": 2, "branchB": 2, "branchC": 2, "branchD": 2}
        )

        self.repo.git("checkout", "branchA")
        self.repo.run(git_squash_branch.main, [])

        self._assertCounts(
            {"branchA": 1, "branchB": 2, "branchC": 2, "branchD": 2}
        )

    def testSquashSequential(self):
        self._assertCounts(
            {"branchA": 2, "branchB": 2, "branchC": 2, "branchD": 2}
        )

        self.repo.git("checkout", "branchA")
        self.repo.run(git_squash_branch.main, [])
        self._assertCounts(
            {"branchA": 1, "branchB": 2, "branchC": 2, "branchD": 2}
        )

        self.repo.git("checkout", "branchB")
        self.repo.run(git_squash_branch.main, [])
        self._assertCounts(
            {"branchA": 1, "branchB": 1, "branchC": 2, "branchD": 2}
        )

    def testSquashCustomMessage(self):
        self.repo.git("checkout", "branchD")
        self.repo.run(
            git_squash_branch.main, ["-m", "Custom squash header message"]
        )
        commit_msg = self.repo.git("log", "-1", "--format=%B", "branchD").stdout
        self.assertTrue(commit_msg.startswith("Custom squash header message"))
        self.assertIn("Added file fileD1", commit_msg)
        self.assertIn("Added file fileD2", commit_msg)

    def testPreservesDownstreamMetadata(self):
        authors_b_before = self.repo.git(
            "log", "--format=%an%x00%ae%x00%aI", "branchA..branchB"
        ).stdout
        authors_c_before = self.repo.git(
            "log", "--format=%an%x00%ae%x00%aI", "branchB..branchC"
        ).stdout

        self.repo.git("checkout", "branchA")
        self.repo.run(git_squash_branch.main, [])

        self._assertCounts(
            {"branchA": 1, "branchB": 2, "branchC": 2, "branchD": 2}
        )

        # Verify downstream commits on branchB, branchC preserved commit messages
        log_b = self.repo.git("log", "--format=%B", "branchA..branchB").stdout
        self.assertIn("Added file fileB1", log_b)
        self.assertIn("Added file fileB2", log_b)

        log_c = self.repo.git("log", "--format=%B", "branchB..branchC").stdout
        self.assertIn("Added file fileC1", log_c)
        self.assertIn("Added file fileC2", log_c)

        # Verify downstream commits preserved author name, email, and timestamp
        authors_b_after = self.repo.git(
            "log", "--format=%an%x00%ae%x00%aI", "branchA..branchB"
        ).stdout
        self.assertEqual(authors_b_before, authors_b_after)

        authors_c_after = self.repo.git(
            "log", "--format=%an%x00%ae%x00%aI", "branchB..branchC"
        ).stdout
        self.assertEqual(authors_c_before, authors_c_after)

    def testReparentCommitGpgSign(self):
        self.repo.git("checkout", "branchA")
        recorded_calls = []
        real_run = git_common.run

        def intercept_run(*args, **kwargs):
            if args and args[0] == "commit-tree":
                recorded_calls.append(args)
                return "0" * 40
            return real_run(*args, **kwargs)

        with mock.patch(
            "git_common.get_gpg_sign_args", return_value=["-SKEY123"]
        ):
            with mock.patch("git_common.run", side_effect=intercept_run):
                self.repo.run(git_squash_branch.main, [])

        self.assertTrue(len(recorded_calls) > 0)
        for cmd in recorded_calls:
            self.assertIn("-SKEY123", cmd)

    def testReparentBranchWithEmptyCommitMessage(self):
        # Create a downstream commit on leaf branch `branchC` with an empty commit message.
        self.repo.git("checkout", "branchC")
        with self.repo.open("fileC_empty_msg", "w") as f:
            f.write("content")
        self.repo.git("add", "fileC_empty_msg")
        self.repo.git("commit", "--allow-empty-message", "-m", "")

        self.repo.git("checkout", "branchA")
        self.repo.run(git_squash_branch.main, [])

        self._assertCounts(
            {"branchA": 1, "branchB": 2, "branchC": 3, "branchD": 2}
        )

        # Verify that branchC's tip commit was preserved with an empty message.
        msg_c = self.repo.git("log", "-1", "--format=%B", "branchC").stdout
        self.assertEqual(msg_c.strip(), "")

    def testAtomicRollbackOnFailure(self):
        self._assertCounts(
            {"branchA": 2, "branchB": 2, "branchC": 2, "branchD": 2}
        )

        self.repo.git("checkout", "branchA")
        real_run = git_common.run

        def run_with_corrupted_transaction(*args, **kwargs):
            if args and args[0] == "update-ref" and "--stdin" in args:
                indata = kwargs.get("indata", b"").decode("utf-8")
                tokens = indata.rstrip("\0").split("\0")
                tokens[-1] = (
                    "0" * 40
                )  # Corrupt expected old SHA to force failure
                kwargs["indata"] = ("\0".join(tokens) + "\0").encode("utf-8")
            return real_run(*args, **kwargs)

        with mock.patch(
            "git_common.run", side_effect=run_with_corrupted_transaction
        ):
            with self.assertRaises(subprocess2.CalledProcessError):
                self.repo.run(git_squash_branch.main, [])

        # Assert zero branches were modified due to atomic rollback
        self._assertCounts(
            {"branchA": 2, "branchB": 2, "branchC": 2, "branchD": 2}
        )

    def testEmptyBranch(self):
        self.repo.git("checkout", "-B", "emptyBranch", "--track", "main")
        self._createFileAndCommit("tempFile")
        self.repo.git("rm", "tempFile")
        self.repo.git_commit("Removed tempFile")

        self.assertFalse(
            self.repo.run(git_common.squash_branch, "emptyBranch", "main")
        )
        self.assertEqual(
            self.repo.run(git_common.hash_one, "emptyBranch"),
            self.repo.run(git_common.hash_one, "main"),
        )

    def testFailsWithDivergedBranch(self):
        self._assertCounts(
            {"branchA": 2, "branchB": 2, "branchC": 2, "branchD": 2}
        )

        self.repo.git("checkout", "branchB")
        self._createFileAndCommit("fileB3")
        self.repo.git("checkout", "branchA")

        # branchC has now diverged from branchB
        _, stderr = self.repo.capture_stdio(git_squash_branch.main, [])
        self.assertIn("some children have diverged", stderr)

    def testSquashSucceedsWhenUpstreamAdvanced(self):
        # Add a commit to main so branchA's upstream is ahead (diverged).
        self.repo.git("checkout", "main")
        self._createFileAndCommit("main_new_file")

        # Squashing branchA should still succeed against its merge-base.
        self.repo.git("checkout", "branchA")
        self.repo.run(git_squash_branch.main, [])

        self.assertEqual(self._getCountAheadOfUpstream("branchA"), 1)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _assertCounts(self, expected):
        for branch, count in expected.items():
            self.assertEqual(
                self._getCountAheadOfUpstream(branch),
                count,
                f"Branch {branch} expected {count} commits ahead of upstream",
            )

    def _createFileAndCommit(self, filename):
        with self.repo.open(filename, "w") as f:
            f.write("content")
        self.repo.git("add", filename)
        self.repo.git_commit("Added file " + filename)

    def _getCountAheadOfUpstream(self, branch):
        upstream = branch + "@{u}"
        output = self.repo.git(
            "rev-list", "--count", upstream + ".." + branch
        ).stdout
        return int(output)


if __name__ == "__main__":
    unittest.main()
