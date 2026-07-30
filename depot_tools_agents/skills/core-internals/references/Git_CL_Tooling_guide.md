# Git CL Tooling Engineering Guide

## Executive Summary

Welcome to the Git CL Tooling Engineering Guide. This repository of tribal
knowledge exists to establish strict architectural constraints and standardize
how our developer tools interact with both local Git repositories and remote
Gerrit APIs. Historically, organic growth in command-line utilities led to
fragmented implementations, brittle environment assumptions, and unrecoverable
automated mutations. This guide captures the known failure modes—such as mangled
rebase states, broken hooks in non-standard workspaces, and CI/CD overloads from
unprompted bulk operations—and provides authoritative rules to prevent their
regression.

The overarching architectural boundaries detailed herein enforce resilient,
idempotent tooling. The guidelines mandate decoupling git metadata resolution
from physical `.git` folder assumptions to support virtualized environments like
Cog and Git Worktrees. Furthermore, they dictate rigorous standards for batch
operation checkpointing, defensive argument parsing, and conflict recovery. By
strictly separating network-bound operations from local state mutations and
enforcing human-in-the-loop verification for bulk executions, this guide ensures
that our CLI ecosystem remains scalable, predictable, and highly actionable for
developers.

## Summary

| Chapter Theme / Title               | Scope & Objective                      |
| :---------------------------------- | :------------------------------------- |
| **Git Worktree & Environment        | Tooling must decouple internal git     |
: Abstraction**                       : metadata resolution from standard      :
:                                     : `.git` folder assumptions to support   :
:                                     : Git Worktrees and non-Git environments :
:                                     : like Cog. This ensures reliable hook   :
:                                     : execution and repository configuration :
:                                     : lookups regardless of the underlying   :
:                                     : workspace architecture.                :
| **Gerrit REST API & Revision        | This domain governs the translation of |
: Translation**                       : CLI arguments into valid Gerrit REST   :
:                                     : API payloads. It ensures tooling       :
:                                     : interacts with API endpoints using     :
:                                     : flexible, symbolic references (e.g.,   :
:                                     : 'current') while relying on the remote :
:                                     : API for metadata retrieval rather than :
:                                     : local git executions.                  :
| **Batch Operation Checkpointing &   | This domain dictates the constraints   |
: Conflict Recovery**                 : for tracking the execution state of    :
:                                     : multi-step CLI and API operations.     :
:                                     : Strictly enforce precise checkpointing :
:                                     : and resumption markers to allow        :
:                                     : seamless recovery from intermediate    :
:                                     : failures, such as merge conflicts,     :
:                                     : without duplicating work or severing   :
:                                     : commit lineages.                       :
| **CLI Syntax & Command              | This domain dictates the structural    |
: Consolidation**                     : boundaries of CLI tools to prevent     :
:                                     : command and namespace bloat. It        :
:                                     : enforces the consolidation of related  :
:                                     : functionalities via modifier flags,    :
:                                     : integration into established           :
:                                     : namespaces, and the strict parsing of  :
:                                     : raw argument separators.               :
| **Deterministic Asset Naming &      | Auto-generating assets like Git        |
: Idempotency**                       : branches must rely on deterministic,   :
:                                     : hash-based naming derived from payload :
:                                     : contents and sanitized file paths.     :
:                                     : This enforces idempotent execution and :
:                                     : enables safe resumption of interrupted :
:                                     : batch operations without state loss or :
:                                     : namespace collisions.                  :
| **Human-in-the-Loop Automation &    | This domain governs the execution      |
: Dry-Run Boundaries**                : boundaries of bulk automation scripts, :
:                                     : ensuring interactive user verification :
:                                     : strictly precedes remote state         :
:                                     : mutation. It mandates explicit         :
:                                     : confirmation prompts and predictive    :
:                                     : summaries to prevent nondeterministic  :
:                                     : operations from overwhelming CI/CD     :
:                                     : infrastructure.                        :
| **Interactive Configuration         | This section governs the design and    |
: Serialization**                     : parsing of human-readable,             :
:                                     : intermediate file formats used for     :
:                                     : persistent state operations. It        :
:                                     : mandates robust regex-based extraction :
:                                     : over naive delimiters to safely ingest :
:                                     : manual user edits and gracefully       :
:                                     : handle environment edge cases.         :
| **Rebase Traversal & Conflict       | This boundary governs how automated    |
: Escapes**                           : Git operations handle detached or      :
:                                     : mid-rebase states to prevent           :
:                                     : destructive history modifications. It  :
:                                     : mandates explicit, automated abort     :
:                                     : instructions and defined escape        :
:                                     : hatches when operational conflicts     :
:                                     : arise.                                 :
| **Strict Git Reference Resolution** | Resolving symbolic Git references into |
:                                     : precise commit hashes is critical for  :
:                                     : maintaining an accurate, deterministic :
:                                     : history during automation. This domain :
:                                     : ensures that operations systematically :
:                                     : log and act upon exact hashes to       :
:                                     : prevent debugging ambiguities when     :
:                                     : volatile references shift.             :
| **Stale Local Branch Garbage        | This domain isolates the mechanisms    |
: Collection**                        : for identifying, squashing, and        :
:                                     : cleaning up stale local branches       :
:                                     : linked to closed upstream changes. To  :
:                                     : preserve deterministic local           :
:                                     : repository performance, these          :
:                                     : network-bound garbage collection       :
:                                     : routines must be strictly decoupled    :
:                                     : from standard offline operations.      :
| **Defensive Host URL Parsing**      | User-provided or environment-derived   |
:                                     : domain URLs must be parsed using       :
:                                     : standard libraries like `urllib`       :
:                                     : rather than fragile manual string      :
:                                     : manipulation. All parsing logic must   :
:                                     : be wrapped in defensive exception      :
:                                     : handling to prevent malformed inputs   :
:                                     : from triggering raw stack traces.      :
| **Actionable CLI Diagnostics &      | This domain defines the strict         |
: Terminology**                       : linguistic and structural requirements :
:                                     : for CLI diagnostics, ensuring error    :
:                                     : messages use ubiquitous terminology    :
:                                     : and provide copy-pasteable,            :
:                                     : context-aware recovery commands. It    :
:                                     : prevents workflow blockages by         :
:                                     : mandating actionable output for        :
:                                     : unhandled states and non-standard      :
:                                     : environments.                          :

