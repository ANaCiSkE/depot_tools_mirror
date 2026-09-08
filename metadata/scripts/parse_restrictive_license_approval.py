#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# /// script
# requires-python = '>=3.11,<3.12'
# dependencies = [
#   'protobuf==4.25.1',
#   'googleapis-common-protos==1.61.0'
# ]
# ///

import json
import os
import sys

_THIS_DIR = os.path.abspath(os.path.dirname(__file__))
_METADATA_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
sys.path.insert(0, _METADATA_DIR)

import restrictive_license_approval_pb2 as rla_pb2  # noqa: E402
from google.protobuf import text_format  # noqa: E402
from fields.custom.license_allowlist import (  # noqa: E402
    SCRIPT_INPUT_ENV,
    SCRIPT_EXIT_CODE_INVALID_PROTO,
)

"""Reads `SCRIPT_INPUT_ENV` environment variable and prints parsing results to stdout."""


def main():
    # Don't use sys.argv to pass arguments. Their character escaping is hard
    # to get right on Windows.
    path = os.environ.get(SCRIPT_INPUT_ENV, None)
    if not path:
        print("No input path given.", file=sys.stderr)
        sys.exit(2)

    proto_msg = rla_pb2.RestrictiveLicenseApproval()
    try:
        with open(path, "r", encoding="utf-8") as f:
            text_format.Parse(f.read(), proto_msg)
    except Exception as e:
        print(f"Error parsing proto: {e}", file=sys.stderr)
        sys.exit(SCRIPT_EXIT_CODE_INVALID_PROTO)

    approvals = []
    for approval in proto_msg.license_approval:
        # Approval requires a License ID and bug.
        if approval.id and approval.bug:
            approvals.append(
                {
                    "id": approval.id,
                    "bug": approval.bug,
                }
            )

    print(json.dumps(approvals))


if __name__ == "__main__":
    main()
