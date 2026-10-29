#!/usr/bin/env vpython3
# Copyright 2015 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import codecs
import contextlib
import copy
import datetime
import io
import json
import optparse
import os
import sys
import tempfile
import time
from typing import Any
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "recipes",
        "recipe_modules",
        "bot_update",
        "resources",
    ),
)
import bot_update


class MockedPopen(object):
    """A fake instance of a called subprocess.

    This is meant to be used in conjunction with MockedCall.
    """

    def __init__(self, args=None, kwargs=None):
        self.args = args or []
        self.kwargs = kwargs or {}
        self.return_value = None
        self.fails = False

    def returns(self, rv):
        """Set the return value when this popen is called.

        rv can be a string, or a callable (eg function).
        """
        self.return_value = rv
        return self

    def check(self, args, kwargs):
        """Check to see if the given args/kwargs call match this instance.

        This does a partial match, so that a call to "git clone foo" will match
        this instance if this instance was recorded as "git clone"
        """
        if any(
            input_arg != expected_arg
            for (input_arg, expected_arg) in zip(args, self.args)
        ):
            return False
        return self.return_value

    def __call__(self, args, kwargs):
        """Actually call this popen instance."""
        if hasattr(self.return_value, "__call__"):
            return self.return_value(*args, **kwargs)
        return self.return_value


class MockedCall(object):
    """A fake instance of bot_update.call().

    This object is pre-seeded with "answers" in self.expectations.  The type
    is a MockedPopen object, or any object with a __call__() and check() method.
    The check() method is used to check to see if the correct popen object is
    chosen (can be a partial match, eg a "git clone" popen module would match
    a "git clone foo" call).
    By default, if no answers have been pre-seeded, the call() returns successful
    with an empty string.
    """

    def __init__(self, fake_filesystem):
        self.expectations = []
        self.records = []

    def expect(self, args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}
        popen = MockedPopen(args, kwargs)
        self.expectations.append(popen)
        return popen

    def __call__(self, *args, **kwargs):
        self.records.append((args, kwargs))
        for popen in self.expectations:
            if popen.check(args, kwargs):
                self.expectations.remove(popen)
                return popen(args, kwargs)
        return ""


class MockedGclientSync:
    """A class producing a callable instance of gclient sync."""

    def __init__(self, fake_filesystem):
        self.records = []

    def __call__(self, *args, **_):
        self.records.append(args)


class FakeFile:
    def __init__(self):
        self.contents = ""

    def write(self, buf):
        if isinstance(buf, bytes):
            buf = buf.decode("utf-8")
        self.contents += buf

    def read(self, size: int = -1) -> str:
        if size is None or size < 0:
            return self.contents
        return self.contents[:size]

    def __enter__(self):
        return self

    def __exit__(self, _, __, ___):
        pass


class FakeFilesystem:
    def __init__(self):
        self.files = {}

    def open(self, target, mode="r", encoding=None):
        if "w" in mode:
            self.files[target] = FakeFile()
            return self.files[target]
        return self.files[target]


def fake_git(*args, **kwargs):
    return bot_update.call("git", *args, **kwargs)


