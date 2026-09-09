#!/usr/bin/env python3
# Copyright 2021 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import io
import os.path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from testing_support.presubmit_canned_checks_test_mocks import (  # noqa: E402
    MockFile,
    MockAffectedFile,
    MockInputApi,
    MockOutputApi,
    MockChange,
)

import presubmit_canned_checks  # noqa: E402
import run_alint  # noqa: E402


class InclusiveLanguageCheckTest(unittest.TestCase):
    def testBlockedTerms(self):
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: ""
        input_api.presubmit_local_path = ""

        input_api.files = [
            MockFile(
                os.path.normpath(
                    "infra/inclusive_language_presubmit_exempt_dirs.txt"
                ),
                [
                    "some/dir 2 1",
                    "some/other/dir 2 1",
                ],
            ),
            MockFile(
                os.path.normpath("some/ios/file.mm"),
                [
                    "TEST(SomeClassTest, SomeInteraction, blacklist) {",  # nocheck
                    "}",
                ],
            ),
            MockFile(
                os.path.normpath("some/mac/file.mm"),
                [
                    "TEST(SomeClassTest, SomeInteraction, BlackList) {",  # nocheck
                    "}",
                ],
            ),
            MockFile(
                os.path.normpath("another/ios_file.mm"),
                ["class SomeTest : public testing::Test blocklist {};"],
            ),
            MockFile(
                os.path.normpath("some/ios/file_egtest.mm"),
                ["- (void)testSomething { V(whitelist); }"],
            ),  # nocheck
            MockFile(
                os.path.normpath("some/ios/file_unittest.mm"),
                ["TEST_F(SomeTest, Whitelist) { V(allowlist); }"],
            ),  # nocheck
            MockFile(
                os.path.normpath("some/doc/file.md"),
                [
                    "# Title",
                    "Some markdown text includes master.",  # nocheck
                ],
            ),
            MockFile(
                os.path.normpath("some/doc/ok_file.md"),
                [
                    "# Title",
                    # This link contains a '//' which the matcher thinks is a
                    # C-style comment, and the 'master' term appears after the
                    # '//' in the URL, so it gets ignored as a side-effect.
                    "[Ignored](https://git/project.git/+/master/foo)",  # nocheck
                ],
            ),
            MockFile(
                os.path.normpath("some/doc/branch_name_file.md"),
                [
                    "# Title",
                    # Matches appearing before `//` still trigger the check.
                    "[src/master](https://git/p.git/+/master/foo)",  # nocheck
                ],
            ),
            MockFile(
                os.path.normpath("some/java/file/TestJavaDoc.java"),
                [
                    "/**",
                    " * This line contains the word master,",  # nocheck
                    "* ignored because this is a comment. See {@link",
                    " * https://s/src/+/master:tools/README.md}",  # nocheck
                    " */",
                ],
            ),
            MockFile(
                os.path.normpath("some/java/file/TestJava.java"),
                [
                    "class TestJava {",
                    "  public String master;",  # nocheck
                    "}",
                ],
            ),
            MockFile(
                os.path.normpath("some/html/file.html"),
                [
                    "<-- an existing html multiline comment",
                    'says "master" here',  # nocheck
                    "in the comment -->",
                ],
            ),
        ]

        errors = presubmit_canned_checks.CheckInclusiveLanguage(
            input_api, MockOutputApi()
        )
        self.assertEqual(1, len(errors))
        self.assertTrue(
            os.path.normpath("some/ios/file.mm") in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("another/ios_file.mm") not in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/mac/file.mm") in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/ios/file_egtest.mm") in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/ios/file_unittest.mm") in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/doc/file.md") not in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/doc/ok_file.md") not in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/doc/branch_name_file.md")
            not in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/java/file/TestJavaDoc.java")
            not in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/java/file/TestJava.java")
            not in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/html/file.html") not in errors[0].message
        )

    def testBlockedTermsWithLegacy(self):
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: ""
        input_api.presubmit_local_path = ""

        input_api.files = [
            MockFile(
                os.path.normpath(
                    "infra/inclusive_language_presubmit_exempt_dirs.txt"
                ),
                [
                    "some/ios 2 1",
                    "some/other/dir 2 1",
                ],
            ),
            MockFile(
                os.path.normpath("some/ios/file.mm"),
                [
                    "TEST(SomeClassTest, SomeInteraction, blacklist) {",  # nocheck
                    "}",
                ],
            ),
            MockFile(
                os.path.normpath("some/ios/subdir/file.mm"),
                [
                    "TEST(SomeClassTest, SomeInteraction, blacklist) {",  # nocheck
                    "}",
                ],
            ),
            MockFile(
                os.path.normpath("some/mac/file.mm"),
                [
                    "TEST(SomeClassTest, SomeInteraction, BlackList) {",  # nocheck
                    "}",
                ],
            ),
            MockFile(
                os.path.normpath("another/ios_file.mm"),
                ["class SomeTest : public testing::Test blocklist {};"],
            ),
            MockFile(
                os.path.normpath("some/ios/file_egtest.mm"),
                ["- (void)testSomething { V(whitelist); }"],
            ),  # nocheck
            MockFile(
                os.path.normpath("some/ios/file_unittest.mm"),
                ["TEST_F(SomeTest, Whitelist) { V(allowlist); }"],
            ),  # nocheck
        ]

        errors = presubmit_canned_checks.CheckInclusiveLanguage(
            input_api, MockOutputApi()
        )
        self.assertEqual(1, len(errors))
        self.assertTrue(
            os.path.normpath("some/ios/file.mm") not in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/ios/subdir/file.mm") in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("another/ios_file.mm") not in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/mac/file.mm") in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/ios/file_egtest.mm") not in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("some/ios/file_unittest.mm")
            not in errors[0].message
        )

    def testBlockedTermsWithNocheck(self):
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: ""
        input_api.presubmit_local_path = ""

        input_api.files = [
            MockFile(
                os.path.normpath(
                    "infra/inclusive_language_presubmit_exempt_dirs.txt"
                ),
                [
                    "some/dir 2 1",
                    "some/other/dir 2 1",
                ],
            ),
            MockFile(
                os.path.normpath("some/ios/file.mm"),
                [
                    "TEST(SomeClassTest, SomeInteraction, ",
                    " blacklist) { // nocheck",  # nocheck
                    "}",
                ],
            ),
            MockFile(
                os.path.normpath("some/mac/file.mm"),
                [
                    "TEST(SomeClassTest, SomeInteraction, ",
                    "BlackList) { // nocheck",  # nocheck
                    "}",
                ],
            ),
            MockFile(
                os.path.normpath("another/ios_file.mm"),
                ["class SomeTest : public testing::Test blocklist {};"],
            ),
            MockFile(
                os.path.normpath("some/ios/file_egtest.mm"),
                ["- (void)testSomething { ", "V(whitelist); } // nocheck"],
            ),  # nocheck
            MockFile(
                os.path.normpath("some/ios/file_unittest.mm"),
                [
                    "TEST_F(SomeTest, Whitelist) // nocheck",  # nocheck
                    " { V(allowlist); }",
                ],
            ),
            MockFile(
                os.path.normpath("some/doc/file.md"),
                [
                    "Master in markdown <!-- nocheck -->",  # nocheck
                    "## Subheading is okay",
                ],
            ),
            MockFile(
                os.path.normpath("some/java/file/TestJava.java"),
                [
                    "class TestJava {",
                    "  public String master; // nocheck",  # nocheck
                    "}",
                ],
            ),
            MockFile(
                os.path.normpath("some/html/file.html"),
                [
                    "<-- an existing html multiline comment",
                    'says "master" here --><!-- nocheck -->',  # nocheck
                    "<!-- in the comment -->",
                ],
            ),
        ]

        errors = presubmit_canned_checks.CheckInclusiveLanguage(
            input_api, MockOutputApi()
        )
        self.assertEqual(0, len(errors))

    def testTopLevelDirExcempt(self):
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: ""
        input_api.presubmit_local_path = ""

        input_api.files = [
            MockFile(
                os.path.normpath(
                    "infra/inclusive_language_presubmit_exempt_dirs.txt"
                ),
                [
                    ". 2 1",
                    "some/other/dir 2 1",
                ],
            ),
            MockFile(
                os.path.normpath("presubmit_canned_checks_test.py"),
                [
                    "TEST(SomeClassTest, SomeInteraction, blacklist) {",  # nocheck
                    "}",
                ],
            ),
            MockFile(
                os.path.normpath("presubmit_canned_checks.py"),
                ["- (void)testSth { V(whitelist); } // nocheck"],
            ),  # nocheck
        ]

        errors = presubmit_canned_checks.CheckInclusiveLanguage(
            input_api, MockOutputApi()
        )
        self.assertEqual(1, len(errors))
        self.assertTrue(
            os.path.normpath("presubmit_canned_checks_test.py")
            in errors[0].message
        )
        self.assertTrue(
            os.path.normpath("presubmit_canned_checks.py")
            not in errors[0].message
        )

    def testChangeIsForSomeOtherRepo(self):
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: "v8"
        input_api.presubmit_local_path = ""

        input_api.files = [
            MockFile(
                os.path.normpath("some_file"),
                [
                    "# this is a blacklist",  # nocheck
                ],
            ),
        ]
        errors = presubmit_canned_checks.CheckInclusiveLanguage(
            input_api, MockOutputApi()
        )
        self.assertEqual([], errors)

    def testDirExemptWithComment(self):
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: ""
        input_api.presubmit_local_path = ""

        input_api.files = [
            MockFile(
                os.path.normpath(
                    "infra/inclusive_language_presubmit_exempt_dirs.txt"
                ),
                [
                    "# this is a comment",
                    "dir1",
                    "# dir2",
                ],
            ),
            # this should be excluded
            MockFile(
                os.path.normpath("dir1/1.py"),
                [
                    "TEST(SomeClassTest, SomeInteraction, blacklist) {",  # nocheck
                    "}",
                ],
            ),
            # this should not be excluded
            MockFile(
                os.path.normpath("dir2/2.py"),
                ["- (void)testSth { V(whitelist); }"],
            ),  # nocheck
        ]

        errors = presubmit_canned_checks.CheckInclusiveLanguage(
            input_api, MockOutputApi()
        )
        self.assertEqual(1, len(errors))
        self.assertTrue(os.path.normpath("dir1/1.py") not in errors[0].message)
        self.assertTrue(os.path.normpath("dir2/2.py") in errors[0].message)


