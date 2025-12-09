#!/usr/bin/env python3
# Copyright (c) 2024 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import io
import os
import shlex
import sys
import unittest
import platform
from unittest import mock
import subprocess
import itertools

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import siso
from testing_support import trial_dir


class SisoTest(trial_dir.TestCase):

    def setUp(self):
        super().setUp()
        self.previous_dir = os.getcwd()
        os.chdir(self.root_dir)
        self.patchers_to_stop = []
        patcher = mock.patch('siso.getpass.getuser', return_value='testuser')
        patcher.start()
        self.patchers_to_stop.append(patcher)

    def tearDown(self):
        os.chdir(self.previous_dir)
        for patcher in reversed(self.patchers_to_stop):
            patcher.stop()
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

        def side_effect(cmd, *_, **__):
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
        self.assertEqual(env.get("GOOGLE_API_USE_CLIENT_CERTIFICATE"), "false")

    def test_fetch_metrics_project(self):
        test_cases = {
            'metrics_project_arg': {
                'args': ['--metrics_project', 'proj1'],
                'env': {},
                'want': 'proj1',
            },
            'project_arg': {
                'args': ['--project', 'proj2'],
                'env': {},
                'want': 'proj2',
            },
            'metrics_project_and_project_args': {
                'args': ['--metrics_project', 'proj1', '--project', 'proj2'],
                'env': {},
                'want': 'proj1',
            },
            'rbe_metrics_project_env': {
                'args': [],
                'env': {
                    'RBE_metrics_project': 'proj3'
                },
                'want': 'proj3',
            },
            'siso_project_env': {
                'args': [],
                'env': {
                    'SISO_PROJECT': 'proj4'
                },
                'want': 'proj4',
            },
            'rbe_and_siso_project_env': {
                'args': [],
                'env': {
                    'RBE_metrics_project': 'proj3',
                    'SISO_PROJECT': 'proj4'
                },
                'want': 'proj3',
            },
            'project_arg_and_rbe_env': {
                'args': ['--project', 'proj2'],
                'env': {
                    'RBE_metrics_project': 'proj3'
                },
                'want': 'proj2',
            },
            'metrics_project_arg_and_rbe_env': {
                'args': ['--metrics_project', 'proj1'],
                'env': {
                    'RBE_metrics_project': 'proj3'
                },
                'want': 'proj1',
            },
            'no_project': {
                'args': [],
                'env': {},
                'want': '',
            },
            'short_metrics_project_arg': {
                'args': ['-metrics_project', 'proj1'],
                'env': {},
                'want': 'proj1',
            },
            'short_project_arg': {
                'args': ['-project', 'proj2'],
                'env': {},
                'want': 'proj2',
            },
        }

        for name, tc in test_cases.items():
            with self.subTest(name):
                got = siso._fetch_metrics_project(tc['args'], tc['env'])
                self.assertEqual(got, tc['want'])

    def test_resolve_sockets_folder(self):
        xdg_runtime_dir_val = os.path.join(self.root_dir, "run/user/1000")
        darwin_tmpdir_val = os.path.join(self.root_dir, "var/folders/12/345...")
        user = 'testuser'
        test_cases = {
            "linux_xdg_runtime_dir": {
                "platform": "Linux",
                "env": {
                    "XDG_RUNTIME_DIR": xdg_runtime_dir_val
                },
                "want_path": os.path.join(xdg_runtime_dir_val, user, "siso"),
            },
            "linux_tmp": {
                "platform": "Linux",
                "env": {},
                "want_path": os.path.join("/tmp", user, "siso"),
            },
            "darwin_tmpdir": {
                "platform": "Darwin",
                "env": {
                    "TMPDIR": darwin_tmpdir_val
                },
                "want_path": os.path.join(darwin_tmpdir_val, user, "siso"),
            },
            "darwin_tmp": {
                "platform": "Darwin",
                "env": {},
                "want_path": os.path.join("/tmp", user, "siso"),
            },
            "long_path": {
                "platform": "Linux",
                "env": {
                    "XDG_RUNTIME_DIR": "a" * 100
                },
                "want_path": os.path.join("/tmp", user, "siso"),
            },
        }

        for name, tc in test_cases.items():
            with self.subTest(name):
                # The code under test uses sys.platform, which is lowercase.
                platform_value = tc["platform"].lower()
                if platform_value == 'windows':
                    platform_value = 'win32'
                with mock.patch('sys.platform', new=platform_value):
                    path, length = siso._resolve_sockets_folder(tc["env"])

                    expected_path = tc["want_path"]
                    # If the desired path is too long, the function will fall back to /tmp/<user>/siso
                    if (104 - len(tc["want_path"]) - 6) < 1:
                        expected_path = os.path.join("/tmp", user, "siso")

                    expected_len = 104 - len(expected_path) - 6

                    self.assertEqual(path, expected_path)
                    self.assertEqual(length, expected_len)
                    self.assertTrue(os.path.isdir(path))

    @mock.patch('siso._start_collector')
    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso._fetch_metrics_project', return_value='test-project')
    def test_handle_collector_args_disabled(self, mock_fetch, mock_system,
                                            mock_start_collector):
        siso_path = 'path/to/siso'
        out_dir = 'out/Default'
        env = {'SISO_PROJECT': 'test-project'}
        args = ['ninja', '-C', out_dir]

        result = siso._handle_collector_args(siso_path, args, env)

        self.assertEqual(result, args)
        mock_fetch.assert_not_called()
        mock_start_collector.assert_not_called()

    @unittest.skipIf(platform.system() == 'Windows',
                     'Skipping Linux-specific test on Windows')
    @mock.patch('siso._start_collector', return_value=True)
    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('sys.platform', new='linux')
    def test_handle_collector_args_starts_linux(self, mock_system,
                                                mock_start_collector):
        siso_path = 'path/to/siso'
        env = {'SISO_PROJECT': 'test-project', 'XDG_RUNTIME_DIR': '/tmp/run'}
        args = ['ninja', '--enable_collector']

        captured_args = []

        def fetch_metrics_project_side_effect(args, env):
            captured_args.append(list(args))
            return 'test-project'

        with mock.patch('siso._fetch_metrics_project',
                        side_effect=fetch_metrics_project_side_effect):
            result = siso._handle_collector_args(siso_path, args, env)

            sockets_file = "/tmp/run/testuser/siso/test-project.sock"
            self.assertEqual(result, [
                'ninja', '--enable_collector',
                f'--collector_address=unix://{sockets_file}'
            ])
            self.assertEqual(captured_args, [['ninja', '--enable_collector']])
            mock_start_collector.assert_called_once_with(
                siso_path, sockets_file, 'test-project')

    @mock.patch('siso._start_collector', return_value=True)
    @mock.patch('siso.platform.system', return_value='Windows')
    @mock.patch('siso._fetch_metrics_project', return_value='test-project')
    @mock.patch('sys.platform', new='win32')
    def test_handle_collector_args_starts_windows(self, mock_fetch, mock_system,
                                                  mock_start_collector):
        siso_path = 'path/to/siso'
        env = {'SISO_PROJECT': 'test-project'}
        args = ['ninja', '--enable_collector']
        original_args = list(args)

        result = siso._handle_collector_args(siso_path, args, env)

        self.assertEqual(result, ['ninja', '--enable_collector'])
        mock_fetch.assert_called_once_with(original_args, env)
        mock_start_collector.assert_called_once_with(siso_path, None,
                                                     'test-project')

    @unittest.skipIf(platform.system() == 'Windows',
                     'Skipping Linux-specific test on Windows')
    @mock.patch('siso._start_collector', return_value=False)
    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('sys.platform', new='linux')
    def test_handle_collector_args_fails(self, mock_system,
                                         mock_start_collector):
        siso_path = 'path/to/siso'
        env = {'SISO_PROJECT': 'test-project', 'XDG_RUNTIME_DIR': '/tmp/run'}
        args = ['ninja', '--enable_collector']

        captured_args = []

        def fetch_metrics_project_side_effect(args, env):
            captured_args.append(list(args))
            return 'test-project'

        with mock.patch('siso._fetch_metrics_project',
                        side_effect=fetch_metrics_project_side_effect):
            result = siso._handle_collector_args(siso_path, args, env)

            self.assertEqual(result, ['ninja', '--enable_collector=false'])
            self.assertEqual(captured_args, [['ninja', '--enable_collector']])
            sockets_file = "/tmp/run/testuser/siso/test-project.sock"
            mock_start_collector.assert_called_once_with(
                siso_path, sockets_file, 'test-project')

    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.remove')
    def test_start_collector_removes_existing_socket_file(
            self, mock_os_remove, mock_os_path_exists, mock_system):
        m = self._start_collector_mocks()
        siso_path = "siso_path"
        project = "test-project"
        sockets_file = "/tmp/test.sock"
        self._configure_http_responses(m.mock_conn,
                                       status_responses=[(404, None),
                                                         (200, None)],
                                       config_responses=[(200, None),
                                                         (200, None)])
        status_healthy = {'healthy': True, 'status': 'StatusOK'}
        config = {
            'receivers': {
                'otlp': {
                    'protocols': {
                        'grpc': {
                            'endpoint': sockets_file
                        }
                    }
                }
            }
        }
        with mock.patch('siso.json.loads',
                        side_effect=[status_healthy, config, config]):
            siso._start_collector(siso_path, sockets_file, project)
            mock_os_path_exists.assert_called_with(sockets_file)
            mock_os_remove.assert_called_with(sockets_file)

    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.remove', side_effect=OSError("Permission denied"))
    def test_start_collector_remove_socket_file_fails(self, mock_os_remove,
                                                      mock_os_path_exists,
                                                      mock_system):
        m = self._start_collector_mocks()
        siso_path = "siso_path"
        project = "test-project"
        sockets_file = "/tmp/test.sock"
        self._configure_http_responses(m.mock_conn,
                                       status_responses=[(404, None),
                                                         (200, None)],
                                       config_responses=[(200, None),
                                                         (200, None)])
        status_healthy = {'healthy': True, 'status': 'StatusOK'}
        config = {
            'receivers': {
                'otlp': {
                    'protocols': {
                        'grpc': {
                            'endpoint': siso._OTLP_DEFAULT_TCP_ENDPOINT
                        }
                    }
                }
            }
        }
        with mock.patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            with mock.patch('siso.json.loads',
                            side_effect=[status_healthy, config, config]):
                siso._start_collector(siso_path, sockets_file, project)

                mock_os_path_exists.assert_called_with(sockets_file)
                mock_os_remove.assert_called_with(sockets_file)
                self.assertIn(f"Failed to remove {sockets_file}",
                              mock_stderr.getvalue())


    def test_process_args(self):
        user_system = siso._SYSTEM_DICT.get(platform.system(),
                                            platform.system())
        processed_args = ['-gflag', 'ninja', '-sflag', '-C', 'out/Default']

        test_cases = {
            "no_ninja": {
                "args": ["other", "-C", "out/Default"],
                "subcmd": "other",
                "should_collect_logs": True,
                "want": ["other", "-C", "out/Default"],
            },
            "ninja_no_logs": {
                "args": ["ninja", "-C", "out/Default"],
                "subcmd": "ninja",
                "should_collect_logs": False,
                "want": [
                    "ninja",
                    "-C",
                    "out/Default",
                    "--metrics_labels",
                    f"type=developer,tool=siso,host_os={user_system}",
                ],
            },
            "ninja_with_logs_no_project": {
                "args": ["ninja", "-C", "out/Default"],
                "subcmd": "ninja",
                "should_collect_logs": True,
                "want": [
                    "ninja",
                    "-C",
                    "out/Default",
                    "--metrics_labels",
                    f"type=developer,tool=siso,host_os={user_system}",
                ],
            },
            "ninja_with_logs_with_project_in_args": {
                "args": [
                    "ninja",
                    "-C",
                    "out/Default",
                    "--project=test-project",
                ],
                "subcmd": "ninja",
                "should_collect_logs": True,
                "want": [
                    "ninja",
                    "-C",
                    "out/Default",
                    "--project=test-project",
                    "--metrics_labels",
                    f"type=developer,tool=siso,host_os={user_system}",
                    "--enable_cloud_monitoring",
                    "--enable_cloud_profiler",
                    "--enable_cloud_trace",
                    "--enable_cloud_logging",
                    "--metrics_project=test-project",
                ],
            },
            "ninja_with_logs_with_project_in_env": {
                "args": ["ninja", "-C", "out/Default"],
                "subcmd": "ninja",
                "should_collect_logs": True,
                "env": {"SISO_PROJECT": "test-project"},
                "want": [
                    "ninja",
                    "-C",
                    "out/Default",
                    "--metrics_labels",
                    f"type=developer,tool=siso,host_os={user_system}",
                    "--enable_cloud_monitoring",
                    "--enable_cloud_profiler",
                    "--enable_cloud_trace",
                    "--enable_cloud_logging",
                    "--metrics_project=test-project",
                ],
            },
            "with_sisorc": {
                "global_flags": ["-gflag"],
                "subcmd_flags": {"ninja": ["-sflag"]},
                "args": ["ninja", "-C", "out/Default"],
                "subcmd": "ninja",
                "should_collect_logs": False,
                "want": processed_args
                + [
                    "--metrics_labels",
                    f"type=developer,tool=siso,host_os={user_system}",
                ],
                "want_stderr": "depot_tools/siso.py: %s\n"
                % shlex.join(processed_args),
            },
            "with_sisorc_global_flags_only": {
                "global_flags": ["-gflag_only"],
                "args": ["ninja", "-C", "out/Default"],
                "subcmd": "ninja",
                "should_collect_logs": False,
                "want": [
                    "-gflag_only",
                    "ninja",
                    "-C",
                    "out/Default",
                    "--metrics_labels",
                    f"type=developer,tool=siso,host_os={user_system}",
                ],
                "want_stderr": "depot_tools/siso.py: %s\n"
                % shlex.join(["-gflag_only", "ninja", "-C", "out/Default"]),
            },
            "with_sisorc_subcmd_flags_only": {
                "subcmd_flags": {"ninja": ["-sflag_only"]},
                "args": ["ninja", "-C", "out/Default"],
                "subcmd": "ninja",
                "should_collect_logs": False,
                "want": [
                    "ninja",
                    "-sflag_only",
                    "-C",
                    "out/Default",
                    "--metrics_labels",
                    f"type=developer,tool=siso,host_os={user_system}",
                ],
                "want_stderr": "depot_tools/siso.py: %s\n"
                % shlex.join(["ninja", "-sflag_only", "-C", "out/Default"]),
            },
            "with_sisorc_global_and_subcmd_flags_and_telemetry": {
                "global_flags": ["-gflag_tel"],
                "subcmd_flags": {"ninja": ["-sflag_tel"]},
                "args": ["ninja", "-C", "out/Default"],
                "subcmd": "ninja",
                "should_collect_logs": True,
                "env": {"SISO_PROJECT": "telemetry-project"},
                "want": [
                    "-gflag_tel",
                    "ninja",
                    "-sflag_tel",
                    "-C",
                    "out/Default",
                    "--metrics_labels",
                    f"type=developer,tool=siso,host_os={user_system}",
                    "--enable_cloud_monitoring",
                    "--enable_cloud_profiler",
                    "--enable_cloud_trace",
                    "--enable_cloud_logging",
                    "--metrics_project=telemetry-project",
                ],
                "want_stderr": "depot_tools/siso.py: %s\n"
                % shlex.join(["-gflag_tel", "ninja", "-sflag_tel", "-C", "out/Default"]),
            },
            "with_sisorc_non_ninja_subcmd": {
                "global_flags": ["-gflag_non_ninja"],
                "subcmd_flags": {"other_subcmd": ["-sflag_non_ninja"]},
                "args": ["other_subcmd", "-C", "out/Default"],
                "subcmd": "other_subcmd",
                "should_collect_logs": True,
                "env": {"SISO_PROJECT": "telemetry-project"},
                "want": [
                    "-gflag_non_ninja",
                    "other_subcmd",
                    "-sflag_non_ninja",
                    "-C",
                    "out/Default",
                ],
                "want_stderr": "depot_tools/siso.py: %s\n"
                % shlex.join(["-gflag_non_ninja", "other_subcmd", "-sflag_non_ninja", "-C", "out/Default"]),
            },
        }

        for name, tc in test_cases.items():
            with self.subTest(name):
                with mock.patch('sys.stderr',
                                new_callable=io.StringIO) as mock_stderr:
                    got = siso._process_args(tc.get('global_flags', []),
                                             tc.get('subcmd_flags', {}),
                                             tc['args'], tc['subcmd'],
                                             tc['should_collect_logs'],
                                             tc.get('env', {}))
                    self.assertEqual(got, tc['want'])
                    self.assertEqual(mock_stderr.getvalue(),
                                     tc.get('want_stderr', ''))

    @unittest.skipIf(platform.system() == 'Windows',
                     'Not applicable on Windows')
    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso.os.kill')
    @mock.patch('siso.subprocess.run')
    def test_kill_collector_process_found_and_killed_posix(
            self, mock_subprocess_run, mock_os_kill, _):
        mock_subprocess_run.return_value = mock.Mock(stdout=b'123\n',
                                                     stderr=b'',
                                                     returncode=0)

        self.assertTrue(siso._kill_collector())

        mock_subprocess_run.assert_called_once_with(
            ['lsof', '-t', f'-i:{siso._OTLP_HEALTH_PORT}'], capture_output=True)
        mock_os_kill.assert_called_once_with(123, siso.signal.SIGKILL)

    @unittest.skipIf(platform.system() == 'Windows',
                     'Not applicable on Windows')
    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso.os.kill')
    @mock.patch('siso.subprocess.run')
    def test_kill_collector_process_not_found_posix(self, mock_subprocess_run,
                                                    mock_os_kill, _):
        mock_subprocess_run.return_value = mock.Mock(
            stdout=b'', stderr=b'lsof: no process found\n', returncode=1)

        self.assertFalse(siso._kill_collector())

        mock_subprocess_run.assert_called_once_with(
            ['lsof', '-t', f'-i:{siso._OTLP_HEALTH_PORT}'], capture_output=True)
        mock_os_kill.assert_not_called()

    @unittest.skipIf(platform.system() == 'Windows',
                     'Not applicable on Windows')
    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso.os.kill')
    @mock.patch('siso.subprocess.run')
    def test_kill_collector_kill_fails_posix(self, mock_subprocess_run,
                                             mock_os_kill, _):
        mock_subprocess_run.return_value = mock.Mock(stdout=b'123\n',
                                                     stderr=b'',
                                                     returncode=0)
        mock_os_kill.side_effect = OSError("Operation not permitted")

        self.assertFalse(siso._kill_collector())

        mock_subprocess_run.assert_called_once_with(
            ['lsof', '-t', f'-i:{siso._OTLP_HEALTH_PORT}'], capture_output=True)
        mock_os_kill.assert_called_once_with(123, siso.signal.SIGKILL)

    @unittest.skipIf(platform.system() == 'Windows',
                     'Not applicable on Windows')
    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso.os.kill')
    @mock.patch('siso.subprocess.run')
    def test_kill_collector_no_pids_found_posix(self, mock_subprocess_run,
                                                mock_os_kill, _):
        # stdout is empty, so no PIDs.
        mock_subprocess_run.return_value = mock.Mock(stdout=b'\n',
                                                     stderr=b'',
                                                     returncode=0)

        self.assertFalse(siso._kill_collector())

        mock_subprocess_run.assert_called_once_with(
            ['lsof', '-t', f'-i:{siso._OTLP_HEALTH_PORT}'], capture_output=True)
        # os.kill should not be called.
        mock_os_kill.assert_not_called()

    @unittest.skipIf(platform.system() == 'Windows',
                     'Not applicable on Windows')
    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso.os.kill')
    @mock.patch('siso.subprocess.run')
    def test_kill_collector_multiple_pids_found_posix(self, mock_subprocess_run,
                                                      mock_os_kill, _):
        # stdout has two PIDs.
        mock_subprocess_run.return_value = mock.Mock(stdout=b'0\n123\n456\n',
                                                     stderr=b'',
                                                     returncode=0)

        self.assertTrue(siso._kill_collector())

        mock_subprocess_run.assert_called_once_with(
            ['lsof', '-t', f'-i:{siso._OTLP_HEALTH_PORT}'], capture_output=True)
        # Only the first PID should be killed.
        mock_os_kill.assert_called_once_with(123, siso.signal.SIGKILL)

    @mock.patch('siso.platform.system', return_value='Windows')
    @mock.patch('siso.subprocess.run')
    def test_kill_collector_process_found_and_killed_windows(
            self, mock_subprocess_run, _):
        netstat_output = (
            f'  TCP    127.0.0.1:{siso._OTLP_HEALTH_PORT}        [::]:0                 LISTENING       1234\r\n'
        )
        mock_subprocess_run.side_effect = [
            mock.Mock(stdout=netstat_output.encode('utf-8'),
                      stderr=b'',
                      returncode=0),
            mock.Mock(stdout=b'', stderr=b'', returncode=0)
        ]

        self.assertTrue(siso._kill_collector())

        self.assertEqual(mock_subprocess_run.call_count, 2)
        mock_subprocess_run.assert_has_calls([
            mock.call(['netstat', '-aon'], capture_output=True),
            mock.call(
                ['taskkill', '/F', '/T', '/PID', '1234'],
                capture_output=True,
            )
        ])

    @mock.patch('siso.platform.system', return_value='Windows')
    @mock.patch('siso.subprocess.run')
    def test_kill_collector_process_not_found_windows(self, mock_subprocess_run,
                                                      _):
        netstat_output = (
            b'  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       868\r\n'
        )
        mock_subprocess_run.return_value = mock.Mock(stdout=netstat_output,
                                                     stderr=b'',
                                                     returncode=0)

        self.assertFalse(siso._kill_collector())

        mock_subprocess_run.assert_called_once_with(['netstat', '-aon'],
                                                    capture_output=True)
        self.assertEqual(mock_subprocess_run.call_count, 1)

    @mock.patch('siso.platform.system', return_value='Windows')
    @mock.patch('siso.subprocess.run')
    def test_kill_collector_multiple_pids_found_windows(self,
                                                        mock_subprocess_run, _):
        netstat_output = (
            f'  TCP    127.0.0.1:{siso._OTLP_HEALTH_PORT}        [::]:0                 LISTENING       0\r\n'
            f'  TCP    127.0.0.1:{siso._OTLP_HEALTH_PORT}        [::]:0                 LISTENING       0\r\n'
            f'  TCP    127.0.0.1:{siso._OTLP_HEALTH_PORT}        [::]:0                 LISTENING       1234\r\n'
            f'  TCP    127.0.0.1:{siso._OTLP_HEALTH_PORT}        [::]:0                 LISTENING       5678\r\n'
        )
        mock_subprocess_run.side_effect = [
            mock.Mock(stdout=netstat_output.encode('utf-8'),
                      stderr=b'',
                      returncode=0),
            mock.Mock(stdout=b'', stderr=b'', returncode=0)
        ]

        self.assertTrue(siso._kill_collector())

        self.assertEqual(mock_subprocess_run.call_count, 2)
        mock_subprocess_run.assert_has_calls([
            mock.call(['netstat', '-aon'], capture_output=True),
            # Only the first PID should be killed.
            mock.call(
                ['taskkill', '/F', '/T', '/PID', '1234'],
                capture_output=True,
            )
        ])

    @mock.patch('siso.platform.system', return_value='Windows')
    @mock.patch('siso.subprocess.run')
    def test_kill_collector_netstat_fails_windows(self, mock_subprocess_run, _):
        mock_subprocess_run.return_value = mock.Mock(stdout=b'',
                                                     stderr=b'netstat error\n',
                                                     returncode=1)

        self.assertFalse(siso._kill_collector())

        mock_subprocess_run.assert_called_once_with(['netstat', '-aon'],
                                                    capture_output=True)

    @mock.patch('siso.platform.system', return_value='Windows')
    @mock.patch('siso.subprocess.run')
    def test_kill_collector_taskkill_fails_windows(self, mock_subprocess_run,
                                                   _):
        netstat_output = (
            f'  TCP    127.0.0.1:{siso._OTLP_HEALTH_PORT}        [::]:0                 LISTENING       1234\r\n'
        )
        mock_subprocess_run.side_effect = [
            mock.Mock(stdout=netstat_output.encode('utf-8'),
                      stderr=b'',
                      returncode=0),
            mock.Mock(stdout=b'',
                      stderr=b'ERROR: Cannot terminate process.',
                      returncode=1)
        ]

        self.assertFalse(siso._kill_collector())

        self.assertEqual(mock_subprocess_run.call_count, 2)
        mock_subprocess_run.assert_has_calls([
            mock.call(['netstat', '-aon'], capture_output=True),
            mock.call(
                ['taskkill', '/F', '/T', '/PID', '1234'],
                capture_output=True,
            )
        ])

    def _start_collector_mocks(self):
        patchers = {
            'is_subcommand_present':
            mock.patch('siso._is_subcommand_present', return_value=True),
            'subprocess_run':
            mock.patch('siso.subprocess.run'),
            'kill_collector':
            mock.patch('siso._kill_collector'),
            'time_sleep':
            mock.patch('siso.time.sleep'),
            'time_time':
            mock.patch('siso.time.time'),
            'http_connection':
            mock.patch('siso.http.client.HTTPConnection'),
            'subprocess_popen':
            mock.patch('siso.subprocess.Popen'),
        }
        mocks = {}
        for name, patcher in patchers.items():
            mocks[name] = patcher.start()
            self.patchers_to_stop.append(patcher)

        # Make time advance quickly to prevent test timeouts.
        mocks['time_time'].side_effect = (1000 + i * 0.1 for i in range(100))

        m = mock.MagicMock()
        for name, mocked in mocks.items():
            setattr(m, name, mocked)

        m.mock_conn = mock.Mock()
        m.http_connection.return_value = m.mock_conn

        return m

    def _configure_http_responses(self,
                                  mock_conn,
                                  status_responses,
                                  config_responses=None):
        if config_responses is None:
            config_responses = []

        request_path_history = []

        def request_side_effect(method, path):
            request_path_history.append(path)

        def getresponse_side_effect():
            path = request_path_history[-1]
            if path == '/health/status':
                if not status_responses:
                    return mock.Mock(status=404,
                                     read=mock.Mock(return_value=b''))
                status_code, _ = status_responses.pop(0)
                return mock.Mock(status=status_code,
                                 read=mock.Mock(return_value=b'')
                                 )  # Data will be handled by json_loads mock
            if path == '/health/config':
                if not config_responses:
                    return mock.Mock(status=200,
                                     read=mock.Mock(return_value=b'{}'))
                status_code, _ = config_responses.pop(0)
                return mock.Mock(status=status_code,
                                 read=mock.Mock(return_value=b'')
                                 )  # Data will be handled by json_loads mock
            return mock.Mock(status=404)

        mock_conn.request.side_effect = request_side_effect
        mock_conn.getresponse.side_effect = getresponse_side_effect

    def test_start_collector_subcommand_not_present(self):
        m = self._start_collector_mocks()
        siso_path = "siso_path"
        project = "test-project"
        result = siso._start_collector(siso_path, None, project)
        self.assertFalse(result)
        m.is_subcommand_present.assert_called_once_with(siso_path, 'collector')

    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso.json.loads')
    def test_start_collector_dead_then_healthy(self, mock_json_loads,
                                               _mock_system):
        m = self._start_collector_mocks()
        siso_path = "siso_path"
        project = "test-project"

        self._configure_http_responses(m.mock_conn,
                                       status_responses=[(404, None),
                                                         (200, None)],
                                       config_responses=[(200, None),
                                                         (200, None)])
        status_healthy = {'healthy': True, 'status': 'StatusOK'}
        config_project_full = {
            'exporters': {
                'googlecloud': {
                    'project': project
                }
            },
            'receivers': {
                'otlp': {
                    'protocols': {
                        'grpc': {
                            'endpoint': siso._OTLP_DEFAULT_TCP_ENDPOINT
                        }
                    }
                }
            }
        }
        mock_json_loads.side_effect = [
            status_healthy, config_project_full, config_project_full
        ]

        result = siso._start_collector(siso_path, None, project)

        self.assertTrue(result)
        m.subprocess_popen.assert_called_once_with(
            [siso_path, "collector", "--project", project],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            creationflags=0)
        m.kill_collector.assert_not_called()

    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso.json.loads')
    def test_start_collector_unhealthy_then_healthy(self, mock_json_loads,
                                                    _mock_system):
        m = self._start_collector_mocks()
        siso_path = "siso_path"
        project = "test-project"
        self._configure_http_responses(m.mock_conn,
                                       status_responses=[(200, None),
                                                         (200, None)],
                                       config_responses=[(200, None),
                                                         (200, None)])

        status_unhealthy = {'healthy': False, 'status': 'NotOK'}
        status_healthy = {'healthy': True, 'status': 'StatusOK'}
        config_project_full = {
            'exporters': {
                'googlecloud': {
                    'project': project
                }
            },
            'receivers': {
                'otlp': {
                    'protocols': {
                        'grpc': {
                            'endpoint': siso._OTLP_DEFAULT_TCP_ENDPOINT
                        }
                    }
                }
            }
        }
        mock_json_loads.side_effect = [
            status_unhealthy, status_healthy, config_project_full,
            config_project_full
        ]

        result = siso._start_collector(siso_path, None, project)

        self.assertTrue(result)
        m.subprocess_popen.assert_called_once_with(
            [siso_path, "collector", "--project", project],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            creationflags=0)
        m.kill_collector.assert_called_once()

    @mock.patch('siso.platform.system', return_value='Windows')
    @mock.patch('siso.json.loads')
    def test_start_collector_dead_then_healthy_windows(self, mock_json_loads,
                                                       _mock_system):
        m = self._start_collector_mocks()
        siso_path = "siso_path"
        project = "test-project"

        self._configure_http_responses(m.mock_conn,
                                       status_responses=[(404, None),
                                                         (200, None)],
                                       config_responses=[(200, None),
                                                         (200, None)])
        status_healthy = {'healthy': True, 'status': 'StatusOK'}
        config_project_full = {
            'exporters': {
                'googlecloud': {
                    'project': project
                }
            },
            'receivers': {
                'otlp': {
                    'protocols': {
                        'grpc': {
                            'endpoint': siso._OTLP_DEFAULT_TCP_ENDPOINT
                        }
                    }
                }
            }
        }
        mock_json_loads.side_effect = [
            status_healthy, config_project_full, config_project_full
        ]

        # On non-Windows platforms, subprocess.CREATE_NEW_PROCESS_GROUP does not exist.
        # We mock it here to make the test runnable on all platforms.
        with mock.patch('subprocess.CREATE_NEW_PROCESS_GROUP', 512,
                        create=True):
            result = siso._start_collector(siso_path, None, project)

            self.assertTrue(result)
            m.subprocess_popen.assert_called_once_with(
                [siso_path, "collector", "--project", project],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            m.kill_collector.assert_not_called()

    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso.json.loads')
    def test_start_collector_wrong_project_no_restart(self, mock_json_loads,
                                                        _mock_system):
        m = self._start_collector_mocks()
        siso_path = "siso_path"
        project = "test-project"
        self._configure_http_responses(m.mock_conn,
                                       status_responses=[(200, None),
                                                         (200, None)],
                                       config_responses=[(200, None),
                                                         (200, None)])

        status_healthy = {'healthy': True, 'status': 'StatusOK'}
        config_wrong_project_full = {
            'exporters': {
                'googlecloud': {
                    'project': 'wrong-project'
                }
            },
            'receivers': {
                'otlp': {
                    'protocols': {
                        'grpc': {
                            'endpoint': siso._OTLP_DEFAULT_TCP_ENDPOINT
                        }
                    }
                }
            }
        }
        mock_json_loads.side_effect = [
            status_healthy, config_wrong_project_full
        ]

        result = siso._start_collector(siso_path, None, project)

        self.assertTrue(result)
        m.subprocess_popen.assert_not_called()
        m.kill_collector.assert_not_called()

    @mock.patch('siso.json.loads')
    def test_start_collector_already_healthy(self, mock_json_loads):
        m = self._start_collector_mocks()
        siso_path = "siso_path"
        project = "test-project"
        self._configure_http_responses(m.mock_conn,
                                       status_responses=[(200, None)],
                                       config_responses=[(200, None),
                                                         (200, None)])

        status_healthy = {'healthy': True, 'status': 'StatusOK'}
        config_project_full = {
            'exporters': {
                'googlecloud': {
                    'project': project
                }
            },
            'receivers': {
                'otlp': {
                    'protocols': {
                        'grpc': {
                            'endpoint': siso._OTLP_DEFAULT_TCP_ENDPOINT
                        }
                    }
                }
            }
        }
        mock_json_loads.side_effect = [
            status_healthy, config_project_full, config_project_full
        ]

        result = siso._start_collector(siso_path, None, project)

        self.assertTrue(result)
        m.subprocess_popen.assert_not_called()
        m.kill_collector.assert_not_called()

    @mock.patch('siso.platform.system', return_value='Linux')
    def test_start_collector_never_healthy(self, _mock_system):
        m = self._start_collector_mocks()
        siso_path = "siso_path"
        project = "test-project"
        self._configure_http_responses(m.mock_conn,
                                       status_responses=[(404, None)])

        siso._start_collector(siso_path, None, project)

        m.subprocess_popen.assert_called_once_with(
            [siso_path, "collector", "--project", project],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            creationflags=0)
        m.kill_collector.assert_not_called()

    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso.json.loads')
    def test_start_collector_healthy_after_retries(self, mock_json_loads,
                                                   _mock_system):
        m = self._start_collector_mocks()
        siso_path = "siso_path"
        project = "test-project"
        self._configure_http_responses(m.mock_conn,
                                       status_responses=[(404, None), (404,
                                                                       None),
                                                         (404, None),
                                                         (200, None)],
                                       config_responses=[(200, None),
                                                         (200, None)])

        status_healthy = {'healthy': True, 'status': 'StatusOK'}
        config_project_full = {
            'exporters': {
                'googlecloud': {
                    'project': project
                }
            },
            'receivers': {
                'otlp': {
                    'protocols': {
                        'grpc': {
                            'endpoint': siso._OTLP_DEFAULT_TCP_ENDPOINT
                        }
                    }
                }
            }
        }
        mock_json_loads.side_effect = [
            status_healthy, config_project_full, config_project_full
        ]

        result = siso._start_collector(siso_path, None, project)

        self.assertTrue(result)
        m.subprocess_popen.assert_called_once_with(
            [siso_path, "collector", "--project", project],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            creationflags=0)
        m.kill_collector.assert_not_called()

    @mock.patch('siso.platform.system', return_value='Linux')
    @mock.patch('siso.json.loads')
    @mock.patch('os.path.isfile', return_value=False)
    @mock.patch('os.path.exists')
    @mock.patch('os.remove')
    def test_start_collector_with_sockets_file(self, mock_os_remove,
                                               mock_os_exists, mock_os_isfile,
                                               mock_json_loads, _mock_system):
        siso_path = "siso_path"
        project = "test-project"
        sockets_file = "/tmp/test-socket.sock"

        status_healthy = {'healthy': True, 'status': 'StatusOK'}
        config_with_socket = {
            'receivers': {
                'otlp': {
                    'protocols': {
                        'grpc': {
                            'endpoint': sockets_file
                        }
                    }
                }
            }
        }

        test_cases = {
            "socket_exists": {
                "os_path_exists_side_effect": itertools.repeat(True),
                "expected_result": True,
                "http_status_responses": [(404, None), (200, None)],
                "json_loads_side_effect": [status_healthy, config_with_socket],
                "expected_os_exists_calls": 2,
            },
            "appears_later": {
                "os_path_exists_side_effect": [False] * 8 + [True],
                "expected_result": True,
                "http_status_responses": [(404, None)] + [(200, None)] * 9,
                "json_loads_side_effect":
                [status_healthy, config_with_socket] * 9,
                "expected_os_exists_calls": 9,
            },
            "never_appears": {
                "os_path_exists_side_effect": [False] * 10,
                "expected_result": False,
                "http_status_responses": [(404, None)] + [(200, None)] * 9,
                "json_loads_side_effect":
                [status_healthy, config_with_socket] * 9,
                "expected_os_exists_calls": 10,
            },
        }

        for name, tc in test_cases.items():
            with self.subTest(name):
                m = self._start_collector_mocks()
                mock_os_exists.reset_mock()
                mock_os_exists.side_effect = tc["os_path_exists_side_effect"]
                mock_json_loads.reset_mock()
                mock_json_loads.side_effect = tc["json_loads_side_effect"]

                self._configure_http_responses(
                    m.mock_conn,
                    status_responses=list(tc["http_status_responses"]),
                    config_responses=[(200, None)] * 20)

                result = siso._start_collector(siso_path, sockets_file, project)

                self.assertEqual(result, tc["expected_result"])
                m.subprocess_popen.assert_called_once_with(
                    [
                        siso_path, "collector", "--project", project,
                        "--collector_address", f"unix://{sockets_file}"
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    creationflags=0)
                m.kill_collector.assert_not_called()
                self.assertEqual(mock_os_exists.call_count,
                                 tc["expected_os_exists_calls"])

if __name__ == '__main__':
    # Suppress print to console for unit tests.
    unittest.main(buffer=True)
