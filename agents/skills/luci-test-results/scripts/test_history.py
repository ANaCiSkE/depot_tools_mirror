#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Queries LUCI Analysis for test history of a specific test variant."""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luci_client import run_prpc

GLYPH_PASS = "P"
GLYPH_FAIL = "F"
GLYPH_FLAKY = "R"
GLYPH_SKIP = "S"
DEFAULT_SINGLE_BUILDER_LIMIT = 100
DEFAULT_MULTI_BUILDER_LIMIT = 15
MAX_PARALLEL_BUILDERS = 40
MAX_WORKERS = 16


def query_tests(project, test_query):
    """Queries LUCI Analysis for test IDs matching a substring."""
    res = run_prpc(
        "analysis.api.luci.app",
        "luci.analysis.v1.TestHistory.QueryTests",
        {"project": project, "testIdSubstring": test_query},
    )
    return res.get("testIds", []) if res else []


def query_variant_builders(project, test_id, predicate=None):
    """Maps variantHash -> bucket/builder using TestHistory.QueryVariants."""
    mapping = {}
    page_token = None
    while True:
        payload = {"project": project, "testId": test_id, "pageSize": 1000}
        if predicate:
            payload["variantPredicate"] = predicate.get(
                "variantPredicate", predicate
            )
        if page_token:
            payload["pageToken"] = page_token
        res = run_prpc(
            "analysis.api.luci.app",
            "luci.analysis.v1.TestHistory.QueryVariants",
            payload,
        )
        if not res:
            break
        for v in res.get("variants", []):
            v_hash = v.get("variantHash")
            def_map = v.get("variant", {}).get("def", {})
            builder = def_map.get("builder")
            bucket = def_map.get("bucket", "ci")
            if v_hash and builder:
                mapping[v_hash] = f"{bucket}/{builder}"
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return mapping


def _build_predicate(
    builder, bucket, device_os, device_type, os_val, test_suite
):
    variant_def = {}
    if builder:
        variant_def["builder"] = builder
    if bucket:
        variant_def["bucket"] = bucket
    if device_os:
        variant_def["device_os"] = device_os
    if device_type:
        variant_def["device_type"] = device_type
    if os_val:
        variant_def["os"] = os_val
    if test_suite:
        variant_def["test_suite"] = test_suite
    if not variant_def:
        return {}
    return {"variantPredicate": {"contains": {"def": variant_def}}}


def test_history(
    project,
    test_id,
    limit=DEFAULT_SINGLE_BUILDER_LIMIT,
    builder=None,
    bucket=None,
    device_os=None,
    device_type=None,
    os_val=None,
    test_suite=None,
):
    """Queries LUCI Analysis for the test history of a specific test variant."""
    predicate = _build_predicate(
        builder, bucket, device_os, device_type, os_val, test_suite
    )
    verdicts = []
    page_token = None
    target_limit = int(limit) if limit else DEFAULT_SINGLE_BUILDER_LIMIT

    while len(verdicts) < target_limit:
        batch_size = min(1000, target_limit - len(verdicts))
        payload = {
            "project": project,
            "testId": test_id,
            "predicate": predicate,
            "pageSize": batch_size,
        }
        if page_token:
            payload["pageToken"] = page_token

        result = run_prpc(
            "analysis.api.luci.app",
            "luci.analysis.v1.TestHistory.Query",
            payload,
        )
        if not result or "verdicts" not in result:
            break
        verdicts.extend(result["verdicts"])
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    verdicts = verdicts[:target_limit]
    if builder or bucket:
        for v in verdicts:
            if bucket:
                v.setdefault("bucket", bucket)
            if builder:
                v.setdefault("builder", builder)
    return verdicts


