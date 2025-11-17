#!/usr/bin/env python3
# Copyright (c) 2025 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest
import platform
from unittest import mock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import siso
from testing_support import trial_dir


class SisoTest(trial_dir.TestCase):

    def setUp(self):
        super().setUp()
        self.previous_dir = os.getcwd()
        os.chdir(self.root_dir)

    def tearDown(self):
        os.chdir(self.previous_dir)
        super().tearDown()

    def test_load_sisorc_no_file(self):
        global_flags, subcmd_flags = siso.load_sisorc(
            os.path.join('build', 'config', 'siso', '.sisorc'))
        self.assertEqual(global_flags, [])
        self.assertEqual(subcmd_flags, {})

    def test_load_sisorc(self):
        sisorc = os.path.join('build', 'config', 'siso', '.sisorc')
        os.makedirs(os.path.dirname(sisorc))
        with open(sisorc, 'w') as f:
            f.write("""
# comment
-credential_helper=gcloud
ninja --failure_verbose=false -k=0
            """)
        global_flags, subcmd_flags = siso.load_sisorc(sisorc)
        self.assertEqual(global_flags, ['-credential_helper=gcloud'])
        self.assertEqual(subcmd_flags,
                         {'ninja': ['--failure_verbose=false', '-k=0']})

    def test_apply_sisorc_none(self):
        new_args = siso.apply_sisorc([], {}, ['ninja', '-C', 'out/Default'],
                                     'ninja')
        self.assertEqual(new_args, ['ninja', '-C', 'out/Default'])

    def test_apply_sisorc_nosubcmd(self):
        new_args = siso.apply_sisorc([], {'ninja': ['-k=0']}, ['-version'], '')
        self.assertEqual(new_args, ['-version'])

    def test_apply_sisorc(self):
        new_args = siso.apply_sisorc(
            ['-credential_helper=luci-auth'], {'ninja': ['-k=0']},
            ['-log_dir=/tmp', 'ninja', '-C', 'out/Default'], 'ninja')
        self.assertEqual(new_args, [
            '-credential_helper=luci-auth', '-log_dir=/tmp', 'ninja', '-k=0',
            '-C', 'out/Default'
        ])

    @mock.patch('siso.subprocess.call')
    def test_is_subcommand_present(self, mock_call):

        def side_effect(cmd):
            if cmd[2] in ['collector', 'ninja']:
                return 0
            return 2

        mock_call.side_effect = side_effect
        self.assertTrue(siso._is_subcommand_present('siso_path', 'collector'))
        self.assertTrue(siso._is_subcommand_present('siso_path', 'ninja'))
        self.assertFalse(siso._is_subcommand_present('siso_path', 'unknown'))

    def test_apply_metrics_labels(self):
        user_system = siso._SYSTEM_DICT.get(platform.system(),
                                            platform.system())
        test_cases = {
            'no_labels': {
                'args': ['ninja', '-C', 'out/Default'],
                'want': [
                    'ninja', '-C', 'out/Default', '--metrics_labels',
                    f'type=developer,tool=siso,host_os={user_system}'
                ]
            },
            'labels_exist': {
                'args':
                ['ninja', '-C', 'out/Default', '--metrics_labels=foo=bar'],
                'want':
                ['ninja', '-C', 'out/Default', '--metrics_labels=foo=bar']
            }
        }
        for name, tc in test_cases.items():
            with self.subTest(name):
                got = siso.apply_metrics_labels(tc['args'])
                self.assertEqual(got, tc['want'])

    def test_apply_telemetry_flags(self):
        test_cases = {
            'no_env_flags': {
                'args': ['ninja', '-C', 'out/Default'],
                'env': {},
                'want': ['ninja', '-C', 'out/Default'],
            },
            'some_already_applied_no_env_flags': {
                'args': [
                    'ninja', '-C', 'out/Default', '--enable_cloud_monitoring',
                    '--enable_cloud_profiler'
                ],
                'env': {},
                'want': [
                    'ninja', '-C', 'out/Default', '--enable_cloud_monitoring',
                    '--enable_cloud_profiler'
                ],
            },
            'metrics_project_set': {
                'args': [
                    'ninja', '-C', 'out/Default', '--metrics_project',
                    'some_project'
                ],
                'env': {},
                'want': [
                    'ninja', '-C', 'out/Default', '--metrics_project',
                    'some_project', '--enable_cloud_monitoring',
                    '--enable_cloud_profiler', '--enable_cloud_trace',
                    '--enable_cloud_logging'
                ],
            },
            'metrics_project_set_thru_env': {
                'args': ['ninja', '-C', 'out/Default'],
                'env': {
                    'RBE_metrics_project': 'some_project'
                },
                'want': [
                    'ninja', '-C', 'out/Default', '--enable_cloud_monitoring',
                    '--enable_cloud_profiler', '--enable_cloud_trace',
                    '--enable_cloud_logging'
                ],
            },
            'cloud_project_set': {
                'args':
                ['ninja', '-C', 'out/Default', '--project', 'some_project'],
                'env': {},
                'want': [
                    'ninja',
                    '-C',
                    'out/Default',
                    '--project',
                    'some_project',
                    '--enable_cloud_monitoring',
                    '--enable_cloud_profiler',
                    '--enable_cloud_trace',
                    '--enable_cloud_logging',
                    '--metrics_project=some_project',
                ],
            },
            'cloud_project_set_thru_env': {
                'args': ['ninja', '-C', 'out/Default'],
                'env': {
                    'SISO_PROJECT': 'some_project'
                },
                'want': [
                    'ninja',
                    '-C',
                    'out/Default',
                    '--enable_cloud_monitoring',
                    '--enable_cloud_profiler',
                    '--enable_cloud_trace',
                    '--enable_cloud_logging',
                    '--metrics_project=some_project',
                ],
            },
            'respects_set_flags': {
                'args':
                ['ninja', '-C', 'out/Default', '--enable_cloud_profiler=false'],
                'env': {
                    'SISO_PROJECT': 'some_project'
                },
                'want': [
                    'ninja',
                    '-C',
                    'out/Default',
                    '--enable_cloud_profiler=false',
                    '--enable_cloud_monitoring',
                    '--enable_cloud_trace',
                    '--enable_cloud_logging',
                    '--metrics_project=some_project',
                ],
            },
        }

        for name, tc in test_cases.items():
            with self.subTest(name):
                got = siso.apply_telemetry_flags(tc['args'], tc['env'])
                self.assertEqual(got, tc['want'])

    @mock.patch.dict('os.environ', {})
    def test_apply_telemetry_flags_sets_expected_env_var(self):
        args = [
            'ninja',
            '-C',
            'out/Default',
        ]
        env = {}
        _ = siso.apply_telemetry_flags(args, env)
        self.assertEqual(os.environ.get("GOOGLE_API_USE_CLIENT_CERTIFICATE"),
                         "false")


if __name__ == '__main__':
    unittest.main()
