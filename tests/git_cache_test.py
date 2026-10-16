#!/usr/bin/env vpython3
# Copyright 2015 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for git_cache.py"""

import contextlib
from io import StringIO
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

DEPOT_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEPOT_TOOLS_ROOT)

from testing_support import coverage_utils  # noqa: E402
import gclient_utils  # noqa: E402
import git_cache  # noqa: E402
import git_common  # noqa: E402


class GitCacheTest(unittest.TestCase):
    def setUp(self):
        self.cache_dir = tempfile.mkdtemp(prefix="git_cache_test_")
        self.addCleanup(shutil.rmtree, self.cache_dir, ignore_errors=True)
        self.origin_dir = tempfile.mkdtemp(suffix="origin.git")
        self.addCleanup(shutil.rmtree, self.origin_dir, ignore_errors=True)
        git_cache.Mirror.SetCachePath(self.cache_dir)

        # Ensure git_cache works with safe.bareRepository.
        mock.patch.dict(
            "os.environ",
            {
                "GIT_CONFIG_GLOBAL": os.path.join(self.cache_dir, ".gitconfig"),
            },
        ).start()
        self.addCleanup(mock.patch.stopall)
        self.git(
            [
                "config",
                "--file",
                os.path.join(self.cache_dir, ".gitconfig"),
                "--add",
                "safe.bareRepository",
                "explicit",
            ]
        )

    def git(self, cmd, cwd=None):
        cwd = cwd or self.origin_dir
        git = "git.bat" if sys.platform == "win32" else "git"
        subprocess.check_call([git] + cmd, cwd=cwd)

    def _cacheHasTag(self, cache_dir: str, tag: str = "TAG") -> bool:
        git = "git.bat" if sys.platform == "win32" else "git"
        return (
            subprocess.call(
                [
                    git,
                    "--git-dir",
                    cache_dir,
                    "show-ref",
                    "--verify",
                    "--quiet",
                    f"refs/tags/{tag}",
                ]
            )
            == 0
        )

    def _supportsReftable(self) -> bool:
        return git_common.meets_git_version((2, 45, 0))

    def _setDefaultRefFormat(self, ref_format: str):
        """Makes the host git default to ref_format for new/re-inits."""
        self.git(
            [
                "config",
                "--file",
                os.path.join(self.cache_dir, ".gitconfig"),
                "init.defaultRefFormat",
                ref_format,
            ]
        )

    def _makeBareMirrorWithHead(
        self, head_ref: str, ref_format: str = "reftable"
    ) -> git_cache.Mirror:
        """Creates the mirror as a bare repo with HEAD pointing at head_ref."""
        mirror = git_cache.Mirror(self.origin_dir)
        gclient_utils.rmtree(mirror.mirror_path)
        cmd = ["init", "-q", "--bare"]
        if ref_format:
            cmd.append(f"--ref-format={ref_format}")
        cmd.append(mirror.mirror_path)
        self.git(cmd)
        self.git(
            ["--git-dir", mirror.mirror_path, "symbolic-ref", "HEAD", head_ref]
        )
        return mirror

    @mock.patch("git_cache.Mirror.bootstrap_repo", return_value=True)
    def testEnsureBootstrappedHandlesStaleMasterHead(self, _mock_bootstrap):
        # HEAD is read via git (symbolic-ref), so a cache left pointing at
        # refs/heads/master (with no such ref) is detected as stale and nuked,
        # while a healthy refs/heads/main cache is kept -- regardless of the
        # on-disk ref backend (loose, packed, or reftable).
        ref_formats = ["files"]
        if self._supportsReftable():
            ref_formats.append("reftable")
        cases = [
            # (head_ref, expect_deleted)
            ("refs/heads/master", True),
            ("refs/heads/main", False),
        ]
        for ref_format in ref_formats:
            for head_ref, expect_deleted in cases:
                with self.subTest(head_ref=head_ref, ref_format=ref_format):
                    mirror = self._makeBareMirrorWithHead(
                        head_ref, ref_format=ref_format
                    )
                    with mock.patch(
                        "git_cache.gclient_utils.rmtree"
                    ) as mock_rmtree:
                        mirror._ensure_bootstrapped(None, True, False)
                    if expect_deleted:
                        mock_rmtree.assert_any_call(mirror.mirror_path)
                    else:
                        mock_rmtree.assert_not_called()

    def testParseFetchSpec(self):
        testData = [
            ([], []),
            (
                ["main"],
                [("+refs/heads/main:refs/heads/main", r"\+refs/heads/main:.*")],
            ),
            (
                ["main/"],
                [("+refs/heads/main:refs/heads/main", r"\+refs/heads/main:.*")],
            ),
            (
                ["+main"],
                [("+refs/heads/main:refs/heads/main", r"\+refs/heads/main:.*")],
            ),
            (
                ["master"],
                [
                    (
                        "+refs/heads/master:refs/heads/master",
                        r"\+refs/heads/master:.*",
                    )
                ],
            ),
            (
                ["master/"],
                [
                    (
                        "+refs/heads/master:refs/heads/master",
                        r"\+refs/heads/master:.*",
                    )
                ],
            ),
            (
                ["+master"],
                [
                    (
                        "+refs/heads/master:refs/heads/master",
                        r"\+refs/heads/master:.*",
                    )
                ],
            ),
            (
                ["refs/heads/*"],
                [("+refs/heads/*:refs/heads/*", r"\+refs/heads/\*:.*")],
            ),
            (
                ["foo/bar/*", "baz"],
                [
                    (
                        "+refs/heads/foo/bar/*:refs/heads/foo/bar/*",
                        r"\+refs/heads/foo/bar/\*:.*",
                    ),
                    ("+refs/heads/baz:refs/heads/baz", r"\+refs/heads/baz:.*"),
                ],
            ),
            (
                ["refs/foo/*:refs/bar/*"],
                [("+refs/foo/*:refs/bar/*", r"\+refs/foo/\*:.*")],
            ),
        ]

        mirror = git_cache.Mirror("test://phony.example.biz")
        for fetch_specs, expected in testData:
            mirror = git_cache.Mirror(
                "test://phony.example.biz", refs=fetch_specs
            )
            self.assertEqual(mirror.fetch_specs, set(expected))

    def testPopulate(self):
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

    def testPopulateResetFetchConfig(self):
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        # Add a bad refspec to the cache's fetch config.
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        self.git(
            [
                "--git-dir",
                cache_dir,
                "config",
                "--add",
                "remote.origin.fetch",
                "+refs/heads/foo:refs/heads/foo",
            ],
            cwd=cache_dir,
        )

        mirror.populate(reset_fetch_config=True)

    def testPopulateTwice(self):
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        mirror.populate()

    def testPopulateDeletesTmpPackFiles(self):
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        # Create tmp pack files.
        pack_dir = os.path.join(mirror.mirror_path, "objects", "pack")
        os.makedirs(pack_dir, exist_ok=True)
        tmp_pack_path = os.path.join(pack_dir, "tmp_pack_abc")
        tmp_idx_path = os.path.join(pack_dir, ".tmp-1234-pack-def.idx")
        with open(tmp_pack_path, "w") as f:
            f.write("content")
        with open(tmp_idx_path, "w") as f:
            f.write("idx content")

        self.assertTrue(os.path.exists(tmp_pack_path))
        self.assertTrue(os.path.exists(tmp_idx_path))

        mirror.populate()

        # The temporary files should be deleted.
        self.assertFalse(os.path.exists(tmp_pack_path))
        self.assertFalse(os.path.exists(tmp_idx_path))

    @mock.patch("sys.stdout", StringIO())
    def testPruneRequired(self):
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["checkout", "-b", "foo"])
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        self.git(["checkout", "-b", "foo_tmp", "foo"])
        self.git(["branch", "-D", "foo"])
        self.git(["checkout", "-b", "foo/bar", "foo_tmp"])
        mirror.populate()
        self.assertNotIn(
            git_cache.GIT_CACHE_CORRUPT_MESSAGE, sys.stdout.getvalue()
        )

    @mock.patch("sys.stdout", StringIO())
    def testBadInit(self):
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )

        mirror = git_cache.Mirror(self.origin_dir)

        # Simulate init being interrupted during fetch phase.
        with mock.patch.object(mirror, "_fetch"):
            mirror.populate()

        # Corrupt message is not expected at this point since it was
        # "interrupted".
        self.assertNotIn(
            git_cache.GIT_CACHE_CORRUPT_MESSAGE, sys.stdout.getvalue()
        )

        # We call mirror.populate() without _fetch patched. This time, a
        # sentient file should prompt cache deletion.
        mirror.populate()
        self.assertIn(
            git_cache.GIT_CACHE_CORRUPT_MESSAGE, sys.stdout.getvalue()
        )

    def testPopulateInitObjectFormat(self):
        """A fresh mirror pins the bare repo to the remote object format.

        An existing mirror that is re-initialized must not pass
        --object-format, since the object format cannot be changed after
        creation.
        """
        self._makeGitRepo()
        mirror = git_cache.Mirror(self.origin_dir)
        real_run_git = mirror.RunGit

        def populate_capturing_init():
            init_calls = []

            def record(cmd, *args, **kwargs):
                if cmd[:1] == ["init"]:
                    init_calls.append(list(cmd))
                return real_run_git(cmd, *args, **kwargs)

            with mock.patch.object(mirror, "RunGit", side_effect=record):
                mirror.populate()
            return init_calls

        with mock.patch.object(
            git_cache.scm.GIT,
            "GetRemoteObjectFormat",
            return_value="sha1",
        ) as mock_object_format:
            fresh_init_calls = populate_capturing_init()
            existing_init_calls = populate_capturing_init()

        mock_object_format.assert_called_with(self.origin_dir)

        with self.subTest("fresh mirror pins object format"):
            self.assertTrue(
                any("--object-format=sha1" in cmd for cmd in fresh_init_calls),
                fresh_init_calls,
            )
            if self._supportsReftable():
                self.assertTrue(
                    any(
                        "--ref-format=files" in cmd for cmd in fresh_init_calls
                    ),
                    fresh_init_calls,
                )

        with self.subTest("existing mirror omits object format"):
            self.assertTrue(existing_init_calls)
            for cmd in existing_init_calls:
                self.assertNotIn("--object-format=sha1", cmd)
                if self._supportsReftable():
                    self.assertIn("--ref-format=files", cmd)

    def testBootstrapRepoPinsRefFormatFiles(self):
        mirror = git_cache.Mirror("https://chromium.googlesource.com/foo/bar")
        init_calls = []
        real_run_git = mirror.RunGit

        def record_git(cmd, *args, **kwargs):
            if cmd[:1] == ["init"]:
                init_calls.append(list(cmd))
            return real_run_git(cmd, *args, **kwargs)

        with (
            mock.patch.object(
                git_cache.Gsutil,
                "check_call",
                return_value=(
                    0,
                    "gs://chromium-git-cache/v2/foo-bar/100.ready\n"
                    "gs://chromium-git-cache/v2/foo-bar/100/\n",
                    "",
                ),
            ),
            mock.patch.object(git_cache.Gsutil, "call", return_value=0),
            mock.patch.object(mirror, "RunGit", side_effect=record_git),
        ):
            target_dir = os.path.join(self.cache_dir, "test_target")
            self.assertTrue(mirror.bootstrap_repo(target_dir))

        if self._supportsReftable():
            self.assertTrue(
                any("--ref-format=files" in cmd for cmd in init_calls),
                init_calls,
            )

    def testEnsureBootstrappedPreservesExistingRefFormat(self):
        """Re-initializing an existing mirror must keep its ref backend.

        git rejects an init that would change the ref storage format, so
        pinning files unconditionally would permanently break mirrors created
        before the files pin landed -- e.g. by an older depot_tools on a host
        whose git defaults to reftable.
        """
        if not self._supportsReftable():
            self.skipTest("git is too old for --ref-format")

        mirror = self._makeBareMirrorWithHead(
            "refs/heads/main", ref_format="reftable"
        )
        self.assertEqual("reftable", mirror._get_ref_format())

        with (
            mock.patch.object(
                git_cache.Mirror, "bootstrap_repo", return_value=False
            ),
            mock.patch.object(git_cache.Mirror, "_set_symbolic_ref"),
        ):
            mirror._ensure_bootstrapped(None, True, False)

        self.assertEqual("reftable", mirror._get_ref_format())

    def testEnsureBootstrappedFilesMirrorOnReftableHost(self):
        """A files mirror must survive re-init where git defaults to reftable.

        This is the reported breakage: plain `git init --bare` picks the host
        default, then dies on the existing refs/heads directory.
        """
        if not self._supportsReftable():
            self.skipTest("git is too old for --ref-format")

        mirror = self._makeBareMirrorWithHead(
            "refs/heads/main", ref_format="files"
        )
        self._setDefaultRefFormat("reftable")

        with (
            mock.patch.object(
                git_cache.Mirror, "bootstrap_repo", return_value=False
            ),
            mock.patch.object(git_cache.Mirror, "_set_symbolic_ref"),
        ):
            mirror._ensure_bootstrapped(None, True, False)

        self.assertEqual("files", mirror._get_ref_format())

    def testEnsureBootstrappedRepairsPoisonedRefFormat(self):
        """A failed reftable init leaves a config that hides every ref.

        git writes extensions.refStorage before it fails on refs/heads, so a
        mirror broken by a pre-fix depot_tools reports no refs and re-fails
        every init. The refs are intact; re-init must repair rather than
        inherit the bad format.
        """
        if not self._supportsReftable():
            self.skipTest("git is too old for --ref-format")

        self._makeGitRepoWithTag()
        mirror = git_cache.Mirror(self.origin_dir)
        gclient_utils.rmtree(mirror.mirror_path)
        self.git(
            [
                "clone",
                "--bare",
                "--ref-format=files",
                self.origin_dir,
                mirror.mirror_path,
            ]
        )
        self.assertTrue(self._cacheHasTag(mirror.mirror_path))

        # Poison it exactly the way a pre-fix depot_tools did.
        self._setDefaultRefFormat("reftable")
        with self.assertRaises(subprocess.CalledProcessError):
            self.git(["--git-dir", mirror.mirror_path, "init", "--bare"])
        self.assertEqual("reftable", mirror._get_ref_format())
        self.assertFalse(self._cacheHasTag(mirror.mirror_path))

        with (
            mock.patch.object(
                git_cache.Mirror, "bootstrap_repo", return_value=False
            ),
            mock.patch.object(git_cache.Mirror, "_set_symbolic_ref"),
        ):
            mirror._ensure_bootstrapped(None, True, False)

        self.assertEqual("files", mirror._get_ref_format())
        self.assertTrue(self._cacheHasTag(mirror.mirror_path))

    def testRefFormatArgsSkippedOnOldGit(self):
        """The --ref-format flag only exists in git 2.45+."""
        with mock.patch.object(
            git_cache.git_common, "meets_git_version", return_value=False
        ):
            self.assertEqual([], git_cache._ref_format_args())
        with mock.patch.object(
            git_cache.git_common, "meets_git_version", return_value=True
        ):
            self.assertEqual(
                ["--ref-format=files"], git_cache._ref_format_args()
            )
            self.assertEqual(
                ["--ref-format=reftable"],
                git_cache._ref_format_args("reftable"),
            )

    def _makeGitRepo(self):
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )

    def _makeGitRepoWithTag(self):
        self._makeGitRepo()
        self.git(["tag", "TAG"])
        self.git(["pack-refs"])

    def testPopulateFetchTagsByDefault(self):
        self._makeGitRepoWithTag()

        # Default behaviour includes tags.
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        self.assertTrue(self._cacheHasTag(cache_dir))

    def testPopulateFetchWithoutTags(self):
        self._makeGitRepoWithTag()

        # Ask to not include tags.
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate(no_fetch_tags=True)

        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        self.assertFalse(self._cacheHasTag(cache_dir))

    def testPopulateResetFetchConfigEmptyFetchConfig(self):
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate(reset_fetch_config=True)

    def testPopulateWithCommitsAndMultipleRefsEndToEnd(self):
        self._makeGitRepo()
        git = "git.bat" if sys.platform == "win32" else "git"
        head_sha = (
            subprocess.check_output(
                [git, "rev-parse", "HEAD"], cwd=self.origin_dir
            )
            .decode("utf-8")
            .strip()
        )
        self.git(["update-ref", "refs/branch-heads/m1", head_sha])

        mirror = git_cache.Mirror(
            self.origin_dir,
            refs=["refs/branch-heads/*"],
            commits=[head_sha],
        )
        real_run_git = mirror.RunGit
        fetch_calls = []

        def record_run_git(cmd, *args, **kwargs):
            if cmd[:1] == ["fetch"]:
                fetch_calls.append(list(cmd))
            return real_run_git(cmd, *args, **kwargs)

        with mock.patch.object(mirror, "RunGit", side_effect=record_run_git):
            mirror.populate()

        # Both refspecs should be fetched in a single batched git fetch call,
        # and the commit already present in the mirror should not be fetched
        # a second time.
        self.assertEqual(
            fetch_calls,
            [
                [
                    "fetch",
                    "--prune",
                    "origin",
                    "+refs/heads/*:refs/heads/*",
                    "+refs/branch-heads/*:refs/branch-heads/*",
                ]
            ],
        )
        self.assertTrue(mirror.contains_revision(head_sha, timeout=0))

    def test_fetch_batches_multiple_refspecs(self):
        mirror = git_cache.Mirror(
            "https://chromium.googlesource.com/foo/bar",
            refs=["refs/branch-heads/*"],
            print_func=lambda *args: None,
        )
        specs = [
            "+refs/heads/*:refs/heads/*",
            "+refs/branch-heads/*:refs/branch-heads/*",
        ]
        with (
            mock.patch.object(mirror, "config"),
            mock.patch(
                "subprocess.check_output",
                return_value=("\n".join(specs) + "\n").encode("utf-8"),
            ),
            mock.patch.object(mirror, "RunGit") as mock_run_git,
            mock.patch.object(mirror, "_git_value", return_value="deadbeef"),
            mock.patch.object(
                mirror, "_should_reverify_head", return_value=False
            ),
        ):
            mirror._fetch(
                verbose=False,
                depth=None,
                no_fetch_tags=False,
                reset_fetch_config=False,
            )

        mock_run_git.assert_called_once_with(
            ["fetch", "--prune", "origin"] + specs,
        )

    def test_fetch_falls_back_to_per_spec_on_batch_failure(self):
        specs = [
            "+refs/heads/*:refs/heads/*",
            "+refs/branch-heads/*:refs/branch-heads/*",
        ]
        mirror = git_cache.Mirror(
            "https://chromium.googlesource.com/foo/bar",
            refs=["refs/branch-heads/*"],
            print_func=lambda *args: None,
        )

        with self.subTest("optional spec failure warns without clobbering"):

            def run_git_optional_fails(cmd, **_kwargs):
                if "+refs/branch-heads/*:refs/branch-heads/*" in cmd:
                    raise subprocess.CalledProcessError(128, cmd)

            with (
                mock.patch.object(mirror, "config"),
                mock.patch(
                    "subprocess.check_output",
                    return_value=("\n".join(specs) + "\n").encode("utf-8"),
                ),
                mock.patch.object(
                    mirror, "RunGit", side_effect=run_git_optional_fails
                ) as mock_run_git,
                mock.patch.object(
                    mirror, "_git_value", return_value="deadbeef"
                ),
                mock.patch.object(
                    mirror, "_should_reverify_head", return_value=False
                ),
                mock.patch("logging.warning") as mock_warn,
            ):
                mirror._fetch(
                    verbose=False,
                    depth=None,
                    no_fetch_tags=False,
                    reset_fetch_config=False,
                )

            self.assertEqual(
                mock_run_git.call_args_list,
                [
                    mock.call(["fetch", "--prune", "origin"] + specs),
                    mock.call(
                        ["fetch", "--prune", "origin", specs[0]], retry=True
                    ),
                    mock.call(
                        ["fetch", "--prune", "origin", specs[1]], retry=True
                    ),
                ],
            )
            self.assertEqual(
                mock_warn.call_args_list,
                [
                    mock.call(
                        "Batched fetch failed; fetching each refspec individually."
                    ),
                    mock.call(f"Fetch of {specs[1]} failed"),
                ],
            )

        with self.subTest("heads spec failure raises ClobberNeeded"):
            with (
                mock.patch.object(mirror, "config"),
                mock.patch(
                    "subprocess.check_output",
                    return_value=("\n".join(specs) + "\n").encode("utf-8"),
                ),
                mock.patch.object(
                    mirror,
                    "RunGit",
                    side_effect=subprocess.CalledProcessError(128, "git fetch"),
                ) as mock_run_git,
            ):
                with self.assertRaises(git_cache.ClobberNeeded):
                    mirror._fetch(
                        verbose=False,
                        depth=None,
                        no_fetch_tags=False,
                        reset_fetch_config=False,
                    )

            self.assertEqual(
                mock_run_git.call_args_list,
                [
                    mock.call(["fetch", "--prune", "origin"] + specs),
                    mock.call(
                        ["fetch", "--prune", "origin", specs[0]], retry=True
                    ),
                ],
            )

    def test_fetch_skips_commits_already_in_mirror(self):
        present_commit = "a" * 40
        missing_commit = "b" * 40
        mirror = git_cache.Mirror(
            "https://chromium.googlesource.com/foo/bar",
            commits=[present_commit, missing_commit],
            print_func=lambda *args: None,
        )

        with (
            mock.patch.object(mirror, "config"),
            mock.patch("subprocess.check_output", return_value=b""),
            mock.patch.object(
                mirror,
                "_contains_revision_unlocked",
                side_effect=lambda rev: rev == present_commit,
            ) as mock_contains,
            mock.patch.object(mirror, "RunGit") as mock_run_git,
            mock.patch.object(mirror, "_git_value", return_value="deadbeef"),
            mock.patch.object(
                mirror, "_should_reverify_head", return_value=False
            ),
        ):
            mirror._fetch(
                verbose=False,
                depth=None,
                no_fetch_tags=False,
                reset_fetch_config=False,
            )

        self.assertCountEqual(
            [c.args[0] for c in mock_contains.call_args_list],
            [present_commit, missing_commit],
        )
        mock_run_git.assert_called_once_with(
            ["fetch", "origin", missing_commit], retry=True
        )

    def test_contains_revision_unlocked(self):
        mirror = git_cache.Mirror("https://chromium.googlesource.com/foo/bar")
        self.assertFalse(mirror._contains_revision_unlocked("deadbeef"))

        os.makedirs(mirror.mirror_path, exist_ok=True)
        with open(os.path.join(mirror.mirror_path, "config"), "w") as f:
            f.write("[core]\n\tbare = true\n")

        with (
            mock.patch("sys.platform", "win32"),
            mock.patch.object(mirror, "RunGit") as mock_run_git,
        ):
            mirror.git_exe = r"C:\depot_tools\git.exe"
            self.assertTrue(mirror._contains_revision_unlocked("deadbeef"))
            mock_run_git.assert_called_once_with(
                ["cat-file", "-e", "deadbeef^{commit}"]
            )

            mock_run_git.reset_mock()
            mirror.git_exe = "git.bat"
            self.assertTrue(mirror._contains_revision_unlocked("deadbeef"))
            mock_run_git.assert_called_once_with(
                ["cat-file", "-e", "deadbeef^^^^{commit}"]
            )

            mock_run_git.reset_mock()
            mock_run_git.side_effect = subprocess.CalledProcessError(
                128, "git cat-file"
            )
            self.assertFalse(mirror._contains_revision_unlocked("deadbeef"))

    def test_ensure_bootstrapped_avoids_symbolic_ref_and_mkdir_on_cold_cache(
        self,
    ):
        mirror = git_cache.Mirror(
            "https://chromium.googlesource.com/foo/bar",
            print_func=lambda *args: None,
        )
        self.assertFalse(os.path.exists(mirror.mirror_path))

        dir_existed_before_bootstrap = []

        def fake_bootstrap(directory):
            dir_existed_before_bootstrap.append(os.path.exists(directory))
            os.makedirs(directory, exist_ok=True)
            with open(os.path.join(directory, "config"), "w") as f:
                f.write("[core]\n\tbare = true\n")
            return True

        with (
            mock.patch("subprocess.check_output") as mock_check_output,
            mock.patch.object(
                mirror, "bootstrap_repo", side_effect=fake_bootstrap
            ) as mock_bootstrap,
            mock.patch("scm.GIT.GetRemoteObjectFormat", return_value="sha1"),
            mock.patch.object(
                mirror, "_get_object_format", return_value="sha1"
            ),
        ):
            mirror._ensure_bootstrapped(
                depth=None, bootstrap=True, reset_fetch_config=False
            )

        mock_check_output.assert_not_called()
        mock_bootstrap.assert_called_once_with(mirror.mirror_path)
        self.assertEqual(dir_existed_before_bootstrap, [False])

        # Also verify cold cache when bootstrap=False creates mirror_path before
        # git init without calling symbolic-ref on the non-existent mirror.
        gclient_utils.rmtree(mirror.mirror_path)
        self.assertFalse(os.path.exists(mirror.mirror_path))

        init_dir_existed = []

        def fake_run_git(cmd, **_kwargs):
            if cmd[:1] == ["init"]:
                init_dir_existed.append(os.path.isdir(mirror.mirror_path))
                with open(os.path.join(mirror.mirror_path, "config"), "w") as f:
                    f.write("[core]\n\tbare = true\n")

        with (
            mock.patch("subprocess.check_output") as mock_check_output,
            mock.patch("scm.GIT.GetRemoteObjectFormat", return_value="sha1"),
            mock.patch.object(mirror, "RunGit", side_effect=fake_run_git),
            mock.patch.object(mirror, "_set_symbolic_ref"),
        ):
            mirror._ensure_bootstrapped(
                depth=None, bootstrap=False, reset_fetch_config=False
            )

        mock_check_output.assert_not_called()
        self.assertEqual(init_dir_existed, [True])

    def _assertSetsHead(self, remote_info, branch_refs, expected):
        """Drives _set_symbolic_ref over a given remote answer and ref list.

        Passing expected=None asserts HEAD is left alone.
        """
        mirror = git_cache.Mirror(self.origin_dir)
        with mock.patch(
            "gclient_utils.exponential_backoff_retry",
            return_value=remote_info,
        ):
            with mock.patch.object(
                mirror, "_local_branch_refs", return_value=branch_refs
            ):
                with mock.patch.object(mirror, "RunGit") as mock_rungit:
                    mirror._set_symbolic_ref()
        if expected is None:
            for call in mock_rungit.call_args_list:
                self.assertNotIn("symbolic-ref", call.args[0])
        else:
            mock_rungit.assert_called_once_with(
                ["symbolic-ref", "HEAD", expected]
            )

    def testSetSymbolicRefUnknownNoLocalBranches(self):
        self._assertSetsHead("HEAD branch: (unknown)", [], None)

    def testSetSymbolicRefUnknownFallsBackToKnownBranchName(self):
        self._assertSetsHead(
            "HEAD branch: (unknown)",
            ["refs/heads/feature-x", "refs/heads/upstream/main"],
            "refs/heads/upstream/main",
        )

    def testSetSymbolicRefUnknownPrefersLiveBranchOverStaleName(self):
        # The newer upstream/main must beat the frozen master by recency.
        self._assertSetsHead(
            "HEAD branch: (unknown)",
            ["refs/heads/upstream/main", "refs/heads/master"],
            "refs/heads/upstream/main",
        )

    def testSetSymbolicRefUnknownFallsBackToNewestBranch(self):
        self._assertSetsHead(
            "HEAD branch: (unknown)",
            ["refs/heads/feature-x", "refs/heads/feature-y"],
            "refs/heads/feature-x",
        )

    def testSetSymbolicRefKnown(self):
        self._assertSetsHead(
            "HEAD branch: main",
            ["refs/heads/main", "refs/heads/other"],
            "refs/heads/main",
        )

    def testSetSymbolicRefKnownOnEmptyMirror(self):
        # A freshly init'd bare mirror has no branches yet; the advertised
        # default is all there is to go on, and the fetch supplies it.
        self._assertSetsHead("HEAD branch: main", [], "refs/heads/main")

    def testSetSymbolicRefKnownMissingLocallyPicksLiveBranch(self):
        # Remote names a branch this mirror does not carry: pointing HEAD at
        # it would just install a different dead HEAD.
        self._assertSetsHead(
            "HEAD branch: absent",
            ["refs/heads/feature-x", "refs/heads/upstream/main"],
            "refs/heads/upstream/main",
        )

    def testSetSymbolicRefStripsCarriageReturn(self):
        # "git remote show" output read on Windows can carry a CR, which would
        # otherwise be spliced into the refname and rejected by symbolic-ref.
        self._assertSetsHead(
            "  HEAD branch: main\r\n  Remote branches:",
            ["refs/heads/main"],
            "refs/heads/main",
        )

    def _mirror_head(self, mirror):
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        return (
            subprocess.check_output(
                ["git", "--git-dir", cache_dir, "symbolic-ref", "HEAD"]
            )
            .decode("utf-8")
            .strip()
        )

    def testSetSymbolicRefAdvertisedBranchMissingFallsBack(self):
        # A remote can advertise a default branch this mirror does not carry
        # (restricted fetch specs, or a rename whose branch has not been
        # fetched yet). Pointing HEAD at it regardless leaves HEAD dangling,
        # which is the state this module exists to prevent.
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )
        self.git(["branch", "-m", "live"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        with mock.patch(
            "gclient_utils.exponential_backoff_retry",
            return_value="HEAD branch: absent",
        ):
            mirror._set_symbolic_ref()

        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        self.assertEqual(
            subprocess.call(
                [
                    "git",
                    "--git-dir",
                    cache_dir,
                    "rev-parse",
                    "--verify",
                    "--quiet",
                    "HEAD",
                ],
                stdout=subprocess.DEVNULL,
            ),
            0,
            "HEAD must resolve after healing, not dangle",
        )
        self.assertEqual(self._mirror_head(mirror), "refs/heads/live")

    def testPopulateHealsDanglingHead(self):
        # The origin renamed its default branch and its own HEAD dangles, so
        # it advertises no default branch (as happens to GitHub mirrors on
        # *.googlesource.com). The mirror must still end up with HEAD on a
        # live branch.
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )
        self.git(["branch", "-m", "upstream/main"])
        self.git(["symbolic-ref", "HEAD", "refs/heads/gone"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        self.assertEqual(self._mirror_head(mirror), "refs/heads/upstream/main")

    def testPopulateHealsDanglingHeadWithAmbiguousTag(self):
        # A tag sharing the branch's name must not derail the fallback:
        # %(refname:short) would disambiguate the branch as 'heads/main',
        # which must not be mangled into 'refs/heads/heads/main'.
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )
        self.git(["branch", "-m", "main"])
        self.git(["tag", "main"])
        self.git(["symbolic-ref", "HEAD", "refs/heads/gone"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        self.assertEqual(self._mirror_head(mirror), "refs/heads/main")
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        # HEAD must resolve to a commit again.
        subprocess.check_output(
            ["git", "--git-dir", cache_dir, "rev-parse", "--verify", "HEAD"]
        )

    def testPopulateHealsStaleHead(self):
        # The origin renamed its default branch from master to main but kept
        # the frozen master around. A mirror created before the rename has
        # HEAD on master, which still resolves, so only the staleness check
        # can notice that HEAD must be re-verified against the origin.
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        old_date = "2020-01-01T00:00:00 +0000"
        env = os.environ.copy()
        env["GIT_AUTHOR_DATE"] = old_date
        env["GIT_COMMITTER_DATE"] = old_date
        subprocess.check_call(
            [
                "git",
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "old",
            ],
            cwd=self.origin_dir,
            env=env,
        )
        self.git(["branch", "-m", "master"])
        self.git(["checkout", "-q", "-b", "main"])
        with open(os.path.join(self.origin_dir, "bar"), "w") as f:
            f.write("touched\n")
        self.git(["add", "bar"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "new",
            ]
        )

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        # Simulate a mirror created before the rename.
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        subprocess.check_call(
            [
                "git",
                "--git-dir",
                cache_dir,
                "symbolic-ref",
                "HEAD",
                "refs/heads/master",
            ]
        )

        # A local origin is not a supported_project(), which sends every
        # populate down the re-init path where _set_symbolic_ref runs
        # unconditionally. Pin it True so only the staleness check can heal.
        with mock.patch.object(
            git_cache.Mirror, "supported_project", return_value=True
        ):
            mirror.populate()

        self.assertEqual(self._mirror_head(mirror), "refs/heads/main")

    def testPopulateHealsStaleHeadWithoutAdvertisedDefault(self):
        # GitHub-mirror layout: frozen master, live upstream/main, dangling
        # origin HEAD (no advertised default); heal must pick the live branch.
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        old_date = "2020-01-01T00:00:00 +0000"
        env = os.environ.copy()
        env["GIT_AUTHOR_DATE"] = old_date
        env["GIT_COMMITTER_DATE"] = old_date
        subprocess.check_call(
            [
                "git",
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "old",
            ],
            cwd=self.origin_dir,
            env=env,
        )
        self.git(["branch", "-m", "master"])
        self.git(["checkout", "-q", "-b", "upstream/main"])
        with open(os.path.join(self.origin_dir, "bar"), "w") as f:
            f.write("touched\n")
        self.git(["add", "bar"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "new",
            ]
        )
        self.git(["symbolic-ref", "HEAD", "refs/heads/gone"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        self.assertEqual(self._mirror_head(mirror), "refs/heads/upstream/main")

    def testPopulateKeepsUpstreamMasterHead(self):
        # A mirror whose HEAD validly points at refs/heads/upstream/master
        # (GitHub layout, no plain master) must not be clobbered every populate
        # just because 'master' appears in HEAD.
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )
        self.git(["branch", "-m", "upstream/master"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        subprocess.check_call(
            [
                "git",
                "--git-dir",
                cache_dir,
                "symbolic-ref",
                "HEAD",
                "refs/heads/upstream/master",
            ]
        )
        # Survives only if the guard does not delete the mirror.
        sentinel = os.path.join(cache_dir, "not_clobbered")
        with open(sentinel, "w"):
            pass

        mirror.populate()

        self.assertTrue(os.path.exists(sentinel))
        self.assertEqual(
            self._mirror_head(mirror), "refs/heads/upstream/master"
        )

    def testHeadStaleCheckIgnoresFutureDatedBranches(self):
        # A busy default branch must never look stale, even when some side
        # branch carries a bogus future committer date. Otherwise a repo
        # like chromium/src would pay the remote default-branch lookup on
        # every populate.
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "current",
            ]
        )
        self.git(["branch", "-m", "main"])
        self.git(["checkout", "-q", "-b", "weird"])
        with open(os.path.join(self.origin_dir, "bar"), "w") as f:
            f.write("touched\n")
        self.git(["add", "bar"])
        future_date = "2090-01-01T00:00:00 +0000"
        env = os.environ.copy()
        env["GIT_AUTHOR_DATE"] = future_date
        env["GIT_COMMITTER_DATE"] = future_date
        subprocess.check_call(
            [
                "git",
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "future",
            ],
            cwd=self.origin_dir,
            env=env,
        )
        self.git(["checkout", "-q", "main"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        self.assertFalse(mirror._head_looks_stale())
        self.assertEqual(self._mirror_head(mirror), "refs/heads/main")

    def testHeadStaleCheckSurvivesGitStderrNoise(self):
        # git writes to stderr routinely (credential helpers, redirect
        # warnings, GIT_TRACE). The staleness check must not read those bytes
        # as its value: a parse failure there reports "not stale", silently
        # re-freezing the snapshot this check exists to unfreeze.
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        old_date = "2020-01-01T00:00:00 +0000"
        env = os.environ.copy()
        env["GIT_AUTHOR_DATE"] = old_date
        env["GIT_COMMITTER_DATE"] = old_date
        subprocess.check_call(
            [
                "git",
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "old",
            ],
            cwd=self.origin_dir,
            env=env,
        )
        self.git(["branch", "-m", "master"])
        self.git(["checkout", "-q", "-b", "main"])
        with open(os.path.join(self.origin_dir, "bar"), "w") as f:
            f.write("touched\n")
        self.git(["add", "bar"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "new",
            ]
        )

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        subprocess.check_call(
            [
                "git",
                "--git-dir",
                cache_dir,
                "symbolic-ref",
                "HEAD",
                "refs/heads/master",
            ]
        )

        with mock.patch.dict(os.environ, {"GIT_TRACE": "1"}):
            self.assertTrue(mirror._head_looks_stale())

    def testUpdateBootstrapFailsWhenGenNumberFails(self):
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        with mock.patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "git number"),
        ):
            with mock.patch.object(mirror, "_set_symbolic_ref") as heal:
                self.assertFalse(mirror.update_bootstrap())
                heal.assert_called_once()

    def testUpdateBootstrapReturnsFalseWhenHealFails(self):
        # The generation number fails and the HEAD repair cannot reach the
        # remote either. update_bootstrap must report failure rather than let
        # the network error escape as a traceback.
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        with mock.patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "git number"),
        ):
            with mock.patch.object(
                mirror,
                "_set_symbolic_ref",
                side_effect=subprocess.CalledProcessError(1, "git remote show"),
            ):
                self.assertFalse(mirror.update_bootstrap())

    def testUpdateBootstrapHealsBrokenHead(self):
        self.git(["init", "-q"])
        with open(os.path.join(self.origin_dir, "foo"), "w") as f:
            f.write("touched\n")
        self.git(["add", "foo"])
        self.git(
            [
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                "foo",
            ]
        )
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        # Break the mirror's HEAD the way a default-branch rename does.
        subprocess.check_call(
            [
                "git",
                "--git-dir",
                cache_dir,
                "symbolic-ref",
                "HEAD",
                "refs/heads/gone",
            ]
        )

        # Repairs HEAD like _set_symbolic_ref (tested on its own) would,
        # minus the remote lookup.
        def heal():
            branch = (
                subprocess.check_output(
                    [
                        "git",
                        "--git-dir",
                        cache_dir,
                        "for-each-ref",
                        "--count=1",
                        "--format=%(refname)",
                        "refs/heads",
                    ]
                )
                .decode()
                .strip()
            )
            subprocess.check_call(
                ["git", "--git-dir", cache_dir, "symbolic-ref", "HEAD", branch]
            )

        real_check_output = subprocess.check_output
        gen_calls = []

        # git number fails on the broken HEAD, then succeeds after the heal.
        def fake_check_output(cmd, *args, **kwargs):
            if "number" in cmd:
                gen_calls.append(cmd)
                if len(gen_calls) == 1:
                    raise subprocess.CalledProcessError(1, cmd)
                return b"42\n"
            return real_check_output(cmd, *args, **kwargs)

        with mock.patch("git_cache.Gsutil") as gsutil_cls:
            gsutil_cls.return_value.check_call_with_retries.return_value = (
                0,
                "",
                "",
            )
            # 0 == success; a bare MagicMock would read as a failed upload.
            gsutil_cls.return_value.call.return_value = 0
            with mock.patch(
                "subprocess.check_output", side_effect=fake_check_output
            ):
                with mock.patch.object(
                    mirror, "_set_symbolic_ref", side_effect=heal
                ) as heal_mock:
                    self.assertTrue(mirror.update_bootstrap())
                    heal_mock.assert_called_once()
        self.assertEqual(len(gen_calls), 2)

    def _commitOrigin(self, name, date=None):
        env = os.environ.copy()
        if date:
            env["GIT_AUTHOR_DATE"] = date
            env["GIT_COMMITTER_DATE"] = date
        with open(os.path.join(self.origin_dir, name), "w") as f:
            f.write(name + "\n")
        self.git(["add", name])
        subprocess.check_call(
            [
                "git",
                "-c",
                "user.name=Test user",
                "-c",
                "user.email=joj@test.com",
                "commit",
                "-m",
                name,
            ],
            cwd=self.origin_dir,
            env=env,
        )

    def _updateBootstrapRecordingUploads(self, mirror, cache_dir):
        """Runs update_bootstrap with the real heal path, recording uploads.

        `git number` is stubbed to the commit count of whatever HEAD names at
        the time it runs, so the recorded destination shows which branch the
        snapshot was cut from.
        """
        real_check_output = subprocess.check_output
        calls = []

        def fake_check_output(cmd, *args, **kwargs):
            if "number" in cmd:
                return real_check_output(
                    [
                        "git",
                        "--git-dir",
                        cache_dir,
                        "rev-list",
                        "--count",
                        "HEAD",
                    ]
                )
            return real_check_output(cmd, *args, **kwargs)

        with mock.patch("git_cache.Gsutil") as gsutil_cls:
            gs = gsutil_cls.return_value
            gs.check_call_with_retries.return_value = (0, "", "")
            gs.call.side_effect = lambda *a: calls.append(a) or 0
            with mock.patch(
                "subprocess.check_output", side_effect=fake_check_output
            ):
                ok = mirror.update_bootstrap()
        uploads = [c for c in calls if "rsync" in c]
        return ok, uploads

    def testUpdateBootstrapUploadsAfterHealingUnadvertisedDefault(self):
        # The production case: the remote advertises no default branch and the
        # mirror's HEAD is dead, so the generation number cannot be computed.
        # Before healing, this uploaded nothing while reporting success, which
        # is why these repos have no snapshot at all.
        self.git(["init", "-q"])
        self._commitOrigin("foo")
        self.git(["branch", "-m", "live"])
        # An origin whose HEAD names a missing branch advertises no default.
        self.git(["symbolic-ref", "HEAD", "refs/heads/does-not-exist"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        subprocess.check_call(
            [
                "git",
                "--git-dir",
                cache_dir,
                "symbolic-ref",
                "HEAD",
                "refs/heads/gone",
            ]
        )

        ok, uploads = self._updateBootstrapRecordingUploads(mirror, cache_dir)

        self.assertEqual(len(uploads), 1, "snapshot must be uploaded")
        self.assertTrue(uploads[0][-1].endswith("/1"), uploads[0][-1])
        self.assertEqual(self._mirror_head(mirror), "refs/heads/live")
        self.assertTrue(ok)

    def testUpdateBootstrapSnapshotTracksLiveBranchNotFrozenHead(self):
        # A HEAD frozen on a pre-rename branch still resolves, so the
        # generation number is computable and the upload "succeeds" while
        # pinning the snapshot to the stale branch forever.
        self.git(["init", "-q"])
        self._commitOrigin("old", date="2020-01-01T00:00:00 +0000")
        self.git(["branch", "-m", "master"])
        self.git(["checkout", "-q", "-b", "upstream/main"])
        self._commitOrigin("new1")
        self._commitOrigin("new2")
        self.git(["symbolic-ref", "HEAD", "refs/heads/does-not-exist"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        # Model a mirror created before the rename.
        subprocess.check_call(
            [
                "git",
                "--git-dir",
                cache_dir,
                "symbolic-ref",
                "HEAD",
                "refs/heads/master",
            ]
        )
        mirror.populate()

        ok, uploads = self._updateBootstrapRecordingUploads(mirror, cache_dir)

        self.assertEqual(len(uploads), 1)
        # master is 1 commit, upstream/main is 3. The snapshot must be cut from
        # the live branch, not the frozen one.
        self.assertTrue(uploads[0][-1].endswith("/3"), uploads[0][-1])
        self.assertEqual(self._mirror_head(mirror), "refs/heads/upstream/main")
        self.assertTrue(ok)

    def testUpdateBootstrapCommandExitsNonZeroWhenUnhealable(self):
        # Nothing to point HEAD at, so no generation number is possible. The
        # command must exit non-zero: a green builder that uploaded nothing is
        # how these snapshots went stale unnoticed.
        self.git(["init", "-q"])

        with mock.patch("git_cache.Gsutil"):
            rc = git_cache.CMDupdate_bootstrap(
                git_cache.OptionParser(), [self.origin_dir]
            )

        self.assertEqual(rc, 1)

    def testPopulateHealsDanglingHeadDespiteGitStderrNoise(self):
        # The dangling-HEAD detector compares rev-parse's output against the
        # literal "HEAD". Folding git's stderr into that value disables the
        # detector silently: unlike a bad int(), nothing raises.
        self.git(["init", "-q"])
        self._commitOrigin("foo")
        self.git(["branch", "-m", "live"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        subprocess.check_call(
            [
                "git",
                "--git-dir",
                cache_dir,
                "symbolic-ref",
                "HEAD",
                "refs/heads/gone",
            ]
        )

        # supported_project() is False for a local origin, which would heal
        # HEAD via the re-init path regardless. Pin it so only the detector can.
        with mock.patch.object(
            git_cache.Mirror, "supported_project", return_value=True
        ):
            with mock.patch.dict(os.environ, {"GIT_TRACE": "1"}):
                mirror.populate()

        self.assertEqual(self._mirror_head(mirror), "refs/heads/live")

    def testUpdateBootstrapFailsWhenUploadFails(self):
        # The generation number is computable and the snapshot directory is
        # uploaded, but the upload itself fails. Reporting success here is how
        # a builder stays green while publishing nothing.
        self.git(["init", "-q"])
        self._commitOrigin("foo")
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        real_check_output = subprocess.check_output

        def fake_check_output(cmd, *args, **kwargs):
            if "number" in cmd:
                return b"42\n"
            return real_check_output(cmd, *args, **kwargs)

        with mock.patch("git_cache.Gsutil") as gsutil_cls:
            gs = gsutil_cls.return_value
            gs.check_call_with_retries.return_value = (0, "", "")
            gs.call.side_effect = lambda *a: 1 if "rsync" in a else 0
            with mock.patch(
                "subprocess.check_output", side_effect=fake_check_output
            ):
                self.assertFalse(mirror.update_bootstrap())

    @contextlib.contextmanager
    def _recordUpdateBootstrap(self, mirror, on_upload=None, fail_git=None):
        """Records the git and gsutil calls of update_bootstrap, in order.

        Git really runs, leaving the mirror as it would be uploaded; gsutil is
        faked. Yields a list of ("git", cmd) and ("gsutil", args) events.
        on_upload runs as the snapshot is rsync'd, and the git subcommand named
        by fail_git fails instead of running.
        """
        events = []
        real_run_git = mirror.RunGit
        real_check_output = subprocess.check_output

        def record_git(cmd, *args, **kwargs):
            events.append(("git", list(cmd)))
            if cmd[0] == fail_git:
                raise subprocess.CalledProcessError(1, ["git"] + cmd)
            return real_run_git(cmd, *args, **kwargs)

        def record_gsutil(*args):
            events.append(("gsutil", args))
            if on_upload and "rsync" in args:
                on_upload()
            return 0

        def fake_check_output(cmd, *args, **kwargs):
            # `git number` is a depot_tools script; any number will do.
            if "number" in cmd:
                return b"42\n"
            return real_check_output(cmd, *args, **kwargs)

        with (
            mock.patch("git_cache.Gsutil") as gsutil_cls,
            mock.patch(
                "subprocess.check_output", side_effect=fake_check_output
            ),
            mock.patch.object(mirror, "RunGit", side_effect=record_git),
        ):
            gs = gsutil_cls.return_value
            gs.check_call_with_retries.return_value = (0, "", "")
            gs.call.side_effect = record_gsutil
            yield events

    @staticmethod
    def _gitCommands(events):
        return [args for kind, args in events if kind == "git"]

    def _assertGitDoneBeforeUpload(self, events):
        uploads = [
            i
            for i, (kind, args) in enumerate(events)
            if kind == "gsutil" and "rsync" in args
        ]
        self.assertEqual(len(uploads), 1, events)
        self.assertEqual(
            self._gitCommands(events[uploads[0] :]),
            [],
            "git must be done with the mirror before it is uploaded",
        )

    @staticmethod
    def _looseObjects(git_dir):
        """Returns the loose object files in git_dir, as rsync would see them."""
        objects_dir = os.path.join(git_dir, "objects")
        return sorted(
            os.path.join(d, f)
            for d in os.listdir(objects_dir)
            if len(d) == 2 and all(c in "0123456789abcdef" for c in d)
            for f in os.listdir(os.path.join(objects_dir, d))
        )

    def testUpdateBootstrapGcCommands(self):
        self._makeGitRepo()
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        with self._recordUpdateBootstrap(mirror) as events:
            self.assertTrue(mirror.update_bootstrap(gc_aggressive=False))

        # gc prunes unreachable objects itself; no separate prune is needed.
        self.assertEqual(
            self._gitCommands(events),
            [["pack-refs", "--all"], ["gc", "--prune=all"]],
        )
        self._assertGitDoneBeforeUpload(events)

    def testUpdateBootstrapGcAggressiveCommands(self):
        self._makeGitRepo()
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        with self._recordUpdateBootstrap(mirror) as events:
            self.assertTrue(mirror.update_bootstrap(gc_aggressive=True))

        self.assertEqual(
            self._gitCommands(events),
            [
                ["pack-refs", "--all"],
                ["reflog", "expire", "--all"],
                # -a, not -A or --unpack-unreachable, which would explode
                # unreachable packed objects into loose files.
                [
                    "repack",
                    "-d",
                    "-l",
                    "-f",
                    "--depth=50",
                    "--window=250",
                    "-a",
                    "--window-memory=1g",
                ],
                # repack never deletes unreachable loose objects.
                ["prune", "--expire=now"],
            ],
        )
        self._assertGitDoneBeforeUpload(events)

    def testUpdateBootstrapGcAggressiveDoesNotUploadWhenPruneFails(self):
        # A failed prune can leave the loose objects behind or point at a
        # corrupt mirror; either way, the mirror must not be published.
        self._makeGitRepo()
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()

        with self._recordUpdateBootstrap(mirror, fail_git="prune") as events:
            with self.assertRaises(subprocess.CalledProcessError):
                mirror.update_bootstrap(gc_aggressive=True)

        self.assertIn(("git", ["prune", "--expire=now"]), events)
        self.assertEqual(
            [args for kind, args in events if kind == "gsutil"],
            [],
            "neither the snapshot nor its .ready marker may be uploaded",
        )

    def _assertUpdateBootstrapUploadsNoLooseObjects(self, gc_aggressive):
        git = "git.bat" if sys.platform == "win32" else "git"
        self._makeGitRepo()
        self.git(["checkout", "-q", "-b", "doomed"])
        self._commitOrigin("doomed")
        self.git(["checkout", "-q", "-"])
        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        mirror_git = [git, "--git-dir", mirror.mirror_path]

        def rev_parse(rev):
            out = subprocess.check_output(mirror_git + ["rev-parse", rev])
            return out.decode("utf-8").strip()

        # Long-lived mirrors collect unreachable loose objects: small fetches
        # land loose (below transfer.unpackLimit), and `fetch --prune` later
        # drops the refs that kept them reachable...
        doomed = rev_parse("refs/heads/doomed")
        self.git(["branch", "-q", "-D", "doomed"])
        mirror.populate()
        # ...while interrupted fetches leave objects no ref ever pointed at...
        orphan = (
            subprocess.run(
                mirror_git + ["hash-object", "-w", "--stdin"],
                input=b"orphan\n",
                stdout=subprocess.PIPE,
                check=True,
            )
            .stdout.decode("utf-8")
            .strip()
        )
        # ...and unreachable objects in a pack whose mtime is ahead of the
        # clock would be loosened by 'repack -A --unpack-unreachable=all'.
        packed = (
            subprocess.run(
                mirror_git + ["hash-object", "-w", "--stdin"],
                input=b"packed unreachable\n",
                stdout=subprocess.PIPE,
                check=True,
            )
            .stdout.decode("utf-8")
            .strip()
        )
        pack_dir = os.path.join(mirror.mirror_path, "objects", "pack")
        pack_hash = (
            subprocess.run(
                mirror_git
                + ["pack-objects", "-q", os.path.join(pack_dir, "pack")],
                input=(packed + "\n").encode("utf-8"),
                stdout=subprocess.PIPE,
                check=True,
            )
            .stdout.decode("utf-8")
            .strip()
        )
        subprocess.check_call(mirror_git + ["prune-packed"])
        # 'repack -a' (gc_aggressive=True) drops unreachable packs regardless
        # of mtime, whereas 'gc --prune=all' passes 'all' to pack-objects
        # which approxidate() evaluates as current time.
        pack_mtime = time.time() + (3600 if gc_aggressive else -3600)
        for ext in ("pack", "idx"):
            os.utime(
                os.path.join(pack_dir, f"pack-{pack_hash}.{ext}"),
                (pack_mtime, pack_mtime),
            )
        loose_before = self._looseObjects(mirror.mirror_path)
        self.assertIn(os.path.join(doomed[:2], doomed[2:]), loose_before)
        self.assertIn(os.path.join(orphan[:2], orphan[2:]), loose_before)
        self.assertNotIn(os.path.join(packed[:2], packed[2:]), loose_before)
        head = rev_parse("HEAD")

        uploaded = []

        def on_upload():
            uploaded.append(self._looseObjects(mirror.mirror_path))

        with self._recordUpdateBootstrap(mirror, on_upload=on_upload):
            self.assertTrue(
                mirror.update_bootstrap(gc_aggressive=gc_aggressive)
            )

        self.assertEqual(uploaded, [[]], "loose objects were uploaded")
        for oid in (doomed, orphan, packed):
            self.assertNotEqual(
                subprocess.call(
                    mirror_git + ["cat-file", "-e", oid],
                    stderr=subprocess.DEVNULL,
                ),
                0,
                f"unreachable object {oid} survived",
            )
        # Pruning must not take any reachable history with it.
        subprocess.check_call(mirror_git + ["cat-file", "-e", head])
        subprocess.check_call(mirror_git + ["fsck", "--connectivity-only"])

    def testUpdateBootstrapUploadsNoLooseObjects(self):
        self._assertUpdateBootstrapUploadsNoLooseObjects(gc_aggressive=False)

    def testUpdateBootstrapGcAggressiveUploadsNoLooseObjects(self):
        self._assertUpdateBootstrapUploadsNoLooseObjects(gc_aggressive=True)

    def testPopulateSkipsRemoteWhenHeadMatchesLocalPreference(self):
        # A dormant default with a live side branch keeps _head_looks_stale
        # true forever. Healing cannot change anything there, so consulting the
        # remote would put a `git remote show` on every populate for good.
        self.git(["init", "-q"])
        self._commitOrigin("old", date="2020-01-01T00:00:00 +0000")
        self.git(["branch", "-m", "main"])
        self.git(["checkout", "-q", "-b", "feature"])
        self._commitOrigin("new")
        self.git(["checkout", "-q", "main"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        self.assertEqual(self._mirror_head(mirror), "refs/heads/main")
        # Stale, but HEAD is already what the local branches prefer.
        self.assertTrue(mirror._head_looks_stale())

        with mock.patch.object(
            git_cache.Mirror, "supported_project", return_value=True
        ):
            with mock.patch.object(mirror, "_set_symbolic_ref") as heal:
                mirror.populate()
                heal.assert_not_called()

    def testPopulateStopsRecheckingAfterRemoteConfirmsHead(self):
        # The remote confirms the HEAD we already have, so the staleness
        # predicate and the local-preference mismatch both stay true. Without a
        # bound this re-asks the remote on every populate forever.
        self.git(["init", "-q"])
        self._commitOrigin("old", date="2020-01-01T00:00:00 +0000")
        self.git(["branch", "-m", "master"])
        self.git(["checkout", "-q", "-b", "upstream/main"])
        self._commitOrigin("new")
        # The origin advertises the quiet branch, so healing is a no-op.
        self.git(["symbolic-ref", "HEAD", "refs/heads/master"])

        mirror = git_cache.Mirror(self.origin_dir)
        mirror.populate()
        cache_dir = os.path.join(
            self.cache_dir, mirror.UrlToCacheDir(self.origin_dir)
        )
        subprocess.check_call(
            [
                "git",
                "--git-dir",
                cache_dir,
                "symbolic-ref",
                "HEAD",
                "refs/heads/master",
            ]
        )
        # The setup populate already spent this mirror's recheck allowance.
        subprocess.check_call(
            [
                "git",
                "--git-dir",
                cache_dir,
                "config",
                "--unset",
                "cache.headcheckedat",
            ]
        )

        with mock.patch.object(
            git_cache.Mirror, "supported_project", return_value=True
        ):
            with mock.patch.object(mirror, "_set_symbolic_ref") as heal:
                mirror.populate()
                mirror.populate()
                self.assertEqual(
                    heal.call_count,
                    1,
                    "remote must be consulted once, not per populate",
                )


class GitCacheDirTest(unittest.TestCase):
    def setUp(self):
        try:
            delattr(git_cache.Mirror, "cachepath")
        except AttributeError:
            pass
        super(GitCacheDirTest, self).setUp()

    def tearDown(self):
        try:
            delattr(git_cache.Mirror, "cachepath")
        except AttributeError:
            pass
        super(GitCacheDirTest, self).tearDown()

    def test_git_config_read(self):
        (fd, tmpFile) = tempfile.mkstemp()
        old = git_cache.Mirror._GIT_CONFIG_LOCATION
        try:
            try:
                os.write(fd, b'[cache]\n  cachepath="hello world"\n')
            finally:
                os.close(fd)

            git_cache.Mirror._GIT_CONFIG_LOCATION = ["-f", tmpFile]

            self.assertEqual(git_cache.Mirror.GetCachePath(), "hello world")
        finally:
            git_cache.Mirror._GIT_CONFIG_LOCATION = old
            os.remove(tmpFile)

    def test_environ_read(self):
        path = os.environ.get("GIT_CACHE_PATH")
        config = os.environ.get("GIT_CONFIG")
        try:
            os.environ["GIT_CACHE_PATH"] = "hello world"
            os.environ["GIT_CONFIG"] = "disabled"

            self.assertEqual(git_cache.Mirror.GetCachePath(), "hello world")
        finally:
            for name, val in zip(
                ("GIT_CACHE_PATH", "GIT_CONFIG"), (path, config)
            ):
                if val is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = val

    def test_manual_set(self):
        git_cache.Mirror.SetCachePath("hello world")
        self.assertEqual(git_cache.Mirror.GetCachePath(), "hello world")

    def test_unconfigured(self):
        path = os.environ.get("GIT_CACHE_PATH")
        config = os.environ.get("GIT_CONFIG")
        try:
            os.environ.pop("GIT_CACHE_PATH", None)
            os.environ["GIT_CONFIG"] = "disabled"

            with self.assertRaisesRegex(RuntimeError, r"cache\.cachepath"):
                git_cache.Mirror.GetCachePath()

            # negatively cached value still raises
            with self.assertRaisesRegex(RuntimeError, r"cache\.cachepath"):
                git_cache.Mirror.GetCachePath()
        finally:
            for name, val in zip(
                ("GIT_CACHE_PATH", "GIT_CONFIG"), (path, config)
            ):
                if val is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = val


class BootstrapConcurrencyTest(unittest.TestCase):
    def test_default_tracks_sync_parallelism_up_to_cap(self):
        with mock.patch.dict("os.environ", clear=False):
            os.environ.pop("GIT_CACHE_BOOTSTRAP_CONCURRENCY", None)
            with mock.patch("gclient_utils.NumLocalCpus", return_value=4):
                self.assertEqual(
                    git_cache._bootstrap_concurrency(),
                    git_cache.DEFAULT_MIN_BOOTSTRAP_CONCURRENCY,
                )
            with mock.patch("gclient_utils.NumLocalCpus", return_value=24):
                self.assertEqual(git_cache._bootstrap_concurrency(), 24)
            with mock.patch("gclient_utils.NumLocalCpus", return_value=128):
                self.assertEqual(
                    git_cache._bootstrap_concurrency(),
                    git_cache.DEFAULT_MAX_BOOTSTRAP_CONCURRENCY,
                )
            with mock.patch("gclient_utils.NumLocalCpus", return_value=384):
                self.assertEqual(
                    git_cache._bootstrap_concurrency(),
                    git_cache.DEFAULT_MAX_BOOTSTRAP_CONCURRENCY,
                )

    def test_override(self):
        with mock.patch.dict(
            "os.environ", {"GIT_CACHE_BOOTSTRAP_CONCURRENCY": "32"}
        ):
            self.assertEqual(git_cache._bootstrap_concurrency(), 32)

    def test_clamped_to_at_least_one(self):
        with mock.patch.dict(
            "os.environ", {"GIT_CACHE_BOOTSTRAP_CONCURRENCY": "0"}
        ):
            self.assertEqual(git_cache._bootstrap_concurrency(), 1)

    def test_garbage_falls_back_to_default(self):
        with mock.patch.dict(
            "os.environ", {"GIT_CACHE_BOOTSTRAP_CONCURRENCY": "lots"}
        ):
            self.assertEqual(
                git_cache._bootstrap_concurrency(),
                max(
                    git_cache.DEFAULT_MIN_BOOTSTRAP_CONCURRENCY,
                    min(
                        gclient_utils.NumLocalCpus(),
                        git_cache.DEFAULT_MAX_BOOTSTRAP_CONCURRENCY,
                    ),
                ),
            )


class GetBootstrapDefaultBranchTest(unittest.TestCase):
    def setUp(self):
        self.cache_dir = tempfile.mkdtemp(prefix="gc_defbranch_")
        self.addCleanup(shutil.rmtree, self.cache_dir, ignore_errors=True)
        git_cache.Mirror.SetCachePath(self.cache_dir)

    def _patched(self, ls_lines, head="ref: refs/heads/main\n", ls_code=0):
        class _FakeGsutil:
            def __init__(self, *a, **k):
                pass

            def check_call(self, *args):
                if args[0] == "ls":
                    return (ls_code, "\n".join(ls_lines), "")
                if args[0] == "cat":
                    return (0, head, "")
                return (1, "", "")

        return mock.patch.object(git_cache, "Gsutil", _FakeGsutil)

    def test_reads_default_branch_from_snapshot_head(self):
        m = git_cache.Mirror("https://chromium.googlesource.com/foo/bar")
        gp = m._gs_path
        with self._patched(["%s/42/" % gp, "%s/42.ready" % gp]):
            self.assertEqual(m.get_bootstrap_default_branch(), "main")

    def test_respects_non_main_default(self):
        m = git_cache.Mirror("https://chromium.googlesource.com/foo/bar")
        gp = m._gs_path
        with self._patched(
            ["%s/7/" % gp, "%s/7.ready" % gp], head="ref: refs/heads/master\n"
        ):
            self.assertEqual(m.get_bootstrap_default_branch(), "master")

    def test_bucket_without_snapshot_returns_none(self):
        # Supported host, but no snapshot uploaded for this repo yet.
        m = git_cache.Mirror("https://chromium.googlesource.com/foo/bar")
        with self._patched([]):
            self.assertIsNone(m.get_bootstrap_default_branch())

    def test_unsupported_host_returns_none(self):
        # Host has no bootstrap bucket at all.
        with mock.patch.dict("os.environ", clear=False):
            os.environ.pop("OVERRIDE_BOOTSTRAP_BUCKET", None)
            m = git_cache.Mirror("https://unknown.example.com/foo/bar")
            self.assertIsNone(m.get_bootstrap_default_branch())


class BootstrapBucketTest(unittest.TestCase):
    def setUp(self):
        self.cache_dir = tempfile.mkdtemp(prefix="gc_bucket_")
        self.addCleanup(shutil.rmtree, self.cache_dir, ignore_errors=True)
        git_cache.Mirror.SetCachePath(self.cache_dir)
        mock.patch.dict("os.environ", clear=False).start()
        self.addCleanup(mock.patch.stopall)
        os.environ.pop("OVERRIDE_BOOTSTRAP_BUCKET", None)

    def test_chromium_host(self):
        m = git_cache.Mirror("https://chromium.googlesource.com/v8/v8")
        self.assertEqual(m.bootstrap_bucket, "chromium-git-cache")

    def test_additional_public_hosts(self):
        for host in (
            "dawn",
            "skia",
            "webrtc",
            "pdfium",
            "boringssl",
            "aomedia",
            "quiche",
            "swiftshader",
            "android",
        ):
            m = git_cache.Mirror("https://%s.googlesource.com/x" % host)
            self.assertEqual(m.bootstrap_bucket, "chromium-git-cache", host)

    def test_unknown_host_returns_none(self):
        self.assertIsNone(
            git_cache.Mirror("https://example.com/x").bootstrap_bucket
        )

    def test_aliased_url(self):
        url = (
            "https://chrome-internal.googlesource.com/"
            "chrome/experimental/chromium/src"
        )
        m = git_cache.Mirror(url)
        self.assertEqual(m.basedir, "chromium.googlesource.com-chromium-src")
        self.assertEqual(m.bootstrap_bucket, "chromium-git-cache")
        expected_gs_path = (
            "gs://chromium-git-cache/v2/chromium.googlesource.com-chromium-src"
        )
        self.assertEqual(m._gs_path, expected_gs_path)

    def test_override_env_wins(self):
        with mock.patch.dict(
            "os.environ", {"OVERRIDE_BOOTSTRAP_BUCKET": "my-bucket"}
        ):
            m = git_cache.Mirror("https://example.com/x")
            self.assertEqual(m.bootstrap_bucket, "my-bucket")

    def test_supported_project_only_comprehensive_hosts(self):
        # Only fully-snapshotted hosts get gc.autopacklimit=0 / re-bootstrap.
        self.assertTrue(
            git_cache.Mirror(
                "https://chromium.googlesource.com/x"
            ).supported_project()
        )
        # The other bucket hosts still seed from a snapshot when available, but
        # keep normal git pack maintenance (a repo there may 404).
        for host in (
            "dawn",
            "skia",
            "webrtc",
            "pdfium",
            "boringssl",
            "aomedia",
            "quiche",
            "swiftshader",
            "android",
        ):
            m = git_cache.Mirror("https://%s.googlesource.com/x" % host)
            self.assertFalse(m.supported_project(), host)
            self.assertEqual(m.bootstrap_bucket, "chromium-git-cache", host)

    def test_supported_project_chrome_internal(self):
        m = git_cache.Mirror("https://chrome-internal.googlesource.com/x")
        self.assertTrue(m.supported_project())

    def test_supported_project_unknown_host(self):
        m = git_cache.Mirror("https://example.com/x")
        self.assertFalse(m.supported_project())


class MirrorTest(unittest.TestCase):
    def setUp(self):
        self.cache_dir = tempfile.mkdtemp(prefix="gc_mirror_test_")
        self.addCleanup(shutil.rmtree, self.cache_dir, ignore_errors=True)
        git_cache.Mirror.SetCachePath(self.cache_dir)

    def test_same_cache_for_authenticated_and_unauthenticated_urls(self):
        # GoB can fetch a repo via two different URLs; if the url contains '/a/'
        # it forces authenticated access instead of allowing anonymous access,
        # even in the case where a repo is public. We want this in order to make
        # sure bots are authenticated and get the right quotas. However, we
        # only want to maintain a single cache for the repo.
        self.assertEqual(
            git_cache.Mirror.UrlToCacheDir(
                "https://chromium.googlesource.com/a/chromium/src.git"
            ),
            "chromium.googlesource.com-chromium-src",
        )

    def test_ssh_url_in_UrlToCacheDir_and_CacheDirToUrl(self):
        ssh_url = "git@github.com:chromium/chromium.git"
        self.assertEqual(
            git_cache.Mirror.UrlToCacheDir(ssh_url),
            "git@github.com__chromium-chromium",
        )
        self.assertEqual(
            git_cache.Mirror.CacheDirToUrl(
                git_cache.Mirror.UrlToCacheDir(ssh_url)
            ),
            ssh_url[:-4],
        )

    def test_git_exe_uses_git_common_git_exe(self):
        self.assertEqual(git_cache.Mirror.git_exe, git_common.GIT_EXE)

    def test_run_git_sets_shell_false_for_git_exe(self):
        mirror = git_cache.Mirror("https://chromium.googlesource.com/foo/bar")
        with (
            mock.patch("sys.platform", "win32"),
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("gclient_utils.CheckCallAndFilter") as mock_ccaf,
        ):
            mirror.git_exe = r"C:\depot_tools\git.exe"
            mirror.RunGit(["status"], print_stdout=False)
            _, kwargs = mock_ccaf.call_args
            self.assertIs(kwargs.get("shell"), False)
            self.assertEqual(
                kwargs["env"].get("NoDefaultCurrentDirectoryInExePath"), "1"
            )

            mock_ccaf.reset_mock()
            mirror.git_exe = "git.bat"
            mirror.RunGit(["status"], print_stdout=False)
            _, kwargs = mock_ccaf.call_args
            self.assertNotIn("shell", kwargs)
            self.assertEqual(
                kwargs["env"].get("NoDefaultCurrentDirectoryInExePath"), "1"
            )

    def test_contains_revision_on_windows_git_exe_vs_git_bat(self):
        mirror = git_cache.Mirror("https://chromium.googlesource.com/foo/bar")
        os.makedirs(mirror.mirror_path, exist_ok=True)
        with open(os.path.join(mirror.mirror_path, "config"), "w") as f:
            f.write("[core]\n\tbare = true\n")

        with (
            mock.patch("sys.platform", "win32"),
            mock.patch.object(mirror, "RunGit") as mock_run_git,
        ):
            mirror.git_exe = r"C:\depot_tools\git.exe"
            self.assertTrue(mirror.contains_revision("deadbeef", timeout=0))
            mock_run_git.assert_called_once_with(
                ["cat-file", "-e", "deadbeef^{commit}"]
            )

            mock_run_git.reset_mock()
            mirror.git_exe = "git.bat"
            self.assertTrue(mirror.contains_revision("deadbeef", timeout=0))
            mock_run_git.assert_called_once_with(
                ["cat-file", "-e", "deadbeef^^^^{commit}"]
            )

            mock_run_git.reset_mock()
            mirror.git_exe = r"C:\depot_tools\GIT.CMD"
            self.assertTrue(mirror.contains_revision("deadbeef", timeout=0))
            mock_run_git.assert_called_once_with(
                ["cat-file", "-e", "deadbeef^^^^{commit}"]
            )


class ObjectFormatBootstrapTest(unittest.TestCase):
    def setUp(self):
        self.cache_dir = tempfile.mkdtemp(prefix="gc_obj_fmt_")
        self.addCleanup(shutil.rmtree, self.cache_dir, ignore_errors=True)
        git_cache.Mirror.SetCachePath(self.cache_dir)

    def _init_bare_repo(self, path: str, object_format: str) -> None:
        os.makedirs(path, exist_ok=True)
        git = "git.bat" if sys.platform == "win32" else "git"
        subprocess.check_call(
            [git, "init", f"--object-format={object_format}", "--bare"],
            cwd=path,
        )

    def testBootstrapSnapshotFormatMismatch(self):
        cases = [
            ("sha1", "sha256", True),
            ("sha256", "sha1", True),
            ("sha1", "sha1", False),
            ("sha256", "sha256", False),
        ]
        for snapshot_format, remote_format, expected_discard in cases:
            label = f"snapshot={snapshot_format} remote={remote_format}"
            with self.subTest(label):
                mirror = git_cache.Mirror(
                    "https://chromium.googlesource.com/foo/bar"
                )
                gclient_utils.rmtree(mirror.mirror_path)

                def fake_bootstrap(directory: str) -> bool:
                    self._init_bare_repo(directory, snapshot_format)
                    with open(
                        os.path.join(directory, "snapshot_marker"), "w"
                    ) as f:
                        f.write("snapshot")
                    return True

                with (
                    mock.patch.object(
                        mirror, "bootstrap_repo", side_effect=fake_bootstrap
                    ),
                    mock.patch(
                        "scm.GIT.GetRemoteObjectFormat",
                        return_value=remote_format,
                    ),
                    mock.patch.object(mirror, "_set_symbolic_ref"),
                ):
                    mirror._ensure_bootstrapped(
                        depth=None, bootstrap=True, reset_fetch_config=False
                    )

                self.assertEqual(mirror._get_object_format(), remote_format)
                marker_exists = os.path.exists(
                    os.path.join(mirror.mirror_path, "snapshot_marker")
                )
                if expected_discard:
                    self.assertFalse(marker_exists)
                else:
                    self.assertTrue(marker_exists)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG if "-v" in sys.argv else logging.ERROR
    )
    sys.exit(
        coverage_utils.covered_main(
            (os.path.join(DEPOT_TOOLS_ROOT, "git_cache.py")),
            required_percentage=0,
        )
    )