class CheckLongLinesTest(unittest.TestCase):
    def testCheckJavaLongLines(self):
        test_cases = [
            {
                "name": "Valid Java text blocks (no errors expected)",
                "files": [
                    (
                        "some/java/file/TestBlock.java",
                        [
                            "class TestBlock {",
                            '  String s = """',
                            "    this is a very long line that should be ignored because it is inside a text block and we want to allow it as per the style guide.",
                            '    """;',
                            "}",
                        ],
                    ),
                    (
                        "some/java/file/TestComment.java",
                        [
                            "class TestComment {",
                            '  // Comment with """',
                            '  String s = """',
                            "    this is a very long line that should be ignored because it is inside a text block and we want to allow it as per the style guide.",
                            '    """;',
                            "}",
                        ],
                    ),
                    (
                        "some/java/file/TestEscaped.java",
                        [
                            "class TestEscaped {",
                            '  String s = """',
                            "    line 1",
                            '    escaped \\""" here',
                            "    line 3 that is also long but inside block and should be ignored",
                            '    """;',
                            "}",
                        ],
                    ),
                    (
                        "some/java/file/TestLongClosingContent.java",
                        [
                            "class TestLongClosingContent {",
                            '  String s = """',
                            "    content",
                            '    this is a very long line that ends the text block """;',
                            "}",
                        ],
                    ),
                    (
                        "some/java/file/TestLongClosingCode.java",
                        [
                            "class TestLongClosingCode {",
                            '  String s = """',
                            "    content",
                            '    """; // this line is long but should NOT be flagged because it is the closing line of a text block.',
                            "}",
                        ],
                    ),
                ],
                "expected_errors": 0,
            },
            {
                "name": "Invalid Java lines (errors expected)",
                "files": [
                    (
                        "some/java/file/TestNormal.java",
                        [
                            "class TestNormal {",
                            '  String s = "this is a very long line that should NOT be ignored because it is in a normal string literal.";',
                            "}",
                        ],
                    ),
                    (
                        "some/java/file/TestNormalQuotes.java",
                        [
                            "class TestNormalQuotes {",
                            '  String s = "normal string with \\"\\"\\" inside";',
                            '  String t = "normal string that is very long and should be flagged because it is not a text block.";',
                            "}",
                        ],
                    ),
                ],
                "expected_errors": 1,
                "expected_items": ["TestNormal.java", "TestNormalQuotes.java"],
            },
        ]

        for case in test_cases:
            with self.subTest(case_name=case["name"]):
                input_api = MockInputApi()
                input_api.files = [
                    MockFile(os.path.normpath(path), lines)
                    for path, lines in case["files"]
                ]
                errors = presubmit_canned_checks.CheckLongLines(
                    input_api, MockOutputApi(), maxlen=80
                )
                expected_errors = case.get("expected_errors", 0)
                self.assertEqual(expected_errors, len(errors))
                if expected_errors > 0:
                    all_items = getattr(errors[0], "items", [])
                    expected_items = case.get("expected_items", [])
                    self.assertEqual(len(expected_items), len(all_items))
                    for item in expected_items:
                        self.assertTrue(
                            any(item in str(actual) for actual in all_items)
                        )

    def testCheckPythonLongLines(self):
        input_api = MockInputApi()

        # Case 1: Existing long line, not changed. No warning expected.
        file_existing_long = MockFile(
            os.path.normpath("some/python/file.py"),
            [
                "short line",
                "# This is an existing long line that was already there and not changed so it should not warn",
                "another short line",
            ],
        )
        # Manually set changed contents to exclude the long line (line 2)
        file_existing_long._changed_contents = [
            (1, "short line"),
            (3, "another short line"),
        ]

        # Case 2: New long line. Warning expected.
        file_new_long = MockFile(
            os.path.normpath("some/python/file2.py"),
            [
                "short line",
                "# This is a new long line that should warn because it is new and exceeds the limit",
            ],
        )

        # Case 3: Modified long line. Warning expected.
        file_modified_long = MockFile(
            os.path.normpath("some/python/file3.py"),
            [
                "short line",
                "# This is a modified long line that should warn because it was modified and is long",
            ],
        )
        file_modified_long._changed_contents = [
            (
                2,
                "# This is a modified long line that should warn because it was modified and is long",
            ),
        ]

        # Case 4: Indented long line. Warning expected.
        file_indented_long = MockFile(
            os.path.normpath("some/python/file4.py"),
            [
                "short line",
                "    # This is an existing long line that was indented and should warn because it is now very long indeed",
            ],
        )
        file_indented_long._changed_contents = [
            (
                2,
                "    # This is an existing long line that was indented and should warn because it is now very long indeed",
            ),
        ]

        input_api.files = [
            file_existing_long,
            file_new_long,
            file_modified_long,
            file_indented_long,
        ]

        errors = presubmit_canned_checks.CheckLongLines(
            input_api, MockOutputApi(), maxlen=80
        )

        self.assertEqual(1, len(errors))
        all_items = errors[0].items
        self.assertEqual(3, len(all_items))

        items_strs = [str(item) for item in all_items]
        self.assertTrue(any("file2.py, line 2" in s for s in items_strs))
        self.assertTrue(any("file3.py, line 2" in s for s in items_strs))
        self.assertTrue(any("file4.py, line 2" in s for s in items_strs))
        self.assertFalse(any("file.py" in s for s in items_strs))