def fetch_multi_builder_history(
    project,
    test_id,
    per_builder_limit=DEFAULT_MULTI_BUILDER_LIMIT,
    bucket=None,
    device_os=None,
    device_type=None,
    os_val=None,
    test_suite=None,
    max_builders=MAX_PARALLEL_BUILDERS,
):
    """Discovers builders via QueryVariants and fetches verdicts per builder in parallel."""
    target_bucket = bucket or "ci"
    predicate = _build_predicate(
        None, target_bucket, device_os, device_type, os_val, test_suite
    )
    variant_builders = query_variant_builders(
        project, test_id, predicate=predicate
    )
    distinct = sorted(
        {
            (b.split("/", 1)[0], b.split("/", 1)[1])
            for b in variant_builders.values()
            if "/" in b
        }
    )
    if not distinct:
        verdicts = test_history(
            project,
            test_id,
            limit=per_builder_limit,
            bucket=bucket,
            device_os=device_os,
            device_type=device_type,
            os_val=os_val,
            test_suite=test_suite,
        )
        return verdicts, variant_builders

    if len(distinct) > max_builders:
        print(
            f"Notice: Querying {max_builders} of {len(distinct)} discovered "
            f"builders. Narrow with --builder or --os.",
            file=sys.stderr,
        )
    targets = distinct[:max_builders]

    def _fetch_one(bkt_bld):
        bkt, bld = bkt_bld
        try:
            batch = test_history(
                project,
                test_id,
                limit=per_builder_limit,
                builder=bld,
                bucket=bkt,
                device_os=device_os,
                device_type=device_type,
                os_val=os_val,
                test_suite=test_suite,
            )
            for v in batch:
                v.setdefault("bucket", bkt)
                v.setdefault("builder", bld)
            return batch
        except Exception as e:
            print(
                f"Warning: Failed to fetch history for {bkt}/{bld}: {e}",
                file=sys.stderr,
            )
            return []

    with ThreadPoolExecutor(
        max_workers=min(MAX_WORKERS, len(targets))
    ) as executor:
        results = list(executor.map(_fetch_one, targets))

    all_verdicts = [v for batch in results for v in batch]
    return all_verdicts, variant_builders


def _verdict_glyph(v):
    status = v.get("status", "")
    status_v2 = v.get("statusV2", "")
    if status == "EXPECTED" or status_v2 == "PASSED":
        return GLYPH_PASS
    if status == "FLAKY" or status_v2 == "FLAKY":
        return GLYPH_FLAKY
    if status_v2 == "SKIPPED" or status in ("SKIPPED", "UNEXPECTEDLY_SKIPPED"):
        return GLYPH_SKIP
    return GLYPH_FAIL


def format_summary(verdicts, variant_builders=None, default_builder=None):
    """Formats verdicts into a compact per-builder summary with timeline glyphs."""
    mapping = variant_builders or {}
    by_builder = defaultdict(list)
    for v in verdicts:
        v_hash = v.get("variantHash", "unknown")
        v_bld = v.get("builder")
        if v_bld and v.get("bucket") and "/" not in v_bld:
            v_bld = f"{v['bucket']}/{v_bld}"
        bld = (
            default_builder
            or mapping.get(v_hash)
            or v_bld
            or v.get("variant", {}).get("def", {}).get("builder")
            or v_hash
        )
        by_builder[bld].append(v)

    def sort_key(item):
        bld, v_list = item
        fails = sum(1 for v in v_list if _verdict_glyph(v) == GLYPH_FAIL)
        flakes = sum(1 for v in v_list if _verdict_glyph(v) == GLYPH_FLAKY)
        return (-fails, -flakes, bld)

    lines = []
    passing_builders = []
    for bld, v_list in sorted(by_builder.items(), key=sort_key):
        glyphs = "".join(_verdict_glyph(v) for v in v_list)
        p = glyphs.count(GLYPH_PASS)
        f = glyphs.count(GLYPH_FAIL)
        r = glyphs.count(GLYPH_FLAKY)
        s = glyphs.count(GLYPH_SKIP)

        if f == 0 and r == 0 and len(by_builder) > 1:
            passing_builders.append(f"{bld} ({p} pass)")
            continue

        lines.append(
            f"Builder: {bld} | Pass: {p}, Fail: {f}, Flaky: {r}, Skip: {s}"
        )
        lines.append(f"  Recent (newest->oldest): {glyphs[:80]}")

        by_date = defaultdict(list)
        for v in v_list:
            date_str = v.get("partitionTime", "")[:10]
            if date_str:
                by_date[date_str].append(_verdict_glyph(v))
        for d in sorted(by_date.keys(), reverse=True)[:5]:
            dg = "".join(by_date[d])
            lines.append(
                f"  {d}: Pass={dg.count(GLYPH_PASS)}, "
                f"Fail={dg.count(GLYPH_FAIL)}, "
                f"Flaky={dg.count(GLYPH_FLAKY)}, "
                f"Skip={dg.count(GLYPH_SKIP)} [{dg}]"
            )

    if passing_builders:
        lines.append(
            f"100% Passing Builders ({len(passing_builders)}): "
            + ", ".join(passing_builders)
        )
    return "\n".join(lines)


