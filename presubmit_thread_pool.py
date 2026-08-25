#!/usr/bin/env python3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Thread pool and subprocess execution subsystem for presubmit checks."""

import multiprocessing
import os
import queue
import signal
import subprocess2 as subprocess
import sys
import threading
import time
import traceback

from presubmit_results import (
    _PresubmitError,
    _PresubmitResult,
)


def time_time():
    """Returns the current time.

    Used so that it can be mocked in tests without interfering with python
    system machinery.
    """
    return time.time()


class CommandData:
    def __init__(
        self,
        name,
        cmd,
        kwargs,
        message=None,
        python3=True,
        output_parser=None,
    ):
        # The python3 argument is ignored but has to be retained because of the
        # many callers in other repos that pass it in.
        del python3
        self.name = name
        self.cmd = cmd
        self.stdin = kwargs.get("stdin", None)
        self.kwargs = kwargs.copy()
        self.kwargs["stdout"] = subprocess.PIPE
        self.kwargs["stderr"] = subprocess.STDOUT
        self.kwargs["stdin"] = subprocess.PIPE
        self.message = message
        self.output_parser = output_parser
        self.info = None
        assert output_parser or message
        if message:
            assert issubclass(message, _PresubmitResult)


# Adapted from
# https://github.com/google/gtest-parallel/blob/master/gtest_parallel.py#L37
#
# An object that catches SIGINT sent to the Python process and notices
# if processes passed to wait() die by SIGINT (we need to look for
# both of those cases, because pressing Ctrl+C can result in either
# the main process or one of the subprocesses getting the signal).
#
# Before a SIGINT is seen, wait(p) will simply call p.wait() and
# return the result. Once a SIGINT has been seen (in the main process
# or a subprocess, including the one the current call is waiting for),
# wait(p) will call p.terminate().
class SigintHandler:
    sigint_returncodes = {
        -signal.SIGINT,  # Unix
        -1073741510,  # Windows
    }

    def __init__(self):
        self.__lock = threading.Lock()
        self.__processes = set()
        self.__got_sigint = False
        self.__previous_signal = signal.signal(signal.SIGINT, self.interrupt)

    def __on_sigint(self):
        self.__got_sigint = True
        while self.__processes:
            try:
                self.__processes.pop().terminate()
            except OSError:
                pass

    def interrupt(self, signal_num, frame):
        with self.__lock:
            self.__on_sigint()
        self.__previous_signal(signal_num, frame)

    def got_sigint(self):
        with self.__lock:
            return self.__got_sigint

    def wait(self, p, stdin):
        with self.__lock:
            if self.__got_sigint:
                p.terminate()
            self.__processes.add(p)
        stdout, stderr = p.communicate(stdin)
        code = p.returncode
        with self.__lock:
            self.__processes.discard(p)
            if code in self.sigint_returncodes:
                self.__on_sigint()
        return stdout, stderr


sigint_handler = SigintHandler()


class Timer:
    def __init__(self, timeout, fn):
        self.completed = False
        self._fn = fn
        self._timer = (
            threading.Timer(timeout, self._onTimer) if timeout else None
        )

    def __enter__(self):
        if self._timer:
            self._timer.start()
        return self

    def __exit__(self, _type, _value, _traceback):
        if self._timer:
            self._timer.cancel()

    def _onTimer(self):
        self._fn()
        self.completed = True