class DescriptionChecksTest(unittest.TestCase):
    def testCheckDescriptionUsesColonInsteadOfEquals(self):
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: ""
        input_api.presubmit_local_path = ""

        # Verify error in case of the attempt to use "Bug=".
        input_api.change = MockChange([], "Broken description\nBug=123")
        errors = (
            presubmit_canned_checks.CheckDescriptionUsesColonInsteadOfEquals(
                input_api, MockOutputApi()
            )
        )
        self.assertEqual(1, len(errors))
        self.assertTrue("Bug=" in errors[0].message)

        # Verify error in case of the attempt to use "Fixed=".
        input_api.change = MockChange([], "Broken description\nFixed=123")
        errors = (
            presubmit_canned_checks.CheckDescriptionUsesColonInsteadOfEquals(
                input_api, MockOutputApi()
            )
        )
        self.assertEqual(1, len(errors))
        self.assertTrue("Fixed=" in errors[0].message)

        # Verify error in case of the attempt to use the lower case "bug=".
        input_api.change = MockChange(
            [], "Broken description lowercase\nbug=123"
        )
        errors = (
            presubmit_canned_checks.CheckDescriptionUsesColonInsteadOfEquals(
                input_api, MockOutputApi()
            )
        )
        self.assertEqual(1, len(errors))
        self.assertTrue("Bug=" in errors[0].message)

        # Verify no error in case of "Bug:"
        input_api.change = MockChange([], "Correct description\nBug: 123")
        errors = (
            presubmit_canned_checks.CheckDescriptionUsesColonInsteadOfEquals(
                input_api, MockOutputApi()
            )
        )
        self.assertEqual(0, len(errors))

        # Verify no error in case of "Fixed:"
        input_api.change = MockChange([], "Correct description\nFixed: 123")
        errors = (
            presubmit_canned_checks.CheckDescriptionUsesColonInsteadOfEquals(
                input_api, MockOutputApi()
            )
        )
        self.assertEqual(0, len(errors))


class ChromiumDependencyMetadataCheckTest(unittest.TestCase):
    def testDefaultFileFilter(self):
        """Checks the default file filter limits the scope to Chromium dependency
        metadata files.
        """
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: ""
        input_api.files = [
            MockFile(os.path.normpath("foo/README.md"), ["Shipped: no?"]),
            MockFile(os.path.normpath("foo/main.py"), ["Shipped: yes?"]),
        ]
        results = presubmit_canned_checks.CheckChromiumDependencyMetadata(
            input_api, MockOutputApi()
        )
        self.assertEqual(len(results), 0)

    def testSkipDeletedFiles(self):
        """Checks validation is skipped for deleted files."""
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: ""
        input_api.files = [
            MockFile(
                os.path.normpath("foo/README.chromium"),
                ["No fields"],
                action="D",
            ),
        ]
        results = presubmit_canned_checks.CheckChromiumDependencyMetadata(
            input_api, MockOutputApi()
        )
        self.assertEqual(len(results), 0)

    def testFeedbackForNoMetadata(self):
        """Checks presubmit results are returned for files without any metadata."""
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: ""
        input_api.files = [
            MockFile(os.path.normpath("foo/README.chromium"), ["No fields"]),
        ]
        results = presubmit_canned_checks.CheckChromiumDependencyMetadata(
            input_api, MockOutputApi()
        )
        self.assertEqual(len(results), 1)
        self.assertTrue("No dependency metadata" in results[0].message)

    def testFeedbackForInvalidMetadata(self):
        """Checks presubmit results are returned for files with invalid metadata."""
        input_api = MockInputApi()
        input_api.change.RepositoryRoot = lambda: ""
        test_file = MockFile(
            os.path.normpath("foo/README.chromium"), ["Shipped: yes?"]
        )
        input_api.files = [test_file]
        results = presubmit_canned_checks.CheckChromiumDependencyMetadata(
            input_api, MockOutputApi()
        )

        # There should be 9 results due to
        # - missing 5 mandatory fields: Name, URL, Version, License, and
        #                               Security Critical
        # - 1 error for insufficent versioning info
        # - missing 2 required fields: License File, and
        #                              License Android Compatible
        # - Shipped should be only 'yes' or 'no'.
        self.assertEqual(len(results), 9)

        # Check each presubmit result is associated with the test file.
        for result in results:
            self.assertEqual(len(result.items), 1)
            self.assertEqual(result.items[0], test_file)


class CheckUpdateOwnersFileReferences(unittest.TestCase):
    def testShowsWarningIfDeleting(self):
        input_api = MockInputApi()
        input_api.files = [
            MockFile(os.path.normpath("foo/OWNERS"), [], [], action="D"),
        ]
        results = presubmit_canned_checks.CheckUpdateOwnersFileReferences(
            input_api, MockOutputApi()
        )
        self.assertEqual(1, len(results))
        self.assertEqual("warning", results[0].type)
        self.assertEqual(1, len(results[0].items))

    def testShowsWarningIfMoving(self):
        input_api = MockInputApi()
        input_api.files = [
            MockFile(
                os.path.normpath("new_directory/OWNERS"), [], [], action="A"
            ),
            MockFile(
                os.path.normpath("old_directory/OWNERS"), [], [], action="D"
            ),
        ]
        results = presubmit_canned_checks.CheckUpdateOwnersFileReferences(
            input_api, MockOutputApi()
        )
        self.assertEqual(1, len(results))
        self.assertEqual("warning", results[0].type)
        self.assertEqual(1, len(results[0].items))

    def testNoWarningIfAdding(self):
        input_api = MockInputApi()
        input_api.files = [
            MockFile(os.path.normpath("foo/OWNERS"), [], [], action="A"),
        ]
        results = presubmit_canned_checks.CheckUpdateOwnersFileReferences(
            input_api, MockOutputApi()
        )
        self.assertEqual(0, len(results))


class CheckNoNewGitFilesAddedInDependenciesTest(unittest.TestCase):
    @mock.patch("presubmit_canned_checks._readDeps")
    def testNonNested(self, readDeps):
        readDeps.return_value = """deps = {
      'src/foo': {'url': 'bar', 'condition': 'non_git_source'},
      'src/components/foo/bar': {'url': 'bar', 'condition': 'non_git_source'},
    }"""

        input_api = MockInputApi()
        input_api.files = [
            MockFile("components/foo/file1.java", ["otherFunction"]),
            MockFile("components/foo/file2.java", ["hasSyncConsent"]),
            MockFile("chrome/foo/file3.java", ["canSyncFeatureStart"]),
            MockFile("chrome/foo/file4.java", ["isSyncFeatureEnabled"]),
            MockFile("chrome/foo/file5.java", ["isSyncFeatureActive"]),
        ]
        results = presubmit_canned_checks.CheckNoNewGitFilesAddedInDependencies(
            input_api, MockOutputApi()
        )

        self.assertEqual(0, len(results))

    @mock.patch("presubmit_canned_checks._readDeps")
    def testCollision(self, readDeps):
        readDeps.return_value = """deps = {
      'src/foo': {'url': 'bar', 'condition': 'non_git_source'},
      'src/baz': {'url': 'baz'},
    }"""

        input_api = MockInputApi()
        input_api.files = [
            MockAffectedFile("fo", "content"),  # no conflict
            MockAffectedFile("foo", "content"),  # conflict
            MockAffectedFile("foo/bar", "content"),  # conflict
            MockAffectedFile("baz/qux", "content"),  # conflict, but ignored
        ]
        results = presubmit_canned_checks.CheckNoNewGitFilesAddedInDependencies(
            input_api, MockOutputApi()
        )

        self.assertEqual(2, len(results))
        self.assertIn("File: foo", str(results))
        self.assertIn("File: foo/bar", str(results))

    @mock.patch("presubmit_canned_checks._readDeps")
    def testNoDeps(self, readDeps):
        readDeps.return_value = ""  # Empty deps

        input_api = MockInputApi()
        input_api.files = [
            MockAffectedFile("fo", "content"),  # no conflict
            MockAffectedFile("foo", "content"),  # conflict
            MockAffectedFile("foo/bar", "content"),  # conflict
            MockAffectedFile("baz/qux", "content"),  # conflict, but ignored
        ]
        results = presubmit_canned_checks.CheckNoNewGitFilesAddedInDependencies(
            input_api, MockOutputApi()
        )

        self.assertEqual(0, len(results))


