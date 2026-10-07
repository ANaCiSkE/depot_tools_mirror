#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRAPPER_SRC = os.path.join(ROOT_DIR, 'python-bin', 'python3')


@unittest.skipIf(sys.platform == 'win32', 'POSIX bash wrapper test')
class PythonBinWrapperTest(unittest.TestCase):

    def _create_fake_depot_tools(self, tmpdir, with_git=True):
        dt_dir = os.path.join(tmpdir, 'depot_tools')
        py_bin_dir = os.path.join(dt_dir, 'python-bin')
        os.makedirs(py_bin_dir)
        shutil.copy2(WRAPPER_SRC, os.path.join(py_bin_dir, 'python3'))
        if with_git:
            os.makedirs(os.path.join(dt_dir, '.git'))

        sys_bin_dir = os.path.join(tmpdir, 'sys_bin')
        os.makedirs(sys_bin_dir)
        sys_py = os.path.join(sys_bin_dir, 'python3')
        with open(sys_py, 'w', encoding='utf-8') as f:
            f.write('#!/usr/bin/env bash\necho "system:$*"\n')
        os.chmod(sys_py, 0o755)
        return dt_dir, sys_bin_dir

    def _create_hermetic_python(self, dt_dir, body='echo "hermetic:$*"\n'):
        rel = os.path.join('bootstrap-test_bin', 'python3', 'bin')
        abs_dir = os.path.join(dt_dir, rel)
        os.makedirs(abs_dir)
        hermetic_py = os.path.join(abs_dir, 'python3')
        with open(hermetic_py, 'w', encoding='utf-8') as f:
            f.write('#!/usr/bin/env bash\n' + body)
        os.chmod(hermetic_py, 0o755)
        with open(
            os.path.join(dt_dir, 'python3_bin_reldir.txt'),
            'w',
            encoding='utf-8',
        ) as f:
            f.write(rel + '\n')

    def test_git_checkout_missing_reldir_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dt_dir, sys_bin_dir = self._create_fake_depot_tools(
                tmpdir, with_git=True
            )
            env = os.environ.copy()
            env.pop('DEPOT_TOOLS_BOOTSTRAP_PYTHON3', None)
            env['PATH'] = sys_bin_dir + os.pathsep + env.get('PATH', '')
            res = subprocess.run(
                [os.path.join(dt_dir, 'python-bin', 'python3'), 'arg1'],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(res.returncode, 1)
            self.assertIn('python3_bin_reldir.txt not found', res.stderr)

    def test_tarball_without_git_and_missing_reldir_falls_back_to_system(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dt_dir, sys_bin_dir = self._create_fake_depot_tools(
                tmpdir, with_git=False
            )
            env = os.environ.copy()
            env.pop('DEPOT_TOOLS_BOOTSTRAP_PYTHON3', None)
            env['PATH'] = sys_bin_dir + os.pathsep + env.get('PATH', '')
            res = subprocess.run(
                [os.path.join(dt_dir, 'python-bin', 'python3'), 'arg1'],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(res.stdout.strip(), 'system:arg1')

    def test_tarball_with_working_hermetic_python_uses_hermetic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dt_dir, sys_bin_dir = self._create_fake_depot_tools(
                tmpdir, with_git=False
            )
            self._create_hermetic_python(dt_dir)
            env = os.environ.copy()
            env.pop('DEPOT_TOOLS_BOOTSTRAP_PYTHON3', None)
            env['PATH'] = sys_bin_dir + os.pathsep + env.get('PATH', '')
            res = subprocess.run(
                [os.path.join(dt_dir, 'python-bin', 'python3'), 'arg1'],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(res.stdout.strip(), 'hermetic:arg1')

    def test_tarball_with_incompatible_hermetic_python_falls_back(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dt_dir, sys_bin_dir = self._create_fake_depot_tools(
                tmpdir, with_git=False
            )
            self._create_hermetic_python(dt_dir, body='exit 126\n')
            env = os.environ.copy()
            env.pop('DEPOT_TOOLS_BOOTSTRAP_PYTHON3', None)
            env['PATH'] = sys_bin_dir + os.pathsep + env.get('PATH', '')
            res = subprocess.run(
                [os.path.join(dt_dir, 'python-bin', 'python3'), 'arg1'],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(res.stdout.strip(), 'system:arg1')


if __name__ == '__main__':
    unittest.main()
