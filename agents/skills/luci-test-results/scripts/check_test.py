#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Check if tests matching a regex ran in a specific build."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luci_client import resolve_build_id, run_prpc


def check_test(build_id, test_regex):
    """Checks if a test matching regex ran in the build using QueryTestResults."""
    if build_id.startswith("b"):
        build_id = build_id[1:]

    if not test_regex.startswith(".*"):
        test_regex = ".*" + test_regex
    if not test_regex.endswith(".*"):
        test_regex = test_regex + ".*"

    payload = {
        "invocations": [f"invocations/build-{build_id}"],
        "predicate": {"testIdRegexp": test_regex, "expectancy": "ALL"},
        "pageSize": 1000,
    }

    test_results = []
    while True:
        result = run_prpc(
            "results.api.luci.app",
            "luci.resultdb.v1.ResultDB.QueryTestResults",
            payload,
        )
        if result is None:
            print("Error: Failed to query ResultDB", file=sys.stderr)
            break

        test_results.extend(result.get("testResults", []))

        if "nextPageToken" not in result:
            break
        payload["pageToken"] = result["nextPageToken"]

    matching_tests = []
    for tr in test_results:
        matching_tests.append(
            {
                "id": tr["testId"],
                "status": tr.get("status"),
                "expected": tr.get("expected"),
            }
        )

    return matching_tests


def main():
    parser = argparse.ArgumentParser(
        description="Check if tests matching a regex ran in a build."
    )
    parser.add_argument(
        "--build-id",
        help="Buildbucket ID (e.g. 8673466777718303649)",
    )
    parser.add_argument(
        "--builder",
        help="Builder name to resolve (used with --build-number)",
    )
    parser.add_argument(
        "--build-number",
        help="Build number to resolve (used with --builder)",
    )
    parser.add_argument(
        "--project",
        default="chromium",
        help="LUCI project name (default: chromium)",
    )
    parser.add_argument(
        "--bucket",
        default="ci",
        help="LUCI bucket (default: ci)",
    )
    parser.add_argument(
        "--test-regex",
        required=True,
        help="Regex pattern matching test ID",
    )

    args = parser.parse_args()

    build_id = args.build_id
    if not build_id:
        if args.builder and args.build_number:
            build_id = resolve_build_id(
                args.project, args.bucket, args.builder, args.build_number
            )
            if not build_id:
                print(
                    f"Error: Could not resolve build ID for {args.builder} "
                    f"#{args.build_number}",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            parser.error(
                "Must provide either --build-id or --builder + --build-number"
            )

    results = check_test(build_id, args.test_regex)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