class CheckNewDEPSHooksHasRequiredReviewersTest(unittest.TestCase):
    def setUp(self):
        self.input_api = MockInputApi()
        self.input_api.change = MockChange([], issue=123)
        self.input_api.change.RepositoryRoot = lambda: ""

    def test_no_gerrit_cl(self):
        self.input_api.change = MockChange([], issue=None)
        results = presubmit_canned_checks.CheckNewDEPSHooksHasRequiredReviewers(
            self.input_api, MockOutputApi()
        )
        self.assertEqual(0, len(results))

    def test_no_deps_file_change(self):
        self.input_api.files = [
            MockAffectedFile("foo.py", "content"),
        ]
        results = presubmit_canned_checks.CheckNewDEPSHooksHasRequiredReviewers(
            self.input_api, MockOutputApi()
        )
        self.assertEqual(0, len(results))

    def test_new_deps_hook(self):
        gerrit_mock = mock.Mock()
        self.input_api.gerrit = gerrit_mock
        test_cases = [
            {
                "name": "no new hooks",
                "old_contents": ["hooks = []"],
                "new_contents": ["hooks = []"],
                "reviewers": [],
            },
            {
                "name": "add new hook and require review",
                "old_contents": ['hooks = [{"name": "old_hook"}]'],
                "new_contents": [
                    'hooks = [{"name": "old_hook"}, {"name": "new_hook"},  {"name": "new_hook_2"}]'
                ],
                "reviewers": [],
                "expected_error_msg": "New DEPS hooks (new_hook, new_hook_2) are found. Please "
                "request review from one of the following reviewers:\n "
                "* foo@chromium.org\n * bar@chromium.org\n * baz@chromium.org",
            },
            {
                "name": "add new hook and require approval",
                "old_contents": ['hooks = [{"name": "old_hook"}]'],
                "new_contents": [
                    'hooks = [{"name": "old_hook"}, {"name": "new_hook"},  {"name": "new_hook_2"}]'
                ],
                "submitting": True,
                "reviewers": ["not_relevant@chromium.org"],
                "expected_error_msg": "New DEPS hooks (new_hook, new_hook_2) are found. The CL must "
                "be approved by one of the following reviewers:\n"
                " * foo@chromium.org\n * bar@chromium.org\n * baz@chromium.org",
            },
            {
                "name": "add new hook and reviewer is already added",
                "old_contents": ['hooks = [{"name": "old_hook"}]'],
                "new_contents": [
                    'hooks = [{"name": "old_hook"}, {"name": "new_hook"},  {"name": "new_hook_2"}]'
                ],
                "reviewers": ["baz@chromium.org"],
            },
            {
                "name": "add new hook and reviewer already approves",
                "old_contents": ['hooks = [{"name": "old_hook"}]'],
                "new_contents": [
                    'hooks = [{"name": "old_hook"}, {"name": "new_hook"},  {"name": "new_hook_2"}]'
                ],
                "submitting": True,
                "reviewers": ["foo@chromium.org"],
            },
            {
                "name": "change existing hook",
                "old_contents": [
                    'hooks = [{"name": "existing_hook", "action": ["run", "./test.sh"]}]'
                ],
                "new_contents": [
                    'hooks = [{"name": "existing_hook", "action": ["run", "./test_v2.sh"]}]'
                ],
                "reviewers": [],
            },
            {
                "name": "remove hook",
                "old_contents": [
                    'hooks = [{"name": "old_hook"}, {"name": "hook_to_remove"}]'
                ],
                "new_contents": ['hooks = [{"name": "old_hook"}]'],
                "reviewers": [],
            },
        ]
        for case in test_cases:
            with self.subTest(case_name=case["name"]):
                self.input_api.files = [
                    MockFile(
                        "OWNERS",
                        [
                            "per-file DEPS=foo@chromium.org # For new DEPS hook",
                            "per-file DEPS=bar@chromium.org, baz@chromium.org # For new DEPS hook",
                        ],
                    ),
                    MockAffectedFile(
                        "DEPS",
                        old_contents=case["old_contents"],
                        new_contents=case["new_contents"],
                    ),
                ]
                if case.get("submitting", False):
                    self.input_api.is_committing = True
                    self.input_api.dry_run = False
                gerrit_mock.GetChangeReviewers.return_value = case["reviewers"]
                results = presubmit_canned_checks.CheckNewDEPSHooksHasRequiredReviewers(
                    self.input_api,
                    MockOutputApi(),
                )
                if "expected_error_msg" in case:
                    self.assertEqual(1, len(results))
                    self.assertEqual(
                        case["expected_error_msg"], results[0].message
                    )
                else:
                    self.assertEqual(0, len(results))


class CheckAyeAyeTest(unittest.TestCase):
    def setUp(self):
        super(CheckAyeAyeTest, self).setUp()
        self.addCleanup(mock.patch.stopall)

        self.input_api = MockInputApi()
        self.output_api = MockOutputApi()

        self.mock_repo_root = mock.patch.object(
            self.input_api.change, "RepositoryRoot", create=True
        ).start()
        self.mock_repo_root.return_value = "/fake/repo/root"

        self.mock_popen = mock.patch.object(
            self.input_api.subprocess, "Popen", autospec=True
        ).start()
        self.mock_proc = mock.Mock()
        self.mock_popen.return_value = self.mock_proc
        self.input_api.subprocess.PIPE = subprocess.PIPE
        self.input_api.subprocess.STDOUT = subprocess.STDOUT

        self.mock_exists = mock.patch.object(
            presubmit_canned_checks._os.path, "exists", autospec=True
        ).start()
        self.mock_exists.return_value = True

    def test_ayeaye_findings_with_errors(self):
        # Simulate run_alint JSON output containing both errors and warnings
        json_output = json.dumps(
            {
                "errors": ["This is an error.", "Another error."],
                "warnings": ["This is a warning.", "Another warning."],
            }
        ).encode("utf-8")
        self.mock_proc.communicate.return_value = (json_output, b"")
        self.mock_proc.returncode = 0

        results = presubmit_canned_checks.CheckAyeAye(
            self.input_api, self.output_api
        )

        self.assertEqual(len(results), 4)

        result_types = sorted([r.type for r in results])
        self.assertEqual(result_types, ["error", "error", "warning", "warning"])

        messages = sorted([r.message for r in results])
        expected_messages = sorted(
            [
                "This is an error.",
                "Another error.",
                "This is a warning.",
                "Another warning.",
            ]
        )
        self.assertEqual(messages, expected_messages)

        self.mock_popen.assert_called_once()
        called_args = self.mock_popen.call_args[0][0]
        self.assertEqual(called_args[0], "vpython3")
        self.assertTrue(called_args[1].endswith("run_alint.py"))
        self.assertEqual(called_args[2], "/google/bin/releases/alint/alint")
        self.assertEqual(called_args[3], "/fake/repo/root")
        self.assertEqual(called_args[4], "-t=30s")

    def test_ayeaye_findings_only_warnings(self):
        # Simulate run_alint JSON output with only warnings
        json_output = json.dumps(
            {
                "errors": [],
                "warnings": ["This is a warning.", "Another warning."],
            }
        ).encode("utf-8")
        self.mock_proc.communicate.return_value = (json_output, b"")
        self.mock_proc.returncode = 0

        results = presubmit_canned_checks.CheckAyeAye(
            self.input_api, self.output_api
        )

        self.assertEqual(len(results), 2)
        result_types = sorted([r.type for r in results])
        self.assertEqual(result_types, ["warning", "warning"])
        messages = sorted([r.message for r in results])
        expected_messages = sorted(
            [
                "This is a warning.",
                "Another warning.",
            ]
        )
        self.assertEqual(messages, expected_messages)

    def test_ayeaye_no_findings(self):
        json_output = json.dumps({"errors": [], "warnings": []}).encode("utf-8")
        self.mock_proc.communicate.return_value = (json_output, b"")
        self.mock_proc.returncode = 0
        results = presubmit_canned_checks.CheckAyeAye(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 0)

    def test_ayeaye_alint_not_found(self):
        self.mock_exists.return_value = False
        results = presubmit_canned_checks.CheckAyeAye(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 0)

    def test_ayeaye_subprocess_exception(self):
        self.mock_popen.side_effect = Exception("BOOM")
        results = presubmit_canned_checks.CheckAyeAye(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].type, "error")
        self.assertIn("Unexpected error in AyeAye:", results[0].message)
        self.assertIn("BOOM", results[0].message)

    def test_ayeaye_alint_fails(self):
        json_output = json.dumps(
            {
                "errors": ["Failed to run."],
                "warnings": [],
            }
        ).encode("utf-8")
        self.mock_proc.communicate.return_value = (json_output, b"")
        self.mock_proc.returncode = 0

        self.input_api.is_committing = True

        results = presubmit_canned_checks.CheckAyeAye(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].type, "error")
        self.assertIn("Failed to run.", results[0].message)

    def test_ayeaye_execution_error(self):
        json_output = json.dumps(
            {
                "errors": [],
                "warnings": [],
                "execution_error": {
                    "exit_code": 128,
                    "output": "fatal: bad object HEAD:third_party/litert/src\nFailed to build request proto",
                },
            }
        ).encode("utf-8")
        self.mock_proc.communicate.return_value = (json_output, b"")
        self.mock_proc.returncode = 0

        results = presubmit_canned_checks.CheckAyeAye(
            self.input_api, self.output_api
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].type, "warning")
        self.assertEqual(
            results[0].message,
            "AyeAye execution failed (exit code 128):\n"
            "fatal: bad object HEAD:third_party/litert/src\n"
            "Failed to build request proto",
        )

    def test_ayeaye_execution_error_no_output(self):
        json_output = json.dumps(
            {
                "errors": [],
                "warnings": [],
                "execution_error": {
                    "exit_code": 1,
                    "output": "",
                },
            }
        ).encode("utf-8")
        self.mock_proc.communicate.return_value = (json_output, b"")
        self.mock_proc.returncode = 0

        results = presubmit_canned_checks.CheckAyeAye(
            self.input_api, self.output_api
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].type, "warning")
        self.assertEqual(
            results[0].message,
            "AyeAye execution failed (exit code 1)",
        )


