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
failures and test history across LUCI shards and tasks.

> [!TIP]
> **CLI Help & Flags**: Run any script with `-h` or `--help` (e.g.
> `vpython3 scripts/list_failures.py -h` or
> `vpython3 scripts/test_history.py -h`) to view all supported arguments,
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
>   the Gerrit REST API. If the latest patchset has 0 builds, it retries up to 3
>   preceding patchsets and reports which one it used in the `patchset` field of
>   each returned build (plus a `stderr` notice). Always check `patchset` before
>   attributing results to your current code.
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
  [--include-exonerated] \
  [--limit <LIMIT>]

# Or resolve builder directly:
vpython3 scripts/list_failures.py \
  --builder "<BUILDER>" \
  --build-number <NUMBER> \
  [--project chromium] \
  [--bucket ci] \
  [--limit <LIMIT>]
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

## 5. Check Specific Test in a Single Build (`check_test.py`)

Query **ResultDB** for all runs (passing and failing) matching a regex inside **1
specific build**:

```bash
vpython3 scripts/check_test.py \
  --build-id <BUILD_ID> \
  --test-regex "<TEST_REGEX>"

# Or resolve builder directly:
vpython3 scripts/check_test.py \
  --builder "<BUILDER>" \
  --build-number <NUMBER> \
  [--project chromium] \
  [--bucket ci] \
  --test-regex "<TEST_REGEX>"
```

- **When to use (`check_test` vs. `list_failures` / `test_history`)**:
  - Unlike `list_failures.py` (which only returns unexpected failures), `check_test.py`
    fetches **all** results (`expectancy: ALL`, including `PASS`), returning each
    result's `res` resource name (usable directly with `fetch_log.py --res <RES>`)
    and `err` (`primaryErrorMessage`). Use it to verify that a test actually ran and
    passed in a specific build, or to discover the full ResultDB `testId` string from
    a partial class/method regex.
  - Unlike `test_history.py` (which looks across time/builders), `check_test.py`
    is strictly scoped to a single build.

## 6. Query Test History Across Builds & Builders (`test_history.py`)

Query **LUCI Analysis** for historical verdicts of **1 specific test ID** (or
substring) across time and CI/try builders:

```bash
# Formatted per-builder summary (default):
vpython3 scripts/test_history.py \
  (--test-id '<TEST_ID>' | --test-substring '<CLASS_OR_METHOD_SUBSTRING>') \
  [--project <chromium|chrome>] \
  [--builder <BUILDER>] \
  [--bucket <BUCKET>] \
  [--device-os <DEVICE_OS>] \
  [--device-type <DEVICE_TYPE>] \
  [--os <OS>] \
  [--test-suite <TEST_SUITE>] \
  [--limit <LIMIT>] \
  [--raw]
```

> [!IMPORTANT]
> **Single Quotes Required**: ResultDB Test IDs often contain exclamation marks
> (e.g. `!junit` or `!gtest`). Always enclose `--test-id` in **single quotes**
> (`'...'`) to prevent Bash from attempting history expansion
> (`bash: !...: event not found`).

- **When to use**: Once you have a test ID (from `list_failures.py` or `check_test.py`),
  or a `Class#method` substring (`--test-substring`, mutually exclusive with
  `--test-id`), use `test_history.py` to check if a failure is a fresh trunk
  regression, a known flake across multiple builders, or isolated to your CL.
- **Parallel Per-Builder Fair Sampling**: When `--builder` is omitted, discovers
  active builders via `QueryVariants` and fetches recent verdicts per builder in
  parallel (`--limit` defaults to `15` verdicts/builder across `ci` builders, or `100`
  verdicts when a single `--builder` is specified). This prevents high-frequency bots
  from crowding out slower platform/form-factor bots.
- **Per-Builder Structuring**: Failing and flaky builders are sorted first, while
  100% passing builders are condensed into a single summary line.
- **Timeline Glyphs**: Displays recent verdicts ordered newest →
  oldest (`P` = Pass, `F` = Fail, `R` = Flaky/Pass on Retry, `S` = Skip), along
  with daily breakdowns.
- **Raw Output**: Use `--raw` to print raw JSON verdicts instead of the summary.
- **Substring Resolution & Fuzzy Search Fallback**: Pass `--test-substring` (or a
  short `Class#method` to `--test-id`) to auto-resolve via `QueryTests`
  (`--test-id` and `--test-substring` are mutually exclusive). If no verdicts are
  found, matching candidate Test IDs are printed.

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
