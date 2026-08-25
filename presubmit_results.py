#!/usr/bin/env python3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Result data types for presubmit checks."""

from dataclasses import asdict, dataclass
import os
import sys
import traceback
from typing import ClassVar, Optional

_SHOW_CALLSTACKS = False


def _ensure_str(val) -> str:
    """val: A "stringish" value. Can be any of str or bytes.
    returns: A str after applying encoding/decoding as needed.
    Assumes/uses UTF-8 for relevant inputs/outputs.
    """
    if isinstance(val, str):
        return val
    if isinstance(val, bytes):
        return val.decode()
    raise ValueError(f"Unknown string type {type(val)}")


# Top level object so multiprocessing can pickle
# Public access through OutputApi object.
@dataclass
class _PresubmitResultLocation:
    COMMIT_MSG_PATH: ClassVar[str] = "/COMMIT_MSG"
    # path to the file where errors/warnings are reported.
    #
    # path MUST either be COMMIT_MSG_PATH or relative to the repo root to
    # indicate the errors/warnings are against the commit message
    # (a.k.a cl description).
    file_path: str
    # The range in the file defined by (start_line, start_col) -
    # (end_line, end_col) where errors/warnings are reported.
    # The semantic are the same as Gerrit comment range:
    # https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html#comment-range
    #
    # To specify the entire line, make start_line == end_line and
    # start_col == end_col == 0.
    start_line: int = 0  # inclusive 1-based
    start_col: int = 0  # inclusive 0-based
    end_line: int = 0  # exclusive 1-based
    end_col: int = 0  # exclusive 0-based

    def validate(self):
        if not self.file_path:
            raise ValueError("file path is required")
        if self.file_path != self.COMMIT_MSG_PATH and os.path.isabs(
            self.file_path
        ):
            raise ValueError(
                f"file path must be relative path, got {self.file_path}"
            )
        if not self.start_line:
            if self.end_line:
                raise ValueError(
                    "end_line must be empty if start line is not specified"
                )
            if self.start_col:
                raise ValueError(
                    "start_col must be empty if start line is not specified"
                )
            if self.end_col:
                raise ValueError(
                    "end_col must be empty if start line is not specified"
                )
        elif self.start_line < 0:
            raise ValueError(
                f"start_line MUST not be negative, got {self.start_line}"
            )
        elif self.end_line < 1:
            raise ValueError(
                "start_line is specified so end_line must be "
                f"positive, got {self.end_line}"
            )
        elif self.start_col < 0:
            raise ValueError(
                f"start_col MUST not be negative, got {self.start_col}"
            )
        elif self.end_col < 0:
            raise ValueError(
                f"end_col MUST not be negative, got {self.end_col}"
            )
        elif self.start_line > self.end_line or (
            self.start_line == self.end_line
            and self.start_col > self.end_col
            and self.end_col > 0
        ):
            raise ValueError(
                "(start_line, start_col) must not be after (end_line, end_col"
                f"), got ({self.start_line}, {self.start_col}) .. "
                f"({self.end_line}, {self.end_col})"
            )


# Top level object so multiprocessing can pickle
# Public access through OutputApi object.
class _PresubmitResult:
    """Base class for result objects."""

    fatal = False
    should_prompt = False

    def __init__(
        self,
        message: str,
        items: Optional[list[str]] = None,
        long_text: str = "",
        locations: Optional[list[_PresubmitResultLocation]] = None,
        show_callstack: Optional[bool] = None,
    ):
        """Inits _PresubmitResult.

        Args:
            message: A short one-line message to indicate errors.
            items: A list of short strings to indicate where errors occurred.
                Note that if you are using this parameter to print where errors
                occurred, please use `locations` instead
            long_text: multi-line text output, e.g. from another tool
            locations: The locations indicate where the errors occurred.
        """
        self._message = _ensure_str(message)
        self._items = items or []
        self._long_text = _ensure_str(long_text.rstrip())
        self._locations = locations or []
        for loc in self._locations:
            loc.validate()
        if show_callstack is None:
            show_callstack = _SHOW_CALLSTACKS
        if show_callstack:
            if self._long_text:
                self._long_text += "\n"
            self._long_text += "Presubmit result call stack is:\n"
            self._long_text += "".join(traceback.format_stack(None, 8))

    _ensure_str = staticmethod(_ensure_str)

    def handle(self, out_file=None):
        if not out_file:
            out_file = sys.stdout
        out_file.write(self._message)
        out_file.write("\n")
        for item in self._items:
            out_file.write("  ")
            # Write separately in case it's unicode.
            out_file.write(str(item))
            out_file.write("\n")
        if self._locations:
            out_file.write("Found in:\n")
            for loc in self._locations:
                if loc.file_path == _PresubmitResultLocation.COMMIT_MSG_PATH:
                    out_file.write("  - Commit Message")
                else:
                    out_file.write(f"  - {loc.file_path}")
                if not loc.start_line:
                    pass
                elif loc.start_line == loc.end_line and (
                    loc.start_col == 0 and loc.end_col == 0
                ):
                    out_file.write(f" [Ln {loc.start_line}]")
                elif loc.start_col == 0 and loc.end_col == 0:
                    out_file.write(f" [Ln {loc.start_line} - {loc.end_line}]")
                else:
                    out_file.write(
                        f" [Ln {loc.start_line}, Col {loc.start_col}"
                        f" - Ln {loc.end_line}, Col {loc.end_col}]"
                    )
                out_file.write("\n")
        if self._long_text:
            out_file.write("\n***************\n")
            # Write separately in case it's unicode.
            out_file.write(self._long_text)
            out_file.write("\n***************\n")

    def json_format(self):
        return {
            "message": self._message,
            "items": [str(item) for item in self._items],
            "locations": [asdict(loc) for loc in self._locations],
            "long_text": self._long_text,
            "fatal": self.fatal,
        }


# Top level object so multiprocessing can pickle
# Public access through OutputApi object.
class _PresubmitError(_PresubmitResult):
    """A hard presubmit error."""

    fatal = True


# Top level object so multiprocessing can pickle
# Public access through OutputApi object.
class _PresubmitPromptWarning(_PresubmitResult):
    """A warning that prompts the user if they want to continue."""

    should_prompt = True


# Top level object so multiprocessing can pickle
# Public access through OutputApi object.
class _PresubmitNotifyResult(_PresubmitResult):
    """Just print something to the screen -- but it's not even a warning."""


# Top level object so multiprocessing can pickle
# Public access through OutputApi object.
class _MailTextResult(_PresubmitResult):
    """A warning that should be included in the review request email."""

    def __init__(self, *args, **kwargs):
        del args, kwargs
        raise NotImplementedError()
