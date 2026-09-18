# Copyright 2021 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
import fnmatch
import json
import logging
import os
import re
import subprocess
import presubmit_thread_pool
import sys

from presubmit_canned_checks import _ReportErrorFileAndLine
from presubmit_support import GetFileExtension, PathMatches


class MockCannedChecks(object):
    def _FindNewViolationsOfRule(
        self,
        callable_rule,
        input_api,
        source_file_filter=None,
        error_formatter=_ReportErrorFileAndLine,
    ):
        """Find all newly introduced violations of a per-line rule (a callable).

        Arguments:
            callable_rule: a callable taking a file extension and line of input
                and returning True if the rule is satisfied and False if there
                was a problem.
            input_api: object to enumerate the affected files.
            source_file_filter: a filter to be passed to the input api.
            error_formatter: a callable taking (filename, line_number, line)
                and returning a formatted error string.

        Returns:
            A list of the newly-introduced violations reported by the rule.
        """
        errors = []
        for f in input_api.AffectedFiles(
            include_deletes=False, file_filter=source_file_filter
        ):
            # For speed, we do two passes, checking first the full file.
            # Shelling out to the SCM to determine the changed region can be
            # quite expensive on Win32.  Assuming that most files will be kept
            # problem-free, we can skip the SCM operations most of the time.
            extension = str(f.LocalPath()).rsplit(".", 1)[-1]
            if all(callable_rule(extension, line) for line in f.NewContents()):
                # No violation found in full text: can skip considering diff.
                continue

            for line_num, line in f.ChangedContents():
                if not callable_rule(extension, line):
                    errors.append(
                        error_formatter(f.LocalPath(), line_num, line)
                    )

        return errors


class MockCommand(object):
    def __init__(
        self,
        name,
        cmd,
        kwargs,
        message=None,
        python3=True,
        output_parser=None,
    ):
        self.name = name
        self.cmd = cmd
        self.kwargs = kwargs
        self.message = message
        self.python3 = python3
        self.output_parser = output_parser


