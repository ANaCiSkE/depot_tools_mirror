#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Find Buildbucket builds triggered for a Gerrit CL."""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luci_client import run_prpc


def find_cl_builds(cl_number, patchset=None, host=None, show_all=False):
    """Finds builds for a specific CL and patchset."""
    if not host:
        host = "chromium-review.googlesource.com"

    if not patchset:
        base_url = f"https://{host}/changes"
        cmd = ["curl", "-s", f"{base_url}/{cl_number}?o=CURRENT_REVISION"]
        try:
            output = (
                subprocess.check_output(cmd).decode("utf-8").splitlines()[1:]
            )
            data = json.loads("\n".join(output))
            patchset = data["revisions"][data["current_revision"]]["_number"]
        except Exception as e:
            print(f"Error getting latest patchset: {e}", file=sys.stderr)
            return []

    payload = {
        "predicate": {
            "gerritChanges": [
                {
                    "host": host,
                    "change": int(cl_number),
                    "patchset": int(patchset),
                }
            ]
        }
    }
    result = run_prpc(
        "cr-buildbucket.appspot.com",
        "buildbucket.v2.Builds.SearchBuilds",
        payload,
    )
    if not result or "builds" not in result:
        return []

    return [
        {
            "builder": b["builder"]["builder"],
            "status": b["status"],
            "id": b["id"],
        }
        for b in result["builds"]
        if show_all or b["status"] not in ("SUCCESS", "STARTED")
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Find Buildbucket builds triggered for a Gerrit CL."
    )
    parser.add_argument(
        "--cl",
        required=True,
        help="Gerrit CL number (e.g. 8260911)",
    )
    parser.add_argument(
        "--patchset",
        help="Optional patchset number (defaults to latest)",
    )
    parser.add_argument(
        "--host",
        default="chromium-review.googlesource.com",
        help="Gerrit host (default: chromium-review.googlesource.com)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all builds, not just failures/running builds",
    )

    args = parser.parse_args()
    builds = find_cl_builds(
        args.cl, patchset=args.patchset, host=args.host, show_all=args.all
    )
    print(json.dumps(builds, indent=2))


if __name__ == "__main__":
    main()
