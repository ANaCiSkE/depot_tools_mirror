#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Shared LUCI pRPC client and Buildbucket utilities."""

import argparse
import json
import subprocess
import sys


def run_prpc(service, method, payload):
    """Calls a pRPC service and returns the parsed JSON response."""
    cmd = ["prpc", "call", service, method]
    with subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        stdout, stderr = process.communicate(input=json.dumps(payload))
        if process.returncode != 0:
            print(
                f"Error calling {service}.{method}: {stderr}", file=sys.stderr
            )
            return None
        return json.loads(stdout)


def is_authenticated():
    """Checks if the user is logged into buildbucket."""
    try:
        res = subprocess.run(
            ["bb", "auth-info"], capture_output=True, text=True, check=False
        )
        return res.returncode == 0
    except FileNotFoundError:
        return False


def resolve_build_id(project, bucket, builder, build_number):
    """Resolves a builder and build number to a Buildbucket ID."""
    payload = {
        "builder": {"project": project, "bucket": bucket, "builder": builder},
        "buildNumber": int(build_number),
    }
    result = run_prpc(
        "cr-buildbucket.appspot.com", "buildbucket.v2.Builds.GetBuild", payload
    )
    return result.get("id") if result else None


def get_build(build_id):
    """Retrieves detailed information about a build."""
    if build_id.startswith("b"):
        build_id = build_id[1:]
    payload = {
        "id": build_id,
        "mask": {"fields": "id,builder,number,status,summaryMarkdown,output"},
    }
    return run_prpc(
        "cr-buildbucket.appspot.com", "buildbucket.v2.Builds.GetBuild", payload
    )


def main():
    parser = argparse.ArgumentParser(
        description="Resolve or inspect Buildbucket builds."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # resolve-build-id
    p = subparsers.add_parser(
        "resolve-build-id",
        help="Resolve builder and build number to a Buildbucket ID.",
    )
    p.add_argument(
        "--project",
        default="chromium",
        help="LUCI project (default: chromium)",
    )
    p.add_argument("--bucket", default="ci", help="LUCI bucket (default: ci)")
    p.add_argument(
        "--builder",
        required=True,
        help="Builder name (e.g. android-13-x64-rel)",
    )
    p.add_argument(
        "--build-number",
        required=True,
        help="Build number integer",
    )

    # get-build
    p = subparsers.add_parser(
        "get-build",
        help="Retrieve detailed Buildbucket metadata and step summaries.",
    )
    p.add_argument(
        "--build-id",
        required=True,
        help="Buildbucket ID (e.g. 8673466777718303649)",
    )

    args = parser.parse_args()
    if args.command == "resolve-build-id":
        build_id = resolve_build_id(
            args.project, args.bucket, args.builder, args.build_number
        )
        if build_id:
            print(build_id)
        else:
            sys.exit(1)
    elif args.command == "get-build":
        data = get_build(args.build_id)
        if data:
            print(json.dumps(data, indent=2))
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