--------------------------------------------------------------------------------
--------------------------------------------------------------------------------

## Chapter: Git Worktree & Environment Abstraction

**Context:** Tooling must decouple internal git metadata resolution from
standard `.git` folder assumptions to support Git Worktrees and non-Git
environments like Cog. This ensures reliable hook execution and repository
configuration lookups regardless of the underlying workspace architecture.

### Summary

| Rule ID    | Principle / Constraint | Priority | Primary Symptom / Trap  |
| :--------- | :--------------------- | :------- | :---------------------- |
| **T01-01** | Git Worktree           | High     | Assuming the `.git`     |
:            : Compatibility for Hook :          : directory is a physical :
:            : Paths                  :          : folder located at the   :
:            :                        :          : repository root.        :

--------------------------------------------------------------------------------

### Rules

#### T01-01: Git Worktree Compatibility for Hook Paths

> **Rule:** Always resolve Git metadata directories dynamically via API or `git
> rev-parse --git-common-dir` instead of hardcoding `.git/` paths.
>
> **What:** Repository tooling must resolve Git metadata directories using the
> `git rev-parse --git-common-dir` command rather than hardcoding `.git/`
> directory paths.
>
> **Applies To:** All Python/Bash CLI scripts interacting with Git hooks or
> reading raw configuration from the `.git` directory.
>
> **Why:** When a developer operated within a Git worktree, the local `.git`
> structure was merely a pointer file, not a directory. Hardcoded `.git` path
> lookups failed to locate hooks (like `commit-msg`), breaking CL uploads.
> Failing to adhere to this typically results in **Command Failure / Missing
> Hooks**.

**Trap 1: Assuming the `.git` directory is a physical folder located at the
repository root.**

**Don't:**

```python
def get_git_dir(repo_root):
    return os.path.join(repo_root, '.git')
```

**Do:**

```python
def get_git_dir(repo_root):
    # Uses 'git rev-parse --git-common-dir' under the hood
    return scm.GIT.GetGitCommonDir(repo_root)
```

## Chapter: Gerrit REST API & Revision Translation

**Context:** This domain governs the translation of CLI arguments into valid
Gerrit REST API payloads. It ensures tooling interacts with API endpoints using
flexible, symbolic references (e.g., 'current') while relying on the remote API
for metadata retrieval rather than local git executions.

### Summary

| Rule ID    | Principle / Constraint | Priority | Primary Symptom / Trap  |
| :--------- | :--------------------- | :------- | :---------------------- |
| **T02-01** | Support for Symbolic   | Medium   | Casting Gerrit revision |
:            : Gerrit API Revisions   :          : inputs strictly to      :
:            :                        :          : integers.               :

--------------------------------------------------------------------------------

### Rules

#### T02-01: Support for Symbolic Gerrit API Revisions

> **Rule:** Always type Gerrit revision CLI arguments as strings to natively
> support both explicit commit hashes and symbolic API identifiers like
> "current".
>
> **What:** Command-line tools targeting Gerrit APIs must not enforce strict
> integer types on revision arguments, allowing for symbolic Gerrit identifiers
> (like 'current') or raw commit hashes.
>
> **Applies To:** Gerrit client wrappers and REST API payload construct
> functions.
>
> **Why:** A newly introduced `--revision` flag forced an integer type, breaking
> workflows that relied on the implicit ability to target the 'current'
> revision. By typing it as a string and defaulting to 'current', backward
> compatibility was restored. Failing to adhere to this typically results in
> **Type Error / API Failure**.

**Trap 1: Casting Gerrit revision inputs strictly to integers.**

**Don't:**

```python
parser.add_option('-r', '--revision', type=int, help='revision number')
```

**Do:**

