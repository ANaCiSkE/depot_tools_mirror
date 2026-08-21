#!/usr/bin/env python3
# Copyright 2011 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Watchlists

Watchlists is a mechanism that allow a developer (a "watcher") to watch over
portions of code that they are interested in. A "watcher" will be cc-ed to
changes that modify that portion of code, thereby giving them an opportunity
to make comments on chromium-review.googlesource.com even before the change is
committed.
Refer:
https://chromium.googlesource.com/chromium/src/+/HEAD/docs/infra/watchlists.md

When invoked directly from the base of a repository, this script lists out
the watchers for files given on the command line. This is useful to verify
changes to WATCHLISTS files.
"""

import ast
from collections.abc import Iterable
import functools
import logging
import os
import re
import sys
from typing import Any, Dict, NamedTuple, Pattern


class WatchlistRules(NamedTuple):
    """Parsed and compiled WATCHLISTS rules."""

    defns: Dict[str, Any]
    watchlists: Dict[str, Any]
    path_regexps: Dict[str, Pattern[str]]


@functools.lru_cache(maxsize=8)
def _ParseAndCompileWatchlistRules(
    contents: str, rules_filepath: str
) -> WatchlistRules:
    """Parses and compiles WATCHLISTS rules with LRU caching.

    Args:
        contents: Raw text contents of the WATCHLISTS file.
        rules_filepath: Path to the WATCHLISTS file (used for error logging).

    Returns:
        WatchlistRules containing:
            defns: Raw watchlist definitions dictionary.
            watchlists: Mapping of watchlist names to watcher email lists.
            path_regexps: Precompiled regular expressions for defined rules.
    """
    if not contents:
        return WatchlistRules({}, {}, {})

    try:
        watchlists_data = ast.literal_eval(contents)
    except Exception as e:
        logging.error("Cannot parse %s: %s", rules_filepath, e)
        return WatchlistRules({}, {}, {})

    if not isinstance(watchlists_data, dict):
        logging.error("WATCHLISTS content in %s must be a dict", rules_filepath)
        return WatchlistRules({}, {}, {})

    defns = watchlists_data.get("WATCHLIST_DEFINITIONS")
    if not isinstance(defns, dict) or not defns:
        logging.error("WATCHLIST_DEFINITIONS not defined in %s", rules_filepath)
        return WatchlistRules({}, {}, {})
    watchlists = watchlists_data.get("WATCHLISTS")
    if not isinstance(watchlists, dict) or not watchlists:
        logging.error("WATCHLISTS not defined in %s", rules_filepath)
        return WatchlistRules({}, {}, {})

    # Compile the regular expressions ahead of time to avoid creating them
    # on-the-fly multiple times per file.
    path_regexps = {}
    for name, rule in defns.items():
        if not isinstance(rule, dict):
            logging.error(
                "Rule for %s in %s must be a dict, got %s",
                name,
                rules_filepath,
                type(rule).__name__,
            )
            continue
        filepath = rule.get("filepath")
        if not filepath:
            continue
        if not isinstance(filepath, str):
            logging.error(
                "Rule for %s in %s has invalid non-string filepath: %s",
                name,
                rules_filepath,
                type(filepath).__name__,
            )
            continue
        try:
            path_regexps[name] = re.compile(filepath)
        except re.error as e:
            logging.error(
                "Invalid regex for %s in %s: %s", name, rules_filepath, e
            )

    # Verify that all watchlist names are defined.
    for name in watchlists:
        if name not in defns:
            logging.error("%s not defined in %s", name, rules_filepath)

    return WatchlistRules(defns, watchlists, path_regexps)


def _CloneContainer(val: Any) -> Any:
    """Recursively clones mutable or nested containers (dicts, lists, sets, tuples).

    Because `_ParseAndCompileWatchlistRules` caches parsed AST rules across
    instances in the same process, we must deeply clone mutable containers upon
    assignment to avoid cross-instance cache poisoning if a caller mutates
    instance attributes. A custom recursive traversal is used instead of
    `copy.deepcopy` for substantial performance gains (~3x faster).
    """
    if isinstance(val, dict):
        return {k: _CloneContainer(v) for k, v in val.items()}
    if isinstance(val, set):
        return set(val)
    if isinstance(val, (list, tuple)):
        return type(val)(_CloneContainer(x) for x in val)
    return val


class Watchlists(object):
    """Manage Watchlists.

    This class provides mechanism to load watchlists for a repo and identify
    watchers.
    Usage:
        wl = Watchlists("/path/to/repo/root")
        watchers = wl.GetWatchersForPaths(["/path/to/file1",
                                        "/path/to/file2",])
    """

    _RULES = "WATCHLISTS"
    _RULES_FILENAME = _RULES

    def __init__(self, repo_root):
        self._repo_root = repo_root
        self._defns = {}
        self._watchlists = {}
        self._path_regexps = {}
        self._LoadWatchlistRules()

    def _GetRulesFilePath(self):
        """Returns path to WATCHLISTS file."""
        if self._repo_root is None:
            return ""
        return os.path.abspath(
            os.path.join(self._repo_root, self._RULES_FILENAME)
        )

    def _HasWatchlistsFile(self):
        """Determine if watchlists are available for this repo."""
        if self._repo_root is None:
            return False
        return os.path.exists(self._GetRulesFilePath())

    def _ContentsOfWatchlistsFile(self):
        """Read the WATCHLISTS file and return its contents."""
        try:
            with open(self._GetRulesFilePath(), "r", encoding="utf-8") as f:
                return f.read()
        except (IOError, OSError, ValueError) as e:
            logging.error("Cannot read %s: %s", self._GetRulesFilePath(), e)
            return ""

    def _LoadWatchlistRules(self):
        """Load watchlists from WATCHLISTS file. Does nothing if not present."""
        if not self._HasWatchlistsFile():
            return

        contents = self._ContentsOfWatchlistsFile()
        if not contents:
            return

        rules = _ParseAndCompileWatchlistRules(
            contents, self._GetRulesFilePath()
        )
        # Deeply clone cached mutable structures to prevent in-place caller
        # mutations from poisoning the module-level LRU cache.
        self._defns = _CloneContainer(rules.defns)
        self._watchlists = _CloneContainer(rules.watchlists)
        self._path_regexps = _CloneContainer(rules.path_regexps)

    def GetWatchersForPaths(self, paths):
        """Fetch the list of watchers for |paths|

        Args:
            paths: [path1, path2, ...]

        Returns:
            [u1@chromium.org, u2@gmail.com, ...]
        """
        if not paths or not self._path_regexps:
            return []

        watchers = set()  # A set, to avoid duplicates
        for path in paths:
            if not isinstance(path, str) or not path:
                continue
            path = path.replace("\\", "/")
            if path.startswith("./"):
                path = path[2:]
            for name, rule in self._path_regexps.items():
                if name not in self._watchlists:
                    continue
                if rule.search(path):
                    emails = self._watchlists[name]
                    if isinstance(emails, str):
                        if emails:
                            watchers.add(emails)
                    elif isinstance(emails, Iterable):
                        for watchlist in emails:
                            if isinstance(watchlist, str) and watchlist:
                                watchers.add(watchlist)
        return sorted(watchers)


def main(argv):
    # Confirm that watchlists can be parsed and spew out the watchers
    if len(argv) < 2:
        print("Usage (from the base of repo):")
        print("  %s [file-1] [file-2] ...." % argv[0])
        return 1
    wl = Watchlists(os.getcwd())
    watchers = wl.GetWatchersForPaths(argv[1:])
    print(watchers)


if __name__ == "__main__":
    main(sys.argv)
