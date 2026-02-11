# Copyright (c) 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import pathlib
import subprocess

import gclient_scm


class JjWrapper(gclient_scm.GitWrapper):
    """JjWrapper handles repos that are intended to be used with jj.

    The repo does not yet need to be using jj, and does not even need to exist.
    """

    def _GetSubmodulePaths(self):
        with pathlib.Path(self.checkout_path, '.gitmodules').open('r') as f:
            for line in f:
                line = line.strip()
                if not line.startswith('path = '):
                    continue
                path = pathlib.Path(self.checkout_path, line[len('path = '):])
                # Not every submodule will exist, because many are conditional.
                if path.is_dir():
                    yield path

    def GetSubmoduleStateFromIndex(self):
        # Jj doesn't have an index as such, it just has a working copy.
        # Since jj doesn't yet have full submodule support, we just
        # read the submodules from the .gitmodules file.
        state = {}
        for submodule_path in self._GetSubmodulePaths():
            # TODO: Convert the submodule to jj and use jj log instead.
            state[str(submodule_path)] = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                check=True,
                cwd=submodule_path,
                stdout=subprocess.PIPE,
            ).stdout.decode('utf-8').strip()
        return state

    def GetSubmoduleDiff(self):
        # Git has an index and working copy, and calculates the submodule state
        # at the index and a diff since the index.
        # Jj has no index so this is always empty.
        return {}