```python
parser.add_option('-r', '--revision', type=str, default='current', help='revision ID (e.g. current or a hash)')
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T05 | CLI Syntax & Command Consolidation - *Flexible CLI
    parsing logic directly enables the injection of symbolic string references.*
*   **Downstream:** T10 | Strict Git Reference Resolution - *Local symbolic git
    references (like FETCH_HEAD) are resolved to absolute hashes before being
    passed as string parameters to the Gerrit API.*

## Chapter: Batch Operation Checkpointing & Conflict Recovery

**Context:** This domain dictates the constraints for tracking the execution
state of multi-step CLI and API operations. Strictly enforce precise
checkpointing and resumption markers to allow seamless recovery from
intermediate failures, such as merge conflicts, without duplicating work or
severing commit lineages.

### Summary

| Rule ID    | Principle / Constraint | Priority | Primary Symptom / Trap     |
| :--------- | :--------------------- | :------- | :------------------------- |
| **T04-01** | Precise Checkpointing  | High     | Popping the task item from |
:            : for Chained Operation  :          : the tracking queue before  :
:            : Resumption             :          : the network execution      :
:            :                        :          : completes.                 :
| **T04-02** | Resumption Markers for | High     | Aborting a multi-step loop |
:            : Batch API Mutations    :          : upon encountering an error :
:            :                        :          : without saving state or    :
:            :                        :          : providing a targeted       :
:            :                        :          : restart flag.              :

--------------------------------------------------------------------------------

### Rules

#### T04-01: Precise Checkpointing for Chained Operation Resumption

> **Rule:** Always update task execution state immediately after unrecoverable
> remote executions complete, but strictly before proceeding to subsequent
> recoverable steps.
>
> **What:** In multi-step chained operations, task execution state must be
> popped/updated immediately after the unrecoverable step (e.g., remote entity
> creation) but *before* subsequent, recoverable steps (e.g., rebasing),
> ensuring the tool can resume without duplicating data.
>
> **Applies To:** `git cl cherry-pick` loops and batch Gerrit interactions.
>
> **Why:** When cherry-picking, popping the tracking state before the remote
> change was actually created resulted in lost operations if the network
> dropped. Popping it too late caused duplicate attempts when recovering from
> standard merge conflicts. Failing to adhere to this typically results in
> **State Desync / Duplicate Operations**.

**Trap 1: Popping the task item from the tracking queue before the network
execution completes.**

**Don't:**

```python
# BAD: Removing from queue before creation
for change_id in change_ids_to_message:
    change_ids_to_commit.pop(change_id)
    new_change = gerrit_util.CherryPick(change_id)
    gerrit_util.RebaseChange(new_change)
```

**Do:**

```python
# GOOD: Removing from queue only after successful creation, but before rebase
for change_id in change_ids_to_message:
    new_change = gerrit_util.CherryPick(change_id)
    change_ids_to_commit.pop(change_id) # Safe to pop here
    gerrit_util.RebaseChange(new_change)
```

--------------------------------------------------------------------------------

#### T04-02: Resumption Markers for Batch API Mutations

> **Rule:** Must design multi-step automated CLI workflows with explicit
> checkpoint arguments to allow stateful resumption after an interrupted batch
> sequence.
>
> **What:** Automated scripts performing chained mutations over remote APIs must
> provide state tracking and explicit CLI mechanisms to resume execution from an
> intermediate point if the batch is interrupted by an error (e.g., merge
> conflicts).
>
> **Applies To:** Multi-step automated CLI processes; specifically chained
> Gerrit REST API operations (e.g., sequenced cherry-picks or rebases).
>
> **Why:** During chained Gerrit cherry-picks, encountering a merge conflict
> would hard-stop the script. Without a resumption mechanism, users had no
> structural way to restart the remainder of the chain after resolving the
> conflict, risking duplicated effort or broken parent-child commit linkages.
> Failing to adhere to this typically results in **Orphaned State /
> Unrecoverable Halt**.

**Trap 1: Aborting a multi-step loop upon encountering an error without saving
state or providing a targeted restart flag.**

**Don't:**

*   Failing a chain of API calls on a conflict and requiring the user to
    manually strip out already-processed items from the original command to
    retry.

**Do:**

*   Providing a checkpoint argument (e.g., `--parent-change-num`) that anchors
    the script to the last successful upstream change, allowing clean resumption
    of the remaining sequence.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T02 | Gerrit REST API & Revision Translation - *Batch
    mutations and checkpointing mechanisms rely heavily on precise payload
    routing and state translation against the Gerrit REST API.*
*   **Downstream:** T09 | Rebase Traversal & Conflict Escapes - *Recovering from
    mid-operation pauses requires explicit mid-rebase state detection and
    conflict escape hatches before the batch chain can safely resume.*

## Chapter: CLI Syntax & Command Consolidation

**Context:** This domain dictates the structural boundaries of CLI tools to
prevent command and namespace bloat. It enforces the consolidation of related
functionalities via modifier flags, integration into established namespaces, and
the strict parsing of raw argument separators.

### Summary

| Rule ID    | Principle / Constraint   | Priority | Primary Symptom / Trap   |
| :--------- | :----------------------- | :------- | :----------------------- |
| **T05-01** | Command Consolidation    | Medium   | Creating a dedicated     |
:            : via Operational Flags    :          : subcommand to slightly   :
:            :                          :          : alter the behavior of an :
:            :                          :          : existing operation.      :
| **T05-02** | Strict Separation of     | High     | Relying purely on        |
:            : Positional Arguments via :          : `parse_args` to evaluate :
:            : '--'                     :          : unformatted argument     :
:            :                          :          : lists without checking   :
:            :                          :          : raw syntax structures.   :
| **T05-03** | Integration of New       | Medium   | Creating a new top-level |
:            : Subcommands into         :          : executable script or     :
:            : Established Namespaces   :          : namespace to house new   :
:            :                          :          : API interactions.        :

--------------------------------------------------------------------------------

### Rules

#### T05-01: Command Consolidation via Operational Flags

> **Rule:** Always extend existing commands with modifier flags rather than
> creating entirely new top-level commands for minor workflow variants.
>
> **What:** Avoid creating entirely new top-level commands for workflow variants
> that share 80%+ of an existing command's logic. Instead, extend existing
> commands with modifier flags.
>
> **Applies To:** CLI command schemas and argument parsing logic.
>
> **Why:** A new subcommand was proposed to allow a developer to apply another
> user's CL as their own (re-authoring). The overlap with standard patch
> applications was high enough that introducing a new command caused bloat.
> Failing to adhere to this typically results in **CLI Bloat / Code
> Duplication**.

**Trap 1: Creating a dedicated subcommand to slightly alter the behavior of an
existing operation.**

**Don't:**

```python
@subcommand.usage('<codereview url or issue id>')
def CMDdiff_apply(parser, args):
    """Applies a CL's diff to the current branch without authoring."""
