---
name: swarming
description: >-
  Explore and query LUCI Swarming v2 APIs on chromium-swarm.appspot.com using the prpc CLI. Use when investigating task execution status, bot health, pool capacity, logs, dimensions, or querying Swarming endpoints. Don't use for triggering new tasks (use led) or Buildbucket builds (use bb).
---

# LUCI Swarming API Investigation

LUCI Swarming provides a **v2 pRPC (Proto-over-HTTP)** API on `chromium-swarm.appspot.com` encoding messages with `protojson`.

> [!IMPORTANT]
> **API Discovery Rule**: Do not guess or assume Swarming service names, RPC methods, parameter names, or enum values. **Use `prpc show` to discover and figure out the schema by yourself.**

---

## 1. Exploring APIs with `prpc show`

Swarming supports runtime reflection. You can explore the entire API surface dynamically using `prpc` (bundled with `depot_tools`).

### Discovery Workflow via `prpc show`

1. **Discover available services**:
   ```bash
   prpc show chromium-swarm.appspot.com
   ```

2. **Discover methods and docstrings for a service**:
   ```bash
   prpc show chromium-swarm.appspot.com <service>
   # Examples:
   # prpc show chromium-swarm.appspot.com swarming.v2.Tasks
   # prpc show chromium-swarm.appspot.com swarming.v2.Bots
   ```

3. **Inspect request/response message schemas and enums**:
   Run `prpc show` on any input message type, output message type, or enum referenced in a method signature to see field names, types, constraints, and docstrings:
   ```bash
   prpc show chromium-swarm.appspot.com <message_or_enum_type>
   # Examples:
   # prpc show chromium-swarm.appspot.com swarming.v2.TasksWithPerfRequest
   # prpc show chromium-swarm.appspot.com swarming.v2.BotsRequest
   # prpc show chromium-swarm.appspot.com swarming.v2.StateQuery
   ```

---

## 2. Calling APIs

Send requests using `prpc call` with JSONPB-encoded request messages:
```bash
prpc call chromium-swarm.appspot.com <service>.<Method> <<EOF
{
  "key": "value"
}
EOF
```

---

## 3. Gotchas

- **Timestamps (`google.protobuf.Timestamp`)**:
  Per the JSONPB specification, timestamps must be RFC 3339 formatted strings (e.g. `"2026-09-01T12:00:00Z"`). Dynamic shell generation:
  ```bash
  START_TIME=$(date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ)
  ```
- **Task State Filtering (`StateQuery` enum)**:
  By default, `state` in task listing/counting endpoints defaults to `QUERY_PENDING` (value 0). If you want active, running, or historical tasks, you must explicitly specify `"state": "QUERY_PENDING_RUNNING"`, `"state": "QUERY_RUNNING"`, or `"state": "QUERY_ALL"`. Run `prpc show chromium-swarm.appspot.com swarming.v2.StateQuery` to view all valid state options and their meanings.
- **Bot Task Constraints**:
  Methods querying tasks on a specific bot reject `QUERY_PENDING` with an `InvalidArgument` error because pending tasks are not yet assigned to any bot. Always use `QUERY_ALL`, `QUERY_RUNNING`, or `QUERY_COMPLETED`.
- **Nullable Booleans (`NullableBool`)**:
  Used in bot filtering fields (e.g., `is_busy`, `is_dead`, `quarantined`). Pass `"TRUE"`, `"FALSE"`, or omit/set to `"NULL"`.
- **Base64-Encoded Stdout**:
  Stdout output in responses (such as `GetStdout`) is base64-encoded in the `.output` field:
  ```bash
  prpc call chromium-swarm.appspot.com swarming.v2.Tasks.GetStdout <<EOF | jq -r '.output // empty' | base64 -d
  {
    "task_id": "{task_id}",
    "offset": 0,
    "length": 1048576
  }
  EOF
  ```
- **Pagination & Limits**:
  Listing queries typically accept `limit` (integer, e.g., 1 to 1000, default 100) and `cursor` (string from previous page response).
- **Task ID Types**:
  - Summary task ID ends with `0` (represents overall task, handles retries transparently).
  - Run ID ends with `1`, `2`, etc. (represents a specific retry attempt).

---

## 4. Parsing Bot Info (`BotInfo`) & State

When inspecting bot details or bot events (e.g., via `Bots.GetBot` or `Bots.ListBots`), the returned `BotInfo` contains a `state` field.

