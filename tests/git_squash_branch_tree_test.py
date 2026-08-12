#!/usr/bin/env vpython3
# coding=utf-8
# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for git_squash_branch_tree."""

import os
import sys
import unittest
from unittest import mock

DEPOT_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEPOT_TOOLS_ROOT)

from testing_support import git_test_utils

import git_squash_branch_tree
import git_common
import subprocess2

git_common.TEST_MODE = True


class GitSquashBranchTreeTest(git_test_utils.GitRepoReadWriteTestBase):
    REPO_SCHEMA = """
  """

    def setUp(self):
        super(GitSquashBranchTreeTest, self).setUp()

        # Create a repo with the following schema:
        #
        # main <- branchA <- branchB
        #            ^
        #            \ branchC
        #
        # where each branch has 2 commits.
        self.repo.git("commit", "-m", "First commit", "--allow-empty")

        self.repo.git("checkout", "-B", "branchA", "--track", "main")
        self._createFileAndCommit("fileA1")
        self._createFileAndCommit("fileA2")

        self.repo.git("checkout", "-B", "branchB", "--track", "branchA")
        self._createFileAndCommit("fileB1")
        self._createFileAndCommit("fileB2")

        self.repo.git("checkout", "-B", "branchC", "--track", "branchA")
        self._createFileAndCommit("fileC1")
        self._createFileAndCommit("fileC2")

    # =========================================================================
    # Core Functionality Tests
    # =========================================================================

    def testSquashSubtreeDefaultCurrent(self):
        self._assertCounts({"branchA": 2, "branchB": 2, "branchC": 2})

        # Passing --ignore-no-upstream since repo has no remote for main
        self.repo.git("checkout", "branchB")
        self.repo.run(git_squash_branch_tree.main, ["--ignore-no-upstream"])

        self._assertCounts({"branchA": 2, "branchB": 1, "branchC": 2})

    def testSquashSubtreeAll(self):
        self._assertCounts({"branchA": 2, "branchB": 2, "branchC": 2})

        self.repo.run(
            git_squash_branch_tree.main,
            ["--branch", "branchA", "--ignore-no-upstream"],
        )

        self._assertCounts({"branchA": 1, "branchB": 1, "branchC": 1})

    def testSquashSubtreePreservesCommitMessageIsolation(self):
        self.repo.run(
            git_squash_branch_tree.main,
            ["--branch", "branchA", "--ignore-no-upstream"],
        )

        msg_a = self.repo.git("log", "-1", "--format=%B", "branchA").stdout
        self.assertIn("Added file fileA1", msg_a)
        self.assertIn("Added file fileA2", msg_a)
        self.assertNotIn("Added file fileB1", msg_a)

        msg_b = self.repo.git("log", "-1", "--format=%B", "branchB").stdout
        self.assertIn("Added file fileB1", msg_b)
        self.assertIn("Added file fileB2", msg_b)
        # Verify branchB does not contain branchA commits in its squash message
        self.assertNotIn("Added file fileA1", msg_b)
        self.assertNotIn("Added file fileA2", msg_b)

        msg_c = self.repo.git("log", "-1", "--format=%B", "branchC").stdout
        self.assertIn("Added file fileC1", msg_c)
        self.assertIn("Added file fileC2", msg_c)
        self.assertNotIn("Added file fileA1", msg_c)
        self.assertNotIn("Added file fileB1", msg_c)

    def testAtomicRollbackOnFailure(self):
        self._assertCounts({"branchA": 2, "branchB": 2, "branchC": 2})

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
                self.repo.run(
                    git_squash_branch_tree.main,
                    ["--branch", "branchA", "--ignore-no-upstream"],
                )

        # Assert zero branches were modified due to atomic rollback
        self._assertCounts({"branchA": 2, "branchB": 2, "branchC": 2})

    def testEmptyBranch(self):
        # Make branchB have no net changes relative to branchA
        self.repo.git("checkout", "branchB")
        self.repo.git("rm", "fileB1", "fileB2")
        self.repo.git_commit("Reverted branchB files")

        self.repo.run(
            git_squash_branch_tree.main,
            ["--branch", "branchA", "--ignore-no-upstream"],
        )

        self.assertEqual(self._getCountAheadOfUpstream("branchA"), 1)
        # branchB should now point to branchA
        self.assertEqual(
            self.repo.run(git_common.hash_one, "branchB"),
            self.repo.run(git_common.hash_one, "branchA"),
        )
        self.assertEqual(self._getCountAheadOfUpstream("branchC"), 1)

    def testFailsWhenUpstreamDiverged(self):
        # Advance upstream 'main' with a commit that branchA does not have
        self.repo.git("checkout", "main")
        self._createFileAndCommit("mainFileAfterBranching")

        # Squashing branchA subtree must fail because branchA has diverged from main
        self.repo.git("checkout", "branchA")
        _, stderr = self.repo.capture_stdio(
            git_squash_branch_tree.main,
            ["--branch", "branchA", "--ignore-no-upstream"],
        )
        self.assertIn("branches have diverged from their upstream", stderr)

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