```

**Do:**

```python
# Inside existing CMDpatch logic
parser.add_option(
    '--reauthor',
    action='store_true',
    dest='reauthor',
    help='patch the commit and reset author, removing the Change-Id footer so a new CL can be created.')
```

#### T05-02: Strict Separation of Positional Arguments via '--'

> **Rule:** Must manually verify the strict separation of positional arguments
> placed after the `--` separator before forwarding raw arguments to underlying
> executables.
>
> **What:** When passing raw unparsed arguments to an underlying executable
> (like `git`), the parser must manually enforce that all positional file
> targets appear strictly after the `--` separator to prevent syntax collisions.
>
> **Applies To:** Command wrappers that intercept standard arguments and forward
> remaining arbitrary arguments to a subprocess.
>
> **Why:** Standard argument parsing logic stripped out the `--` separator
> silently, leading to commands failing when positional files were incorrectly
> mixed with optional flags. Failing to adhere to this typically results in
> **Execution Failure / Silent Parsing Bug**.

**Trap 1: Relying purely on `parse_args` to evaluate unformatted argument lists
without checking raw syntax structures.**

**Don't:**

```python
options, args = parser.parse_args(args)
if args:
    parser.error('Unrecognized args: %s' % ' '.join(args))
```

**Do:**

```python
options, args = parser.parse_args(raw_args)
# OptionParser.parse() strips '--' so check raw_args
if '--' in raw_args:
    if any(not a.startswith('-') for a in raw_args[:raw_args.index('--')]):
        parser.error('-- should come before positional arguments')
```

#### T05-03: Integration of New Subcommands into Established Namespaces

> **Rule:** Never spawn separate top-level executable scripts or namespaces for
> new developer tooling; always integrate them as subcommands within existing
> entry points.
>
> **What:** New developer tooling functionality must be integrated as logical
> subcommands within existing, established CLI entry points rather than spawning
> separate top-level executable scripts.
>
> **Applies To:** CLI architecture and interface design, specifically within
> depot_tools and the `git_cl.py` ecosystem.
>
> **Why:** A new tool for orchestrating Gerrit cherry-picks was initially
> proposed under a standalone `git gerrit` namespace. This approach risked
> ecosystem fragmentation and namespace bloat before it was re-homed into the
> existing toolset. Failing to adhere to this typically results in **Namespace
> Pollution / UX Fragmentation**.

**Trap 1: Creating a new top-level executable script or namespace to house new
API interactions.**

**Don't:**

*   Allocating a new top-level namespace like `git gerrit` for a cherry-pick
    feature.

**Do:**

*   Extending existing tools with logical subcommands, such as integrating the
    feature into `git cl cherry-pick`.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Downstream:** T03 | Commit Message & Footer Mutation - *Consolidating
    commands via flags (like `--reauthor`) often necessitates automated footer
    mutation logic to strip inherited `Change-Id` footers for new code reviews.*

## Chapter: Deterministic Asset Naming & Idempotency

**Context:** Auto-generating assets like Git branches must rely on
deterministic, hash-based naming derived from payload contents and sanitized
file paths. This enforces idempotent execution and enables safe resumption of
interrupted batch operations without state loss or namespace collisions.

### Summary

| Rule ID    | Principle / Constraint   | Priority | Primary Symptom / Trap    |
| :--------- | :----------------------- | :------- | :------------------------ |
| **T06-01** | Platform-Safe            | Medium   | Generating branch names   |
:            : Deterministic Branch     :          : by directly concatenating :
:            : Generation               :          : raw file paths without    :
:            :                          :          : escaping slashes.         :
| **T06-02** | Deterministic Hash-Based | High     | Naming a branch based on  |
:            : Branch Naming for Batch  :          : the first item in a       :
:            : Operations               :          : collection or using a     :
:            :                          :          : simple incremental        :
:            :                          :          : counter.                  :

--------------------------------------------------------------------------------

### Rules

#### T06-01: Platform-Safe Deterministic Branch Generation

> **Rule:** Always sanitize file paths by replacing slashes with underscores and
> append a unique payload hash when dynamically generating branch names.
>
> **What:** Auto-generated branch names derived from file paths must be
> sanitized to replace slashes with underscores and include a uniqueness hash to
> prevent git protocol errors and name collisions.
>
> **Applies To:** Automated code splitting, batch refactoring, or
> patch-application scripts.
>
> **Why:** Scripts generating branches dynamically from directory paths
> generated illegal branch characters or inadvertently created nested branch
> structures that conflicted on Windows machines. Failing to adhere to this
> typically results in **Branch Creation Failure / Collision**.

**Trap 1: Generating branch names by directly concatenating raw file paths
without escaping slashes.**

**Don't:**

```python
branch_name = f"split_{filepath}"
```

**Do:**

```python
# Using hash for uniqueness and sanitizing paths
branch_name = f"bts_{hash_val}_{filepath.replace('/', '_')}_split"
```

--------------------------------------------------------------------------------

#### T06-02: Deterministic Hash-Based Branch Naming for Batch Operations

> **Rule:** Derive batch operation branch names deterministically by hashing the
> exact payload contents rather than using arbitrary or sequential identifiers.
>
> **What:** When auto-generating branches for bulk operations, branch names must
> be derived deterministically from their payload (e.g., hashing the contents)
> rather than using arbitrary, non-unique, or sequential identifiers.
>
> **Applies To:** Branch creation logic in `git cl split` and related batch
> operation scripts.
>
> **Why:** Nondeterministic branch naming (like using the first directory name
> or incremental integers) prevented the tool from safely resuming interrupted
> uploads without creating duplicate branches or losing track of existing ones.
> Failing to adhere to this typically results in **Duplicate Branch Creation /
> State Loss**.

**Trap 1: Naming a branch based on the first item in a collection or using a
simple incremental counter.**

**Don't:**

```python
# BAD: Nondeterministic / Collides easily
branch_name = prefix + '_' + directories[0] + '_split'
```

**Do:**

```python
# GOOD: Deterministic, payload-based naming
files_hash = hash(tuple(sorted(files)))
branch_name = f'{prefix}_{files_hash}_split'
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T08 | Interactive Configuration Serialization - *Configuration
    serializers parsing manual CL splits provide the robust file payload inputs
    that are subsequently hashed for deterministic branch naming.*