> [!NOTE]
> The `state` field is a raw **serialized JSON string** (`string state`) representing an arbitrary dictionary — it is plain JSON, **not JSONPB** of a protobuf message nor a nested protobuf message. You must parse / deserialize it as JSON to access its contents.

### Parsing Examples

**Using `jq` with `fromjson`**:
```bash
# Retrieve and parse the bot state:
prpc call chromium-swarm.appspot.com swarming.v2.Bots.GetBot <<EOF | jq '.state | fromjson'
{
  "bot_id": "{bot_id}"
}
EOF

# Parse state alongside other BotInfo fields:
prpc call chromium-swarm.appspot.com swarming.v2.Bots.GetBot <<EOF1 | jq -f /dev/fd/3 3<<EOF2
{
  "bot_id": "{bot_id}"
}
EOF1
{
  bot_id: .botId,
  quarantined: .quarantined,
  state: (.state | fromjson)
}
EOF2
```

**Using Python**:
```python
import json

# bot_info is the JSON response from Bots.GetBot or Bots.ListBots
state = json.loads(bot_info.get("state", "{}"))
```

---

## 5. Relationship Between Buildbucket & Swarming Tasks

Buildbucket builds and Swarming tasks are closely linked in LUCI infrastructure:

- **Buildbucket Builds Run as Swarming Tasks**:
  When a Buildbucket build is scheduled, Buildbucket launches a top-level Swarming task to execute the build's recipe or executable (tagged with `buildbucket_build_id:<build_id>`).
- **Child Tasks**:
  The orchestrating build task can trigger multiple child Swarming tasks (e.g., isolated test suites, shards, or sub-builds) to run in parallel across the fleet.
- **Finding Child Tasks via `parent_task_id`**:
  Every child task spawned by a parent task is automatically tagged with `parent_task_id:{parent_task_id}`, where `{parent_task_id}` must be the parent task's **Run ID** (ending in `1`, `2`, etc., representing the specific execution attempt), **not** the Summary Task ID (ending in `0`).

### A. Querying the Swarming Run ID & Creation Time from a Buildbucket ID
Given a Buildbucket build ID, query Buildbucket's pRPC API (`cr-buildbucket.appspot.com`) to get its creation time and Summary Task ID, then resolve its **Run ID** via `Tasks.GetResult`:

```bash
# 1. Get the build's creation time and Summary Task ID (ending in 0):
prpc call cr-buildbucket.appspot.com buildbucket.v2.Builds.GetBuild <<EOF | jq '{create_time: .createTime, summary_task_id: .infra.backend.task.id.id}'
{
  "id": "{buildbucket_id}",
  "mask": {
    "fields": "create_time,infra.backend.task.id"
  }
}
EOF

# 2. Resolve the Run ID (ending in 1, 2, etc.) from the Summary Task ID:
prpc call chromium-swarm.appspot.com swarming.v2.Tasks.GetResult <<EOF | jq -r '.runId'
{
  "task_id": "{summary_task_id}"
}
EOF
```

### B. Querying Child Tasks via `parent_task_id`
Using the Run ID as `{parent_task_id}` and anchoring `start` on the parent build's `create_time`, list all child tasks spawned by that build:

```bash
prpc call chromium-swarm.appspot.com swarming.v2.Tasks.ListTasks <<EOF
{
  "start": "{create_time}",
  "tags": [
    "parent_task_id:{parent_task_id}"
  ],
  "state": "QUERY_ALL",
  "limit": 100
}
EOF
```

---

## 6. Example: Discovery & Invocation in Action

Here is an example showing how to figure out a method and call it:

```bash
# 1. Discover available methods on swarming.v2.Tasks:
prpc show chromium-swarm.appspot.com swarming.v2.Tasks

# 2. Inspect the request schema for ListTasks (TasksWithPerfRequest):
prpc show chromium-swarm.appspot.com swarming.v2.TasksWithPerfRequest

# 3. Call the endpoint with your desired filters:
START_TIME=$(date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ)

prpc call chromium-swarm.appspot.com swarming.v2.Tasks.ListTasks <<EOF
{
  "start": "${START_TIME}",
  "tags": [
    "pool:luci.chromium.try",
    "cpu:x86-64"
  ],
  "state": "QUERY_PENDING_RUNNING",
  "limit": 20
}
EOF
```
