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

# alint (--verbose) prints this after all findings, before its telemetry flush.
# It's an unstable debug log (colored text-format proto); if it's missing we
# wait for alint to exit.
# TODO(b/534712288): Use a stable completion signal from alint instead.
_END_EVENT_PREFIX = "INFO: endEvent:"
_END_EVENT_EXIT_CODE_RE = re.compile(
    r"invocation_stopped:\s*\{\s*exit_code:\s*(\d+)"
)
_NO_END_EVENT_NOTICE = (
    "[AyeAye] alint did not report completion (no endEvent line with an exit "
    "code), so presubmit waited for it to exit."
)


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


def _strip_info_lines(clean_output):
    """Drops alint's --verbose INFO lines from an execution error report."""
    return "\n".join(
        line
        for line in clean_output.splitlines()
        if not line.strip().startswith("INFO:")
    ).strip()


def _run_alint(cmd, env):
    """Runs alint and returns (exit_code, output, saw_end_event).

    Returns at the endEvent line instead of waiting for the telemetry flush.
    Output goes through `tee -p`, which keeps draining alint after we stop;
    Go programs die on SIGPIPE writing to a closed stdout even if it's ignored.
    """
    alint = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    tee = subprocess.Popen(
        ["tee", "-p", os.devnull],
        stdin=alint.stdout,
        stdout=subprocess.PIPE,
        start_new_session=True,
    )
    alint.stdout.close()
    output = []
    with tee.stdout:
        for raw in tee.stdout:
            output.append(raw)
            line = _strip_ansi_codes(raw.decode("utf-8", "ignore")).strip()
            if not line.startswith(_END_EVENT_PREFIX):
                continue
            # Without an exit code, keep reading and use alint's real one.
            match = _END_EVENT_EXIT_CODE_RE.search(line)
            if match:
                # Join the raw lines; drop any bytes that aren't valid UTF-8.
                output_str = b"".join(output).decode("utf-8", "ignore")
                return int(match.group(1)), output_str, True
    tee.wait()
    output_str = b"".join(output).decode("utf-8", "ignore")
    return alint.wait(), output_str, False


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

    # git cl requires a clean tree, so lint HEAD directly instead of letting
    # alint scan the worktree to choose between HEAD and uncommitted changes.
    # --verbose makes alint print the endEvent line _run_alint() waits for.
    cmd = [alint_path, "--verbose", "--"] + sys.argv[3:] + ["--commit=HEAD"]
    try:
        env = os.environ.copy()
        git_params = env.get("GIT_CONFIG_PARAMETERS", "").strip()
        params = []
        if not re.search(
            r"'status\.showuntrackedfiles=no'", git_params, re.IGNORECASE
        ):
            params.append("'status.showUntrackedFiles=no'")
        if not re.search(
            r"'diff\.ignoresubmodules=all'", git_params, re.IGNORECASE
        ):
            params.append("'diff.ignoreSubmodules=all'")
        if params:
            new_params = " ".join(params)
            if git_params:
                env["GIT_CONFIG_PARAMETERS"] = f"{git_params} {new_params}"
            else:
                env["GIT_CONFIG_PARAMETERS"] = new_params

        returncode, output_str, saw_end_event = _run_alint(cmd, env)
        clean = _strip_ansi_codes(output_str).strip()
        parsed = _parse_alint_output(clean)
        if returncode and not parsed["errors"] and not parsed["warnings"]:
            parsed["execution_error"] = {
                "exit_code": returncode,
                "output": _strip_info_lines(clean),
            }
        if not saw_end_event:
            parsed["notices"] = [_NO_END_EVENT_NOTICE]
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