def _is_bounded_suffix(test_id, suffix):
    """Returns True if test_id ends with suffix at a valid test ID delimiter."""
    if not test_id.endswith(suffix):
        return False
    if len(test_id) == len(suffix):
        return True
    return test_id[-len(suffix) - 1] in "#./:!"


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Query LUCI Analysis for test history verdicts."
    )
    parser.add_argument(
        "--project", default="chromium", help="LUCI project name"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--test-id",
        help="Full ResultDB test ID (or Class#method substring)",
    )
    group.add_argument(
        "--test-substring",
        help="Test ID substring (e.g. Class#method) to resolve via QueryTests",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            f"Max verdicts to return (default: {DEFAULT_SINGLE_BUILDER_LIMIT} "
            f"for single builder, {DEFAULT_MULTI_BUILDER_LIMIT}/builder "
            "across builders)"
        ),
    )
    parser.add_argument("--builder", help="Filter by builder name")
    parser.add_argument("--bucket", help="Filter by bucket (e.g. try, ci)")
    parser.add_argument("--device-os", help="Filter by device OS")
    parser.add_argument("--device-type", help="Filter by device type")
    parser.add_argument("--os", help="Filter by OS")
    parser.add_argument("--test-suite", help="Filter by test suite")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw JSON verdicts instead of formatted summary",
    )

    args = parser.parse_args()

    target_test_id = args.test_id
    if args.test_substring or (
        target_test_id and not target_test_id.startswith(("://", "ninja://"))
    ):
        sub_query = args.test_substring or target_test_id
        matched_ids = query_tests(args.project, sub_query)
        exact = [m for m in matched_ids if _is_bounded_suffix(m, sub_query)]
        chosen_pool = exact or matched_ids
        if not chosen_pool:
            print(
                f"No matching test IDs found for '{sub_query}'.",
                file=sys.stderr,
            )
            sys.exit(1)
        chosen_pool.sort(key=lambda m: (0 if m.startswith("://") else 1, m))
        target_test_id = chosen_pool[0]
        if len(chosen_pool) > 1:
            others = ", ".join(chosen_pool[1:4])
            print(
                f"Notice: Resolved '{sub_query}' to '{target_test_id}' "
                f"({len(chosen_pool)} matches; others: {others}).",
                file=sys.stderr,
            )

    if args.builder:
        verdicts = test_history(
            args.project,
            target_test_id,
            limit=args.limit or DEFAULT_SINGLE_BUILDER_LIMIT,
            builder=args.builder,
            bucket=args.bucket,
            device_os=args.device_os,
            device_type=args.device_type,
            os_val=args.os,
            test_suite=args.test_suite,
        )
        variant_builders = None
    else:
        verdicts, variant_builders = fetch_multi_builder_history(
            args.project,
            target_test_id,
            per_builder_limit=args.limit or DEFAULT_MULTI_BUILDER_LIMIT,
            bucket=args.bucket,
            device_os=args.device_os,
            device_type=args.device_type,
            os_val=args.os,
            test_suite=args.test_suite,
        )

    if not verdicts:
        if args.raw:
            print("[]")
            return
        search_query = (
            target_test_id.split("#")[-1]
            if "#" in target_test_id
            else target_test_id.split(":")[-1]
        ).strip()
        candidates = [
            c
            for c in query_tests(args.project, search_query)
            if c != target_test_id
        ]
        print(f"No verdicts found for '{target_test_id}'.", file=sys.stderr)
        if candidates:
            print("Did you mean one of these active tests?", file=sys.stderr)
            for tid in candidates[:10]:
                print(f"  {tid}", file=sys.stderr)
        else:
            print("No similar test IDs found in project.", file=sys.stderr)
        sys.exit(1)

    if args.raw:
        print(json.dumps(verdicts, indent=2))
    else:
        print(
            format_summary(
                verdicts,
                variant_builders=variant_builders,
                default_builder=args.builder,
            )
        )


if __name__ == "__main__":
    main()
