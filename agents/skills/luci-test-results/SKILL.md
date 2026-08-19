---
name: luci-test-results
description: >
  Triage and analyze LUCI build results (including tests and compile).
  Fetches a list of test failures by querying ResultDB directly.
  Use this for detailed information about specific test case regressions,
  grouping failures by task, and extracting filtered log snippets.
  For high-level builder status or compile errors, use the 'buildbucket' skill.
---

# LUCI Triage Cheat Sheet

This skill provides modular scripts for deep-diving into **Test-level**
failures across LUCI shards and tasks.

> [!TIP]
> **CLI Help & Flags**: Run any script with `-h` or `--help` (e.g.
> `vpython3 scripts/list_failures.py -h` or
> `vpython3 scripts/check_test.py -h`) to view all supported arguments,
> defaults, and flags without reading the script source files.

## 1. Resolve Build ID & Inspect Builds

Resolve a builder name + build number to a canonical `<BUILD_ID>`, or fetch
detailed build properties:

```bash
# Resolve builder + build number to Buildbucket ID:
vpython3 scripts/luci_client.py resolve-build-id \
  --builder "<BUILDER>" \
  --build-number <NUMBER> \
  [--project chromium] \
  [--bucket ci]

# Get detailed build metadata and step summaries:
vpython3 scripts/luci_client.py get-build \
  --build-id <BUILD_ID>
```

For example, for the URL
`https://ci.chromium.org/ui/p/chromium/builders/try/linux-chromeos-rel/2769679/overview`:
```bash
vpython3 scripts/luci_client.py resolve-build-id \
  --builder "linux-chromeos-rel" \
  --build-number 2769679 \
  --project chromium \
  --bucket try
```

## 2. Find Builds for Gerrit CL

Find builds for a specific CL and patchset (defaults to non-successful builds):

```bash
vpython3 scripts/find_cl_builds.py \
  --cl <CL_NUMBER> \
  [--patchset <PATCHSET>] \
  [--all] \
  [--host <HOST>]
```

> [!NOTE]
> - By default, this command only returns builds that did not succeed
>   (e.g., FAILURE, INFRA_FAILURE). Use `--all` to include SUCCESSFUL builds.
> - If `--patchset` is omitted, the script auto-detects the latest patchset via
>   the Gerrit REST API.
> - **Gerrit Auth Issue**: Auto-detecting patchset for internal CLs
>   (on `chromium-review.git.corp.google.com`) might fail with auth errors.
>   Workaround: Provide `--patchset` explicitly.

## 3. List Unexpected Failures

Get a clean list of tests that failed unexpectedly in a build, deduplicated and
grouped by Swarming task:

```bash
vpython3 scripts/list_failures.py \
  --build-id <BUILD_ID> \
  [--ignore-flaky] \
  [--include-exonerated]

# Or resolve builder directly:
vpython3 scripts/list_failures.py \
  --builder "<BUILDER>" \
  --build-number <NUMBER>
```

- **Filtering:** By default, exonerated test variants (known flakes and baseline
  expectations) are excluded, and results are sorted with unexonerated
  `UNEXPECTED` regressions first.
- **Ignore Flakes:** Use `--ignore-flaky` to filter out flaky tests and return
  only unexonerated `UNEXPECTED` failures.
- **Include Exonerated:** Use `--include-exonerated` to include exonerated test
  variants in the output.
- **Triage Priority:** If multiple tests share a `task` ID, triage **one**
  result first (often indicating a shard crash or runner failure).

## 4. Fetch Log Snippet

Retrieve a filtered failure log snippet using the result name (`res`) from step
3:

```bash
vpython3 scripts/fetch_log.py \
  --res "<RES_NAME>" \
  [--raw]
```

## 5. Check Specific Test in Build

Check if a specific test (or tests matching a regex) ran in a build, and see
its status:

```bash
vpython3 scripts/check_test.py \
  --build-id <BUILD_ID> \
  --test-regex "<TEST_REGEX>"

# Or resolve builder directly:
vpython3 scripts/check_test.py \
  --builder "<BUILDER>" \
  --build-number <NUMBER> \
  --test-regex "<TEST_REGEX>"
```

- **Efficiency:** This command uses server-side filtering via `QueryTestResults`
  and automatically wraps your regex with `.*` for partial matching. It fetches
  all results (expected and unexpected) for matching tests.

## 6. Get Test History

Query LUCI Analysis for the historical verdicts of a specific test variant:

```bash
vpython3 scripts/test_history.py \
  --project <PROJECT> \
  --test-id "<TEST_ID>" \
  [--limit <LIMIT>] \
  [--builder <BUILDER>] \
  [--bucket <BUCKET>] \
  [--device-os <DEVICE_OS>] \
  [--device-type <DEVICE_TYPE>] \
  [--os <OS>] \
  [--test-suite <TEST_SUITE>]
```

## Troubleshooting

- **"No Artifacts Found"**: This can happen if the build failed before producing
  ResultDB artifacts, if the logs were purged (old build), or if there is an
  auth issue (`bb auth-login`).
- **Fallback**: If artifacts are missing, use `bb log <build_id> <step_name>`
  (from the `buildbucket` skill) to see the raw step output.

## Implementation Notes

1. **Task-Based Triage:** A shard crash often manifests as
   `CascadingFailureException`. Triage the root failure in that shard first by
   checking the first failure in a task group.
2. **Log Filtering:** The `fetch_log.py` command automatically filters for
   `AssertionError`, `FATAL`, `Exception`, `FAIL`, and leak reports to keep the
   context window clean.