class RunAlintTest(unittest.TestCase):
    def test_parse_alint_output(self):
        alint_output = (
            '\x1b[31mERROR:\x1b[0m [CheckMetadata/missing_field] README.chromium:1: ERR: Missing field "Name"\n'
            "Some other info line\n"
            "\x1b[33mWARNING:\x1b[0m [CheckContents/trailing_whitespace] /COMMIT_MSG:18: WARN: Please remove the trailing whitespace.\n"
            "\x1b[94mINFO:\x1b[0m This is an info.\n"
            "\x1b[31mERROR:\x1b[0m Bare error.\n"
            "\x1b[33mWARNING:\x1b[0m Bare warning.\n"
            "WARNING: [AyeAye/AlreadyPrefixed] Already prefixed."
        )
        clean = run_alint._strip_ansi_codes(alint_output).strip()
        parsed = run_alint._parse_alint_output(clean)
        self.assertEqual(
            parsed["errors"],
            [
                '[AyeAye/CheckMetadata/missing_field] README.chromium:1: ERR: Missing field "Name"',
                "[AyeAye] Bare error.",
            ],
        )
        self.assertEqual(
            parsed["warnings"],
            [
                "[AyeAye/CheckContents/trailing_whitespace] /COMMIT_MSG:18: WARN: Please remove the trailing whitespace.",
                "[AyeAye] Bare warning.",
                "[AyeAye/AlreadyPrefixed] Already prefixed.",
            ],
        )

    @mock.patch("sys.argv", ["run_alint.py", "/bin/alint", "/repo"])
    @mock.patch("os.chdir")
    @mock.patch("subprocess.Popen")
    def test_main_execution_error(self, mock_popen, mock_chdir):
        mock_proc = mock.Mock()
        mock_proc.communicate.return_value = (b"fatal: bad object HEAD", b"")
        mock_proc.returncode = 128
        mock_popen.return_value = mock_proc

        with mock.patch("sys.stdout", new=io.StringIO()) as mock_stdout:
            exit_code = run_alint.main()
            self.assertEqual(exit_code, 0)
            mock_chdir.assert_called_once_with("/repo")
            result = json.loads(mock_stdout.getvalue())
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["warnings"], [])
            self.assertEqual(
                result["execution_error"],
                {
                    "exit_code": 128,
                    "output": "fatal: bad object HEAD",
                },
            )

    @mock.patch("sys.argv", ["run_alint.py", "/bin/alint", "/repo", "-t=30s"])
    @mock.patch("os.chdir")
    @mock.patch("subprocess.Popen")
    def test_main_success_findings(self, mock_popen, mock_chdir):
        mock_proc = mock.Mock()
        mock_proc.communicate.return_value = (
            b"WARNING: [CheckContents/trailing_whitespace] /COMMIT_MSG:18: WARN: trailing space\n",
            b"",
        )
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        with mock.patch("sys.stdout", new=io.StringIO()) as mock_stdout:
            exit_code = run_alint.main()
            self.assertEqual(exit_code, 0)
            mock_chdir.assert_called_once_with("/repo")
            mock_popen.assert_called_once()
            called_args, called_kwargs = mock_popen.call_args
            self.assertEqual(called_args[0], ["/bin/alint", "--", "-t=30s"])
            self.assertEqual(called_kwargs["stdout"], subprocess.PIPE)
            self.assertEqual(called_kwargs["stderr"], subprocess.STDOUT)
            self.assertIn("GIT_CONFIG_PARAMETERS", called_kwargs["env"])
            self.assertIn(
                "'status.showUntrackedFiles=no'",
                called_kwargs["env"]["GIT_CONFIG_PARAMETERS"],
            )
            result = json.loads(mock_stdout.getvalue())
            self.assertEqual(result["errors"], [])
            self.assertEqual(
                result["warnings"],
                [
                    "[AyeAye/CheckContents/trailing_whitespace] /COMMIT_MSG:18: WARN: trailing space"
                ],
            )
            self.assertNotIn("execution_error", result)

    @mock.patch("sys.argv", ["run_alint.py", "/bin/alint", "/repo"])
    @mock.patch("os.chdir")
    @mock.patch("subprocess.Popen")
    def test_main_exception(self, mock_popen, mock_chdir):
        mock_popen.side_effect = OSError("Executable not found")

        with mock.patch("sys.stdout", new=io.StringIO()) as mock_stdout:
            exit_code = run_alint.main()
            self.assertEqual(exit_code, 0)
            mock_chdir.assert_called_once_with("/repo")
            result = json.loads(mock_stdout.getvalue())
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["warnings"], [])
            self.assertEqual(result["execution_error"]["exit_code"], 1)
            self.assertIn(
                "Executable not found", result["execution_error"]["output"]
            )

    @mock.patch.dict(os.environ, {"GIT_CONFIG_PARAMETERS": "'custom.key=val'"})
    @mock.patch("sys.argv", ["run_alint.py", "/bin/alint", "/repo", "-t=30s"])
    @mock.patch("os.chdir")
    @mock.patch("subprocess.Popen")
    def test_main_preserves_existing_git_config_parameters(
        self, mock_popen, mock_chdir
    ):
        mock_proc = mock.Mock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        with mock.patch("sys.stdout", new=io.StringIO()):
            exit_code = run_alint.main()
            self.assertEqual(exit_code, 0)
            mock_popen.assert_called_once()
            called_env = mock_popen.call_args[1]["env"]
            self.assertEqual(
                called_env["GIT_CONFIG_PARAMETERS"],
                "'custom.key=val' 'status.showUntrackedFiles=no'",
            )

    @mock.patch.dict(os.environ, {"GIT_CONFIG_PARAMETERS": "   "})
    @mock.patch("sys.argv", ["run_alint.py", "/bin/alint", "/repo", "-t=30s"])
    @mock.patch("os.chdir")
    @mock.patch("subprocess.Popen")
    def test_main_strips_whitespace_git_config_parameters(
        self, mock_popen, mock_chdir
    ):
        mock_proc = mock.Mock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        with mock.patch("sys.stdout", new=io.StringIO()):
            exit_code = run_alint.main()
            self.assertEqual(exit_code, 0)
            mock_popen.assert_called_once()
            called_env = mock_popen.call_args[1]["env"]
            self.assertEqual(
                called_env["GIT_CONFIG_PARAMETERS"],
                "'status.showUntrackedFiles=no'",
            )

    @mock.patch.dict(
        os.environ,
        {"GIT_CONFIG_PARAMETERS": "'status.showuntrackedfiles=no'"},
    )
    @mock.patch("sys.argv", ["run_alint.py", "/bin/alint", "/repo", "-t=30s"])
    @mock.patch("os.chdir")
    @mock.patch("subprocess.Popen")
    def test_main_does_not_duplicate_status_show_untracked_files(
        self, mock_popen, mock_chdir
    ):
        mock_proc = mock.Mock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        with mock.patch("sys.stdout", new=io.StringIO()):
            exit_code = run_alint.main()
            self.assertEqual(exit_code, 0)
            mock_popen.assert_called_once()
            called_env = mock_popen.call_args[1]["env"]
            self.assertEqual(
                called_env["GIT_CONFIG_PARAMETERS"],
                "'status.showuntrackedfiles=no'",
            )

    @mock.patch.dict(
        os.environ,
        {"GIT_CONFIG_PARAMETERS": "'status.showuntrackedfiles=normal'"},
    )
    @mock.patch("sys.argv", ["run_alint.py", "/bin/alint", "/repo", "-t=30s"])
    @mock.patch("os.chdir")
    @mock.patch("subprocess.Popen")
    def test_main_enforces_status_show_untracked_files_no_over_normal(
        self, mock_popen, mock_chdir
    ):
        mock_proc = mock.Mock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        with mock.patch("sys.stdout", new=io.StringIO()):
            exit_code = run_alint.main()
            self.assertEqual(exit_code, 0)
            mock_popen.assert_called_once()
            called_env = mock_popen.call_args[1]["env"]
            self.assertEqual(
                called_env["GIT_CONFIG_PARAMETERS"],
                "'status.showuntrackedfiles=normal' 'status.showUntrackedFiles=no'",
            )