*   **Downstream:** T04 | Batch Operation Checkpointing & Conflict Recovery -
    *Deterministic, hash-based branch naming is a prerequisite for tracking
    execution state and safely resuming interrupted batch operations.*

## Chapter: Human-in-the-Loop Automation & Dry-Run Boundaries

**Context:** This domain governs the execution boundaries of bulk automation
scripts, ensuring interactive user verification strictly precedes remote state
mutation. It mandates explicit confirmation prompts and predictive summaries to
prevent nondeterministic operations from overwhelming CI/CD infrastructure.

### Summary

| Rule ID    | Principle /       | Priority | Primary Symptom / Trap          |
:            : Constraint        :          :                                 :
| :--------- | :---------------- | :------- | :------------------------------ |
| **T07-01** | Mandatory         | High     | Executing bulk uploads directly |
:            : Human-in-the-Loop :          : without prompting, or only      :
:            : Confirmation for  :          : gating them behind arbitrarily  :
:            : Bulk Remote       :          : high limit thresholds.          :
:            : Mutations         :          :                                 :

--------------------------------------------------------------------------------

### Rules

#### T07-01: Mandatory Human-in-the-Loop Confirmation for Bulk Remote Mutations

> **Rule:** Always halt bulk remote mutations to present a predictive summary
> and demand explicit user confirmation before execution. Never bypass prompts
> based on arbitrary quantity thresholds.
>
> **What:** Automated operations that generate bulk network mutations (like
> splitting and uploading multiple CLs) must halt, display a summary in the
> future tense, and require an explicit user prompt before proceeding.
>
> **Applies To:** `git cl split` and batch upload processes.
>
> **Why:** Nondeterministic splitting algorithms executing without supervision
> led to incorrect CL generation, spamming reviewers, and overloading CI/CD
> infrastructure, which then required painful manual reversions. Failing to
> adhere to this typically results in **Infrastructure Overload / Unintended
> Executions**.

**Trap 1: Executing bulk uploads directly without prompting, or only gating them
behind arbitrarily high limit thresholds.**

**Don't:**

```python
# BAD: Only asking for confirmation if > 10 CLs are generated
if not dry_run and num_cls > CL_SPLIT_FORCE_LIMIT:
    AskForData('Proceed?')
```

**Do:**

```python
# GOOD: Always summarize and enforce confirmation
if not dry_run:
    PrintSummary(files_split_by_reviewers)
    answer = AskForData('Proceed? (y/n):')
    if answer.lower() != 'y':
        return 0
```

**Exceptions:** Dry-run execution modes where no actual mutation occurs.

## Chapter: Interactive Configuration Serialization

**Context:** This section governs the design and parsing of human-readable,
intermediate file formats used for persistent state operations. It mandates
robust regex-based extraction over naive delimiters to safely ingest manual user
edits and gracefully handle environment edge cases.

### Summary

| Rule ID    | Principle / Constraint    | Priority | Primary Symptom / |
:            :                           :          : Trap              :
| :--------- | :------------------------ | :------- | :---------------- |
| **T08-01** | Regex-Based Parsing for   | High     | Using             |
:            : Delimiter-Heavy Filepaths :          : `line.split(',')` :
:            :                           :          : to separate a     :
:            :                           :          : state prefix from :
:            :                           :          : a file path.      :

--------------------------------------------------------------------------------

### Rules

#### T08-01: Regex-Based Parsing for Delimiter-Heavy Filepaths

> **Rule:** Always use robust regular expressions instead of naive string
> splitting when parsing structured configuration lines that contain filepaths.
>
> **What:** Parsers ingesting structured configuration files containing system
> paths must use regex to extract known prefixes/formats rather than naive
> string splitting (e.g., `,`), as valid filepaths frequently contain the
> delimiter character.
>
> **Applies To:** Interactive configuration parsers processing files generated
> by `git status` or custom serialization.
>
> **Why:** The tool crashed when processing a file format that used comma
> separation for file metadata, because certain valid paths (e.g., font files in
> `third_party`) contained commas in their names. Failing to adhere to this
> typically results in **Parsing Crash / Exception**.

