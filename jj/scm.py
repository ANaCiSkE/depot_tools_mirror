# Copyright (c) 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import pathlib
import subprocess

import gclient_scm


class JjWrapper(gclient_scm.SCMWrapper):
    """JjWrapper handles repos that are intended to be used with jj.

    The repo does not yet need to be using jj, and does not even need to exist.
    """

    def __init__(self, url=None, *args, **kwargs):
        super(JjWrapper, self).__init__(url, *args, **kwargs)
        git_path = pathlib.Path(self.checkout_path, '.git')
        if git_path.exists():
            self._git_wrapper = gclient_scm.GitWrapper(url, *args, **kwargs)
        else:
            self._git_wrapper = None

    def _check_git_wrapper(self, command):
        if not self._git_wrapper:
            self.Print(
                f"Command '{command}' is not supported on JJ workspaces "
                "without a .git directory or worktree file"
            )
            return False
        return True

    def update(self, options, args, file_list):
        if self._check_git_wrapper('update'):
            self._git_wrapper.update(options, args, file_list)

    def revert(self, options, args, file_list):
        if self._check_git_wrapper('revert'):
            self._git_wrapper.revert(options, args, file_list)

    def revinfo(self, options, args, file_list):
        if self._check_git_wrapper('revinfo'):
            self._git_wrapper.revinfo(options, args, file_list)

    def status(self, options, args, file_list):
        if self._check_git_wrapper('status'):
            self._git_wrapper.status(options, args, file_list)

    def diff(self, options, args, file_list):
        if self._check_git_wrapper('diff'):
            self._git_wrapper.diff(options, args, file_list)

    def pack(self, options, args, file_list):
        if self._check_git_wrapper('pack'):
            self._git_wrapper.pack(options, args, file_list)

    def runhooks(self, options, args, file_list):
        if self._check_git_wrapper('runhooks'):
            self._git_wrapper.runhooks(options, args, file_list)


    def _GetSubmodulePaths(self):
        gitmodules_path = pathlib.Path(self.checkout_path, '.gitmodules')
        with gitmodules_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line.startswith('path = '):
                    continue
                path = pathlib.Path(self.checkout_path, line[len('path = '):])
                # Not every submodule will exist, because many are conditional.
                if path.is_dir() and (path / '.git').exists():
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
