#!/usr/bin/env python3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Thread pool and subprocess management primitives for presubmit checks."""

import multiprocessing
import os
import signal
import sys
import threading
import time
import traceback

import subprocess2 as subprocess

from presubmit_results import (
    _PresubmitError,
    _PresubmitResult,
)


def time_time():
    # Use this so that it can be mocked in tests without interfering with python
    # system machinery.
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
        self.info = None
        self.output_parser = output_parser

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
    def __init__(self, pool_size=None, timeout=None):
        self.timeout = timeout
        self._pool_size = pool_size or multiprocessing.cpu_count()
        if sys.platform == "win32":
            # TODO(crbug.com/1190269) - we can't use more than 56 child
            # processes on Windows or Python3 may hang.
            self._pool_size = min(self._pool_size, 56)
        self._messages = []
        self._messages_lock = threading.Lock()
        self._tests = []
        self._tests_lock = threading.Lock()
        self._nonparallel_tests = []

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
        p = subprocess.Popen(cmd, **kwargs)
        with Timer(self.timeout, p.terminate) as timer:
            stdout, _ = sigint_handler.wait(p, stdin)
            stdout = stdout.decode("utf-8", "ignore")
            if timer.completed:
                stdout = f"Process timed out after {self.timeout}s\n{stdout}"
            return p.returncode, stdout

    def CallCommand(self, test, show_callstack=None):
        """Runs an external program.

        This function converts invocation of .py files and invocations of 'python'
        to vpython invocations.
        """
        cmd = self._GetCommand(test)
        start = time_time()

        def error_results(msg, exception=""):
            duration = time_time() - start
            msg_type = test.message or _PresubmitError
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
        if parallel:
            self._tests.extend(tests)
        else:
            self._nonparallel_tests.extend(tests)

    def RunAsync(self):
        self._messages = []

        def _WorkerFn():
            while True:
                test = None
                with self._tests_lock:
                    if not self._tests:
                        break
                    test = self._tests.pop()
                result = self.CallCommand(test, show_callstack=False)
                if result:
                    with self._messages_lock:
                        if isinstance(result, (list, tuple)):
                            self._messages.extend(result)
                        else:
                            self._messages.append(result)

        def _StartDaemon():
            t = threading.Thread(target=_WorkerFn, daemon=True)
            t.start()
            return t

        while self._nonparallel_tests:
            test = self._nonparallel_tests.pop()
            result = self.CallCommand(test)
            if result:
                if isinstance(result, (list, tuple)):
                    self._messages.extend(result)
                else:
                    self._messages.append(result)

        if self._tests:
            threads = [_StartDaemon() for _ in range(self._pool_size)]
            for worker in threads:
                worker.join()

        return self._messages