class MockInputApi(object):
    """Mock class for the InputApi class.

    This class can be used for unittests for presubmit by initializing the files
    attribute as the list of changed files.
    """

    DEFAULT_FILES_TO_SKIP = ()

    def __init__(self):
        self.canned_checks = MockCannedChecks()
        self.fnmatch = fnmatch
        self.json = json
        self.re = re
        self.os_path = os.path
        self.platform = sys.platform
        self.python_executable = sys.executable
        self.python3_executable = "vpython3"
        self.platform = sys.platform
        self.subprocess = subprocess
        self.sys = sys
        self.files = []
        self.is_committing = False
        self.no_diffs = False
        self.change = MockChange([])
        self.presubmit_local_path = os.path.dirname(__file__)
        self.logging = logging.getLogger("PRESUBMIT")
        self.Command = MockCommand

    @property
    def is_windows(self):
        return self.platform == "win32"

    def CreateMockFileInPath(self, f_list):
        self.os_path.exists = lambda x: x in f_list

    def AffectedFiles(self, file_filter=None, include_deletes=True):
        for file in self.files:
            if file_filter and not file_filter(file):
                continue
            if not include_deletes and file.Action() == "D":
                continue
            yield file

    def AffectedSourceFiles(self, file_filter=None):
        return self.AffectedFiles(file_filter=file_filter)

    def FilterSourceFile(
        self,
        file,
        files_to_check=(),
        files_to_skip=(),
    ):
        local_path = file.LocalPath()
        found_in_files_to_check = not files_to_check
        if files_to_check:
            if isinstance(files_to_check, str):
                raise TypeError(
                    "files_to_check should be an iterable of strings"
                )
            for pattern in files_to_check:
                compiled_pattern = re.compile(pattern)
                if compiled_pattern.search(local_path):
                    found_in_files_to_check = True
                    break
        if files_to_skip:
            if isinstance(files_to_skip, str):
                raise TypeError(
                    "files_to_skip should be an iterable of strings"
                )
            for pattern in files_to_skip:
                compiled_pattern = re.compile(pattern)
                if compiled_pattern.search(local_path):
                    return False
        return found_in_files_to_check

    def LocalPaths(self):
        return [file.LocalPath() for file in self.files]

    def _AffectedFilesInScope(self, include_deletes, recursive=True):
        presubmit_dir = os.path.normcase(
            os.path.normpath(self.PresubmitLocalPath())
        )
        presubmit_prefix = (
            presubmit_dir
            if presubmit_dir.endswith(os.path.sep)
            else presubmit_dir + os.path.sep
        )
        for f in self.AffectedFiles(include_deletes=include_deletes):
            abs_path = f.AbsoluteLocalPath()
            if not os.path.isabs(abs_path):
                abs_path = os.path.join(presubmit_dir, abs_path)
            abs_path = os.path.normcase(os.path.normpath(abs_path))
            if not recursive:
                if os.path.dirname(abs_path) == presubmit_dir:
                    yield abs_path
            else:
                if (
                    abs_path.startswith(presubmit_prefix)
                    or abs_path == presubmit_dir
                ):
                    yield abs_path

    def AffectedExtensions(self):
        exts = {
            GetFileExtension(abs_path)
            for abs_path in self._AffectedFilesInScope(include_deletes=True)
        }
        return frozenset(exts)

    def _HasAffectedExtensions(self, extensions, recursive, include_deletes):
        """Helper for HasAffectedFiles when filtering by file extensions."""
        if isinstance(extensions, str):
            extensions = [extensions]
        norm_exts = set()
        for ext in extensions:
            ext_str = ext.lower()
            if ext_str and not ext_str.startswith("."):
                ext_str = "." + ext_str
            norm_exts.add(ext_str)
        extensions = frozenset(norm_exts)

        # Fast path when checking extensions under current presubmit directory
        if recursive and include_deletes:
            return bool(self.AffectedExtensions().intersection(extensions))

        for abs_path in self._AffectedFilesInScope(include_deletes, recursive):
            if GetFileExtension(abs_path) in extensions:
                return True
        return False

    def _HasAffectedPaths(self, path, recursive, include_deletes):
        """Helper for HasAffectedFiles when filtering by paths."""
        if isinstance(path, str):
            paths = [path]
        else:
            paths = list(path)

        presubmit_dir = os.path.normcase(
            os.path.normpath(self.PresubmitLocalPath())
        )
        resolved_targets = []
        for p in paths:
            if not os.path.isabs(p):
                p = os.path.join(presubmit_dir, p)
            target = os.path.normcase(os.path.normpath(p))
            prefix = (
                target if target.endswith(os.path.sep) else target + os.path.sep
            )
            resolved_targets.append((target, prefix))

        for abs_path in self._AffectedFilesInScope(
            include_deletes, recursive=True
        ):
            if any(
                PathMatches(abs_path, target, prefix, recursive)
                for target, prefix in resolved_targets
            ):
                return True
        return False

    def HasAffectedFiles(
        self,
        *,
        extensions=None,
        path=None,
        recursive=True,
        include_deletes=True,
    ):
        """Returns True if any affected file matches the specified criteria.

        Must specify exactly one of 'extensions' (to match files by extension
        under the current presubmit directory) or 'path' (to match a directory,
        file, or list of paths). They are mutually exclusive.

        Args:
            extensions: A file extension (e.g. '.py') or sequence of
                extensions (e.g. ('.py', '.gn')). Case-insensitive. Leading dot
                is optional.
            path: A directory or file path (or sequence of paths) to check.
                Paths can be relative to PresubmitLocalPath() or absolute
                (must still reside within the current presubmit directory
                scope, as AffectedFiles() is intrinsically scoped).
            recursive: If True (default), checks files in path and any
                subdirectories. If False, checks only direct children of path.
            include_deletes: If True (default), includes deleted files.
        """
        if (extensions is None) == (path is None):
            raise ValueError(
                "Must specify exactly one of 'extensions' or 'path' to "
                "HasAffectedFiles()."
            )

        if extensions is not None:
            return self._HasAffectedExtensions(
                extensions, recursive, include_deletes
            )

        return self._HasAffectedPaths(path, recursive, include_deletes)

    def PresubmitLocalPath(self):
        return self.presubmit_local_path

    def ReadFile(self, filename, mode="rU"):
        if hasattr(filename, "AbsoluteLocalPath"):
            filename = filename.AbsoluteLocalPath()
        for file_ in self.files:
            if file_.LocalPath() == filename:
                return "\n".join(file_.NewContents())
        # Otherwise, file is not in our mock API.
        raise IOError("No such file or directory: '%s'" % filename)

    def RunTests(self, tests, parallel=True, output_parser=None):
        results = []
        for test in tests:
            parser = test.output_parser or output_parser
            try:
                kwargs = test.kwargs.copy()
                stdin_data = kwargs.get("stdin", None)
                if isinstance(stdin_data, bytes):
                    kwargs["stdin"] = self.subprocess.PIPE
                if parser and presubmit_thread_pool.AcceptsStderr(parser):
                    kwargs["stderr"] = self.subprocess.PIPE
                p = self.subprocess.Popen(test.cmd, **kwargs)
                stdout, stderr = p.communicate(
                    input=stdin_data if isinstance(stdin_data, bytes) else None
                )
                stdout_str = (
                    stdout.decode()
                    if isinstance(stdout, bytes)
                    else (stdout or "")
                )
                stderr_str = (
                    stderr.decode()
                    if isinstance(stderr, bytes)
                    else (stderr or "")
                )
                if parser:
                    handled, parse_results = (
                        presubmit_thread_pool.InvokeOutputParser(
                            parser, p.returncode, stdout_str, stderr_str
                        )
                    )
                    if handled:
                        if isinstance(parse_results, (list, tuple)):
                            results.extend(parse_results)
                        elif parse_results:
                            results.append(parse_results)
                        continue

                if p.returncode:
                    msg_type = test.message or MockOutputApi.PresubmitError
                    out_msg = presubmit_thread_pool.CombineOutput(
                        stdout_str, stderr_str
                    )
                    results.append(msg_type(f"{test.name}\n{out_msg}"))
            except Exception as e:
                msg_type = test.message or MockOutputApi.PresubmitError
                results.append(
                    msg_type(f"Unexpected error in {test.name}: {e}")
                )
        return results