**Trap 1: Using `line.split(',')` to separate a state prefix from a file path.**

**Don't:**

```python
parts = line.split(",")
if len(parts) != 2:
    raise ClSplitParseError()
action, path = parts[0].strip(), parts[1].strip()
```

**Do:**

```python
# We use regex parsing instead of naive split because paths can contain commas
file_re = re.compile(r'([MTADRC]{1,2}),\s*(.+)')
m = re.fullmatch(file_re, line)
action, path = m.group(1), m.group(2)
```

## Chapter: Rebase Traversal & Conflict Escapes

**Context:** This boundary governs how automated Git operations handle detached
or mid-rebase states to prevent destructive history modifications. It mandates
explicit, automated abort instructions and defined escape hatches when
operational conflicts arise.

### Summary

| Rule ID    | Principle / Constraint | Priority | Primary Symptom / Trap      |
| :--------- | :--------------------- | :------- | :-------------------------- |
| **T09-01** | Explicit Mid-Rebase    | High     | Telling a user to start a   |
:            : Abort Instructions     :          : new git modification (like  :
:            :                        :          : a squash) immediately after :
:            :                        :          : a rebase conflict without   :
:            :                        :          : resetting state.            :

--------------------------------------------------------------------------------

### Rules

#### T09-01: Explicit Mid-Rebase Abort Instructions

> **Rule:** Always provide explicit commands to abort an ongoing rebase
> operation before suggesting any subsequent Git history manipulations.
>
> **What:** When automated git manipulations fail due to a mid-rebase conflict,
> the user recovery instructions must explicitly include the command to abort
> the ongoing rebase operation before suggesting any further actions.
>
> **Applies To:** Failure handlers for `git rebase` / conflict detection logic.
>
> **Why:** When an automated branch update failed with conflicts, the tool
> suggested the user manually squash their branch. If the user executed the
> squash while still in a detached 'mid-rebase' state, it resulted in corrupted
> Git history. Failing to adhere to this typically results in **Corrupted Git
> State**.

**Trap 1: Telling a user to start a new git modification (like a squash)
immediately after a rebase conflict without resetting state.**

**Don't:**

*   Output incomplete recovery guidance: "Your working copy is in mid-rebase.
    Either completely resolve like a normal git-rebase; OR try squashing your
    branch and try again."

**Do:**

*   Provide the explicit CLI abort command in the instruction flow: "Your
    working copy is in mid-rebase. Either completely resolve like a normal
    git-rebase; OR abort the rebase (`git rebase --abort`) and mark this branch
    as dormant; OR try squashing..."

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Downstream:** T13 | Actionable CLI Diagnostics & Terminology - *Mid-rebase
    recovery instructions must utilize exact, actionable terminal commands to
    ensure safe human-in-the-loop resolution.*

## Chapter: Strict Git Reference Resolution

**Context:** Resolving symbolic Git references into precise commit hashes is
critical for maintaining an accurate, deterministic history during automation.
This domain ensures that operations systematically log and act upon exact hashes
to prevent debugging ambiguities when volatile references shift.

### Summary

| Rule ID    | Principle / Constraint   | Priority | Primary Symptom / Trap |
| :--------- | :----------------------- | :------- | :--------------------- |
| **T10-01** | Dual-Logging of Symbolic | Medium   | Outputting only the    |
:            : Refs and Commit Hashes   :          : unparsed symbolic      :
:            :                          :          : reference during       :
:            :                          :          : execution logs.        :

--------------------------------------------------------------------------------

### Rules

#### T10-01: Dual-Logging of Symbolic Refs and Commit Hashes

> **Rule:** Always resolve and log both the underlying commit hash and the
> original symbolic reference before executing automated git operations.
>
> **What:** When an automated process resolves a symbolic Git reference to a
> commit, it must log both the symbolic name and the resulting commit hash.
>
> **Applies To:** Automated cherry-picking, branch management, and syncing
> scripts.
>
> **Why:** Logs only showed the symbolic target, making it highly difficult to
> debug state disparities when the underlying symbolic reference moved or
> mutated before the log was read. Failing to adhere to this typically results
> in **Ambiguous Audit Logs**.

**Trap 1: Outputting only the unparsed symbolic reference during execution
logs.**

**Don't:**

```python
self.Print('Will cherrypick %r .. %r on top of %r.' % (target_rev, pr, base_rev))
```

**Do:**

