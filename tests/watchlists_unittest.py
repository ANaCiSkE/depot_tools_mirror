#!/usr/bin/env vpython3
# Copyright 2011 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for watchlists.py."""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import watchlists


class WatchlistsTest(unittest.TestCase):
    def setUp(self):
        super(WatchlistsTest, self).setUp()
        watchlists._ParseAndCompileWatchlistRules.cache_clear()
        self.patch_has_file = mock.patch(
            "watchlists.Watchlists._HasWatchlistsFile"
        )
        self.mock_has_file = self.patch_has_file.start()
        self.patch_contents = mock.patch(
            "watchlists.Watchlists._ContentsOfWatchlistsFile"
        )
        self.mock_contents = self.patch_contents.start()
        mock.patch("watchlists.logging.error").start()
        self.addCleanup(mock.patch.stopall)

    def testMissingWatchlistsFileOK(self):
        """Test that we act gracefully if WATCHLISTS file is missing."""
        watchlists.Watchlists._HasWatchlistsFile.return_value = False

        wl = watchlists.Watchlists("/some/random/path")
        self.assertEqual(wl.GetWatchersForPaths(["some_path"]), [])

    def testRepoRootNone(self):
        """Test that None repo_root acts gracefully and does not crash."""
        self.patch_has_file.stop()
        try:
            wl = watchlists.Watchlists(None)
            self.assertEqual(wl._GetRulesFilePath(), "")
            self.assertFalse(wl._HasWatchlistsFile())
            self.assertEqual(wl.GetWatchersForPaths(["some_path"]), [])
        finally:
            self.mock_has_file = self.patch_has_file.start()

    def testRepoRootEmptyResolvesCwd(self):
        """Test that empty string repo_root resolves WATCHLISTS in current working directory."""
        self.patch_has_file.stop()
        try:
            wl = watchlists.Watchlists("")
            self.assertEqual(
                wl._GetRulesFilePath(), os.path.abspath("WATCHLISTS")
            )
        finally:
            self.mock_has_file = self.patch_has_file.start()

    def testPathsWithLeadingDotSlashAndNone(self):
        """Test that paths with leading ./ and None/non-string items are handled cleanly."""
        watchers = ["user@example.com"]
        contents = (
            """{
        'WATCHLIST_DEFINITIONS': {
          'browser': {
            'filepath': '^chrome/browser/.*',
          },
        },
        'WATCHLISTS': {
          'browser': %s,
        },
      }"""
            % watchers
        )
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl = watchlists.Watchlists("/a/path")
        self.assertEqual(
            wl.GetWatchersForPaths(
                [
                    "./chrome/browser/foo.h",
                    r".\chrome\browser\foo.h",
                    None,
                    123,
                    "",
                ]
            ),
            watchers,
        )

    def testSingleStringWatchlistNotCharSplit(self):
        """Test that a string watchlist is not split into individual characters."""
        contents = """{
        'WATCHLIST_DEFINITIONS': {
          'a_module': {
            'filepath': 'a_module',
          },
        },
        'WATCHLISTS': {
          'a_module': 'user@example.com',
        },
      }"""
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl = watchlists.Watchlists("/a/path")
        self.assertEqual(
            wl.GetWatchersForPaths(["a_module"]), ["user@example.com"]
        )

    def testGarbledWatchlistsFileOK(self):
        """Test that we act gracefully if WATCHLISTS file is garbled."""
        contents = "some garbled and unwanted text"
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl = watchlists.Watchlists("/a/path")
        self.assertEqual(wl.GetWatchersForPaths(["some_path"]), [])

    def testUnicodeDecodeErrorHandledGracefully(self):
        """Test that invalid UTF-8 bytes log an error without crashing."""
        self.patch_contents.stop()
        try:
            watchlists.Watchlists._HasWatchlistsFile.return_value = True
            with mock.patch(
                "builtins.open",
                side_effect=UnicodeDecodeError(
                    "utf-8", b"\xff\xff", 0, 1, "invalid start byte"
                ),
            ):
                wl = watchlists.Watchlists("/a/path")
                self.assertEqual(wl.GetWatchersForPaths(["some_path"]), [])
                watchlists.logging.error.assert_called()
        finally:
            self.mock_contents = self.patch_contents.start()

    def testMalformedSchemaAndASTWatchlistsFileOK(self):
        """Test that non-dict AST literals and malformed schemas do not cause crashes."""
        for contents in [
            "42",
            "'hello'",
            "[1, 2, 3]",
            "{'WATCHLIST_DEFINITIONS': 123, 'WATCHLISTS': {}}",
            "{'WATCHLIST_DEFINITIONS': {'mod': '^chrome/browser/.*'}, 'WATCHLISTS': {'mod': ['a@b.com']}}",
            "{'WATCHLIST_DEFINITIONS': {'mod': {'filepath': 12345}}, 'WATCHLISTS': {'mod': ['a@b.com']}}",
        ]:
            watchlists.logging.error.reset_mock()
            watchlists.Watchlists._HasWatchlistsFile.return_value = True
            watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = (
                contents
            )
            wl = watchlists.Watchlists("/a/path")
            self.assertEqual(wl.GetWatchersForPaths(["some_path"]), [])
            watchlists.logging.error.assert_called()

    def testNoWatchers(self):
        contents = """{
        'WATCHLIST_DEFINITIONS': {
          'a_module': {
            'filepath': 'a_module',
          },
        },

        'WATCHLISTS': {
          'a_module': [],
        },
      } """
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl = watchlists.Watchlists("/a/path")
        self.assertEqual(wl.GetWatchersForPaths(["a_module"]), [])

    def testValidWatcher(self):
        watchers = ["abc@def.com", "x1@xyz.org"]
        contents = (
            """{
        'WATCHLIST_DEFINITIONS': {
          'a_module': {
            'filepath': 'a_module',
          },
        },
        'WATCHLISTS': {
          'a_module': %s,
        },
      } """
            % watchers
        )
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl = watchlists.Watchlists("/a/path")
        self.assertEqual(wl.GetWatchersForPaths(["a_module"]), watchers)

    def testMultipleWatchlistsTrigger(self):
        """Test that multiple watchlists can get triggered for one filepath."""
        contents = """{
        'WATCHLIST_DEFINITIONS': {
          'mac': {
            'filepath': 'mac',
          },
          'views': {
            'filepath': 'views',
          },
        },
        'WATCHLISTS': {
          'mac': ['x1@chromium.org'],
          'views': ['x2@chromium.org'],
        },
      } """
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl = watchlists.Watchlists("/a/path")
        self.assertEqual(
            wl.GetWatchersForPaths(["file_views_mac"]),
            ["x1@chromium.org", "x2@chromium.org"],
        )

    def testDuplicateWatchers(self):
        """Test that multiple watchlists can get triggered for one filepath."""
        watchers = ["someone@chromium.org"]
        contents = """{
        'WATCHLIST_DEFINITIONS': {
          'mac': {
            'filepath': 'mac',
          },
          'views': {
            'filepath': 'views',
          },
        },
        'WATCHLISTS': {
          'mac': %s,
          'views': %s,
        },
      } """ % (watchers, watchers)
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl = watchlists.Watchlists("/a/path")
        self.assertEqual(wl.GetWatchersForPaths(["file_views_mac"]), watchers)

    def testWinPathWatchers(self):
        """Test watchers for a windows path (containing backward slashes)."""
        watchers = ["abc@def.com", "x1@xyz.org"]
        contents = (
            """{
        'WATCHLIST_DEFINITIONS': {
          'browser': {
            'filepath': 'chrome/browser/.*',
          },
        },
        'WATCHLISTS': {
          'browser': %s,
        },
      } """
            % watchers
        )
        saved_sep = watchlists.os.sep
        watchlists.os.sep = "\\"  # to pose as win32
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl = watchlists.Watchlists(r"a\path")
        returned_watchers = wl.GetWatchersForPaths(
            [r"chrome\browser\renderer_host\render_widget_host.h"]
        )
        watchlists.os.sep = saved_sep  # revert back os.sep before asserts
        self.assertEqual(returned_watchers, watchers)

    def testEvalSandboxEscapeBlocked(self):
        """Test that a malicious WATCHLISTS file using eval sandbox escape is safely blocked and does not execute."""
        contents = """{
        'WATCHLIST_DEFINITIONS': {
          'rce': {
            'filepath': [c for c in ().__class__.__bases__[0].__subclasses__() if c.__name__ == 'Popen'][0](['sh', '-c', 'echo VULNERABLE'], stdout=-1).communicate()[0] or ".*"
          },
        },
        'WATCHLISTS': {
          'rce': ['attacker@evil.com'],
        },
      }"""
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl = watchlists.Watchlists("/a/path")
        self.assertEqual(wl.GetWatchersForPaths(["rce"]), [])
        watchlists.logging.error.assert_called()

    def testRulesParsingIsCached(self):
        """Test that multiple Watchlists instances reuse compiled rules via cache."""
        contents = """{
        'WATCHLIST_DEFINITIONS': {
          'a_module': {
            'filepath': 'a_module',
          },
        },
        'WATCHLISTS': {
          'a_module': ['user@example.com'],
        },
      }"""
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        with mock.patch(
            "watchlists._ParseAndCompileWatchlistRules",
            wraps=watchlists._ParseAndCompileWatchlistRules,
        ) as mock_parse:
            wl1 = watchlists.Watchlists("/a/path")
            self.assertEqual(
                wl1.GetWatchersForPaths(["a_module"]), ["user@example.com"]
            )
            wl2 = watchlists.Watchlists("/a/path/sub/..")
            self.assertEqual(
                wl2.GetWatchersForPaths(["a_module"]), ["user@example.com"]
            )
            self.assertEqual(mock_parse.call_count, 2)
            cache_info = watchlists._ParseAndCompileWatchlistRules.cache_info()
            self.assertGreaterEqual(cache_info.hits, 1)

    def testInvalidRegexHandledGracefully(self):
        """Test that an invalid regular expression logs an error but does not crash."""
        contents = """{
        'WATCHLIST_DEFINITIONS': {
          'bad_regex': {
            'filepath': '[invalid regex(',
          },
          'good_module': {
            'filepath': 'good_module',
          },
        },
        'WATCHLISTS': {
          'bad_regex': ['bad@example.com'],
          'good_module': ['good@example.com'],
        },
      }"""
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl = watchlists.Watchlists("/a/path")
        self.assertEqual(
            wl.GetWatchersForPaths(["good_module"]), ["good@example.com"]
        )
        self.assertEqual(wl.GetWatchersForPaths(["bad_regex"]), [])
        watchlists.logging.error.assert_called()

    def testCachedRulesMutationIsolated(self):
        """Test that mutations on one instance do not poison the cached rules for other instances."""
        contents = """{
        'WATCHLIST_DEFINITIONS': {
          'a_module': {
            'filepath': 'a_module',
          },
          'set_module': {
            'filepath': 'set_module',
          },
        },
        'WATCHLISTS': {
          'a_module': ['user@example.com'],
          'set_module': {'user@example.com'},
        },
      }"""
        watchlists.Watchlists._HasWatchlistsFile.return_value = True
        watchlists.Watchlists._ContentsOfWatchlistsFile.return_value = contents

        wl1 = watchlists.Watchlists("/a/path")
        # Mutate instance dictionary and nested definition
        wl1._watchlists["a_module"].append("mutated@example.com")
        wl1._watchlists["set_module"].add("mutated@example.com")
        wl1._watchlists["new_module"] = ["rogue@example.com"]
        wl1._defns["a_module"]["filepath"] = "mutated_filepath"
        self.assertEqual(
            wl1.GetWatchersForPaths(["a_module"]),
            ["mutated@example.com", "user@example.com"],
        )
        self.assertEqual(
            wl1.GetWatchersForPaths(["set_module"]),
            ["mutated@example.com", "user@example.com"],
        )

        self.assertIsInstance(wl1._watchlists["a_module"], list)
        self.assertIsInstance(wl1._watchlists["set_module"], set)

        # New instance gets a cache hit, but should be unaffected by wl1 mutations
        wl2 = watchlists.Watchlists("/a/path")
        self.assertIsInstance(wl2._watchlists["a_module"], list)
        self.assertIsInstance(wl2._watchlists["set_module"], set)
        self.assertEqual(
            wl2.GetWatchersForPaths(["a_module"]), ["user@example.com"]
        )
        self.assertEqual(
            wl2.GetWatchersForPaths(["set_module"]), ["user@example.com"]
        )
        self.assertEqual(wl2._defns["a_module"]["filepath"], "a_module")
        self.assertNotIn("new_module", wl2._watchlists)


if __name__ == "__main__":
    import unittest

    unittest.main()