class CheckGNFormattedTest(unittest.TestCase):
    def enter_context(self, cm):
        if hasattr(super(), "enterContext"):
            return super().enterContext(cm)
        val = cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)
        return val

    def setUp(self):
        super().setUp()

        self.input_api = MockInputApi()
        self.input_api.change.RepositoryRoot = lambda: ROOT_DIR
        self.input_api.presubmit_local_path = ROOT_DIR
        self.output_api = MockOutputApi()

        self.mock_proc = mock.Mock()
        self.mock_proc.communicate.return_value = (b"", b"")
        self.mock_proc.returncode = 0

        self.mock_popen = self.enter_context(
            mock.patch.object(self.input_api.subprocess, "Popen", autospec=True)
        )
        self.mock_popen.return_value = self.mock_proc

    def test_gn_formatted_all_files_clean(self):
        f1 = MockAffectedFile("BUILD.gn", ['group("a") {}'])
        f2 = MockAffectedFile("config.gni", ["declare_args() {}"])
        self.input_api.files = [f1, f2]
        self.mock_proc.communicate.return_value = (b"", b"")
        self.mock_proc.returncode = 0

        results = presubmit_canned_checks.CheckGNFormatted(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 0)
        self.mock_popen.assert_called_once()
        cmd = self.mock_popen.call_args[0][0]
        kwargs = self.mock_popen.call_args[1]
        self.assertIn("format", cmd)
        self.assertIn("--dry-run", cmd)
        self.assertIn(f1.AbsoluteLocalPath(), cmd)
        self.assertIn(f2.AbsoluteLocalPath(), cmd)
        self.assertEqual(kwargs.get("cwd"), ROOT_DIR)
        self.assertEqual(kwargs.get("stderr"), subprocess.STDOUT)

    def test_gn_formatted_multiple_unformatted_files(self):
        f1 = MockAffectedFile("BUILD.gn", ['group("a") {}'])
        f2 = MockAffectedFile("bad1.gni", ["bad code 1"])
        f3 = MockAffectedFile("bad2.typemap", ["bad code 2"])
        self.input_api.files = [f1, f2, f3]
        out_bytes = (
            f2.AbsoluteLocalPath().encode("utf-8")
            + b"\n"
            + f3.AbsoluteLocalPath().encode("utf-8")
            + b"\n"
        )
        self.mock_proc.communicate.return_value = (out_bytes, b"")
        self.mock_proc.returncode = 2

        results = presubmit_canned_checks.CheckGNFormatted(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].type, "warning")
        self.assertEqual(results[1].type, "warning")
        self.assertIn("bad1.gni requires formatting", results[0].message)
        self.assertIn("bad2.typemap requires formatting", results[1].message)

    def test_gn_formatted_non_formatting_output_ignored(self):
        # Verify that non-formatting diagnostics or syntax error outputs from GN
        # are safely ignored and do not generate false-positive PresubmitErrors.
        f1 = MockAffectedFile("BUILD.gn", ['group("a") {}'])
        self.input_api.files = [f1]
        self.mock_proc.communicate.return_value = (
            b"ERROR at //BUILD.gn:10: invalid token\nSee //BUILD.gn:5",
            b"",
        )
        self.mock_proc.returncode = 1

        results = presubmit_canned_checks.CheckGNFormatted(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 0)

    def test_gn_formatted_combined_unformatted_and_diagnostics(self):
        # Verify that unformatted files are warned on even if another file in
        # the same chunk causes gn format to exit with code 1 (syntax error).
        f1 = MockAffectedFile("BUILD.gn", ['group("a") { deps = [ ] }'])
        f2 = MockAffectedFile("bad.gni", ["invalid syntax"])
        self.input_api.files = [f1, f2]
        output_bytes = (
            f1.AbsoluteLocalPath().encode("utf-8")
            + b"\nERROR at //bad.gni:1: Expecting assignment or function call.\ninvalid syntax\n"
        )
        self.mock_proc.communicate.return_value = (output_bytes, b"")
        self.mock_proc.returncode = 1

        results = presubmit_canned_checks.CheckGNFormatted(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].type, "warning")
        self.assertIn("BUILD.gn requires formatting", results[0].message)

    def test_gn_formatted_early_exit_no_gn_files(self):
        f1 = MockAffectedFile("foo.py", ["def foo(): pass"])
        self.input_api.files = [f1]

        results = presubmit_canned_checks.CheckGNFormatted(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 0)
        self.mock_popen.assert_not_called()

    def test_gn_formatted_early_exit_deletions_only(self):
        f1 = MockAffectedFile("BUILD.gn", [], action="D")
        self.input_api.files = [f1]

        results = presubmit_canned_checks.CheckGNFormatted(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 0)
        self.mock_popen.assert_not_called()

    def test_gn_formatted_early_exit_empty_files(self):
        self.input_api.files = []

        results = presubmit_canned_checks.CheckGNFormatted(
            self.input_api, self.output_api
        )
        self.assertEqual(len(results), 0)
        self.mock_popen.assert_not_called()

    def test_gn_formatted_chunks_large_file_lists(self):
        # Verify that files are chunked into multiple commands according to chunk_size.
        files = [
            MockAffectedFile(f"dir_{i}/BUILD.gn", [f'group("g_{i}") {{}}'])
            for i in range(5)
        ]
        self.input_api.files = files
        self.mock_proc.communicate.return_value = (b"", b"")
        self.mock_proc.returncode = 0

        results = presubmit_canned_checks.CheckGNFormatted(
            self.input_api, self.output_api, chunk_size=2
        )
        self.assertEqual(len(results), 0)
        self.assertEqual(self.mock_popen.call_count, 3)
        cmd1 = self.mock_popen.call_args_list[0][0][0]
        cmd2 = self.mock_popen.call_args_list[1][0][0]
        cmd3 = self.mock_popen.call_args_list[2][0][0]
        # First chunk has 2 files (+ 4 prefix args = 6)
        self.assertEqual(len(cmd1), 6)
        # Second chunk has 2 files (+ 4 prefix args = 6)
        self.assertEqual(len(cmd2), 6)
        # Third chunk has 1 file (+ 4 prefix args = 5)
        self.assertEqual(len(cmd3), 5)