```python
target_rev_hash = self._Capture(['rev-parse', target_rev])
self.Print('Will cherrypick %r .. %r on top of %r:' % (target_rev_hash, pr, base_rev))
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Downstream:** T04 | Batch Operation Checkpointing & Conflict Recovery -
    *Multi-step operations like chained cherry-picks rely on these strictly
    resolved commit hashes to accurately track state and resume from merge
    conflicts.*

## Chapter: Stale Local Branch Garbage Collection

**Context:** This domain isolates the mechanisms for identifying, squashing, and
cleaning up stale local branches linked to closed upstream changes. To preserve
deterministic local repository performance, these network-bound garbage
collection routines must be strictly decoupled from standard offline operations.

### Summary

| Rule ID    | Principle / Constraint   | Priority | Primary Symptom / Trap  |
| :--------- | :----------------------- | :------- | :---------------------- |
| **T11-01** | Standalone Execution for | Medium   | Coupling remote branch  |
:            : Network-Bound Branch     :          : squashing into existing :
:            : Garbage Collection       :          : update loops via hidden :
:            :                          :          : flags or implicit       :
:            :                          :          : execution.              :

--------------------------------------------------------------------------------

### Rules

#### T11-01: Standalone Execution for Network-Bound Branch Garbage Collection

> **Rule:** Always isolate network-bound local branch cleanup tasks into
> dedicated, standalone commands rather than embedding them as hidden flags in
> standard offline operations.
>
> **What:** Automated cleanup of local branches tied to remote state (e.g.,
> closed issues) must be isolated to a standalone command, preventing unexpected
> network latency or side effects in standard local repository operations.
>
> **Applies To:** Branch management commands (e.g., `git cl squash-closed`).
>
> **Why:** Integrating network-heavy garbage collection implicitly into a local
> rebase command risked surprising the user with unexpected API calls, slowing
> down offline workflows, and tightly coupling unrelated code paths. Failing to
> adhere to this typically results in **Unexpected Network Latency**.

**Trap 1: Coupling remote branch squashing into existing update loops via hidden
flags or implicit execution.**

**Don't:**

*   Adding a `--squash-closed` flag to `git cl rebase-update` which silently
    hits the network to check Gerrit state during a local rebase.

**Do:**

*   Exposing a dedicated, standalone `git cl squash-closed` command that clearly
    telegraphs its network-bound behavior to the user.

## Chapter: Defensive Host URL Parsing

**Context:** User-provided or environment-derived domain URLs must be parsed
using standard libraries like `urllib` rather than fragile manual string
manipulation. All parsing logic must be wrapped in defensive exception handling
to prevent malformed inputs from triggering raw stack traces.

### Summary

| Rule ID    | Principle / Constraint | Priority | Primary Symptom / Trap |
| :--------- | :--------------------- | :------- | :--------------------- |
| **T12-01** | Defensive Parsing for  | Critical | Using manual string    |
:            : Remote Host Resolution :          : replacement to strip   :
:            :                        :          : protocol prefixes and  :
:            :                        :          : slashes.               :

--------------------------------------------------------------------------------

### Rules

#### T12-01: Defensive Parsing for Remote Host Resolution

> **Rule:** Always use standard URL parsing libraries and strict exception
> handling to sanitize host domains. Never rely on manual string replacement to
> extract hostnames from user input.
>
> **What:** User-provided or environment-derived domain URLs must be parsed
> using robust standard libraries (like `urllib.parse.urlparse`) and wrapped in
> strict exception handling to gracefully manage malformed inputs.
>
> **Applies To:** `git cl cherry-pick` and any API client parsing a `--host`
> argument.
>
> **Why:** Manual string manipulation (replace/rstrip) for host extraction
> failed unexpectedly on edge cases, causing unhandled exceptions rather than
> graceful, actionable CLI errors. Failing to adhere to this typically results
> in **Unhandled Exception**.

**Trap 1: Using manual string replacement to strip protocol prefixes and
slashes.**

**Don't:**

```python
# BAD: Fragile string parsing
if host := options.host:
    host = host.replace('https://', '').rstrip('/')
```

**Do:**

```python
# GOOD: Standard library parsing with try/except
if host := options.host:
    try:
        host = urllib.parse.urlparse(host).hostname
    except ValueError:
        host = None
    if not host:
        print(f'Invalid host: {options.host}', file=sys.stderr)
        return 1
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Downstream:** T02 | Gerrit REST API & Revision Translation - *Safely
    resolved host URLs are required to instantiate robust Gerrit REST API client
    connections.*
*   **Downstream:** T13 | Actionable CLI Diagnostics & Terminology - *Gracefully
    caught parsing exceptions must yield actionable error messages rather than
    raw stack traces.*

## Chapter: Actionable CLI Diagnostics & Terminology

**Context:** This domain defines the strict linguistic and structural
requirements for CLI diagnostics, ensuring error messages use ubiquitous
terminology and provide copy-pasteable, context-aware recovery commands. It
prevents workflow blockages by mandating actionable output for unhandled states
and non-standard environments.

### Summary

| Rule ID    | Principle /          | Priority | Primary Symptom / Trap        |
:            : Constraint           :          :                               :
| :--------- | :------------------- | :------- | :---------------------------- |
| **T13-01** | Ubiquitous           | Medium   | Reusing 'issue'               |
:            : Terminology in CLI   :          : interchangeably to describe a :
:            : Outputs              :          : code revision.                :
| **T13-02** | Actionable Context   | Medium   | Returning a generic failure   |
:            : in                   :          : state without explaining the  :
:            : Environment-Specific :          : environment context or        :
:            : Diagnostics          :          : alternative solutions.        :
| **T13-03** | Interpolating Exact  | Medium   | Instructing the user to use a |
:            : Resumption           :          : flag without providing the    :
:            : Parameters in Error  :          : exact required argument       :
:            : States               :          : value.                        :
| **T13-04** | Explicit Terminal    | Medium   | Printing generic exception    |
:            : Instructions for CLI :          : messages and exiting without  :
:            : Conflict Recovery    :          : instructing the user on the   :
:            :                      :          : next steps.                   :

--------------------------------------------------------------------------------

### Rules

#### T13-01: Ubiquitous Terminology in CLI Outputs

