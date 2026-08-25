#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for presubmit_thread_pool.py."""

import os
import sys
import threading
import unittest
from unittest import mock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

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
        with presubmit_thread_pool.ThreadPool(pool_size=2) as t:
            t.AddTests([mock_test], parallel=True)

        self.assertTrue(mock_thread.called)
        for call in mock_thread.call_args_list:
            self.assertTrue(call.kwargs.get("daemon"))

    def testEagerExecutionBeforeRunAsync(self):
        started_event = threading.Event()
        release_event = threading.Event()

        def SlowPopen(cmd, **kwargs):
            started_event.set()
            release_event.wait(timeout=5.0)
            return mock.Mock(returncode=0)

        mock_test = presubmit_thread_pool.CommandData(
            name="eager_test",
            cmd=["eager_cmd"],
            kwargs={},
            message=presubmit_results._PresubmitError,
        )

        with mock.patch.object(subprocess2, "Popen", side_effect=SlowPopen):
            with presubmit_thread_pool.ThreadPool(1) as t:
                t.AddTests([mock_test], parallel=True)
                # Verify the worker started the command eagerly BEFORE RunAsync is called.
                self.assertTrue(started_event.wait(timeout=2.0))
                release_event.set()
                messages = t.RunAsync()
                self.assertEqual([], messages)

    def testBarrierNonparallelOrdering(self):
        execution_order = []

        def FakePopen(cmd, **kwargs):
            if cmd[0] == "parallel_task":
                import time as py_time

                py_time.sleep(0.05)
                execution_order.append("parallel")
            elif cmd[0] == "sequential_task":
                execution_order.append("sequential")
            return mock.Mock(returncode=0)

        test_parallel = presubmit_thread_pool.CommandData(
            name="parallel",
            cmd=["parallel_task"],
            kwargs={},
            message=presubmit_results._PresubmitError,
        )
        test_seq = presubmit_thread_pool.CommandData(
            name="sequential",
            cmd=["sequential_task"],
            kwargs={},
            message=presubmit_results._PresubmitError,
        )

        with mock.patch.object(subprocess2, "Popen", side_effect=FakePopen):
            with presubmit_thread_pool.ThreadPool(2) as t:
                t.AddTests([test_parallel], parallel=True)
                t.AddTests([test_seq], parallel=False)
                t.RunAsync()

        # Non-parallel test should execute only after the barrier drains parallel tasks
        self.assertEqual(["parallel", "sequential"], execution_order)

    def testContextManagerDeferredTempFileCleanup(self):
        with mock.patch("os.remove") as mock_remove:
            with presubmit_thread_pool.ThreadPool(1) as t:
                t.RegisterTemporaryFiles(
                    ["fake_file_1.txt", "fake_file_2.txt", "fake_file_1.txt"]
                )
                mock_remove.assert_not_called()

            # Using a set guarantees deduplication
            self.assertEqual(2, mock_remove.call_count)
            mock_remove.assert_has_calls(
                [mock.call("fake_file_1.txt"), mock.call("fake_file_2.txt")],
                any_order=True,
            )

    def testAbsoluteCwdNormalization(self):
        captured_kwargs = []

        def FakePopen(cmd, **kwargs):
            captured_kwargs.append(kwargs)
            return mock.Mock(returncode=0)

        mock_test = presubmit_thread_pool.CommandData(
            name="cwd_test",
            cmd=["test_cmd"],
            kwargs={"cwd": "."},
            message=presubmit_results._PresubmitError,
        )

        with mock.patch.object(subprocess2, "Popen", side_effect=FakePopen):
            with presubmit_thread_pool.ThreadPool(1) as t:
                t.AddTests([mock_test], parallel=True)
                t.RunAsync()

        self.assertEqual(1, len(captured_kwargs))
        self.assertTrue(os.path.isabs(captured_kwargs[0]["cwd"]))

    def testCancelTerminatesActiveSubprocesses(self):
        started_event = threading.Event()
        mock_proc = mock.Mock()

        def FakeWait(p, stdin):
            started_event.set()
            while not mock_proc.terminate.called:
                import time as py_time

                py_time.sleep(0.01)
            return b"stdout", b""

        mock_test = presubmit_thread_pool.CommandData(
            name="hanging_test",
            cmd=["hanging_cmd"],
            kwargs={},
            message=presubmit_results._PresubmitError,
        )

        with mock.patch.object(
            presubmit_thread_pool.sigint_handler, "wait", side_effect=FakeWait
        ):
            with mock.patch.object(
                subprocess2, "Popen", return_value=mock_proc
            ):
                t = presubmit_thread_pool.ThreadPool(1)
                t.AddTests([mock_test], parallel=True)
                self.assertTrue(started_event.wait(timeout=2.0))
                t.Cancel()
                mock_proc.terminate.assert_called_once()
                t.Close()
                t.Join(timeout=0.5)

    def testStandaloneThreadPoolReusableAcrossMultipleRuns(self):
        """Tests that standalone ThreadPool can process multiple AddTests + RunAsync batches."""
        mock_test1 = presubmit_thread_pool.CommandData(
            name="test1",
            cmd=["test1"],
            kwargs={},
            message=presubmit_results._PresubmitError,
        )
        mock_test2 = presubmit_thread_pool.CommandData(
            name="test2",
            cmd=["test2"],
            kwargs={},
            message=presubmit_results._PresubmitError,
        )

        with mock.patch.object(
            subprocess2, "Popen", return_value=mock.Mock(returncode=0)
        ):
            t = presubmit_thread_pool.ThreadPool(2)
            try:
                t.AddTests([mock_test1], parallel=True)
                messages1 = t.RunAsync()
                self.assertEqual([], messages1)

                t.AddTests([mock_test2], parallel=True)
                messages2 = t.RunAsync()
                self.assertEqual([], messages2)
            finally:
                t.Close()
                t.Join(timeout=0.5)

    def testAddTestsAcceptsGenerator(self):
        """Tests that AddTests correctly consumes single-pass iterables / generators."""
        mock_tests = (
            presubmit_thread_pool.CommandData(
                name=f"gen_{i}",
                cmd=[f"cmd_{i}"],
                kwargs={},
                message=presubmit_results._PresubmitError,
            )
            for i in range(3)
        )

        with mock.patch.object(
            subprocess2, "Popen", return_value=mock.Mock(returncode=0)
        ):
            with presubmit_thread_pool.ThreadPool(2) as t:
                t.AddTests(mock_tests, parallel=True)
                messages = t.RunAsync()
                self.assertEqual([], messages)

    def testConcurrentAddTestsThreadSafe(self):
        """Tests that concurrent calls to AddTests start workers safely without duplicates."""
        t = presubmit_thread_pool.ThreadPool(pool_size=4)

        def AddBatch(idx):
            test = presubmit_thread_pool.CommandData(
                name=f"thread_{idx}",
                cmd=[f"cmd_{idx}"],
                kwargs={},
                message=presubmit_results._PresubmitError,
            )
            t.AddTests([test], parallel=True)

        threads = [
            threading.Thread(target=AddBatch, args=(i,)) for i in range(10)
        ]
        with mock.patch.object(
            subprocess2, "Popen", return_value=mock.Mock(returncode=0)
        ):
            try:
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()

                self.assertEqual(4, len(t._workers))
                messages = t.RunAsync()
                self.assertEqual([], messages)
            finally:
                t.Close()
                t.Join(timeout=0.5)

    def testNonparallelCwdNormalization(self):
        """Tests that cwd normalization occurs at AddTests time for nonparallel tests too."""
        captured_kwargs = []

        def FakePopen(cmd, **kwargs):
            captured_kwargs.append(kwargs)
            return mock.Mock(returncode=0)

        mock_test = presubmit_thread_pool.CommandData(
            name="nonparallel_cwd_test",
            cmd=["test_cmd"],
            kwargs={"cwd": "."},
            message=presubmit_results._PresubmitError,
        )

        with mock.patch.object(subprocess2, "Popen", side_effect=FakePopen):
            t = presubmit_thread_pool.ThreadPool(1)
            t.AddTests([mock_test], parallel=False)
            t.RunAsync()

        self.assertEqual(1, len(captured_kwargs))
        self.assertTrue(os.path.isabs(captured_kwargs[0]["cwd"]))

    def testAddEmptyGeneratorDoesNotStartWorkers(self):
        """Tests that passing an empty generator does not spawn worker threads."""
        empty_gen = (x for x in [])
        t = presubmit_thread_pool.ThreadPool(pool_size=4)
        try:
            t.AddTests(empty_gen, parallel=True)
            self.assertFalse(t._started)
            self.assertEqual(0, len(t._workers))
        finally:
            t.Close()
            t.Join(timeout=0.5)

    def testCancelNotifiesDrainingConditionAndDecrementsCount(self):
        """Tests that Cancel() decrements active task count and notifies drained condition immediately."""
        mock_proc = mock.Mock()
        started_event = threading.Event()

        def FakeWait(p, stdin):
            started_event.set()
            while not mock_proc.terminate.called:
                import time as py_time

                py_time.sleep(0.01)
            return b"stdout", b""

        tests = [
            presubmit_thread_pool.CommandData(
                name=f"task_{i}",
                cmd=[f"cmd_{i}"],
                kwargs={},
                message=presubmit_results._PresubmitError,
            )
            for i in range(5)
        ]

        with mock.patch.object(
            presubmit_thread_pool.sigint_handler, "wait", side_effect=FakeWait
        ):
            with mock.patch.object(
                subprocess2, "Popen", return_value=mock_proc
            ):
                t = presubmit_thread_pool.ThreadPool(pool_size=1)
                try:
                    t.AddTests(tests, parallel=True)
                    self.assertTrue(started_event.wait(timeout=2.0))
                    self.assertEqual(5, t._active_tasks_count)

                    t.Cancel()
                    # After cancel, queued tasks should be drained and count decremented
                    self.assertEqual(1, t._active_tasks_count)
                    self.assertTrue(t._task_queue.empty())
                finally:
                    t.Close()
                    t.Join(timeout=0.5)

    def testAddTestsAfterCloseRaisesRuntimeError(self):
        """Tests that AddTests raises RuntimeError if the ThreadPool has already been closed."""
        t = presubmit_thread_pool.ThreadPool(1)
        t.Close()
        test = presubmit_thread_pool.CommandData(
            name="test",
            cmd=["cmd"],
            kwargs={},
            message=presubmit_results._PresubmitError,
        )
        with self.assertRaises(RuntimeError):
            t.AddTests([test])

    def testCancelAfterCloseDoesNotDecrementPoisonPills(self):
        """Tests that Cancel() ignores None poison pills in queue accounting."""
        t = presubmit_thread_pool.ThreadPool(pool_size=2)
        try:
            # Enqueue poison pills via Close()
            t.Close()
            # Calling Cancel() after Close() should not cause active task count to go negative
            t.Cancel()
            self.assertEqual(0, t._active_tasks_count)
        finally:
            t.Join(timeout=0.5)

    def testNonparallelLoopExitsImmediatelyOnCancel(self):
        """Tests that nonparallel task execution halts immediately when canceled."""
        t = presubmit_thread_pool.ThreadPool(1)
        executed = []

        def FakePopen(cmd, **kwargs):
            executed.append(cmd[0])
            return mock.Mock(returncode=0)

        test1 = presubmit_thread_pool.CommandData(
            name="seq1",
            cmd=["seq1"],
            kwargs={},
            message=presubmit_results._PresubmitError,
        )
        test2 = presubmit_thread_pool.CommandData(
            name="seq2",
            cmd=["seq2"],
            kwargs={},
            message=presubmit_results._PresubmitError,
        )
        t.AddTests([test1, test2], parallel=False)
        t.Cancel()

        with mock.patch.object(subprocess2, "Popen", side_effect=FakePopen):
            t.RunAsync()

        # When canceled, no nonparallel tests should be executed
        self.assertEqual([], executed)

    def testRegisterAndCleanupTemporaryDirectories(self):
        mock_dir1 = mock.Mock()
        mock_dir2 = mock.Mock()
        t = presubmit_thread_pool.ThreadPool(pool_size=1)
        t.RegisterTemporaryDirectories([mock_dir1, mock_dir2])
        t.CleanupTemporaryDirectories()
        mock_dir1.cleanup.assert_called_once()
        mock_dir2.cleanup.assert_called_once()
        self.assertEqual([], t._deferred_cleanup_dirs)


if __name__ == "__main__":
    unittest.main()