class CheckAuthorizedAuthorTest(unittest.TestCase):
    def setUp(self):
        self.input_api = MockInputApi()
        self.output_api = MockOutputApi()
        self.td = tempfile.TemporaryDirectory()
        self.authors_path = os.path.join(self.td.name, "AUTHORS")
        self.input_api.PresubmitLocalPath = lambda: self.td.name

    def tearDown(self):
        presubmit_canned_checks._ParseAuthors.cache_clear()
        self.td.cleanup()

    def _write_authors(self, lines):
        with open(self.authors_path, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines) + "\n")

    def test_no_author(self):
        self.input_api.change.author_email = None
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual([], results)

    def test_bot_allowlist(self):
        self.input_api.change.author_email = "bot@example.com"
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api,
            self.output_api,
            bot_allowlist=["bot@example.com"],
        )
        self.assertEqual([], results)

    def test_missing_authors_file(self):
        self.input_api.change.author_email = "anyone@example.com"
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))
        self.assertIn("Failed to read AUTHORS file", results[0].message)

    def test_exact_author_match(self):
        self._write_authors(
            [
                "# Comment",
                "John Doe <jdoe@example.com>",
                "Jane Smith <jsmith@sample.org>",
            ]
        )
        self.input_api.change.author_email = "jdoe@example.com"
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual([], results)

    def test_wildcard_domain_match(self):
        self._write_authors(
            [
                "# Organization wildcards",
                "Google Inc. <*@google.com>",
                "The Chromium Authors <*@chromium.org>",
            ]
        )
        self.input_api.change.author_email = "developer@google.com"
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual([], results)

    def test_arbitrary_wildcard_match(self):
        self._write_authors(
            [
                "Nutanix <*nutanix.com>",
            ]
        )
        self.input_api.change.author_email = "eng@corp.nutanix.com"
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual([], results)

    def test_character_class_wildcards(self):
        self._write_authors(
            [
                "Bot <bot-[0-9]@example.com>",
                "Cluster <*@[a-c].example.com>",
            ]
        )
        self.input_api.change.author_email = "bot-5@example.com"
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual([], results)

        self.input_api.change.author_email = "bot-x@example.com"
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))

        self.input_api.change.author_email = "worker@b.example.com"
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual([], results)

    def test_unauthorized_author_warning_on_upload(self):
        self._write_authors(
            [
                "Google Inc. <*@google.com>",
            ]
        )
        self.input_api.is_committing = False
        self.input_api.no_diffs = False
        self.input_api.change.author_email = "unauthorized@unknown.org"
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))
        self.assertEqual("warning", results[0].type)
        self.assertIn(
            "unauthorized@unknown.org is not in AUTHORS", results[0].message
        )

    def test_unauthorized_author_error_on_commit(self):
        self._write_authors(
            [
                "Google Inc. <*@google.com>",
            ]
        )
        self.input_api.is_committing = True
        self.input_api.change.author_email = "unauthorized@unknown.org"
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))
        self.assertEqual("error", results[0].type)
        self.assertIn(
            "unauthorized@unknown.org is not in AUTHORS", results[0].message
        )

    def test_cache_invalidation_on_file_update(self):
        self._write_authors(
            [
                "Original Author <orig@example.com>",
            ]
        )
        self.input_api.change.author_email = "newbie@example.com"
        # First check fails
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))

        # Update AUTHORS with newbie@example.com and advance mtime
        new_mtime = os.path.getmtime(self.authors_path) + 2
        self._write_authors(
            [
                "Original Author <orig@example.com>",
                "Newbie <newbie@example.com>",
            ]
        )
        os.utime(self.authors_path, (new_mtime, new_mtime))

        # Second check succeeds via cache reload
        results = presubmit_canned_checks.CheckAuthorizedAuthor(
            self.input_api, self.output_api
        )
        self.assertEqual([], results)


class CheckForCommitObjectsTest(unittest.TestCase):
    def setUp(self):
        self.input_api = MockInputApi()
        self.input_api.change.scm = "git"
        self.input_api.subprocess = mock.Mock()
        self.output_api = MockOutputApi()

        self.patcher = mock.patch("presubmit_canned_checks._ParseDeps")
        self.mock_parse_deps = self.patcher.start()
        self.mock_parse_deps.return_value = {"git_dependencies": "DEPS"}
        self.input_api.change.RepositoryRoot = lambda: ""

    def tearDown(self):
        self.patcher.stop()

    def testNoGitlinks(self):
        # No gitlinks at all.
        self.input_api.subprocess.check_output.side_effect = [
            b"",  # git show HEAD:DEPS
            b"100644 blob 1234\tfile.txt\0",
        ]

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )
        self.assertEqual(0, len(results))

    def testGitlinkFound(self):
        # One gitlink found.
        self.input_api.subprocess.check_output.side_effect = [
            b"",  # git show HEAD:DEPS
            b"160000 commit 1234\tsubmodule\0",
        ]

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))
        self.assertEqual("submodule", results[0].items[0])

    def testGitlinkMiddle(self):
        # Gitlink in the middle of other files.
        self.input_api.subprocess.check_output.side_effect = [
            b"",  # git show HEAD:DEPS
            b"100644 blob 1111\tfile1\0"
            + b"160000 commit 2222\tsubmodule\0"
            + b"100644 blob 3333\tfile2\0",
        ]

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )

        self.assertEqual(1, len(results))
        self.assertEqual("submodule", results[0].items[0])

    def testGitlinkStart(self):
        # Gitlink at the very start.
        self.input_api.subprocess.check_output.side_effect = [
            b"",  # git show HEAD:DEPS
            b"160000 commit 2222\tsubmodule\0" + b"100644 blob 3333\tfile2\0",
        ]

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))
        self.assertEqual("submodule", results[0].items[0])

    def testGitlinkEnd(self):
        # Gitlink at the very end.
        self.input_api.subprocess.check_output.side_effect = [
            b"",  # git show HEAD:DEPS
            b"100644 blob 3333\tfile2\0" + b"160000 commit 2222\tsubmodule\0",
        ]

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))
        self.assertEqual("submodule", results[0].items[0])

    def testMultipleGitlinks(self):
        # Multiple gitlinks.
        self.input_api.subprocess.check_output.side_effect = [
            b"",  # git show HEAD:DEPS
            b"160000 commit 1111\tsub1\0"
            + b"100644 blob 2222\tfile\0"
            + b"160000 commit 3333\tsub2\0",
        ]

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))
        self.assertEqual(2, len(results[0].items))
        self.assertIn("sub1", results[0].items)
        self.assertIn("sub2", results[0].items)

    @mock.patch("configparser.ConfigParser")
    def testMultipleGitlinksWithSameHashSync(self, mock_config_parser):
        # Multiple gitlinks with same hash syncing via DEPS.
        self.mock_parse_deps.return_value = {
            "git_dependencies": "SYNC",
            "deps": {
                "src/third_party/sub1": "https://repo.git@1111",
                "src/third_party/sub2": "https://repo.git@1111",
            },
        }
        self.input_api.subprocess.check_output.side_effect = [
            b"",  # git show HEAD:DEPS
            b"160000 commit 1111\tsrc/third_party/sub1\0"
            + b"160000 commit 1111\tsrc/third_party/sub2\0",
        ]

        mock_instance = mock_config_parser.return_value
        mock_instance.items.return_value = [
            ('submodule "sub1"', {"path": "src/third_party/sub1"}),
            ('submodule "sub2"', {"path": "src/third_party/sub2"}),
        ]

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )

        self.assertEqual(0, len(results))

    def testFalsePositiveText(self):
        # "160000" in filename but not mode.
        self.input_api.subprocess.check_output.side_effect = [
            b"",  # git show HEAD:DEPS
            b"100644 blob 1234\t160000_file.txt\0",
        ]

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )
        self.assertEqual(0, len(results))

    def testRunFromSubdir_SmallFiles_NoSubmodules(self):
        self.input_api.presubmit_local_path = os.path.join(ROOT_DIR, "subdir")
        self.input_api.change.RepositoryRoot = lambda: ROOT_DIR
        self.input_api.files = [MockAffectedFile("foo.txt", "content")]
        self.input_api.subprocess.check_output.return_value = b""

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )
        self.assertEqual(0, len(results))

    def testRunFromSubdir_SmallFiles_WithSubmodules(self):
        self.input_api.presubmit_local_path = os.path.join(ROOT_DIR, "subdir")
        self.input_api.change.RepositoryRoot = lambda: ROOT_DIR
        self.input_api.files = [MockAffectedFile("foo.txt", "content")]
        self.input_api.subprocess.check_output.return_value = (
            b"160000 commit 1234\tsubmodule\0"
        )

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))
        self.assertIn("submodule", results[0].items)

    def testRunFromSubdir_LargeFiles_NoSubmodules(self):
        self.input_api.presubmit_local_path = os.path.join(ROOT_DIR, "subdir")
        self.input_api.change.RepositoryRoot = lambda: ROOT_DIR
        self.input_api.files = [
            MockAffectedFile(f"f{i}", "") for i in range(1001)
        ]
        self.input_api.subprocess.check_output.return_value = b""

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )
        self.assertEqual(0, len(results))

    def testRunFromSubdir_LargeFiles_WithSubmodules(self):
        self.input_api.presubmit_local_path = os.path.join(ROOT_DIR, "subdir")
        self.input_api.change.RepositoryRoot = lambda: ROOT_DIR
        self.input_api.files = [
            MockAffectedFile(f"f{i}", "") for i in range(1001)
        ]
        self.input_api.subprocess.check_output.return_value = (
            b"160000 commit 1234\tsubmodule\0"
        )

        results = presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )
        self.assertEqual(1, len(results))
        self.assertIn("submodule", results[0].items)

    def testWindowsCommandLineLimit(self):
        # On Windows, if the command line is too long, we should fall back to a
        # recursive ls-tree.
        self.input_api.platform = "win32"
        self.input_api.files = [
            MockAffectedFile("a" * 100, "") for i in range(350)
        ]
        self.input_api.subprocess.check_output.return_value = b""

        presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )

        # The first call is to `git show HEAD:DEPS`.
        # The second call is to `git ls-tree`.
        self.assertEqual(2, self.input_api.subprocess.check_output.call_count)
        ls_tree_cmd = self.input_api.subprocess.check_output.call_args_list[1][
            0
        ][0]
        self.assertIn("-r", ls_tree_cmd)

    def testWindowsCommandLineNotTooLong(self):
        # On Windows, if the command line is not too long, we should pass the
        # file list.
        self.input_api.platform = "win32"
        self.input_api.files = [MockAffectedFile("foo.txt", "")]
        self.input_api.subprocess.check_output.return_value = b""

        presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )

        # The first call is to `git show HEAD:DEPS`.
        # The second call is to `git ls-tree`.
        self.assertEqual(2, self.input_api.subprocess.check_output.call_count)
        ls_tree_cmd = self.input_api.subprocess.check_output.call_args_list[1][
            0
        ][0]
        self.assertNotIn("-r", ls_tree_cmd)
        self.assertIn("--", ls_tree_cmd)
        self.assertIn("foo.txt", ls_tree_cmd)

    def testWindowsSpecialCharacters(self):
        # On Windows, if a file contains special characters like '&', we don't
        # need to fall back to a recursive ls-tree when using shell=False.
        self.input_api.platform = "win32"
        self.input_api.files = [MockAffectedFile("foo&bar.txt", "")]
        self.input_api.subprocess.check_output.return_value = b""

        presubmit_canned_checks.CheckForCommitObjects(
            self.input_api, self.output_api
        )

        # The first call is to `git show HEAD:DEPS`.
        # The second call is to `git ls-tree`.
        self.assertEqual(2, self.input_api.subprocess.check_output.call_count)
        ls_tree_cmd = self.input_api.subprocess.check_output.call_args_list[1][
            0
        ][0]
        self.assertNotIn("-r", ls_tree_cmd)
        self.assertIn("foo&bar.txt", ls_tree_cmd)


