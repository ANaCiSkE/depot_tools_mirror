#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Fetch and extract filtered failure logs from a ResultDB artifact."""

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luci_client import is_authenticated, run_prpc


def fetch_log_snippet(res_name, raw=False):
    """Fetches a filtered snippet of the failure log."""
    payload = {"parent": res_name}
    result = run_prpc(
        "results.api.luci.app",
        "luci.resultdb.v1.ResultDB.ListArtifacts",
        payload,
    )
    if not result or not result.get("artifacts"):
        msg = (
            "No artifacts found. This can happen if the build failed early "
            "or the logs were purged."
        )
        if not is_authenticated():
            msg += (
                " If the build is private, the user must run `bb auth-login` "
                "to authenticate."
            )
        return msg

    artifacts = result["artifacts"]
    target = next(
        (
            a
            for a in artifacts
            if a["artifactId"] in ("test_log", "stdout", "logs")
        ),
        artifacts[0],
    )

    url = target["fetchUrl"]
    cmd = ["curl", "-sL", url]
    try:
        output = subprocess.check_output(cmd).decode("utf-8", errors="ignore")
    except Exception as e:
        return f"Error fetching log: {e}"

    if raw:
        return output

    lines = output.splitlines()
    patterns = [
        r"AssertionError",
        r"FATAL",
        r"Exception",
        r"FAILED",
        r"FAIL",
        r"Leaking",
    ]
    combined_pattern = "|".join(patterns)

    interesting_indices = [
        i
        for i, line in enumerate(lines)
        if re.search(combined_pattern, line, re.I)
    ]

    if not interesting_indices:
        return "\n".join(lines[:100])

    output_lines = []
    last_idx = -1
    primary_indices = [
        i
        for i in interesting_indices
        if re.search(r"AssertionError|Exception", lines[i], re.I)
    ]
    if primary_indices:
        interesting_indices = primary_indices

    for idx in interesting_indices[:5]:
        start = max(0, idx - 15)
        end = min(len(lines), idx + 10)
        if start > last_idx + 1 and last_idx != -1:
            output_lines.append("...")
        output_lines.extend(lines[max(last_idx + 1, start) : end])
        last_idx = end - 1

    return "\n".join(output_lines[:200])


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and extract filtered failure logs from ResultDB."
    )
    parser.add_argument(
        "--res",
        required=True,
        help="Full result resource name (e.g. from list_failures.py output)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Return full raw log without regex filtering",
    )

    args = parser.parse_args()
    print(fetch_log_snippet(args.res, raw=args.raw))


if __name__ == "__main__":
    main()