> **Rule:** Always use precise domain terminology in CLI outputs, strictly
> distinguishing between Changelists (CLs) and bug tracker items (Issues).
>
> **What:** Error messages and CLI help texts must strictly distinguish between
> Changelists (CLs/revisions) and bug tracker items (Issues/Bugs).
>
> **Applies To:** All user-facing docstrings, error raises, and argument parser
> help fields.
>
> **Why:** Using the generic term 'issue' to refer to a Gerrit Changelist caused
> friction, as the domain vocabulary defaults to 'CL' for code changes and
> 'Issue' exclusively for bug tracker entries. Failing to adhere to this
> typically results in **User Confusion / UX Degradation**.

**Trap 1: Reusing 'issue' interchangeably to describe a code revision.**

**Don't:**

```python
parser.error('Must specify issue number or URL.')
```

**Do:**

```python
parser.error('Must specify CL number or URL.')
```

#### T13-02: Actionable Context in Environment-Specific Diagnostics

> **Rule:** Must provide exact UI alternatives or actionable bypass commands
> when halting execution due to an unsupported environment.
>
> **What:** CLI error messages resulting from unsupported environments must
> explicitly state the environment limitation and provide the exact UI
> alternative or command needed to bypass the blockage.
>
> **Applies To:** Tooling executed in non-git environments (e.g., Cog
> workspaces).
>
> **Why:** Users executing standard git operations in virtualized workspaces hit
> generic 'not supported' errors without a clear path to resolution, leading to
> immediate workflow blockages. Failing to adhere to this typically results in
> **Workflow Blockage**.

**Trap 1: Returning a generic failure state without explaining the environment
context or alternative solutions.**

**Don't:**

```python
# BAD: Dead-end error message
print('presubmit command is not supported in non-git environment.', file=sys.stderr)
```

**Do:**

```python
# GOOD: Explains context and gives actionable UI steps
print('presubmit command is not supported in non-git environment. Please use the "Chromium PRESUBMITS" panel or the "Run Presubmit Checks" command in the command palette instead.', file=sys.stderr)
```

#### T13-03: Interpolating Exact Resumption Parameters in Error States

> **Rule:** Always interpolate exact runtime identifiers directly into terminal
> instructions to eliminate manual user lookups during recovery.
>
> **What:** When a multi-step operation halts due to a recoverable error, the
> CLI output must interpolate the exact data identifiers (e.g., change numbers)
> required by CLI flags to resume the operation, rather than leaving the user to
> look them up.
>
> **Applies To:** Error handling in `git cl cherry-pick` during failed rebases.
>
> **Why:** When a rebase failed in a cherry-pick chain, users had to manually
> search the Gerrit UI or previous console logs to look up the last successful
> change number to resume the chain via the `--parent-change-num` flag. Failing
> to adhere to this typically results in **High Cognitive Load**.

**Trap 1: Instructing the user to use a flag without providing the exact
required argument value.**

**Don't:**

```python
# BAD: Generic instruction requiring manual lookup
print('Once resolved, you can continue the CL chain with --parent-change-num and specify which change the chain should start with.')
```

**Do:**

```python
# GOOD: Interpolated, copy-pasteable parameters
print(f'Once resolved, you can continue the CL chain with --parent-change-num {new_change_num}')
```

#### T13-04: Explicit Terminal Instructions for CLI Conflict Recovery

> **Rule:** Must dynamically generate and print exact recovery commands and
> remaining payload identifiers when halting on user-actionable conflicts.
>
> **What:** When an automated operation halts due to a user-actionable state
> (like a version control conflict), the terminal output must dynamically
> generate and print the exact recovery commands and remaining un-processed
> payloads required to resume.
>
> **Applies To:** Exception handling and error reporting blocks for CLI tools
> handling Git/Gerrit version control states (e.g., handling
> `gerrit_util.GerritError`).
>
> **Why:** When a batch script failed midway through processing multiple
> commits, users were left confused regarding which commits were already
> uploaded and exactly how to construct the command line arguments to finish the
> job. Failing to adhere to this typically results in **User Confusion / Stalled
> Workflow**.

**Trap 1: Printing generic exception messages and exiting without instructing
the user on the next steps.**

**Don't:**

```python
except gerrit_util.GerritError as e:
    print(f'Failed to rebase: {e}')
    return 1
```

**Do:**

```python
except gerrit_util.GerritError as e:
    print(f'Failed to rebase... Please resolve any merge conflicts.')
    print(f'Once resolved, you can continue the CL chain with `--parent-change-num={new_change_num}`')
    # Also inform user of remaining commits
    return 1
```

**Trap 2: Failing to disclose the remaining workload upon a mid-flight crash.**

**Don't:**

*   Terminating silently after an error, forcing the user to manually correlate
    local Git history with remote API state.

**Do:**

*   Dumping the specific remaining commit hashes or sequence identifiers to
    standard out before exit.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T01 | Git Worktree & Environment Abstraction - *Determines
    environmental boundaries (e.g., Cog) which trigger the environment-specific
    diagnostic rules.*
*   **Downstream:** T04 | Batch Operation Checkpointing & Conflict Recovery -
    *Relies directly on these diagnostic rules to present accurate
    `--parent-change-num` checkpoint data for chained operations.*
*   **Downstream:** T09 | Rebase Traversal & Conflict Escapes - *Surfaces
    explicit rebase escapes and instructions utilizing the output formatting
    mandated here.*
