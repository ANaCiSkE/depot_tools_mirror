---
name: luci-test-results
description: Triage and analyze any LUCI build results (including tests and compile). Supports finding builds by CL, failure listing, and log fetching.
---

# LUCI Triage Cheat Sheet

## 1. Resolve Build ID

If you have a builder + build number, get the long `<BUILD_ID>`:

```bash
scripts/luci_triage.py resolve-build-id \
  --builder "<BUILDER>" \
  --build-number <NUMBER>
```

## 2. Find Builds for Gerrit CL

Find failed builds for a specific CL and patchset:

```bash
scripts/luci_triage.py find-cl-builds \
  --cl <CL_NUMBER> \
  [--patchset <PATCHSET>]
```
## 3. Get Build Details

Get status, summary markdown, and output properties of a build:

```bash
scripts/luci_triage.py get-build \
  --build-id <BUILD_ID>
```

## 4. List Unexpected Failures

Get a clean list of tests that failed unexpectedly, deduplicated by test ID and
grouped by Swarming task:

```bash
scripts/luci_triage.py list-failures \
  --build-id <BUILD_ID>
```

- **Triage Priority:** If multiple tests share a `task` ID, triage **one**
  result first.

## 5. Fetch Log Snippet

Retrieve a filtered failure log snippet using the result name (`res`) from step
4:

```bash
scripts/luci_triage.py fetch-log \
  --res "<RES_NAME>"
```

## Implementation Notes

1. **Task-Based Triage:** A shard crash often manifests as
   `CascadingFailureException`. Triage the root failure in that shard first by
   checking the first failure in a task group.
2. **Log Filtering:** The `fetch-log` command automatically filters for
   `AssertionError`, `FATAL`, `Exception`, and `FAIL` to keep the context window
   clean.
