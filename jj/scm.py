# Copyright (c) 2026 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""SCM wrapper for jj."""
import functools
import pathlib
import subprocess

import gclient_scm
import gclient_utils


def prefer_git_wrapper(func):
    """Dynamically delegates to GitWrapper unless a .jj directory exists,
    without a corresponding .git directory, as in a standalone JJ workspace."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # pylint: disable=protected-access
        if not hasattr(self, '_prefer_git'):
            git_path = pathlib.Path(self.checkout_path, '.git')
            jj_path = pathlib.Path(self.checkout_path, '.jj')
            self._prefer_git = git_path.exists() or not jj_path.exists()
        if self._prefer_git:
            super_method = getattr(super(JjWrapper, self), func.__name__)
            return super_method(*args, **kwargs)
        return func(self, *args, **kwargs)

    return wrapper


class JjWrapper(gclient_scm.GitWrapper):
    """JjWrapper handles repos that are intended to be used with jj.

    The repo does not yet need to be using jj, and does not even need to exist.
    """

    @prefer_git_wrapper
    def _GetSubmodulePaths(self):
        gitmodules_path = pathlib.Path(self.checkout_path, '.gitmodules')
        with gitmodules_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line.startswith('path = '):
                    continue
                path = pathlib.Path(self.checkout_path, line[len('path = '):])
                # Not every submodule will exist, because many are conditional.
                if path.is_dir() and ((path / '.git').exists() or
                                      (path / '.jj').exists()):
                    yield path

    @prefer_git_wrapper
    def GetSubmoduleStateFromIndex(self):
        # Jj doesn't have an index as such, it just has a working copy.
        # Since jj doesn't yet have full submodule support, we just
        # read the submodules from the .gitmodules file.
        state = {}
        for submodule_path in self._GetSubmodulePaths():
            if (submodule_path / '.git').exists():
                state[str(submodule_path)] = (subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=submodule_path,
                    capture_output=True,
                    check=True,
                ).stdout.decode('utf-8').strip())
            elif (submodule_path / '.jj').exists():
                state[str(submodule_path)] = (subprocess.run(
                    ['jj', 'log', '-r', '@-', '-T', 'commit_id'],
                    cwd=submodule_path,
                    capture_output=True,
                    check=True,
                ).stdout.decode('utf-8').strip())
            else:
                raise RuntimeError(
                    f'Could not determine submodule repo type: {submodule_path}'
                )

        return state

    @prefer_git_wrapper
    def GetSubmoduleDiff(self):
        # Git has an index and working copy, and calculates the submodule state
        # at the index and a diff since the index.
        # Jj has no index so this is always empty.
        return {}

    @prefer_git_wrapper
    def GetCacheMirror(self):
        return None

    @prefer_git_wrapper
    def GetActualRemoteURL(self, options):
        return None

    @prefer_git_wrapper
    def DoesRemoteURLMatch(self, options):
        del options
        return True

    @prefer_git_wrapper
    def revert(self, options, args, file_list):
        pass

    @prefer_git_wrapper
    def diff(self, options, args, file_list):
        pass

    @prefer_git_wrapper
    def pack(self, options, args, file_list):
        pass

    @prefer_git_wrapper
    def revinfo(self, options, args, file_list):
        return subprocess.run(['jj', 'log', '-r', '@-', '-T', 'commit_id'],
                    cwd=self.checkout_path,
                    capture_output=True,
                    check=True,
                ).stdout.decode('utf-8').strip()

    @prefer_git_wrapper
    def status(self, options, args, file_list):
        pass

    @prefer_git_wrapper
    def update(self, options, args, file_list):
        url, deps_revision = gclient_utils.SplitUrlRevision(self.url)
        revision = deps_revision
        if options.revision:
            revision = str(options.revision)
        if not revision:
            revision = 'main@origin'
        if revision == 'unmanaged':
            return

        # Fetch if the revision is missing locally
        check_res = subprocess.run(
            ['jj', 'log', '-r', revision, '-G', '-T', ''],
            cwd=self.checkout_path,
            capture_output=True,
        )
        if check_res.returncode != 0:
            subprocess.run(
                ['jj', 'git', 'fetch'],
                cwd=self.checkout_path,
                capture_output=True,
                check=True,
            )

        subprocess.run(
            ['jj', 'new', revision],
            cwd=self.checkout_path,
            capture_output=True,
            check=True,
        )