class CheckPatchFormattedTest(unittest.TestCase):
    def setUp(self):
        self.input_api = MockInputApi()
        self.input_api.change.RepositoryRoot = lambda: ROOT_DIR
        self.input_api.presubmit_local_path = os.path.join(ROOT_DIR, "subdir")
        self.output_api = MockOutputApi()

    def testCheckPatchFormatted_WithFileFilter(self):
        file1 = MockAffectedFile("file1.cc", ["int main() {}"])
        file2 = MockAffectedFile("file2.py", ["def main(): pass"])
        self.input_api.files = [file1, file2]

        # Filter to only include python files
        file_filter = lambda f: f.LocalPath().endswith(".py")  # noqa: E731

        with mock.patch.object(
            self.input_api, "RunTests", return_value=[]
        ) as mock_run_tests:
            presubmit_canned_checks.CheckPatchFormatted(
                self.input_api, self.output_api, file_filter=file_filter
            )
            mock_run_tests.assert_called_once()
            cmd_obj = mock_run_tests.call_args[0][0][0]
            stdin_content = cmd_obj.kwargs["stdin"].decode("utf-8")

            # Verify that only file2.py's diff is in the diff stream
            self.assertIn("file2.py", stdin_content)
            self.assertNotIn("file1.cc", stdin_content)

    def testCheckPatchFormatted_WithoutFileFilter(self):
        file1 = MockAffectedFile("file1.cc", ["int main() {}"])
        file2 = MockAffectedFile("file2.py", ["def main(): pass"])
        self.input_api.files = [file1, file2]

        with mock.patch.object(
            self.input_api, "RunTests", return_value=[]
        ) as mock_run_tests:
            presubmit_canned_checks.CheckPatchFormatted(
                self.input_api, self.output_api
            )
            mock_run_tests.assert_called_once()
            cmd_obj = mock_run_tests.call_args[0][0][0]
            stdin_content = cmd_obj.kwargs["stdin"].decode("utf-8")

            # Verify that both files are in the diff stream
            self.assertIn("file1.cc", stdin_content)
            self.assertIn("file2.py", stdin_content)

    def testCheckPatchFormatted_OutputParser(self):
        file1 = MockAffectedFile("file1.cc", ["int main() {}"])
        self.input_api.files = [file1]

        with mock.patch.object(self.input_api, "RunTests") as mock_run_tests:
            presubmit_canned_checks.CheckPatchFormatted(
                self.input_api, self.output_api
            )
            cmd_obj = mock_run_tests.call_args[0][0][0]
            parser = cmd_obj.output_parser

            # Exit code 0 -> returns None to allow test.info success logging
            self.assertIsNone(parser(0, ""))

            # Exit code 2 -> format warning
            results = parser(2, "Formatting error in file1.cc")
            self.assertEqual(1, len(results))
            self.assertEqual("warning", results[0].type)
            self.assertIn("git cl format", results[0].message)

            # Exit code 1 with bypass_warnings=True -> suppressed
            self.assertEqual([], parser(1, "Tool error"))

    def testMockInputApiRunTestsLegacyParserExitCode(self):
        # Legacy 1-arg parser returning [] on failure falls through to error
        def legacy_parser(output):
            return []

        def returncode_aware_parser(code, output):
            if code == 1:
                return []  # Suppress
            return []

        from testing_support.presubmit_canned_checks_test_mocks import (
            MockCommand,
        )

        cmd1 = MockCommand(
            "legacy_fail", ["fake_cmd"], {}, output_parser=legacy_parser
        )
        cmd2 = MockCommand(
            "code_aware_suppressed",
            ["fake_cmd"],
            {},
            output_parser=returncode_aware_parser,
        )

        with mock.patch.object(
            self.input_api.subprocess, "Popen"
        ) as mock_popen:
            mock_proc = mock.Mock()
            mock_proc.returncode = 1
            mock_proc.communicate.return_value = (b"output", b"")
            mock_popen.return_value = mock_proc

            results1 = self.input_api.RunTests([cmd1])
            self.assertEqual(1, len(results1))
            self.assertIn("legacy_fail", results1[0].message)

            results2 = self.input_api.RunTests([cmd2])
            self.assertEqual(0, len(results2))

    def testMockInputApiRunTestsStdinHandling(self):
        from testing_support.presubmit_canned_checks_test_mocks import (
            MockCommand,
        )

        stream_stdin = io.StringIO("stream_content")
        cmd_bytes = MockCommand(
            "bytes_test", ["fake_cmd"], {"stdin": b"payload"}
        )
        cmd_stream = MockCommand(
            "stream_test", ["fake_cmd"], {"stdin": stream_stdin}
        )

        with mock.patch.object(
            self.input_api.subprocess, "Popen"
        ) as mock_popen:
            mock_proc = mock.Mock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"output", b"")
            mock_popen.return_value = mock_proc

            self.input_api.RunTests([cmd_bytes, cmd_stream])

            self.assertEqual(2, mock_popen.call_count)
            # Bytes stdin sets kwargs['stdin'] to PIPE and passes payload to communicate()
            self.assertEqual(
                subprocess.PIPE, mock_popen.call_args_list[0][1]["stdin"]
            )
            self.assertEqual(
                b"payload", mock_proc.communicate.call_args_list[0][1]["input"]
            )
            # Stream stdin preserves stream in kwargs['stdin'] and passes None to communicate()
            self.assertEqual(
                stream_stdin, mock_popen.call_args_list[1][1]["stdin"]
            )
            self.assertIsNone(
                mock_proc.communicate.call_args_list[1][1]["input"]
            )


if __name__ == "__main__":
    unittest.main()
