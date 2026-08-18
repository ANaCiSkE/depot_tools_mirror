#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Live integration tests for luci_triage.py.

Dynamically discovers fresh CI builds and tests against live endpoints.
Prints structured test results for LLM agent confirmation.
Requires `bb auth-login`.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import luci_triage

SAMPLE_BUILDER = "android-13-x64-rel"
SAMPLE_CL = "8260911"
SAMPLE_JAVA_TEST_QUERY = "ExampleFreshCtaTest"
SAMPLE_JAVA_TEST_ID = (
    "://chrome/android\\:chrome_public_test_apk!junit:"
    "org.chromium.chrome.browser:ExampleFreshCtaTest#testStartOnBlankPage"
)
SAMPLE_CPP_TEST_QUERY = "JSONReaderTest"
SAMPLE_CPP_TEST_ID = (
    "://base\\:base_unittests!gtest::JSONReaderTest#ASCIIControlCodes"
)


class TestLuciTriageIntegration(unittest.TestCase):
    success_build_id = None
    success_build_num = None
    failure_build_id = None
    failure_build_num = None

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 80)
        print("[LUCI Integration Test] Starting live endpoint validation")
        print("=" * 80)

        if not luci_triage.is_authenticated():
            print("[AUTH] Not authenticated to LUCI (run 'bb auth-login')")
            return

        # Dynamically discover the latest SUCCESS CI build
        res_success = luci_triage.run_prpc(
            "cr-buildbucket.appspot.com",
            "buildbucket.v2.Builds.SearchBuilds",
            {
                "predicate": {
                    "builder": {
                        "project": "chromium",
                        "bucket": "ci",
                        "builder": SAMPLE_BUILDER,
                    },
                    "status": "SUCCESS",
                },
                "pageSize": 1,
            },
        )
        if res_success and res_success.get("builds"):
            cls.success_build_id = res_success["builds"][0]["id"]
            cls.success_build_num = res_success["builds"][0]["number"]
            print(
                f"[DISCOVERY] Latest SUCCESS CI build: {SAMPLE_BUILDER}/"
                f"{cls.success_build_num} (id: {cls.success_build_id})"
            )
        else:
            cls.success_build_id = None
            cls.success_build_num = None

        # Dynamically discover the latest FAILURE CI build
        res_fail = luci_triage.run_prpc(
            "cr-buildbucket.appspot.com",
            "buildbucket.v2.Builds.SearchBuilds",
            {
                "predicate": {
                    "builder": {
                        "project": "chromium",
                        "bucket": "ci",
                        "builder": SAMPLE_BUILDER,
                    },
                    "status": "FAILURE",
                },
                "pageSize": 1,
            },
        )
        if res_fail and res_fail.get("builds"):
            cls.failure_build_id = res_fail["builds"][0]["id"]
            cls.failure_build_num = res_fail["builds"][0]["number"]
            print(
                f"[DISCOVERY] Latest FAILURE CI build: {SAMPLE_BUILDER}/"
                f"{cls.failure_build_num} (id: {cls.failure_build_id})"
            )
        else:
            cls.failure_build_id = None
            cls.failure_build_num = None

        print(
            f"[DISCOVERY] Target Test Queries: '{SAMPLE_JAVA_TEST_QUERY}' (Java),"
            f" '{SAMPLE_CPP_TEST_QUERY}' (C++ GTest)"
        )
        print("-" * 80)

    def setUp(self):
        if not luci_triage.is_authenticated():
            self.skipTest("Not authenticated to LUCI (run 'bb auth-login')")
        if not self.success_build_id:
            self.skipTest("Could not discover latest CI build for builder")

    def test_resolve_build_id(self):
        build_id = luci_triage.resolve_build_id(
            "chromium", "ci", SAMPLE_BUILDER, self.success_build_num
        )
        self.assertEqual(build_id, self.success_build_id)
        print(
            f"[PASS] resolve_build_id: {SAMPLE_BUILDER}/{self.success_build_num}"
            f" -> {build_id}"
        )

    def test_get_build(self):
        data = luci_triage.get_build(f"b{self.success_build_id}")
        self.assertEqual(data.get("status"), "SUCCESS")
        self.assertEqual(data.get("id"), self.success_build_id)
        print(
            f"[PASS] get_build: Build {self.success_build_id} status = "
            f"{data.get('status')}"
        )

    def test_find_cl_builds(self):
        # Test default behavior: queries Gerrit REST API for latest patchset
        builds_latest = luci_triage.find_cl_builds(SAMPLE_CL)
        self.assertIsInstance(builds_latest, list)
        self.assertTrue(
            all("builder" in b and "id" in b for b in builds_latest)
        )
        print(
            f"[PASS] find_cl_builds (latest patchset via Gerrit): Found "
            f"{len(builds_latest)} non-success build(s) for CL {SAMPLE_CL}"
        )

        # Test show_all=True: returns all builds including SUCCESS/STARTED
        builds_all = luci_triage.find_cl_builds(SAMPLE_CL, show_all=True)
        self.assertGreater(len(builds_all), 0)
        self.assertGreaterEqual(len(builds_all), len(builds_latest))
        print(
            f"[PASS] find_cl_builds (show_all=True): Found {len(builds_all)} "
            f"total build(s) for latest patchset"
        )

    def test_check_test_in_build(self):
        for query, lang in [
            (SAMPLE_JAVA_TEST_QUERY, "Java"),
            (SAMPLE_CPP_TEST_QUERY, "C++"),
        ]:
            res = luci_triage.check_test(f"b{self.success_build_id}", query)
            self.assertGreater(len(res), 0)
            self.assertTrue(any(query in r.get("id", "") for r in res))
            print(
                f"[PASS] check_test ({lang}): Found {len(res)} test result(s) for "
                f"'{query}' in build {self.success_build_id}:"
            )
            for tr in res[:2]:
                print(f"       - {tr.get('id')} ({tr.get('status')})")

    def test_test_history(self):
        for test_id, suite, label in [
            (SAMPLE_JAVA_TEST_ID, "chrome_public_test_apk", "Java JUnit"),
            (SAMPLE_CPP_TEST_ID, "base_unittests", "C++ GTest"),
        ]:
            verdicts = luci_triage.test_history(
                "chromium",
                test_id,
                limit=5,
                builder=SAMPLE_BUILDER,
                test_suite=suite,
            )
            self.assertGreaterEqual(len(verdicts), 1)
            self.assertEqual(verdicts[0].get("testId"), test_id)
            print(
                f"[PASS] test_history ({label}): Queried {len(verdicts)} verdict(s)"
                f" for {test_id.split('!')[-1]} on {SAMPLE_BUILDER}"
            )

    def test_list_failures_and_fetch_log(self):
        if not self.failure_build_id:
            self.skipTest("No recent failing build found for builder")

        res = luci_triage.list_failures(f"b{self.failure_build_id}")
        if not res:
            self.skipTest(
                f"Build {self.failure_build_id} has no failed test variants in"
                " ResultDB (likely a compile/infra step failure)"
            )
        first_task = next(iter(res))
        self.assertIn("id", res[first_task][0])
        self.assertIn("res", res[first_task][0])

        first_res_name = res[first_task][0]["res"]
        first_test_id = res[first_task][0]["id"]
        output = luci_triage.fetch_log_snippet(first_res_name)
        self.assertGreater(len(output), 0)

        preview = output.strip().split("\n")[0][:100]
        print(
            f"[PASS] list_failures_and_fetch_log: Build {self.failure_build_id} "
            f"has {len(res)} failing task(s).\n"
            f"       Fetched log snippet for {first_test_id} ({len(output)} bytes).\n"
            f"       Log preview: {preview}..."
        )


if __name__ == "__main__":
    unittest.main()
