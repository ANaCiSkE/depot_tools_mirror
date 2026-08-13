#!/usr/bin/env python3
# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Tool to squash all branches and their downstream branches. Useful to avoid
potential conflicts during a git rebase-update with multiple stacked CLs.
"""

from __future__ import annotations

import argparse
import sys

import gclient_utils
import git_common as git


def stage_squash_branch(
    branch: str,
    tree: dict[str, str],
    new_shas: dict[str, str],
) -> str:
    """Creates a squash commit for `branch` on top of its parent commit.

    Args:
        branch: The branch to squash.
        tree: Mapping of {branch: upstream_branch}.
        new_shas: Mapping of {branch: squashed_commit_sha} updated in-place.

    Returns:
        The new squash commit SHA (or parent SHA if branch is empty).
    """
    print(f"Squashing branch {branch}.")
    assert branch in tree
    parent = tree[branch]
    merge_base = git.get_or_create_merge_base(branch, parent)
    assert merge_base, (
        f"Unable to determine merge base for `{branch}` on `{parent}`."
    )
    # If the parent branch was already squashed earlier in this run, use its
    # newly generated commit SHA from new_shas as our parent.
    parent_sha = new_shas.get(parent)
    if parent_sha is None:
        parent_sha = git.hash_one(merge_base)
    msg = git.get_squash_message(branch, merge_base)
    commit_sha = git.create_squash_commit(
        branch,
        parent_sha,
        msg,
    )
    if commit_sha is None:
        print("Nothing to commit; squashed branch is empty")
        return parent_sha
    return commit_sha


def squash_subtree(
    branch: str,
    tree: dict[str, str],
    downstream_branches: dict[str, list[str]],
    initial_hashes: dict[str, str],
    new_shas: dict[str, str],
) -> list[tuple[str, str, str]]:
    """Recursively squashes `branch` and all of its downstream branches.

    Args:
        branch: The root branch of the subtree to squash.
        tree: Mapping of {branch: upstream_branch}.
        downstream_branches: Mapping of {branch: list_of_children}.
        initial_hashes: Mapping of {branch: original_commit_sha}.
        new_shas: Mapping of {branch: squashed_commit_sha} updated in-place.

    Returns:
        List of (branch, new_sha, old_sha) tuples.
    """
    ref_updates = []
    # Top-down recursive traversal: squash this branch first so its new SHA is
    # registered in new_shas before downstream children are squashed on top of it.
    # The upstream default never has to be squashed (e.g. origin/main).
    if branch != git.upstream_default():
        target_sha = stage_squash_branch(
            branch,
            tree,
            new_shas,
        )
        new_shas[branch] = target_sha
        ref_updates.append((branch, target_sha, initial_hashes[branch]))

    # Recurse on downstream branches, if any.
    for downstream_branch in downstream_branches[branch]:
        ref_updates.extend(
            squash_subtree(
                downstream_branch,
                tree,
                downstream_branches,
                initial_hashes,
                new_shas,
            )
        )
    return ref_updates


def main(args=None):
    if gclient_utils.IsEnvCog():
        print(
            "squash-branch-tree command is not supported in non-git environment.",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ignore-no-upstream",
        action="store_true",
        help="Allows proceeding if any branch has no upstreams.",
    )
    parser.add_argument(
        "--branch",
        "-b",
        type=str,
        default=git.current_branch(),
        help="The name of the branch whose subtree must be "
        "squashed. Defaults to the current branch.",
    )
    opts = parser.parse_args(args)

    if git.in_rebase():
        print(
            "Cannot squash while a rebase is in progress. Please finish or abort the rebase first.",
            file=sys.stderr,
        )
        return 1
    if git.is_dirty_git_tree("squash-branch-tree"):
        return 1

    if not opts.branch or opts.branch == "HEAD":
        print("Cannot squash in detached HEAD.", file=sys.stderr)
        return 1

    branches_without_upstream, tree = git.get_branch_tree()

    if not opts.ignore_no_upstream and branches_without_upstream:
        print(
            "Cannot use `git squash-branch-tree` since the following\n"
            "branches don't have an upstream:",
            file=sys.stderr,
        )
        for branch in branches_without_upstream:
            print(f"  - {branch}", file=sys.stderr)
        print(
            "Use --ignore-no-upstream to ignore this check and proceed.",
            file=sys.stderr,
        )
        return 1

    if opts.branch != git.upstream_default() and opts.branch not in tree:
        print(
            f"Cannot squash `{opts.branch}` because it has no upstream.",
            file=sys.stderr,
        )
        return 1

    diverged_branches = git.get_diverged_branches(tree)
    if diverged_branches:
        print(
            "Cannot use `git squash-branch-tree` since the following\n"
            "branches have diverged from their upstream and could cause\n"
            "conflicts:",
            file=sys.stderr,
        )
        for diverged_branch in diverged_branches:
            print(f"  - {diverged_branch}", file=sys.stderr)
        return 1

    downstream_branches = git.get_downstream_branches(tree)
    initial_hashes = git.get_hashes(tree)
    new_shas = {}

    # Phase 1: Generate all squashed commit objects in the object store.
    ref_updates = squash_subtree(
        opts.branch,
        tree,
        downstream_branches,
        initial_hashes,
        new_shas,
    )

    # Phase 2: Commit all branch reference updates in a single atomic transaction.
    # Prevents leaving branches in a partially squashed state if interrupted.
    git.update_refs_atomic(ref_updates, "squash-branch-tree")

    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write("interrupted\n")
        sys.exit(1)
