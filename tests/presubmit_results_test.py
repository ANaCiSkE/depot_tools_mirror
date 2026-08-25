#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for presubmit_results.py."""

import os
import sys
import unittest
from unittest import mock

# Add parent directory to sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import presubmit_results  # noqa: E402


class PresubmitResultsTest(unittest.TestCase):
    def testPresubmitResultBasics(self):
        res = presubmit_results._PresubmitResult(
            "test message", ["item1", "item2"]
        )
        self.assertEqual("test message", res._message)
        self.assertEqual(["item1", "item2"], res._items)
        self.assertFalse(res.fatal)
        self.assertFalse(res.should_prompt)

    def testPresubmitError(self):
        err = presubmit_results._PresubmitError("error message")
        self.assertTrue(err.fatal)
        self.assertFalse(err.should_prompt)

    def testPresubmitPromptWarning(self):
        warn = presubmit_results._PresubmitPromptWarning("warning message")
        self.assertFalse(warn.fatal)
        self.assertTrue(warn.should_prompt)

    def testPresubmitNotifyResult(self):
        notify = presubmit_results._PresubmitNotifyResult("notify message")
        self.assertFalse(notify.fatal)
        self.assertFalse(notify.should_prompt)

    def testPresubmitResultLocationValidation(self):
        loc = presubmit_results._PresubmitResultLocation(
            file_path="foo/bar.py",
            start_line=1,
            end_line=5,
        )
        loc.validate()

        with self.assertRaises(ValueError):
            bad_loc = presubmit_results._PresubmitResultLocation(file_path="")
            bad_loc.validate()

    def testShowCallstacksDisabledByDefault(self):
        with mock.patch.object(presubmit_results, "_SHOW_CALLSTACKS", False):
            res = presubmit_results._PresubmitResult("msg")
            self.assertNotIn("Presubmit result call stack is:", res._long_text)

    def testShowCallstacksEnabled(self):
        with mock.patch.object(presubmit_results, "_SHOW_CALLSTACKS", True):
            res = presubmit_results._PresubmitResult("msg")
            self.assertIn("Presubmit result call stack is:", res._long_text)

    def testMailTextResultNotImplemented(self):
        with self.assertRaises(NotImplementedError):
            presubmit_results._MailTextResult("test message")

    def testEnsureStr(self):
        self.assertEqual("hello", presubmit_results._ensure_str("hello"))
        self.assertEqual("hello", presubmit_results._ensure_str(b"hello"))
        self.assertEqual(
            "hello", presubmit_results._PresubmitResult._ensure_str("hello")
        )
        with self.assertRaises(ValueError):
            presubmit_results._ensure_str(12345)

    def testShowCallstacksWithExistingLongText(self):
        with mock.patch.object(presubmit_results, "_SHOW_CALLSTACKS", True):
            res = presubmit_results._PresubmitResult(
                "msg", long_text="some long text"
            )
            self.assertTrue(
                res._long_text.startswith(
                    "some long text\nPresubmit result call stack is:\n"
                )
            )

    def testShowCallstacksWithEmptyLongText(self):
        with mock.patch.object(presubmit_results, "_SHOW_CALLSTACKS", True):
            res = presubmit_results._PresubmitResult("msg", long_text="")
            self.assertTrue(
                res._long_text.startswith("Presubmit result call stack is:\n")
            )


if __name__ == "__main__":
    unittest.main()
