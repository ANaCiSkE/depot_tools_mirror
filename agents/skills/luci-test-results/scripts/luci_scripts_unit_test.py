#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for modular luci-test-results scripts."""

import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_test
import fetch_log
import find_cl_builds
import list_failures
import luci_client
import test_history

SAMPLE_BUILD_ID = "8000000000000000001"
SAMPLE_BUILD_ID_SUCCESS = "8000000000000000002"
SAMPLE_BUILD_ID_2 = "8000000000000000003"
SAMPLE_BUILD_ID_3 = "8000000000000000004"
SAMPLE_BUILD_NUM = 12345
SAMPLE_BUILDER = "android-13-x64-rel"
SAMPLE_CL = "1234567"
SAMPLE_TASK_ID = "chromium-swarm.appspot.com-sampletaskid123"
SAMPLE_TEST_QUERY = "JSONReaderTest"
SAMPLE_TEST_ID = (
    "://base\\:base_unittests!gtest::JSONReaderTest#ASCIIControlCodes"
)
SAMPLE_RESULT_NAME = (
    f"invocations/task-{SAMPLE_TASK_ID}/tests/"
    ":%2F%2Fbase%5C:base_unittests%21gtest::"
    "JSONReaderTest%23ASCIIControlCodes/results/sample-result-id"
)