class MockOutputApi(object):
    """Mock class for the OutputApi class.

    An instance of this class can be passed to presubmit unittests for outputing
    various types of results.
    """

    class PresubmitResult(object):
        def __init__(self, message, items=None, long_text=""):
            self.message = message
            self.items = items
            self.long_text = long_text

        def __repr__(self):
            return self.message

    class PresubmitError(PresubmitResult):
        def __init__(self, message, items=None, long_text=""):
            MockOutputApi.PresubmitResult.__init__(
                self, message, items, long_text
            )
            self.type = "error"

    class PresubmitPromptWarning(PresubmitResult):
        def __init__(self, message, items=None, long_text=""):
            MockOutputApi.PresubmitResult.__init__(
                self, message, items, long_text
            )
            self.type = "warning"

    class PresubmitNotifyResult(PresubmitResult):
        def __init__(self, message, items=None, long_text=""):
            MockOutputApi.PresubmitResult.__init__(
                self, message, items, long_text
            )
            self.type = "notify"

    class PresubmitPromptOrNotify(PresubmitResult):
        def __init__(self, message, items=None, long_text=""):
            MockOutputApi.PresubmitResult.__init__(
                self, message, items, long_text
            )
            self.type = "promptOrNotify"

    def __init__(self):
        self.more_cc = []

    def AppendCC(self, more_cc):
        self.more_cc.extend(more_cc)


class MockFile(object):
    """Mock class for the File class.

    This class can be used to form the mock list of changed files in
    MockInputApi for presubmit unittests.
    """

    def __init__(
        self,
        local_path,
        new_contents,
        old_contents=None,
        action="A",
        scm_diff=None,
    ):
        self._local_path = local_path
        self._new_contents = new_contents
        self._changed_contents = [
            (i + 1, l)
            for i, l in enumerate(new_contents)  # noqa: E741
        ]
        self._action = action
        if scm_diff:
            self._scm_diff = scm_diff
        else:
            self._scm_diff = "--- /dev/null\n+++ %s\n@@ -0,0 +1,%d @@\n" % (
                local_path,
                len(new_contents),
            )
            for l in new_contents:  # noqa: E741
                self._scm_diff += "+%s\n" % l
        self._old_contents = old_contents

    def Action(self):
        return self._action

    def ChangedContents(self):
        return self._changed_contents

    def NewContents(self):
        return self._new_contents

    def LocalPath(self):
        return self._local_path

    def AbsoluteLocalPath(self):
        return self._local_path

    def GenerateScmDiff(self):
        return self._scm_diff

    def OldContents(self):
        return self._old_contents

    def rfind(self, p):
        """os.path.basename is used on MockFile so we need an rfind method."""
        return self._local_path.rfind(p)

    def __getitem__(self, i):
        """os.path.basename is used on MockFile so we need a get method."""
        return self._local_path[i]

    def __len__(self):
        """os.path.basename is used on MockFile so we need a len method."""
        return len(self._local_path)

    def replace(self, altsep, sep):
        """os.path.basename is used on MockFile so we need a replace method."""
        return self._local_path.replace(altsep, sep)


class MockAffectedFile(MockFile):
    def AbsoluteLocalPath(self):
        return self._local_path


class MockChange(object):
    """Mock class for Change class.

    This class can be used in presubmit unittests to mock the query of the
    current change.
    """

    def __init__(self, changed_files, description="", issue=0):
        self._changed_files = changed_files
        self.footers = defaultdict(list)
        self._description = description
        self.issue = issue

    def LocalPaths(self):
        return self._changed_files

    def AffectedFiles(
        self, include_dirs=False, include_deletes=True, file_filter=None
    ):
        return self._changed_files

    def GitFootersFromDescription(self):
        return self.footers

    def DescriptionText(self):
        return self._description

    def AffectedSubmodules(self):
        return []

    def AllLocalSubmodules(self):
        return set()

    def UpstreamBranch(self):
        return None
