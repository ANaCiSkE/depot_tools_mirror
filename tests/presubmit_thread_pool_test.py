#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for presubmit_thread_pool.py."""

import os
import sys
import unittest
from unittest import mock

# Add parent directory to sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import presubmit_results  # noqa: E402
import presubmit_thread_pool  # noqa: E402
import subprocess2  # noqa: E402


class ThreadPoolTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        mock.patch.object(subprocess2, "Popen").start()
        mock.patch.object(presubmit_thread_pool, "sigint_handler").start()
        mock.patch.object(
            presubmit_thread_pool, "time_time", return_value=0
        ).start()
        presubmit_thread_pool.sigint_handler.wait.return_value = (b"stdout", "")
        self.addCleanup(mock.patch.stopall)

    def testSurfaceExceptions(self):
        def FakePopen(cmd, **kwargs):
            if cmd[0] == "3":
                raise TypeError("TypeError")
            if cmd[0] == "4":
                raise OSError("OSError")
            if cmd[0] == "5":
                return mock.Mock(returncode=1)
            return mock.Mock(returncode=0)

        subprocess2.Popen.side_effect = FakePopen

        mock_tests = [
            presubmit_thread_pool.CommandData(
                name=str(i),
                cmd=[str(i)],
                kwargs={},
                message=presubmit_results._PresubmitError,
            )
            for i in range(10)
        ]

        t = presubmit_thread_pool.ThreadPool(1)
        t.AddTests(mock_tests)
        messages = sorted(t.RunAsync(), key=lambda x: x._message)

        self.assertEqual(3, len(messages))
        self.assertIn(
            "3\n3 exec failure (0.00s)\nTraceback (most recent call last):",
            messages[0]._message,
        )
        self.assertIn(
            "4\n4 exec failure (0.00s)\nTraceback (most recent call last):",
            messages[1]._message,
        )
        self.assertEqual(
            "5\n5 exit code 1 (0.00s)\nstdout", messages[2]._message
        )

    def testOutputParser(self):
        def FakePopen(cmd, **kwargs):
            if cmd[0] == "multiple":
                return mock.Mock(returncode=0)
            if cmd[0] == "empty_pass":
                return mock.Mock(returncode=0)
            if cmd[0] == "empty_fail":
                return mock.Mock(returncode=1)
            return mock.Mock(returncode=0)

        subprocess2.Popen.side_effect = FakePopen

        def parse_multiple(output):
            return [
                presubmit_results._PresubmitError("error 1"),
                presubmit_results._PresubmitError("error 2"),
                presubmit_results._PresubmitPromptWarning("warning 1"),
            ]

        def parse_empty(output):
            return []

        mock_tests = [
            presubmit_thread_pool.CommandData(
                name="multiple",
                cmd=["multiple"],
                kwargs={},
                output_parser=parse_multiple,
            ),
            presubmit_thread_pool.CommandData(
                name="empty_pass",
                cmd=["empty_pass"],
                kwargs={},
                output_parser=parse_empty,
            ),
            presubmit_thread_pool.CommandData(
                name="empty_fail",
                cmd=["empty_fail"],
                kwargs={},
                message=presubmit_results._PresubmitError,
                output_parser=parse_empty,
            ),
        ]

        t = presubmit_thread_pool.ThreadPool(1)
        t.AddTests(mock_tests)
        messages = t.RunAsync()
        message_strs = [r._message for r in messages]

        self.assertEqual(4, len(messages))
        self.assertIn(
            "empty_fail\nempty_fail exit code 1 (0.00s)\nstdout", message_strs
        )
        self.assertIn("error 1", message_strs)
        self.assertIn("error 2", message_strs)
        self.assertIn("warning 1", message_strs)

    @mock.patch("threading.Thread")
    def testWorkerThreadsSpawnedAsDaemon(self, mock_thread):
        mock_thread_instance = mock.Mock()
        mock_thread.return_value = mock_thread_instance

        mock_test = presubmit_thread_pool.CommandData(
            name="test",
            cmd=["test"],
            kwargs={},
            message=presubmit_results._PresubmitError,
        )
        t = presubmit_thread_pool.ThreadPool(pool_size=2)
        t.AddTests([mock_test])
        t.RunAsync()

        self.assertTrue(mock_thread.called)
        for call in mock_thread.call_args_list:
            self.assertTrue(call.kwargs.get("daemon"))


if __name__ == "__main__":
    unittest.main()