class TestLuciScripts(unittest.TestCase):
    @mock.patch("luci_client.subprocess.Popen")
    def test_run_prpc_success(self, mock_popen):
        mock_proc = mock.MagicMock()
        mock_proc.communicate.return_value = ('{"foo": "bar"}', "")
        mock_proc.returncode = 0
        mock_popen.return_value.__enter__.return_value = mock_proc

        res = luci_client.run_prpc("service.example.com", "Method", {"k": "v"})
        self.assertEqual(res, {"foo": "bar"})

    @mock.patch("sys.stderr", new_callable=io.StringIO)
    @mock.patch("luci_client.subprocess.Popen")
    def test_run_prpc_error(self, mock_popen, mock_stderr):
        mock_proc = mock.MagicMock()
        mock_proc.communicate.return_value = ("", "rpc error")
        mock_proc.returncode = 1
        mock_popen.return_value.__enter__.return_value = mock_proc

        res = luci_client.run_prpc("service.example.com", "Method", {"k": "v"})
        self.assertIsNone(res)

    @mock.patch("luci_client.subprocess.run")
    def test_is_authenticated(self, mock_run):
        mock_run.return_value.returncode = 0
        self.assertTrue(luci_client.is_authenticated())

        mock_run.return_value.returncode = 1
        self.assertFalse(luci_client.is_authenticated())

        mock_run.side_effect = FileNotFoundError()
        self.assertFalse(luci_client.is_authenticated())

    @mock.patch("luci_client.run_prpc")
    def test_resolve_build_id(self, mock_prpc):
        mock_prpc.return_value = {"id": SAMPLE_BUILD_ID_SUCCESS}
        build_id = luci_client.resolve_build_id(
            "chromium", "ci", SAMPLE_BUILDER, SAMPLE_BUILD_NUM
        )
        self.assertEqual(build_id, SAMPLE_BUILD_ID_SUCCESS)
        mock_prpc.assert_called_once_with(
            "cr-buildbucket.appspot.com",
            "buildbucket.v2.Builds.GetBuild",
            {
                "builder": {
                    "project": "chromium",
                    "bucket": "ci",
                    "builder": SAMPLE_BUILDER,
                },
                "buildNumber": SAMPLE_BUILD_NUM,
            },
        )

    @mock.patch("luci_client.run_prpc")
    def test_get_build(self, mock_prpc):
        mock_prpc.return_value = {
            "id": SAMPLE_BUILD_ID_SUCCESS,
            "status": "SUCCESS",
        }
        data = luci_client.get_build(f"b{SAMPLE_BUILD_ID_SUCCESS}")
        self.assertEqual(data["status"], "SUCCESS")
        mock_prpc.assert_called_once_with(
            "cr-buildbucket.appspot.com",
            "buildbucket.v2.Builds.GetBuild",
            {
                "id": SAMPLE_BUILD_ID_SUCCESS,
                "mask": {
                    "fields": "id,builder,number,status,summaryMarkdown,output"
                },
            },
        )

    @mock.patch("find_cl_builds.run_prpc")
    def test_find_cl_builds_with_patchset(self, mock_prpc):
        mock_prpc.return_value = {
            "builds": [
                {
                    "builder": {"builder": "linux-rel"},
                    "status": "FAILURE",
                    "id": SAMPLE_BUILD_ID,
                },
                {
                    "builder": {"builder": "mac-rel"},
                    "status": "STARTED",
                    "id": SAMPLE_BUILD_ID_2,
                },
                {
                    "builder": {"builder": "android-arm64-rel"},
                    "status": "SUCCESS",
                    "id": SAMPLE_BUILD_ID_3,
                },
            ]
        }
        failed = find_cl_builds.find_cl_builds(SAMPLE_CL, patchset=1)
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["builder"], "linux-rel")

        all_builds = find_cl_builds.find_cl_builds(
            SAMPLE_CL, patchset=1, show_all=True
        )
        self.assertEqual(len(all_builds), 3)

    @mock.patch("find_cl_builds.subprocess.check_output")
    @mock.patch("find_cl_builds.run_prpc")
    def test_find_cl_builds_default_patchset(
        self, mock_prpc, mock_check_output
    ):
        gerrit_json = (
            ")]}'\n"
            '{"current_revision": "rev1", "revisions": {"rev1": {"_number": 3}}}'
        )
        mock_check_output.return_value = gerrit_json.encode("utf-8")
        mock_prpc.return_value = {
            "builds": [
                {
                    "builder": {"builder": "linux-rel"},
                    "status": "FAILURE",
                    "id": SAMPLE_BUILD_ID,
                }
            ]
        }
        builds = find_cl_builds.find_cl_builds(SAMPLE_CL)
        self.assertEqual(len(builds), 1)
        mock_prpc.assert_called_once_with(
            "cr-buildbucket.appspot.com",
            "buildbucket.v2.Builds.SearchBuilds",
            {
                "predicate": {
                    "gerritChanges": [
                        {
                            "host": "chromium-review.googlesource.com",
                            "change": int(SAMPLE_CL),
                            "patchset": 3,
                        }
                    ]
                }
            },
        )

    @mock.patch("list_failures.run_prpc")
    def test_list_failures_grouped_by_task(self, mock_prpc):
        mock_prpc.return_value = {
            "testVariants": [
                {
                    "testId": SAMPLE_TEST_ID,
                    "status": "UNEXPECTED",
                    "results": [
                        {
                            "result": {
                                "name": SAMPLE_RESULT_NAME,
                                "status": "FAIL",
                                "failureReason": {
                                    "primaryErrorMessage": "AssertionError"
                                },
                            }
                        }
                    ],
                },
                {
                    "testId": "ninja://test/Class#methodB",
                    "status": "FLAKY",
                    "results": [
                        {
                            "result": {
                                "name": f"invocations/task-{SAMPLE_TASK_ID}/tests/testB/results/1",
                                "status": "FAIL",
                            }
                        }
                    ],
                },
                {
                    "testId": "ninja://test/Class#methodC",
                    "status": "EXONERATED",
                    "results": [
                        {
                            "result": {
                                "name": f"invocations/task-{SAMPLE_TASK_ID}/tests/testC/results/1",
                                "status": "FAIL",
                            }
                        }
                    ],
                },
            ]
        }

        # Default excludes EXONERATED, includes FLAKY and UNEXPECTED
        res = list_failures.list_failures(f"b{SAMPLE_BUILD_ID}")
        self.assertIn(SAMPLE_TASK_ID, res)
        self.assertEqual(len(res[SAMPLE_TASK_ID]), 2)
        self.assertEqual(res[SAMPLE_TASK_ID][0]["id"], SAMPLE_TEST_ID)
        self.assertEqual(res[SAMPLE_TASK_ID][0]["err"], "AssertionError")

        # Ignore flaky
        res_no_flake = list_failures.list_failures(
            SAMPLE_BUILD_ID, ignore_flaky=True
        )
        self.assertEqual(len(res_no_flake[SAMPLE_TASK_ID]), 1)
        self.assertEqual(res_no_flake[SAMPLE_TASK_ID][0]["id"], SAMPLE_TEST_ID)

        # Include exonerated
        res_exonerated = list_failures.list_failures(
            SAMPLE_BUILD_ID, include_exonerated=True
        )
        self.assertEqual(len(res_exonerated[SAMPLE_TASK_ID]), 3)

        # Limit results
        res_limit = list_failures.list_failures(SAMPLE_BUILD_ID, limit=1)
        self.assertEqual(len(res_limit[SAMPLE_TASK_ID]), 1)

    @mock.patch("list_failures.run_prpc")
    def test_list_failures_pagination(self, mock_prpc):
        mock_prpc.side_effect = [
            {
                "testVariants": [
                    {
                        "testId": "ninja://test/Class#method1",
                        "status": "UNEXPECTED",
                        "results": [
                            {
                                "result": {
                                    "name": "invocations/task-task1/tests/test1/results/1",
                                    "status": "FAIL",
                                }
                            }
                        ],
                    }
                ],
                "nextPageToken": "token123",
            },
            {
                "testVariants": [
                    {
                        "testId": "ninja://test/Class#method2",
                        "status": "UNEXPECTED",
                        "results": [
                            {
                                "result": {
                                    "name": "invocations/task-task2/tests/test2/results/1",
                                    "status": "FAIL",
                                }
                            }
                        ],
                    }
                ]
            },
        ]
        res = list_failures.list_failures(SAMPLE_BUILD_ID)
        self.assertEqual(len(res), 2)
        self.assertIn("task1", res)
        self.assertIn("task2", res)

    @mock.patch("fetch_log.subprocess.check_output")
    @mock.patch("fetch_log.run_prpc")
    def test_fetch_log_snippet_regex(self, mock_prpc, mock_check_output):
        mock_prpc.return_value = {
            "artifacts": [
                {
                    "artifactId": "test_log",
                    "fetchUrl": "https://logs.example.com/log.txt",
                }
            ]
        }
        sample_log = (
            "[ RUN      ] SomeTest.Foo\n"
            "Line 2\n"
            "org.junit.ComparisonFailure: expected:<[a]> but was:<[b]>\n"
            "  at java.lang.AssertionError\n"
            "[  FAILED  ] SomeTest.Foo\n"
        )
        mock_check_output.return_value = sample_log.encode("utf-8")

        output = fetch_log.fetch_log_snippet(SAMPLE_RESULT_NAME)
        self.assertIn("[ RUN      ]", output)

    @mock.patch("fetch_log.subprocess.check_output")
    @mock.patch("fetch_log.run_prpc")
    def test_fetch_log_snippet_raw(self, mock_prpc, mock_check_output):
        mock_prpc.return_value = {
            "artifacts": [
                {
                    "artifactId": "stdout",
                    "fetchUrl": "https://logs.example.com/stdout.txt",
                }
            ]
        }
        sample_log = "Raw log output without matches"
        mock_check_output.return_value = sample_log.encode("utf-8")

        output = fetch_log.fetch_log_snippet(SAMPLE_RESULT_NAME, raw=True)
        self.assertEqual(output, sample_log)

    @mock.patch("fetch_log.is_authenticated")
    @mock.patch("fetch_log.run_prpc")
    def test_fetch_log_snippet_no_artifacts(
        self, mock_prpc, mock_is_authenticated
    ):
        mock_is_authenticated.return_value = False

        for empty_val in ({}, {"artifacts": []}, None):
            mock_prpc.return_value = empty_val
            output = fetch_log.fetch_log_snippet(
                "invocations/task-123/tests/foo/results/1"
            )
            self.assertIn("No artifacts found", output)
            self.assertIn("bb auth-login", output)

    @mock.patch("check_test.run_prpc")
    def test_check_test(self, mock_prpc):
        mock_prpc.return_value = {
            "testResults": [
                {
                    "name": SAMPLE_RESULT_NAME,
                    "testId": SAMPLE_TEST_ID,
                    "status": "FAIL",
                    "failureReason": {
                        "primaryErrorMessage": "Expected 1 to equal 2"
                    },
                }
            ]
        }
        res = check_test.check_test(f"b{SAMPLE_BUILD_ID}", SAMPLE_TEST_QUERY)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["status"], "FAIL")
        self.assertFalse(res[0]["expected"])
        self.assertEqual(res[0]["res"], SAMPLE_RESULT_NAME)
        self.assertEqual(res[0]["err"], "Expected 1 to equal 2")
        mock_prpc.assert_called_once_with(
            "results.api.luci.app",
            "luci.resultdb.v1.ResultDB.QueryTestResults",
            {
                "invocations": [f"invocations/build-{SAMPLE_BUILD_ID}"],
                "predicate": {
                    "testIdRegexp": f".*{SAMPLE_TEST_QUERY}.*",
                    "expectancy": "ALL",
                },
                "pageSize": 1000,
            },
        )

    @mock.patch("fetch_log.fetch_log_snippet")
    def test_fetch_log_helper_alias(self, mock_snippet):
        mock_snippet.return_value = "snippet-text"
        self.assertEqual(
            fetch_log.fetch_log(SAMPLE_RESULT_NAME, raw=True), "snippet-text"
        )
        mock_snippet.assert_called_once_with(SAMPLE_RESULT_NAME, raw=True)

    @mock.patch("test_history.run_prpc")
    def test_test_history(self, mock_prpc):
        mock_prpc.return_value = {
            "verdicts": [
                {
                    "testId": SAMPLE_TEST_ID,
                    "status": "EXPECTED",
                }
            ]
        }
        verdicts = test_history.test_history(
            "chromium",
            SAMPLE_TEST_ID,
            limit=5,
            builder=SAMPLE_BUILDER,
            test_suite="base_unittests",
        )
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0]["status"], "EXPECTED")
        mock_prpc.assert_called_once_with(
            "analysis.api.luci.app",
            "luci.analysis.v1.TestHistory.Query",
            {
                "project": "chromium",
                "testId": SAMPLE_TEST_ID,
                "predicate": {
                    "variantPredicate": {
                        "contains": {
                            "def": {
                                "builder": SAMPLE_BUILDER,
                                "test_suite": "base_unittests",
                            }
                        }
                    }
                },
                "pageSize": 5,
            },
        )

    @mock.patch("test_history.run_prpc")
    def test_test_history_pagination(self, mock_prpc):
        mock_prpc.side_effect = [
            {
                "verdicts": [
                    {"testId": SAMPLE_TEST_ID, "status": "UNEXPECTED"}
                ],
                "nextPageToken": "page2",
            },
            {
                "verdicts": [{"testId": SAMPLE_TEST_ID, "status": "EXPECTED"}],
            },
        ]
        verdicts = test_history.test_history(
            "chromium", SAMPLE_TEST_ID, limit=2
        )
        self.assertEqual(len(verdicts), 2)
        self.assertEqual(mock_prpc.call_count, 2)

    @mock.patch("test_history.run_prpc")
    def test_query_variant_builders_and_format_summary(self, mock_prpc):
        mock_prpc.return_value = {
            "variants": [
                {
                    "variantHash": "hash1",
                    "variant": {"def": {"bucket": "ci", "builder": "bot-fail"}},
                },
                {
                    "variantHash": "hash2",
                    "variant": {"def": {"bucket": "ci", "builder": "bot-pass"}},
                },
            ]
        }
        mapping = test_history.query_variant_builders(
            "chromium", SAMPLE_TEST_ID
        )
        self.assertEqual(mapping["hash1"], "ci/bot-fail")

        verdicts = [
            {
                "variantHash": "hash1",
                "status": "UNEXPECTED",
                "partitionTime": "2026-08-25T12:00:00Z",
            },
            {
                "variantHash": "hash1",
                "status": "EXPECTED",
                "partitionTime": "2026-08-25T10:00:00Z",
            },
            {
                "variantHash": "hash2",
                "status": "EXPECTED",
                "partitionTime": "2026-08-25T11:00:00Z",
            },
        ]
        summary = test_history.format_summary(
            verdicts, variant_builders=mapping
        )
        self.assertIn("Builder: ci/bot-fail | Pass: 1, Fail: 1", summary)
        self.assertIn("Recent (newest->oldest): FP", summary)
        self.assertIn(
            "100% Passing Builders (1): ci/bot-pass (1 pass)", summary
        )

    @mock.patch("test_history.run_prpc")
    def test_query_tests(self, mock_prpc):
        mock_prpc.return_value = {"testIds": [SAMPLE_TEST_ID]}
        candidates = test_history.query_tests("chromium", SAMPLE_TEST_QUERY)
        self.assertEqual(candidates, [SAMPLE_TEST_ID])
        mock_prpc.assert_called_once_with(
            "analysis.api.luci.app",
            "luci.analysis.v1.TestHistory.QueryTests",
            {"project": "chromium", "testIdSubstring": SAMPLE_TEST_QUERY},
        )

    @mock.patch("test_history.run_prpc")
    def test_fetch_multi_builder_history(self, mock_prpc):
        def side_effect(service, method, payload):
            if method == "luci.analysis.v1.TestHistory.QueryVariants":
                return {
                    "variants": [
                        {
                            "variantHash": "h1",
                            "variant": {
                                "def": {"bucket": "ci", "builder": "b1"}
                            },
                        },
                        {
                            "variantHash": "h2",
                            "variant": {
                                "def": {"bucket": "ci", "builder": "b2"}
                            },
                        },
                    ]
                }
            return {
                "verdicts": [
                    {
                        "testId": SAMPLE_TEST_ID,
                        "status": "EXPECTED",
                        "variantHash": "h1",
                    }
                ]
            }

        mock_prpc.side_effect = side_effect
        verdicts, mapping = test_history.fetch_multi_builder_history(
            "chromium", SAMPLE_TEST_ID, per_builder_limit=5
        )
        self.assertEqual(len(verdicts), 2)
        self.assertEqual(mapping["h1"], "ci/b1")
        self.assertEqual(mapping["h2"], "ci/b2")

    @mock.patch("test_history.run_prpc")
    def test_query_variant_builders_uses_variant_predicate(self, mock_prpc):
        mock_prpc.return_value = {"variants": []}
        pred = {"variantPredicate": {"contains": {"def": {"bucket": "ci"}}}}
        test_history.query_variant_builders(
            "chromium", SAMPLE_TEST_ID, predicate=pred
        )
        mock_prpc.assert_called_once_with(
            "analysis.api.luci.app",
            "luci.analysis.v1.TestHistory.QueryVariants",
            {
                "project": "chromium",
                "testId": SAMPLE_TEST_ID,
                "pageSize": 1000,
                "variantPredicate": {"contains": {"def": {"bucket": "ci"}}},
            },
        )

    @mock.patch("sys.stderr", new_callable=io.StringIO)
    @mock.patch("test_history.run_prpc")
    def test_fetch_multi_builder_history_truncation_notice(
        self, mock_prpc, mock_stderr
    ):
        def side_effect(service, method, payload):
            if method == "luci.analysis.v1.TestHistory.QueryVariants":
                return {
                    "variants": [
                        {
                            "variantHash": f"h{i}",
                            "variant": {
                                "def": {"bucket": "ci", "builder": f"b{i}"}
                            },
                        }
                        for i in range(3)
                    ]
                }
            return {"verdicts": []}

        mock_prpc.side_effect = side_effect
        test_history.fetch_multi_builder_history(
            "chromium", SAMPLE_TEST_ID, max_builders=2
        )
        self.assertIn(
            "Notice: Querying 2 of 3 discovered builders",
            mock_stderr.getvalue(),
        )

    @mock.patch("sys.stderr", new_callable=io.StringIO)
    @mock.patch("test_history.test_history")
    @mock.patch("test_history.query_variant_builders")
    def test_fetch_multi_builder_history_handles_worker_exception(
        self, mock_variants, mock_history, mock_stderr
    ):
        mock_variants.return_value = {"h1": "ci/b1", "h2": "ci/b2"}

        def history_side_effect(project, test_id, **kwargs):
            if kwargs.get("builder") == "b1":
                raise RuntimeError("Transient RPC failure")
            return [
                {
                    "testId": SAMPLE_TEST_ID,
                    "status": "EXPECTED",
                    "variantHash": "h2",
                }
            ]

        mock_history.side_effect = history_side_effect
        verdicts, _ = test_history.fetch_multi_builder_history(
            "chromium", SAMPLE_TEST_ID
        )
        self.assertEqual(len(verdicts), 1)
        self.assertIn(
            "Warning: Failed to fetch history", mock_stderr.getvalue()
        )

    def test_format_summary_includes_daily_skip_count(self):
        verdicts = [
            {
                "variantHash": "h1",
                "status": "SKIPPED",
                "partitionTime": "2026-08-25T12:00:00Z",
            }
        ]
        summary = test_history.format_summary(
            verdicts, default_builder="ci/bot-skip"
        )
        self.assertIn("Skip=1", summary)

    @mock.patch("sys.stdout", new_callable=io.StringIO)
    @mock.patch("sys.stderr", new_callable=io.StringIO)
    @mock.patch("test_history.query_tests")
    @mock.patch("test_history.test_history")
    def test_main_empty_verdicts_raw_and_self_filter(
        self, mock_history, mock_query_tests, mock_stderr, mock_stdout
    ):
        mock_history.return_value = []
        # 1. --raw should print "[]" and not exit with error
        with mock.patch(
            "sys.argv",
            [
                "test_history.py",
                "--test-id",
                SAMPLE_TEST_ID,
                "--builder",
                "b1",
                "--raw",
            ],
        ):
            test_history.main()
        self.assertEqual(mock_stdout.getvalue().strip(), "[]")

        # 2. Non-raw should filter out args.test_id from suggestions
        mock_query_tests.return_value = [SAMPLE_TEST_ID, "other_candidate_id"]
        with mock.patch(
            "sys.argv",
            [
                "test_history.py",
                "--test-id",
                SAMPLE_TEST_ID,
                "--builder",
                "b1",
            ],
        ):
            with self.assertRaises(SystemExit):
                test_history.main()
        stderr_out = mock_stderr.getvalue()
        self.assertIn("other_candidate_id", stderr_out)
        self.assertNotIn(f"  {SAMPLE_TEST_ID}", stderr_out)

    @mock.patch("sys.stderr", new_callable=io.StringIO)
    @mock.patch("find_cl_builds.subprocess.check_output")
    @mock.patch("find_cl_builds.run_prpc")
    def test_find_cl_builds_fallback_patchset(
        self, mock_prpc, mock_check_output, mock_stderr
    ):
        gerrit_json = (
            ")]}'\n"
            '{"current_revision": "rev4", "revisions": {"rev4": {"_number": 4}}}'
        )
        mock_check_output.return_value = gerrit_json.encode("utf-8")
        mock_prpc.side_effect = [
            # PS 4 (post-submit revision) has 0 builds
            {"builds": []},
            # PS 3 has trybot builds
            {
                "builds": [
                    {
                        "builder": {"builder": "linux-rel"},
                        "status": "FAILURE",
                        "id": SAMPLE_BUILD_ID,
                    }
                ]
            },
        ]
        builds = find_cl_builds.find_cl_builds(SAMPLE_CL)
        self.assertEqual(len(builds), 1)
        self.assertEqual(builds[0]["builder"], "linux-rel")
        self.assertEqual(builds[0]["patchset"], 3)
        self.assertEqual(mock_prpc.call_count, 2)
        self.assertIn(
            "Notice: No builds on patchset 4; using patchset 3.",
            mock_stderr.getvalue(),
        )

    @mock.patch("find_cl_builds.subprocess.check_output")
    @mock.patch("find_cl_builds.run_prpc")
    def test_find_cl_builds_rpc_failure_no_fallback(
        self, mock_prpc, mock_check_output
    ):
        gerrit_json = (
            ")]}'\n"
            '{"current_revision": "rev4", "revisions": {"rev4": {"_number": 4}}}'
        )
        mock_check_output.return_value = gerrit_json.encode("utf-8")
        mock_prpc.return_value = None
        builds = find_cl_builds.find_cl_builds(SAMPLE_CL)
        self.assertEqual(builds, [])
        # Should stop immediately on None rather than looping across patchsets
        self.assertEqual(mock_prpc.call_count, 1)

    @mock.patch("sys.stdout", new_callable=io.StringIO)
    @mock.patch("sys.stderr", new_callable=io.StringIO)
    @mock.patch("test_history.query_tests")
    @mock.patch("test_history.test_history")
    def test_main_substring_resolution(
        self, mock_history, mock_query_tests, mock_stderr, mock_stdout
    ):
        # Prefix-overlapping and non-delimiter suffix candidates:
        # bounded suffix match (preceded by ':') should win.
        prefix_overlap_id = f"{SAMPLE_TEST_ID}NoEmptyElements"
        non_delim_suffix_id = "://base\\:base_unittests!gtest::OtherJSONReaderTest#ASCIIControlCodes"
        mock_query_tests.return_value = [
            prefix_overlap_id,
            non_delim_suffix_id,
            SAMPLE_TEST_ID,
        ]
        mock_history.return_value = [
            {"testId": SAMPLE_TEST_ID, "status": "EXPECTED"}
        ]
        with mock.patch(
            "sys.argv",
            [
                "test_history.py",
                "--test-id",
                "JSONReaderTest#ASCIIControlCodes",
                "--builder",
                SAMPLE_BUILDER,
                "--raw",
            ],
        ):
            test_history.main()
        mock_history.assert_called_once_with(
            "chromium",
            SAMPLE_TEST_ID,
            limit=test_history.DEFAULT_SINGLE_BUILDER_LIMIT,
            builder=SAMPLE_BUILDER,
            bucket=None,
            device_os=None,
            device_type=None,
            os_val=None,
            test_suite=None,
        )

        # Unresolved substring should exit early with code 1 without calling test_history
        mock_history.reset_mock()
        mock_query_tests.return_value = []
        with mock.patch(
            "sys.argv",
            [
                "test_history.py",
                "--test-substring",
                "NonExistentTest#foo",
                "--raw",
            ],
        ):
            with self.assertRaises(SystemExit) as cm:
                test_history.main()
            self.assertEqual(cm.exception.code, 1)
        mock_history.assert_not_called()

        # Passing both --test-id and --test-substring is rejected by mutually exclusive group
        with mock.patch(
            "sys.argv",
            [
                "test_history.py",
                "--test-id",
                SAMPLE_TEST_ID,
                "--test-substring",
                "JSONReaderTest",
            ],
        ):
            with self.assertRaises(SystemExit) as cm:
                test_history.main()
            self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