class BotUpdateUnittests(unittest.TestCase):
    DEFAULT_PARAMS = {
        "solutions": [{"name": "somename", "url": "https://fake.com"}],
        "revisions": {},
        "first_sln": "somename",
        "target_os": None,
        "target_os_only": None,
        "target_cpu": None,
        "patch_root": None,
        "patch_refs": [],
        "gerrit_rebase_patch_ref": None,
        "no_fetch_tags": False,
        "no_history": False,
        "shallow": False,
        "refs": [],
        "git_cache_dir": "",
        "cleanup_dir": None,
        "gerrit_reset": None,
        "enforce_fetch": False,
        "experiments": [],
    }

    def setUp(self):
        self.old_platform = sys.platform
        sys.platform = "linux2"  # For consistency, ya know?
        self.filesystem = FakeFilesystem()
        self.call = MockedCall(self.filesystem)
        self.gclient = MockedGclientSync(self.filesystem)
        self.call.expect(
            (sys.executable, "-u", bot_update.GCLIENT_PATH, "sync")
        ).returns(self.gclient)
        self.old_call = getattr(bot_update, "call")
        self.old_git = getattr(bot_update, "git")
        self.params = copy.deepcopy(self.DEFAULT_PARAMS)
        setattr(bot_update, "call", self.call)
        setattr(bot_update, "git", fake_git)

        self.old_os_cwd = os.getcwd
        setattr(os, "getcwd", lambda: "/b/build/foo/build")

        setattr(bot_update, "open", self.filesystem.open)
        self.old_codecs_open = codecs.open
        setattr(codecs, "open", self.filesystem.open)

    def tearDown(self):
        sys.platform = self.old_platform
        setattr(bot_update, "call", self.old_call)
        setattr(bot_update, "git", self.old_git)
        setattr(os, "getcwd", self.old_os_cwd)
        delattr(bot_update, "open")
        setattr(codecs, "open", self.old_codecs_open)

    def overrideSetupForWindows(self):
        sys.platform = "win"
        self.call.expect(
            (sys.executable, "-u", bot_update.GCLIENT_PATH, "sync")
        ).returns(self.gclient)

    def testBasic(self):
        bot_update.ensure_checkout(**self.params)
        return self.call.records

    def testBasicCachepackOffloading(self):
        os.environ["PACKFILE_OFFLOADING"] = "1"
        bot_update.ensure_checkout(**self.params)
        os.environ.pop("PACKFILE_OFFLOADING")
        return self.call.records

    def testBasicRevision(self):
        self.params["revisions"] = {
            "src": "HEAD",
            "src/v8": "deadbeef",
            "somename": "DNE",
        }
        bot_update.ensure_checkout(**self.params)
        args = self.gclient.records[0]
        idx_first_revision = args.index("--revision")
        idx_second_revision = args.index("--revision", idx_first_revision + 1)
        idx_third_revision = args.index("--revision", idx_second_revision + 1)
        self.assertEqual(args[idx_first_revision + 1], "somename@unmanaged")
        self.assertEqual(
            args[idx_second_revision + 1], "src@refs/remotes/origin/main"
        )
        self.assertEqual(args[idx_third_revision + 1], "src/v8@deadbeef")
        return self.call.records

    def testTagsByDefault(self):
        bot_update.ensure_checkout(**self.params)
        found = False
        for record in self.call.records:
            args = record[0]
            if args[:3] == ("git", "cache", "populate"):
                self.assertFalse("--no-fetch-tags" in args)
                found = True
        self.assertTrue(found)
        return self.call.records

    def testNoTags(self):
        params = self.params
        params["no_fetch_tags"] = True
        bot_update.ensure_checkout(**params)
        found = False
        for record in self.call.records:
            args = record[0]
            if args[:3] == ("git", "cache", "populate"):
                self.assertTrue("--no-fetch-tags" in args)
                found = True
        self.assertTrue(found)
        return self.call.records

    def testGclientNoSyncExperiment(self):
        ref = "refs/changes/12/345/6"
        repo = "https://chromium.googlesource.com/v8/v8"
        self.params["patch_refs"] = ["%s@%s" % (repo, ref)]
        self.params["experiments"] = bot_update.EXP_NO_SYNC
        bot_update.ensure_checkout(**self.params)
        args = self.gclient.records[0]
        idx = args.index("--experiment")
        self.assertEqual(args[idx + 1], bot_update.EXP_NO_SYNC)

    def testApplyPatchOnGclient(self):
        ref = "refs/changes/12/345/6"
        repo = "https://chromium.googlesource.com/v8/v8"
        self.params["patch_refs"] = ["%s@%s" % (repo, ref)]
        bot_update.ensure_checkout(**self.params)
        args = self.gclient.records[0]
        idx = args.index("--patch-ref")
        self.assertEqual(args[idx + 1], self.params["patch_refs"][0])
        self.assertNotIn("--patch-ref", args[idx + 1 :])
        # Assert we're not patching in bot_update.py
        for record in self.call.records:
            self.assertNotIn("git fetch " + repo, " ".join(record[0]))

    def testPatchRefs(self):
        self.params["patch_refs"] = [
            "https://chromium.googlesource.com/chromium/src@refs/changes/12/345/6",
            "https://chromium.googlesource.com/v8/v8@refs/changes/1/234/56",
        ]
        bot_update.ensure_checkout(**self.params)
        args = self.gclient.records[0]
        patch_refs = set(
            args[i + 1]
            for i in range(len(args))
            if args[i] == "--patch-ref" and i + 1 < len(args)
        )
        self.assertIn(self.params["patch_refs"][0], patch_refs)
        self.assertIn(self.params["patch_refs"][1], patch_refs)

    def testGitCheckoutBreaksLocks(self):
        self.overrideSetupForWindows()
        path = "/b/build/foo/build/.git"
        lockfile = "index.lock"
        removed = []
        old_os_walk = os.walk
        old_os_remove = os.remove
        setattr(os, "walk", lambda _: [(path, None, [lockfile])])
        setattr(os, "remove", removed.append)
        bot_update.ensure_checkout(**self.params)
        setattr(os, "walk", old_os_walk)
        setattr(os, "remove", old_os_remove)
        self.assertTrue(os.path.join(path, lockfile) in removed)

    def testGitSyncCorruptionWipesCache(self):
        call_count = [0]

        def mock_sync_stateful(*_args, **_kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise bot_update.GclientSyncFailed(
                    "gclient sync failed", 1, "error: bad object abcde123"
                )
            return ""

        self.call.expectations = []
        self.call.expect(
            (sys.executable, "-u", bot_update.GCLIENT_PATH, "sync")
        ).returns(mock_sync_stateful)
        self.call.expect(
            (sys.executable, "-u", bot_update.GCLIENT_PATH, "sync")
        ).returns(mock_sync_stateful)

        class Options(object):
            def __init__(self):
                self.git_cache_dir = "/fake/git/cache/dir"
                self.cleanup_dir = "/fake/cleanup/dir"
                self.experiments = ""
                self.patch_root = None
                self.patch_refs = []
                self.gerrit_no_rebase_patch_ref = False
                self.download_topics = False
                self.no_fetch_tags = False
                self.no_history = False
                self.shallow = False
                self.enforce_fetch = False
                self.refs = []
                self.clean_ignored = False
                self.gerrit_no_reset = False
                self.output_json = "/fake/output.json"
                self.revision_mapping = {}
                self.clobber = False

        options = Options()
        git_slns = self.params["solutions"]
        specs = {}
        revisions = {"somename": "HEAD"}
        step_text = "some step text"

        removed = []
        old_exists = os.path.exists
        setattr(
            os.path,
            "exists",
            lambda path: (
                True if path == "/fake/git/cache/dir" else old_exists(path)
            ),
        )
        self.addCleanup(setattr, os.path, "exists", old_exists)

        old_makedirs = os.makedirs
        setattr(os, "makedirs", lambda path, exist_ok=False: None)
        self.addCleanup(setattr, os, "makedirs", old_makedirs)

        old_remove = getattr(bot_update, "remove")
        setattr(
            bot_update,
            "remove",
            lambda path, clean_dir: removed.append((path, clean_dir)),
        )
        self.addCleanup(setattr, bot_update, "remove", old_remove)

        old_create_manifest = getattr(bot_update, "create_manifest")
        setattr(bot_update, "create_manifest", lambda: {})
        self.addCleanup(
            setattr, bot_update, "create_manifest", old_create_manifest
        )

        old_disk_usage = getattr(bot_update, "disk_usage")
        setattr(bot_update, "disk_usage", lambda: (10, 100, 10))
        self.addCleanup(setattr, bot_update, "disk_usage", old_disk_usage)

        bot_update.checkout(options, git_slns, specs, revisions, step_text)

        self.assertEqual(call_count[0], 2)
        self.assertEqual(
            removed, [("/fake/git/cache/dir", "/fake/cleanup/dir")]
        )

    def _getCacheEpochOnRealFs(
        self, git_cache_dir: str
    ) -> tuple[int, datetime.datetime, str]:
        """Calls `_get_or_create_cache_epoch()` against the real filesystem.

        Bypasses the fake `open()` installed by `setUp()` so that the symlink,
        directory and removal handling is exercised for real. Returns the
        `(epoch, epoch_dt)` result followed by whatever was printed.
        """
        with (
            mock.patch.object(bot_update, "open", open),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            epoch, epoch_dt = bot_update._get_or_create_cache_epoch(
                git_cache_dir
            )
        return epoch, epoch_dt, stdout.getvalue()

    def testGetOrCreateCacheEpochColdCache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # On a cold bot the git cache directory does not exist yet either.
            git_cache_dir = os.path.join(tmp, "git_cache")
            marker = os.path.join(git_cache_dir, ".cache_epoch")
            before = int(time.time())
            epoch, epoch_dt, stdout = self._getCacheEpochOnRealFs(git_cache_dir)
            after = int(time.time())
            self.assertIsInstance(epoch, int)
            self.assertTrue(before <= epoch <= after)
            self.assertEqual(epoch_dt, datetime.datetime.fromtimestamp(epoch))
            self.assertNotIn("resetting cache epoch", stdout)
            with open(marker) as f:
                self.assertEqual(f.read(), str(epoch))
            # A second (warm) call reads the freshly written marker back.
            self.assertEqual(
                self._getCacheEpochOnRealFs(git_cache_dir),
                (epoch, epoch_dt, ""),
            )

    def testGetOrCreateCacheEpochPreservesValidMarker(self) -> None:
        now = int(time.time())
        valid_contents = {
            # Older bot_update versions wrote the marker with a trailing
            # newline, which must keep being accepted.
            "legacy format": "1700000000\n",
            "current format": "1700000000",
            # Allow for some clock skew between tasks.
            "slightly in the future": str(now + 3600),
        }
        for name, contents in valid_contents.items():
            with (
                self.subTest(name),
                tempfile.TemporaryDirectory() as git_cache_dir,
            ):
                marker = os.path.join(git_cache_dir, ".cache_epoch")
                with open(marker, "w") as f:
                    f.write(contents)
                epoch, epoch_dt, stdout = self._getCacheEpochOnRealFs(
                    git_cache_dir
                )
                self.assertIsInstance(epoch, int)
                self.assertEqual(epoch, int(contents))
                self.assertEqual(
                    epoch_dt, datetime.datetime.fromtimestamp(epoch)
                )
                self.assertEqual(stdout, "")
                with open(marker) as f:
                    self.assertEqual(f.read(), contents)

    def testGetOrCreateCacheEpochResetsInvalidMarkerContents(self) -> None:
        now = int(time.time())
        invalid_contents = {
            "non-numeric": "junk",
            "empty": "",
            "blank first line": "\n1700000000\n",
            "trailing garbage": "1700000000\njunk\n",
            "integer overflow": "9" * 30,
            "negative": "-100",
            "before 2020": "100",
            "far future": str(now + 7 * 86400),
            # Must be rejected by the bounded read, not slurped and parsed.
            "oversized": "1" * 100000,
        }
        for name, contents in invalid_contents.items():
            with (
                self.subTest(name),
                tempfile.TemporaryDirectory() as git_cache_dir,
            ):
                marker = os.path.join(git_cache_dir, ".cache_epoch")
                with open(marker, "w") as f:
                    f.write(contents)
                before = int(time.time())
                epoch, epoch_dt, stdout = self._getCacheEpochOnRealFs(
                    git_cache_dir
                )
                after = int(time.time())
                self.assertIsInstance(epoch, int)
                self.assertTrue(before <= epoch <= after)
                self.assertEqual(
                    epoch_dt, datetime.datetime.fromtimestamp(epoch)
                )
                self.assertIn(
                    f"Warning: invalid or unreadable {marker}; "
                    "resetting cache epoch.",
                    stdout,
                )
                with open(marker) as f:
                    self.assertEqual(f.read(), str(epoch))

        with (
            self.subTest("unremovable marker"),
            tempfile.TemporaryDirectory() as git_cache_dir,
        ):
            marker = os.path.join(git_cache_dir, ".cache_epoch")
            with open(marker, "w") as f:
                f.write("junk")
            with (
                mock.patch.object(
                    os, "remove", side_effect=PermissionError("denied")
                ),
                mock.patch.object(
                    os, "rmdir", side_effect=PermissionError("denied")
                ),
                mock.patch.object(
                    bot_update.shutil,
                    "rmtree",
                    side_effect=PermissionError("denied"),
                ),
            ):
                before = int(time.time())
                epoch, epoch_dt, stdout = self._getCacheEpochOnRealFs(
                    git_cache_dir
                )
                after = int(time.time())
            self.assertIsInstance(epoch, int)
            self.assertTrue(before <= epoch <= after)
            self.assertEqual(epoch_dt, datetime.datetime.fromtimestamp(epoch))
            self.assertIn(f"Warning: failed to reset {marker}:", stdout)

    def testGetOrCreateCacheEpochReplacesSymlinkWithoutFollowingIt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            victim_file = os.path.join(tmp, "victim_file")
            with open(victim_file, "w") as f:
                f.write("1700000000")
            victim_dir = os.path.join(tmp, "victim_dir")
            os.makedirs(victim_dir)
            targets = {
                "file": victim_file,
                "directory": victim_dir,
                "dangling": os.path.join(tmp, "does_not_exist"),
            }
            for name, target in targets.items():
                with (
                    self.subTest(name),
                    tempfile.TemporaryDirectory(dir=tmp) as git_cache_dir,
                ):
                    marker = os.path.join(git_cache_dir, ".cache_epoch")
                    try:
                        os.symlink(target, marker)
                    except (OSError, NotImplementedError):
                        self.skipTest("symlinks not supported")
                    epoch, _, stdout = self._getCacheEpochOnRealFs(
                        git_cache_dir
                    )
                    self.assertIn("resetting cache epoch", stdout)
                    # The symlink itself got replaced by a regular file; the
                    # timestamp it pointed at was never trusted.
                    self.assertNotEqual(epoch, 1700000000)
                    self.assertFalse(os.path.islink(marker))
                    self.assertTrue(os.path.isfile(marker))
                    with open(marker) as f:
                        self.assertEqual(f.read(), str(epoch))
            # Nothing was written or removed through the symlinks.
            with open(victim_file) as f:
                self.assertEqual(f.read(), "1700000000")
            self.assertTrue(os.path.isdir(victim_dir))

    def testGetOrCreateCacheEpochReplacesDirectory(self) -> None:
        with tempfile.TemporaryDirectory() as git_cache_dir:
            marker = os.path.join(git_cache_dir, ".cache_epoch")
            # Non-empty, so that a plain os.remove()/os.rmdir() would fail.
            os.makedirs(os.path.join(marker, "nested"))
            with open(os.path.join(marker, "nested", "file"), "w") as f:
                f.write("1700000000")
            epoch, _, stdout = self._getCacheEpochOnRealFs(git_cache_dir)
            self.assertIn("resetting cache epoch", stdout)
            self.assertIsInstance(epoch, int)
            self.assertTrue(os.path.isfile(marker))
            with open(marker) as f:
                self.assertEqual(f.read(), str(epoch))

    def _runCheckout(
        self,
        git_cache_dir: str = "/fake/git/cache/dir",
        use_real_cache_fs: bool = False,
    ) -> tuple[dict[str, Any], str]:
        """Runs `bot_update.checkout()`.

        Returns the `properties` emitted to `output_json` followed by whatever
        was printed. When `use_real_cache_fs` is True, opens under
        `git_cache_dir` go to the real filesystem while other paths remain on
        the fake filesystem.
        """
        options = optparse.Values(
            {
                "git_cache_dir": git_cache_dir,
                "cleanup_dir": "/fake/cleanup/dir",
                "experiments": "",
                "patch_root": None,
                "patch_refs": [],
                "gerrit_no_rebase_patch_ref": False,
                "download_topics": False,
                "no_fetch_tags": False,
                "no_history": False,
                "shallow": False,
                "enforce_fetch": False,
                "refs": [],
                "clean_ignored": False,
                "gerrit_no_reset": False,
                "output_json": "/fake/output.json",
                "revision_mapping": {},
                "clobber": False,
            }
        )
        fake_open = self.filesystem.open

        def dispatch_open(
            target: str, mode: str = "r", encoding: str | None = None
        ) -> Any:
            if use_real_cache_fs and target.startswith(git_cache_dir + os.sep):
                return open(target, mode, encoding=encoding)
            return fake_open(target, mode, encoding=encoding)

        with (
            contextlib.nullcontext()
            if use_real_cache_fs
            else mock.patch.object(os, "makedirs"),
            mock.patch.object(bot_update, "open", dispatch_open),
            mock.patch.object(bot_update, "create_manifest", return_value={}),
            mock.patch.object(
                bot_update, "disk_usage", return_value=(10, 100, 10)
            ),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            bot_update.checkout(
                options,
                self.params["solutions"],
                {},
                {"somename": "HEAD"},
                "some step text",
            )
        output = json.loads(self.filesystem.files["/fake/output.json"].read())
        return output["properties"], stdout.getvalue()

    def testCheckoutCreatesCacheEpochOnColdCache(self) -> None:
        marker = os.path.join("/fake/git/cache/dir", ".cache_epoch")
        before = int(time.time())
        properties, stdout = self._runCheckout()
        after = int(time.time())
        epoch = properties["git_cache_epoch"]
        self.assertIsInstance(epoch, int)
        self.assertTrue(before <= epoch <= after)
        self.assertEqual(self.filesystem.files[marker].read(), str(epoch))
        self.assertNotIn("resetting cache epoch", stdout)
        self.assertIn("Using git cache directory /fake/git/cache/dir", stdout)

    def testCheckoutPreservesValidCacheEpoch(self) -> None:
        marker = os.path.join("/fake/git/cache/dir", ".cache_epoch")
        self.filesystem.files[marker] = FakeFile()
        self.filesystem.files[marker].write("1700000000\n")
        real_isfile = os.path.isfile
        with mock.patch.object(
            os.path, "isfile", lambda p: p == marker or real_isfile(p)
        ):
            properties, stdout = self._runCheckout()
        # Warm caches used to report a str here while cold caches reported an
        # int; the property must be an int either way.
        self.assertIsInstance(properties["git_cache_epoch"], int)
        self.assertEqual(properties["git_cache_epoch"], 1700000000)
        self.assertEqual(self.filesystem.files[marker].read(), "1700000000\n")
        self.assertNotIn("resetting cache epoch", stdout)
        created_at = datetime.datetime.fromtimestamp(1700000000)
        self.assertIn(
            "Using git cache directory /fake/git/cache/dir "
            f"(created at {created_at.strftime('%Y-%m-%d %H:%M:%S')}, ",
            stdout,
        )

    def testCheckoutSelfHealsCorruptCacheEpoch(self) -> None:
        now = int(time.time())
        invalid_contents = {
            "non-numeric": "junk",
            "empty": "",
            "integer overflow": "9" * 30,
            "negative": "-100",
            "far future": str(now + 7 * 86400),
        }
        for name, contents in invalid_contents.items():
            with (
                self.subTest(name),
                tempfile.TemporaryDirectory() as git_cache_dir,
            ):
                marker = os.path.join(git_cache_dir, ".cache_epoch")
                with open(marker, "w") as f:
                    f.write(contents)
                before = int(time.time())
                properties, stdout = self._runCheckout(
                    git_cache_dir, use_real_cache_fs=True
                )
                after = int(time.time())
                epoch = properties["git_cache_epoch"]
                self.assertIsInstance(epoch, int)
                self.assertTrue(before <= epoch <= after)
                self.assertIn(
                    f"Warning: invalid or unreadable {marker}; "
                    "resetting cache epoch.",
                    stdout,
                )
                with open(marker) as f:
                    self.assertEqual(f.read(), str(epoch))

        with (
            self.subTest("directory"),
            tempfile.TemporaryDirectory() as git_cache_dir,
        ):
            marker = os.path.join(git_cache_dir, ".cache_epoch")
            os.makedirs(os.path.join(marker, "nested"))
            before = int(time.time())
            properties, stdout = self._runCheckout(
                git_cache_dir, use_real_cache_fs=True
            )
            after = int(time.time())
            epoch = properties["git_cache_epoch"]
            self.assertIsInstance(epoch, int)
            self.assertTrue(before <= epoch <= after)
            self.assertTrue(os.path.isfile(marker))
            self.assertIn(
                f"Warning: invalid or unreadable {marker}; "
                "resetting cache epoch.",
                stdout,
            )
            with open(marker) as f:
                self.assertEqual(f.read(), str(epoch))

        with (
            self.subTest("symlink"),
            tempfile.TemporaryDirectory() as tmp,
        ):
            git_cache_dir = os.path.join(tmp, "cache")
            os.makedirs(git_cache_dir)
            target = os.path.join(tmp, "target")
            with open(target, "w") as f:
                f.write("1700000000")
            marker = os.path.join(git_cache_dir, ".cache_epoch")
            try:
                os.symlink(target, marker)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks not supported")
            before = int(time.time())
            properties, stdout = self._runCheckout(
                git_cache_dir, use_real_cache_fs=True
            )
            after = int(time.time())
            epoch = properties["git_cache_epoch"]
            self.assertIsInstance(epoch, int)
            self.assertTrue(before <= epoch <= after)
            self.assertFalse(os.path.islink(marker))
            self.assertTrue(os.path.isfile(marker))
            self.assertIn(
                f"Warning: invalid or unreadable {marker}; "
                "resetting cache epoch.",
                stdout,
            )
            with open(marker) as f:
                self.assertEqual(f.read(), str(epoch))
            with open(target) as f:
                self.assertEqual(f.read(), "1700000000")

    def testParsesRevisions(self):

        revisions = [
            "f671d3baeb64d9dba628ad582e867cf1aebc0207",
            "src@deadbeef",
            "https://foo.googlesource.com/bar@12345",
            "bar@refs/experimental/test@example.com/test",
        ]
        expected_results = {
            "root": "f671d3baeb64d9dba628ad582e867cf1aebc0207",
            "src": "deadbeef",
            "https://foo.googlesource.com/bar.git": "12345",
            "bar": "refs/experimental/test@example.com/test",
        }
        actual_results = bot_update.parse_revisions(revisions, "root")
        self.assertEqual(expected_results, actual_results)

        with self.assertRaises(ValueError):
            bot_update.parse_revisions(["--upload-pack=foo"], "root")
        with self.assertRaises(ValueError):
            bot_update.parse_revisions(["src@--upload-pack=foo"], "root")
        with self.assertRaises(ValueError):
            bot_update.parse_revisions(["-bad_root@HEAD"], "root")
        with self.assertRaises(ValueError):
            bot_update.parse_revisions([], "-bad_root")

        # A ',' must never act as a revision separator. parse_revisions used
        # to split each spec on ',', so a single attacker-controlled value
        # could smuggle in an extra 'dep@rev' pair and override a DEPS pin.
        for bad_revs, bad_root in (
            (["src@deadbeef,src/dep@badbeef"], "root"),
            (["deadbeef,src/dep@badbeef"], "root"),
            (["src@deadbeef", "src/dep@badbeef,src/other@cafe"], "root"),
            ([], "root,other"),
        ):
            with self.subTest(revisions=bad_revs, root=bad_root):
                with self.assertRaisesRegex(ValueError, "','"):
                    bot_update.parse_revisions(bad_revs, bad_root)


class CallUnitTest(unittest.TestCase):
    def testCall(self):
        ret = bot_update.call(sys.executable, "-c", "print(1)")
        self.assertEqual("1\n", ret)

    def testCallOnWindowsSetsNoDefaultCurrentDirectoryInExePath(self):
        with (
            mock.patch.object(sys, "platform", "win32"),
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("subprocess.Popen") as mock_popen,
        ):
            proc = mock_popen.return_value
            proc.stdout.read.return_value = b""
            proc.wait.return_value = 0

            bot_update.call("git.exe", "status")
            _, kwargs = mock_popen.call_args
            self.assertEqual(
                kwargs["env"].get("NoDefaultCurrentDirectoryInExePath"), "1"
            )

            mock_popen.reset_mock()
            bot_update.call(
                "git.exe",
                "status",
                env={"NoDefaultCurrentDirectoryInExePath": "0"},
            )
            _, kwargs = mock_popen.call_args
            self.assertEqual(
                kwargs["env"].get("NoDefaultCurrentDirectoryInExePath"), "0"
            )

    def testGitOnWindowsResolvesGitExe(self):
        bot_update._win_git_executable.cache_clear()
        self.addCleanup(bot_update._win_git_executable.cache_clear)
        with (
            tempfile.TemporaryDirectory() as td,
            mock.patch.object(bot_update, "call", return_value="") as mock_call,
            mock.patch.object(sys, "platform", "win32"),
            mock.patch.object(
                bot_update.git_common,
                "win_find_git",
                wraps=bot_update.git_common.win_find_git,
            ) as mock_win_find_git,
        ):
            # 1. git.exe directly on PATH (and verify repeated calls hit cache).
            exe_dir = os.path.join(td, "exe_dir")
            os.makedirs(exe_dir)
            exe_path = os.path.join(exe_dir, "git.exe")
            with open(exe_path, "w") as f:
                f.write("exe")
            with mock.patch.dict(os.environ, {"PATH": exe_dir}):
                bot_update.git("status")
                bot_update.git("diff")
                self.assertEqual(mock_win_find_git.call_count, 1)
                self.assertEqual(
                    mock_call.call_args_list,
                    [
                        mock.call(exe_path, "status"),
                        mock.call(exe_path, "diff"),
                    ],
                )

            # 2. git.bat on PATH wrapping git.exe via %~dp0.
            mock_call.reset_mock()
            bat_dir = os.path.join(td, "bat_dir")
            os.makedirs(bat_dir)
            bat_path = os.path.join(bat_dir, "git.bat")
            bundled_exe = os.path.join(bat_dir, "bin", "git.exe")
            with open(bat_path, "w") as f:
                f.write(
                    '@echo off\n"%%~dp0%s" %%*\n'
                    % os.path.join("bin", "git.exe")
                )
            with mock.patch.dict(os.environ, {"PATH": bat_dir}):
                bot_update.git("fetch", "origin")
                mock_call.assert_called_once_with(
                    bundled_exe, "fetch", "origin"
                )

            # 3. Fallback to the absolute path of depot_tools' git.bat when Git
            #    is not found on PATH.
            mock_call.reset_mock()
            fallback_bat = os.path.join(bot_update.DEPOT_TOOLS_DIR, "git.bat")
            with mock.patch.dict(os.environ, {"PATH": ""}):
                bot_update.git("status")
                mock_call.assert_called_once_with(fallback_bat, "status")

            # 4. Relative PATH entries are never resolved against the CWD, even
            #    when a git.exe has been planted where they would point.
            mock_call.reset_mock()
            planted_dir = os.path.join(td, "planted")
            os.makedirs(planted_dir)
            with open(os.path.join(planted_dir, "git.exe"), "w") as f:
                f.write("exe")
            original_cwd = os.getcwd()
            os.chdir(td)
            try:
                with mock.patch.dict(os.environ, {"PATH": "planted"}):
                    bot_update.git("status")
            finally:
                os.chdir(original_cwd)
            mock_call.assert_called_once_with(fallback_bat, "status")

    def testGitOnNonWindowsAndCacheCommand(self):
        with (
            mock.patch.object(bot_update, "call", return_value="") as mock_call,
            mock.patch.object(sys, "platform", "linux2"),
        ):
            bot_update.git("status")
            mock_call.assert_called_once_with("git", "status")

            mock_call.reset_mock()
            bot_update.git("cache", "populate", "https://example.com/repo")
            mock_call.assert_called_once_with(
                sys.executable,
                "-u",
                bot_update.GIT_CACHE_PATH,
                "populate",
                "https://example.com/repo",
            )


if __name__ == "__main__":
    unittest.main()
