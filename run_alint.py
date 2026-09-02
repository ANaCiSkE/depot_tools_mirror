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


def _format_finding(finding):
    if not finding:
        return finding
    if finding.startswith(("[AyeAye/", "[AyeAye]")):
        return finding
    if finding.startswith("["):
        return f"[AyeAye/{finding[1:]}"
    return f"[AyeAye] {finding}"


def _parse_alint_output(clean_output):
    errors = []
    warnings = []
    for line in clean_output.splitlines():
        clean_line = line.strip()
        if clean_line.startswith("ERROR:"):
            errors.append(_format_finding(clean_line[len("ERROR:") :].strip()))
        elif clean_line.startswith("WARNING:"):
            warnings.append(
                _format_finding(clean_line[len("WARNING:") :].strip())
            )
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
        clean = _strip_ansi_codes(output_str).strip()
        parsed = _parse_alint_output(clean)
        if p.returncode and not parsed["errors"] and not parsed["warnings"]:
            parsed["execution_error"] = {
                "exit_code": p.returncode,
                "output": clean,
            }
        print(json.dumps(parsed))
        return 0
    except Exception as e:
        print(
            json.dumps(
                {
                    "errors": [],
                    "warnings": [],
                    "execution_error": {
                        "exit_code": 1,
                        "output": f"Unexpected error in AyeAye: {e}",
                    },
                }
            )
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
