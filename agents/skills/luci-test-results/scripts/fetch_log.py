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

# Artifact IDs that hold the main test log, in order of preference. Matched
# case-insensitively with spaces treated as underscores, so "Test Log" (used by
# Chromium gtest/JUnit results) matches "test_log".
PREFERRED_ARTIFACT_IDS = ("test_log", "stdout", "logs")

# Lines that state why a test failed. When any are present, snippets are
# centred on them rather than on the broader patterns below.
# - Java/Python/JS exception or assertion headlines, e.g.
#   "java.lang.RuntimeException: ...", "AssertionError", "ComparisonFailure:".
#   The trailing \b(:|$) keeps gtest frames such as
#   "HandleExceptionsInMethodIfSupported<...>" from matching.
# - gtest assertion failures: "foo_unittest.cc:163: Failure" (matched above)
#   and MSVC-style "foo_unittest.cc(163): error: ..." on Windows.
# - CHECK failures, e.g. "Check failed: !feature.".
PRIMARY_PATTERN = re.compile(
    r"\b[\w.$]*(?:Exception|Error|Failure)\b(?::|$)"
    r"|\(\d+\): error:"
    r"|Check failed"
)
SECONDARY_PATTERN = re.compile(
    r"AssertionError|FATAL|Exception|FAILED|FAIL|Leaking", re.I
)


def _normalize_artifact_id(artifact_id):
    return artifact_id.lower().replace(" ", "_")


def select_artifact(artifacts, artifact_id=None):
    """Returns (artifact, note) for the artifact to read.

    note is a human-readable explanation when the choice is not obvious (an
    explicit ID was not found, or no preferred log artifact exists), else None.
    """
    by_id = {_normalize_artifact_id(a["artifactId"]): a for a in artifacts}
    available = ", ".join(a["artifactId"] for a in artifacts)
    if artifact_id:
        target = by_id.get(_normalize_artifact_id(artifact_id))
        if target:
            return target, None
        return None, (
            f"Artifact '{artifact_id}' not found. Available artifacts: "
            f"{available}"
        )
    for preferred in PREFERRED_ARTIFACT_IDS:
        if preferred in by_id:
            return by_id[preferred], None
    text = [
        a for a in artifacts if a.get("contentType", "").startswith("text/")
    ]
    target = (text or artifacts)[0]
    return target, (
        f"No test log artifact found; showing '{target['artifactId']}'. "
        f"Available artifacts: {available} (use --artifact-id to pick one)"
    )


def filter_log(output):
    """Returns the interesting parts of a test log."""
    lines = output.splitlines()
    interesting_indices = [
        i for i, line in enumerate(lines) if SECONDARY_PATTERN.search(line)
    ]
    primary_indices = [
        i for i, line in enumerate(lines) if PRIMARY_PATTERN.search(line)
    ]
    if primary_indices:
        interesting_indices = primary_indices

    if not interesting_indices:
        return "\n".join(lines[:100])

    output_lines = []
    last_idx = -1
    for idx in interesting_indices[:5]:
        start = max(0, idx - 15)
        end = min(len(lines), idx + 10)
        if start > last_idx + 1 and last_idx != -1:
            output_lines.append("...")
        output_lines.extend(lines[max(last_idx + 1, start) : end])
        last_idx = max(last_idx, end - 1)

    return "\n".join(output_lines[:200])


def fetch_log_snippet(res_name, raw=False, artifact_id=None):
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

    target, note = select_artifact(result["artifacts"], artifact_id)
    if not target:
        return note
    if note:
        print(note, file=sys.stderr)

    url = target["fetchUrl"]
    cmd = ["curl", "-sL", url]
    try:
        output = subprocess.check_output(cmd).decode("utf-8", errors="ignore")
    except Exception as e:
        return f"Error fetching log: {e}"

    if raw:
        return output
    return filter_log(output)


def list_artifacts(res_name):
    """Returns a listing of the artifacts of a test result."""
    result = run_prpc(
        "results.api.luci.app",
        "luci.resultdb.v1.ResultDB.ListArtifacts",
        {"parent": res_name},
    )
    artifacts = (result or {}).get("artifacts", [])
    if not artifacts:
        return "No artifacts found."
    return "\n".join(
        f"{a['artifactId']}\t{a.get('contentType', '-')}\t"
        f"{a.get('sizeBytes', '-')} bytes"
        for a in artifacts
    )


def fetch_log(res_name, raw=False, artifact_id=None):
    """Alias for fetch_log_snippet for module import consistency."""
    return fetch_log_snippet(res_name, raw=raw, artifact_id=artifact_id)


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
    parser.add_argument(
        "--artifact-id",
        help="Artifact to read (default: the test log, e.g. 'Test Log')",
    )
    parser.add_argument(
        "--list-artifacts",
        action="store_true",
        help="List the result's artifacts instead of fetching one",
    )

    args = parser.parse_args()
    if args.list_artifacts:
        print(list_artifacts(args.res))
        return
    print(fetch_log(args.res, raw=args.raw, artifact_id=args.artifact_id))


if __name__ == "__main__":
    main()
