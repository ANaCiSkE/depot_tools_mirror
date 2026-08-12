#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import re
import subprocess
import sys


_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi_codes(text):
    return _ANSI_ESCAPE_RE.sub("", text)


def _parse_alint_output(output_str):
    clean_output = _strip_ansi_codes(output_str)
    errors = []
    warnings = []
    for line in clean_output.splitlines():
        clean_line = line.strip()
        if clean_line.startswith("ERROR:"):
            errors.append(clean_line[len("ERROR:") :].strip())
        elif clean_line.startswith("WARNING:"):
            warnings.append(clean_line[len("WARNING:") :].strip())
    return {"errors": errors, "warnings": warnings}


def main():
    if len(sys.argv) < 3:
        print("Usage: run_alint.py <alint_path> <repo_root> [alint_args...]")
        return 3

    alint_path = sys.argv[1]
    repo_root = sys.argv[2]
    # Change CWD to the repository root. This is necessary because
    # presubmit_support.py has a workaround when testing depot_tools that
    # changes the process CWD to the parent directory of depot_tools.
    # alint requires running from inside a git repository to detect changes.
    os.chdir(repo_root)

    cmd = [alint_path, "--"] + sys.argv[3:]
    try:
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        stdout, _ = p.communicate()
        output_str = stdout.decode("utf-8", "ignore")
        parsed = _parse_alint_output(output_str)
        if p.returncode and not parsed["errors"] and not parsed["warnings"]:
            clean = _strip_ansi_codes(output_str).strip()
            if not clean:
                clean = f"alint had exit code {p.returncode}"
            parsed["warnings"].append(clean)
        print(json.dumps(parsed))
        return 0
    except Exception as e:
        print(
            json.dumps(
                {
                    "errors": [],
                    "warnings": [f"Unexpected error in AyeAye (alint): {e}"],
                }
            )
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