class ThreadPool:
    def __init__(self, pool_size=None, timeout=None, default_error_type=None):
        self.timeout = timeout
        self.default_error_type = default_error_type
        self._pool_size = pool_size or multiprocessing.cpu_count()
        if sys.platform == "win32":
            # TODO(crbug.com/1190269) - we can't use more than 56 child
            # processes on Windows or Python3 may hang.
            self._pool_size = min(self._pool_size, 56)

        self._task_queue = queue.Queue()
        self._messages = []
        self._nonparallel_tests = []
        self._messages_lock = threading.Lock()
        self._workers = []
        self._cancel_event = threading.Event()
        self._active_tasks_lock = threading.Lock()
        self._active_tasks_count = 0
        self._tasks_drained_condition = threading.Condition(
            self._active_tasks_lock
        )
        self._active_processes = set()
        self._active_processes_lock = threading.Lock()
        self._deferred_cleanup_files = set()
        self._deferred_cleanup_dirs = []
        self._started = False
        self._start_lock = threading.Lock()
        self._in_context = False
        self._closed = False

    def __enter__(self):
        self._in_context = True
        self.Start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.Cancel()
            self.Close()
            self.Join()
            self.CleanupTemporaryFiles()
            self.CleanupTemporaryDirectories()
        finally:
            self._in_context = False

    def Start(self):
        with self._start_lock:
            if self._started:
                return
            self._started = True
            for i in range(self._pool_size):
                t = threading.Thread(
                    target=self._WorkerLoop,
                    name=f"PresubmitWorker-{i}",
                    daemon=True,
                )
                t.start()
                self._workers.append(t)

    def _WorkerLoop(self):
        while not self._cancel_event.is_set():
            try:
                test = self._task_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            # Sentinel poison pill for worker shutdown.
            if test is None:
                break

            try:
                if not self._cancel_event.is_set():
                    result = self.CallCommand(test, show_callstack=False)
                    if result:
                        with self._messages_lock:
                            if isinstance(result, (list, tuple)):
                                self._messages.extend(result)
                            else:
                                self._messages.append(result)
            except Exception:
                with self._messages_lock:
                    err_cls = self._GetErrorType(test)
                    self._messages.append(
                        err_cls(
                            f"Worker uncaught exception in {test.name}:\n"
                            f"{traceback.format_exc()}"
                        )
                    )
            finally:
                with self._active_tasks_lock:
                    self._active_tasks_count -= 1
                    if self._active_tasks_count == 0:
                        self._tasks_drained_condition.notify_all()

    def _GetCommand(self, test):
        vpython = "vpython3"
        if sys.platform == "win32":
            vpython += ".bat"

        cmd = test.cmd
        if cmd[0] == "python":
            cmd = list(cmd)
            cmd[0] = vpython
        elif cmd[0].endswith(".py"):
            cmd = [vpython] + cmd

        # On Windows, scripts on the current directory take precedence over
        # PATH, so that when testing depot_tools on Windows, calling
        # `vpython3.bat` will execute the copy of vpython of the depot_tools
        # under test instead of the one in the bot. As a workaround, we run the
        # tests from the parent directory instead.
        if (
            cmd[0] == vpython
            and "cwd" in test.kwargs
            and os.path.basename(test.kwargs["cwd"]) == "depot_tools"
        ):
            test.kwargs["cwd"] = os.path.dirname(test.kwargs["cwd"])
            cmd[1] = os.path.join("depot_tools", cmd[1])

        return cmd

    def _RunWithTimeout(self, cmd, stdin, kwargs):
        if self._cancel_event.is_set():
            return -1, "Canceled before execution"

        p = subprocess.Popen(cmd, **kwargs)
        with self._active_processes_lock:
            if self._cancel_event.is_set():
                try:
                    p.terminate()
                except OSError:
                    pass
            else:
                self._active_processes.add(p)

        try:
            with Timer(self.timeout, p.terminate) as timer:
                stdout, _ = sigint_handler.wait(p, stdin)
                stdout = stdout.decode("utf-8", "ignore")
                if timer.completed:
                    stdout = (
                        f"Process timed out after {self.timeout}s\n{stdout}"
                    )
                return p.returncode, stdout
        finally:
            with self._active_processes_lock:
                self._active_processes.discard(p)

    def _GetErrorType(self, test=None):
        if test and getattr(test, "message", None):
            return test.message
        if self.default_error_type:
            return self.default_error_type
        return _PresubmitError

    def CallCommand(self, test, show_callstack=None):
        """Runs an external program.

        This function converts invocation of .py files and invocations of 'python'
        to vpython invocations.
        """
        cmd = self._GetCommand(test)
        start = time_time()

        def error_results(msg, exception=""):
            duration = time_time() - start
            msg_type = self._GetErrorType(test)
            return msg_type(
                "%s\n%s %s (%4.2fs)\n%s"
                % (test.name, " ".join(cmd), msg, duration, exception),
                show_callstack=show_callstack,
            )

        try:
            returncode, stdout = self._RunWithTimeout(
                cmd, test.stdin, test.kwargs
            )
        except Exception:
            return error_results("exec failure", traceback.format_exc())

        if test.output_parser:
            try:
                results = test.output_parser(stdout)
                if results:
                    return results
            except Exception:
                return error_results(
                    f"Exception while parsing:\n{stdout}",
                    traceback.format_exc(),
                )

        if returncode != 0:
            return error_results(f"exit code {returncode}", stdout)

        if test.info:
            duration = time_time() - start
            return test.info(
                "%s\n%s (%4.2fs)" % (test.name, " ".join(cmd), duration),
                show_callstack=show_callstack,
            )

    def AddTests(self, tests, parallel=True):
        if self._closed:
            raise RuntimeError("Cannot add tests to a closed ThreadPool")
        if tests is None:
            return

        tests = list(tests)
        if not tests:
            return

        for test in tests:
            if getattr(test, "kwargs", None) is None:
                test.kwargs = {}
            if not test.kwargs.get("cwd"):
                test.kwargs["cwd"] = os.getcwd()
            test.kwargs["cwd"] = os.path.abspath(test.kwargs["cwd"])

        if parallel:
            self.Start()
            with self._active_tasks_lock:
                self._active_tasks_count += len(tests)
            for test in tests:
                self._task_queue.put(test)
        else:
            self._nonparallel_tests.extend(tests)

    def DrainInFlightParallelTasks(self):
        """Blocks until all active parallel background tasks have completed."""
        with self._active_tasks_lock:
            while (
                self._active_tasks_count > 0 and not self._cancel_event.is_set()
            ):
                self._tasks_drained_condition.wait(timeout=0.2)

    def RegisterTemporaryFiles(self, files):
        """Defers deletion of temporary files until ThreadPool shutdown."""
        self._deferred_cleanup_files.update(files)

    def CleanupTemporaryFiles(self):
        while self._deferred_cleanup_files:
            f = self._deferred_cleanup_files.pop()
            try:
                os.remove(f)
            except OSError:
                pass

    def RegisterTemporaryDirectories(self, dirs):
        """Defers cleanup of temporary directories until ThreadPool shutdown."""
        self._deferred_cleanup_dirs.extend(dirs)

    def CleanupTemporaryDirectories(self):
        while self._deferred_cleanup_dirs:
            d = self._deferred_cleanup_dirs.pop()
            try:
                d.cleanup()
            except OSError:
                pass

    def Cancel(self):
        """Signals cancellation to all workers and terminates child processes."""
        self._cancel_event.set()
        with self._active_processes_lock:
            while self._active_processes:
                proc = self._active_processes.pop()
                try:
                    proc.terminate()
                except OSError:
                    pass

        drained_count = 0
        while True:
            try:
                task = self._task_queue.get_nowait()
                if task is not None:
                    drained_count += 1
            except queue.Empty:
                break

        with self._active_tasks_lock:
            self._active_tasks_count = max(
                0, self._active_tasks_count - drained_count
            )
            self._tasks_drained_condition.notify_all()

    def Close(self):
        """Signals worker threads to exit once active tasks finish."""
        if self._closed:
            return
        self._closed = True
        for _ in self._workers:
            self._task_queue.put(None)

    def Join(self, timeout=None):
        """Waits for worker threads to terminate cleanly."""
        deadline = time_time() + timeout if timeout is not None else None
        for worker in self._workers:
            if not worker.is_alive():
                continue
            if deadline is not None:
                remaining = max(0.0, deadline - time_time())
                worker.join(timeout=remaining)
            else:
                worker.join()

    def RunAsync(self):
        # Drain all active parallel background tasks before running nonparallel tests.
        self.DrainInFlightParallelTasks()

        # Nonparallel tests run sequentially in LIFO order matching historical presubmit semantics.
        while self._nonparallel_tests and not self._cancel_event.is_set():
            test = self._nonparallel_tests.pop()
            result = self.CallCommand(test)
            if result:
                with self._messages_lock:
                    if isinstance(result, (list, tuple)):
                        self._messages.extend(result)
                    else:
                        self._messages.append(result)

        if not self._in_context:
            self.CleanupTemporaryFiles()
            self.CleanupTemporaryDirectories()

        with self._messages_lock:
            results = list(self._messages)
            self._messages = []
            return results
