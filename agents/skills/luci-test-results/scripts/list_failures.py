#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""List failing and flaky test variants for a build, grouped by Swarming task."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luci_client import resolve_build_id, run_prpc


def list_failures(
    build_id, limit=None, include_exonerated=False, ignore_flaky=False
):
    """Lists failing and flaky test variants for a build, grouped by task."""
    if build_id.startswith("b"):
        build_id = build_id[1:]

    payload = {
        "invocations": [f"invocations/build-{build_id}"],
        "predicate": {"status": "UNEXPECTED_MASK"},
        "pageSize": 1000,
    }

    test_variants = []
    while True:
        result = run_prpc(
            "results.api.luci.app",
            "luci.resultdb.v1.ResultDB.QueryTestVariants",
            payload,
        )
        if not result:
            break

        test_variants.extend(result.get("testVariants", []))

        if "nextPageToken" not in result:
            break
        payload["pageToken"] = result["nextPageToken"]

    if not include_exonerated:
        test_variants = [
            tv
            for tv in test_variants
            if not (
                tv.get("status") == "EXONERATED"
                or tv.get("exonerated") is True
                or "exonerations" in tv
            )
        ]

    if ignore_flaky:
        test_variants = [
            tv for tv in test_variants if tv.get("status") != "FLAKY"
        ]

    status_order = {
        "UNEXPECTED": 0,
        "UNEXPECTEDLY_SKIPPED": 1,
        "FLAKY": 2,
        "EXONERATED": 3,
    }
    test_variants.sort(
        key=lambda tv: status_order.get(tv.get("status", ""), 99)
    )

    if limit is not None:
        test_variants = test_variants[:limit]

    tasks = {}
    for tv in test_variants:
        if "results" not in tv:
            continue

        results = [r["result"] for r in tv["results"]]
        failed_results = [r for r in results if r.get("status") != "PASS"]
        first_result = failed_results[0] if failed_results else results[0]
        res_name = first_result["name"]
        task_id = res_name.split("/")[1].replace("task-", "")

        failure = {
            "id": tv["testId"],
            "res": res_name,
            "err": first_result.get("failureReason", {}).get(
                "primaryErrorMessage", "No error"
            ),
            "status": tv.get("status", "UNEXPECTED"),
            "flaky": tv.get("status") == "FLAKY",
        }

        if task_id not in tasks:
            tasks[task_id] = []
        tasks[task_id].append(failure)

    return tasks


def main():
    parser = argparse.ArgumentParser(
        description=(
            "List failing and flaky test variants for a build, grouped by "
            "Swarming task ID."
        )
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
        help="LUCI project name for builder resolution (default: chromium)",
    )
    parser.add_argument(
        "--bucket",
        default="ci",
        help="LUCI bucket for builder resolution (default: ci)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of failures to return",
    )
    parser.add_argument(
        "--include-exonerated",
        action="store_true",
        help="Include exonerated test variants in the output",
    )
    parser.add_argument(
        "--ignore-flaky",
        action="store_true",
        help=(
            "Ignore flaky test variants (only show unexonerated UNEXPECTED "
            "failures)"
        ),
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

    failures = list_failures(
        build_id,
        limit=args.limit,
        include_exonerated=args.include_exonerated,
        ignore_flaky=args.ignore_flaky,
    )
    print(json.dumps(failures, indent=2))


if __name__ == "__main__":
    main()
