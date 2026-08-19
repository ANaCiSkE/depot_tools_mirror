#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Queries LUCI Analysis for test history of a specific test variant."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luci_client import run_prpc


def test_history(
    project,
    test_id,
    limit=None,
    builder=None,
    bucket=None,
    device_os=None,
    device_type=None,
    os=None,
    test_suite=None,
):
    """Queries LUCI Analysis for the test history of a specific test variant."""
    variant_def = {}
    if builder:
        variant_def["builder"] = builder
    if bucket:
        variant_def["bucket"] = bucket
    if device_os:
        variant_def["device_os"] = device_os
    if device_type:
        variant_def["device_type"] = device_type
    if os:
        variant_def["os"] = os
    if test_suite:
        variant_def["test_suite"] = test_suite

    predicate = {}
    if variant_def:
        predicate["variantPredicate"] = {"contains": {"def": variant_def}}

    payload = {
        "project": project,
        "testId": test_id,
        "predicate": predicate,
    }
    if limit:
        payload["pageSize"] = int(limit)

    result = run_prpc(
        "analysis.api.luci.app", "luci.analysis.v1.TestHistory.Query", payload
    )
    if not result or "verdicts" not in result:
        return []
    return result["verdicts"]


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Query LUCI Analysis for test history verdicts."
    )
    parser.add_argument(
        "--project", default="chromium", help="LUCI project name"
    )
    parser.add_argument("--test-id", required=True, help="Full test ID")
    parser.add_argument(
        "--limit", type=int, default=10, help="Maximum verdicts to return"
    )
    parser.add_argument("--builder", help="Filter by builder name")
    parser.add_argument("--bucket", help="Filter by bucket (e.g. try, ci)")
    parser.add_argument("--device-os", help="Filter by device OS")
    parser.add_argument("--device-type", help="Filter by device type")
    parser.add_argument("--os", help="Filter by OS")
    parser.add_argument("--test-suite", help="Filter by test suite")

    args = parser.parse_args()

    verdicts = test_history(
        args.project,
        args.test_id,
        args.limit,
        builder=args.builder,
        bucket=args.bucket,
        device_os=args.device_os,
        device_type=args.device_type,
        os=args.os,
        test_suite=args.test_suite,
    )
    print(json.dumps(verdicts, indent=2))


if __name__ == "__main__":
    main()
