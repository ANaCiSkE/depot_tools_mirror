# Depot Tools Infrastructure Engineering Guide

## Executive Summary

This guide serves as the authoritative repository of tribal knowledge for the
Depot Tools Infrastructure subsystem. Created to prevent the regression of known
failure modes and capture critical historical context, this document establishes
strict architectural constraints for all engineers operating within the Android
and Chromium build infrastructure ecosystem. By formalizing these guidelines, we
ensure that the complex machinery powering source control management, dependency
resolution, and build pipelines remains robust, predictable, and easily
maintainable across a heavily abstracted, cross-platform workspace.

The overarching technical domains covered within this payload span the entire
lifecycle of developer tooling and CI interaction. This includes the
deterministic management of hybrid SCM workspaces, the hermetic execution of
Python environments via vpython, multithreaded Gclient dependency resolution,
and rigorous presubmit telemetry infrastructure. It further addresses the safe
orchestration of automated formatters, the concurrency rules required for
optimizing shared developer caches, and the highly specific OS-level constraints
required for reliable Windows build toolchains.

Ultimately, this guide establishes clear operational boundaries designed to
safeguard developer velocity. By detailing specific traps, edge cases, and
design anti-patterns—ranging from Git configuration leakage to multi-drive path
resolution bounds—it empowers infrastructure engineers to build resilient,
platform-agnostic tooling without repeating the costly architectural mistakes of
the past.

## Summary

| Chapter Theme / Title                | Scope & Objective                     |
| :----------------------------------- | :------------------------------------ |
| **SCM Wrapper & Git Configuration    | This domain governs version control   |
: Management**                         : abstractions, configuration           :
:                                      : bootstrapping, and sub-process        :
:                                      : execution for Git and alternative     :
:                                      : integrations like Jujutsu. It         :
:                                      : enforces deterministic parsing of Git :
:                                      : states, robust handling of Gerrit     :
:                                      : references, and cross-platform        :
:                                      : compatibility across hybrid source    :
:                                      : control workspaces.                   :
| **Gclient Dependency Resolution &    | This domain governs cross-platform    |
: Execution**                          : dependency resolution, CIPD external  :
:                                      : path targeting, and multithreaded     :
:                                      : ExecutionQueue management. It         :
:                                      : strictly enforces hermetic caching,   :
:                                      : parallel hook concurrency, and        :
:                                      : accurate DEPS parsing to guarantee    :
:                                      : consistent build environments.        :
| **Hermetic Python Environments       | This chapter governs the              |
: (vpython)**                          : configuration and execution of        :
:                                      : hermetic Python environments across   :
:                                      : Depot Tools. It strictly defines      :
:                                      : `.vpython3` dependency management,    :
:                                      : namespace isolation, and legacy       :
:                                      : Python version compatibility          :
:                                      : requirements to ensure consistent,    :
:                                      : cross-platform toolchain execution.   :
| **Presubmit Infrastructure &         | This subsystem governs the strict     |
: Telemetry**                          : constraints for automated repository  :
:                                      : validation and CI telemetry           :
:                                      : reporting. It mandates standardized   :
:                                      : metadata propagation, precise         :
:                                      : environment isolation, and accurate   :
:                                      : git-state parsing to ensure presubmit :
:                                      : checks are reliable, fast, and        :
:                                      : Gerrit-compatible.                    :
| **Formatter & Linter Orchestration** | This domain orchestrates              |
:                                      : language-agnostic and                 :
:                                      : language-specific code formatters     :
:                                      : across multiple platforms. It         :
:                                      : enforces strict project boundary      :
:                                      : traversal, granular syntax exclusion, :
:                                      : precise dependency validation, and    :
:                                      : diff-based execution logic to prevent :
:                                      : configuration leakage and silent tool :
:                                      : failures.                             :
| **Resource Concurrency & Cache       | This domain governs the               |
: Optimization**                       : synchronization and optimization of   :
:                                      : shared developer resources, defining  :
:                                      : strict constraints for                :
:                                      : high-concurrency git cache access,    :
:                                      : dynamic thread scaling, and atomic,   :
:                                      : per-repository file locking.          :
| **Platform-Specific Build Toolchains | This chapter dictates                 |
: (Windows)**                          : Windows-specific execution            :
:                                      : constraints, governing filesystem     :
:                                      : limits, PowerShell boundary           :
:                                      : invocations, path resolution across   :
:                                      : multi-drive or Cygwin environments,   :
:                                      : and the strict handling of NTFS       :
:                                      : directory junctions.                  :

--------------------------------------------------------------------------------
--------------------------------------------------------------------------------

## Chapter: SCM Wrapper & Git Configuration Management

**Context:** This domain governs version control abstractions, configuration
bootstrapping, and sub-process execution for Git and alternative integrations
like Jujutsu. It enforces deterministic parsing of Git states, robust handling
of Gerrit references, and cross-platform compatibility across hybrid source
control workspaces.

### Summary

| Rule ID   | Principle /          | Priority | Primary Symptom  |
:           : Constraint           :          : / Trap           :
| :-------- | :------------------- | :------- | :--------------- |
| **T1-01** | Aligning Generated   | Medium   | Generating       |
:           : SCM Configuration    :          : exhaustive       :
:           : with Presubmit       :          : configuration    :
:           : Exceptions           :          : files that       :
:           :                      :          : include          :
:           :                      :          : stub/placeholder :
:           :                      :          : repositories     :
:           :                      :          : without          :
:           :                      :          : filtering.       :
| **T1-02** | Composition over     | High     | Creating a stub  |
:           : Inheritance for      :          : sub-class for a  :
:           : Hybrid SCM           :          : new SCM tool     :
:           : Workspaces           :          : that breaks      :
:           :                      :          : functionality in :
:           :                      :          : directories      :
:           :                      :          : where the legacy :
:           :                      :          : SCM tool still   :
:           :                      :          : exists.          :
| **T1-03** | Idempotent URL Path  | High     | Unconditionally  |
:           : Encoding in API      :          : calling          :
:           : Clients              :          : url-quoting      :
:           :                      :          : functions on     :
:           :                      :          : dynamic paths,   :
:           :                      :          : leading to       :
:           :                      :          : double-encoding  :
:           :                      :          : if the string    :
:           :                      :          : was already      :
:           :                      :          : partially        :
:           :                      :          : encoded or       :
:           :                      :          : contains query   :
:           :                      :          : artifacts.       :
| **T1-04** | Explicit Maintenance | Medium   | Adding a new     |
:           : Boundaries for       :          : tool directory   :
:           : Experimental SCM     :          : and workflow     :
:           : Wrappers             :          : scripts without  :
:           :                      :          : outlining        :
:           :                      :          : official support :
:           :                      :          : SLA/SLOs.        :
| **T1-05** | Scheme-Agnostic      | Medium   | Hardcoding       |
:           : Hostname Extraction  :          : condition checks :
:           : in Git URLs          :          : against specific :
:           :                      :          : URI schemes to   :
:           :                      :          : extract          :
:           :                      :          : hostnames.       :
| **T1-06** | Explicit Diff        | High     | Relying on the   |
:           : Prefixes for         :          : user's default   :
:           : Deterministic SCM    :          : git config for   :
:           : Parsing              :          : diff prefixes,   :
:           :                      :          : causing tool     :
:           :                      :          : failures on      :
:           :                      :          : certain          :
:           :                      :          : machines.        :
| **T1-07** | Gerrit Change        | High     | Assuming any     |
:           : Reference            :          : reference        :
:           : Classification       :          : starting with    :
:           :                      :          : 'refs/' is a     :
:           :                      :          : branch.          :
| **T1-08** | Strict Gitlink SHA-1 | Critical | Assuming all     |
:           : Validation           :          : revisions        :
:           : Post-Fetch           :          : classified as a  :
:           :                      :          : 'hash' are valid :
:           :                      :          : SHA-1 commits    :
:           :                      :          : that can be      :
:           :                      :          : verified         :
:           :                      :          : locally.         :
| **T1-09** | Superproject Git     | Medium   | Executing the    |
:           : Push Option          :          : push command     :
:           : Aggregation          :          : using only the   :
:           :                      :          : newly generated  :
:           :                      :          : metadata or the  :
:           :                      :          : user options     :
:           :                      :          : independently.   :
| **T1-10** | Legacy Git           | Critical | Using Git 2.46+  |
:           : Subcommand Syntax    :          : specific         :
:           : Compatibility        :          : subcommand       :
:           :                      :          : syntax for       :
:           :                      :          : configuration    :
:           :                      :          : queries to avoid :
:           :                      :          : hyphens.         :
| **T1-11** | Null-Terminated      | High     | Iterating over   |
:           : Parsing for Git      :          : `git config`     :
:           : Configuration Values :          : output           :
:           :                      :          : line-by-line     :
:           :                      :          : using standard   :
:           :                      :          : string splitting :
:           :                      :          : logic.           :
| **T1-12** | Mixed                | Medium   | Using standard   |
:           : Case-Sensitivity     :          : Python           :
:           : Handling for Git     :          : dictionaries for :
:           : Configuration Keys   :          : mapping and      :
:           :                      :          : comparing user   :
:           :                      :          : Git              :
:           :                      :          : configuration    :
:           :                      :          : keys against     :
:           :                      :          : expected states. :
| **T1-13** | Explicit State       | Medium   | Logging a        |
:           : Directives in        :          : generic warning  :
:           : Configuration        :          : that the tool    :
:           : Warnings             :          : wants to         :
:           :                      :          : automatically    :
:           :                      :          : alter the global :
:           :                      :          : environment.     :
| **T1-14** | Idempotent           | Medium   | Preventing state |
:           : Exact-Match          :          : application if   :
:           : Versioning for       :          : the existing     :
:           : Configurations       :          : version is equal :
:           :                      :          : to or newer than :
:           :                      :          : the target       :
:           :                      :          : version.         :
| **T1-15** | Scope-Aware Git      | High     | Invoking a       |
:           : Configuration Batch  :          : subprocess to    :
:           : Fetching             :          : fetch            :
:           :                      :          : configuration    :
:           :                      :          : repeatedly for   :
:           :                      :          : every submodule  :
:           :                      :          : inside a loop.   :
| **T1-16** | Encapsulation of     | Medium   | Relying on the   |
:           : Environment-Specific :          : caller to        :
:           : Validation Logic     :          : evaluate the     :
:           :                      :          : environment      :
:           :                      :          : before invoking  :
:           :                      :          : a core           :
:           :                      :          : validation       :
:           :                      :          : utility.         :

--------------------------------------------------------------------------------

### Rules

#### T1-01: Aligning Generated SCM Configuration with Presubmit Exceptions

> **Rule:** Always filter known stub or placeholder paths from generated SCM
> configuration files to maintain alignment with canned presubmit checks.
>
> **What:** Tools that automatically generate source control configurations
> (e.g., `gclient gitmodules`) must explicitly exclude paths that are known
> placeholders or otherwise skipped by `git cl presubmit` rules to prevent
> continuous integration failures.
>
> **Applies To:** gclient.py (gitmodules generation) and Presubmit Canned
> Checks.
>
> **Why:** Running `gclient gitmodules` generated configurations that included
> `third_party/dummy_chromium` and `placeholder_chromium`. This created a
> sticking point for projects like Dawn and ANGLE, because those generated files
> subsequently failed `git cl presubmit` checks which expected those paths to be
> ignored. Failing to adhere to this typically results in **Presubmit Rejection
> / Workflow Friction**.

**Trap 1: Generating exhaustive configuration files that include
stub/placeholder repositories without filtering.**

**Don't:**

*   Writing every resolved gclient dependency into `.gitmodules`.

**Do:**

*   Filtering known placeholder paths (`dummy_chromium`, `placeholder_chromium`)
    out of the generated `.gitmodules` to align with canned presubmit exception
    lists.

--------------------------------------------------------------------------------

#### T1-02: Composition over Inheritance for Hybrid SCM Workspaces

> **Rule:** Must use composition rather than inheritance when implementing new
> SCM wrappers to preserve legacy VCS fallback capabilities in co-located
> workspaces.
>
> **What:** SCM wrapper abstractions (like Jujutsu/Git) must use composition to
> delegate supported commands when operating in hybrid/co-located directories
> rather than overriding base classes with no-ops.
>
> **Applies To:** SCM Wrappers (`scm.py`), gclient sync target operations, and
> Jujutsu integration.
>
> **Why:** Changing the Jujutsu wrapper to inherit from a bare `SCMWrapper`
> effectively disabled platform-specific dependency synchronization (e.g.,
> `target_os` resolution for fetching Android deps) because underlying Git
> properties were completely overridden or unhandled. Co-located `.jj` and
> `.git` repos require the fallback execution of Git commands. Failing to adhere
> to this typically results in **Broken Dependency Resolution**.

**Trap 1: Creating a stub sub-class for a new SCM tool that breaks functionality
in directories where the legacy SCM tool still exists.**

**Don't:**

```python
# BAD: Inheriting from a bare wrapper and implicitly disabling Git logic
class JjWrapper(gclient_scm.SCMWrapper):
    def update(self):
        pass # Missing git logic
```

**Do:**

```python
# GOOD: Using composition to delegate to Git when present
class JjWrapper(gclient_scm.SCMWrapper):
    def __init__(self, ...):
        if pathlib.Path('.git').exists():
            self._git_wrapper = GitWrapper(...)

    def update(self, ...):
        if self._git_wrapper:
            self._git_wrapper.update(...)
```

**Exceptions:** Standalone `.jj` workspaces without a `.git` directory where no
legacy capabilities are required.

--------------------------------------------------------------------------------

#### T1-03: Idempotent URL Path Encoding in API Clients

> **Rule:** Always conditionally encode external API URL path segments to
> prevent double-encoding of special characters or query parameters.
>
> **What:** When constructing URLs for external API requests (e.g., Gitiles),
> URL path segments must be conditionally encoded to prevent double-encoding of
> special characters or query parameters.
>
> **Applies To:** Gerrit/Gitiles Clients (`gerrit_client.py`); Network and API
> integration layers.
>
> **Why:** File paths containing spaces were failing to fetch from Gitiles. A
> naive attempt to encode the path broke requests containing query parameters by
> double-encoding them. Failing to adhere to this typically results in **HTTP
> 400/404 Errors**.

**Trap 1: Unconditionally calling url-quoting functions on dynamic paths,
leading to double-encoding if the string was already partially encoded or
contains query artifacts.**

**Don't:**

```python
path = urllib.parse.quote(path)
```

**Do:**

```python
# Prevent double quoting.
if urllib.parse.unquote(path) == path:
    path = urllib.parse.quote(path)
```

--------------------------------------------------------------------------------

#### T1-04: Explicit Maintenance Boundaries for Experimental SCM Wrappers

> **Rule:** Must boldly document unsupported, experimental status on
> community-contributed alternative VCS integrations to strictly limit
> maintenance scope.
>
> **What:** Community-contributed integrations for alternative version control
> systems (e.g., Jujutsu/jj) must include prominent documentation explicitly
> defining their unsupported, experimental status to prevent unintended
> maintenance liability.
>
> **Applies To:** Tooling documentation (e.g., `jj/README.md`) and configuration
> files bridging external tools with `depot_tools`.
>
> **Why:** The introduction of modern VCS alternatives required a strict
> governance boundary to ensure that the core infrastructure team would not be
> expected to triage, fix bugs, or maintain SLOs for tools they did not natively
> author. Failing to adhere to this typically results in **Support Sprawl /
> Scope Creep**.

**Trap 1: Adding a new tool directory and workflow scripts without outlining
official support SLA/SLOs.**

**Don't:**

*   Adding the tool to the repository with standard usage instructions, implying
    it has the same support guarantees as core tools.

**Do:**

*   Adding a clear, bolded "Unsupported status" disclaimer explicitly stating:
    "jj is not officially supported... works on a best-effort and as-is basis...
    There is no SLO for triage or fixing of bugs and no dedicated staffing."

--------------------------------------------------------------------------------

#### T1-05: Scheme-Agnostic Hostname Extraction in Git URLs

> **Rule:** Parse git URLs using standard scheme-agnostic URI extraction to
> avoid fragile, hardcoded branching against specific transport protocols like
> `sso://`.
>
> **What:** URL parsing logic for Git repository extraction should avoid
> hardcoded branching based on the protocol scheme (e.g., branching on
> `sso://`), relying instead on standard URI structure parsing.
>
> **Applies To:** URL parsing and repository extraction utilities within Git SCM
> wrappers (e.g., git_cl.py).
>
> **Why:** Previous parsing logic attempted to handle 'sso' URLs differently
> from 'https' URLs, which created fragile edge cases and redundant string
> manipulations when determining the target Gerrit host. Failing to adhere to
> this typically results in **Incorrect Host Extraction**.

**Trap 1: Hardcoding condition checks against specific URI schemes to extract
hostnames.**

**Don't:**

```python
# BAD: Scheme-specific branching
parts = urllib.parse.urlparse(x)
if parts.scheme == 'sso':
    host = parts.netloc
else:
    host = parts.netloc.split('.')[0]
```

**Do:**

```python
# GOOD: Scheme-agnostic parsing using consistent string manipulation
parts = urllib.parse.urlparse(x)
host = parts.netloc.split('.')[0]
if host.endswith('-review'):
    host = host[:-len('-review')]
```

--------------------------------------------------------------------------------

#### T1-06: Explicit Diff Prefixes for Deterministic SCM Parsing

> **Rule:** Always explicitly inject `--src-prefix` and `--dst-prefix` when
> generating unified diffs via Git to override arbitrary local configuration
> defaults (e.g., `diff.noprefix`).
>
> **What:** Git SCM wrappers generating unified diffs for downstream tools must
> explicitly inject `--src-prefix` and `--dst-prefix` arguments to override
> arbitrary user configurations.
>
> **Applies To:** SCM Wrappers generating diffs for formatters and parsers
> (e.g., `git_cl.py`, `scm.py`).
>
> **Why:** Users with `diff.noprefix` enabled in their global Git configurations
> produced diffs missing the expected 'a/' and 'b/' prefixes. This caused
> downstream automated diff parsers to crash or fail to map modified lines.
> Failing to adhere to this typically results in **Diff Parsing Failure**.

**Trap 1: Relying on the user's default git config for diff prefixes, causing
tool failures on certain machines.**

**Don't:**

```python
# BAD: Does not override user config, vulnerable to diff.noprefix
command = [
    'diff',
    '-p',
    '--no-color',
    '--no-ext-diff',
    branch + "..." + branch_head,
]
```

**Do:**

```python
# GOOD: Explicitly enforce standard prefixes for consumable diffs
command = [
    'diff',
    '-p',
    '--no-color',
    '--no-ext-diff',
]
if allow_prefix:
    command += ['--src-prefix=a/', '--dst-prefix=b/']
else:
    command += ['--no-prefix']
```

**Exceptions:** Diff operations strictly intended for direct human reading in
the CLI, where tool parsing is not a requirement.

--------------------------------------------------------------------------------

#### T1-07: Gerrit Change Reference Classification

> **Rule:** Never classify Gerrit change references (`refs/changes/*`) as local
> tracking branches; treat them strictly as immutable hash revisions.
>
> **What:** Gerrit change references (`refs/changes/*`) must be strictly
> classified as immutable hash revisions rather than tracking branches to
> prevent unintended side effects during checkout.
>
> **Applies To:** gclient revision type detection logic (e.g.,
> `gclient_scm.py`).
>
> **Why:** Historically, gclient mistakenly identified `refs/changes/*` as local
> branches because it blindly matched the `refs/` prefix. This led to confusing
> checkout behaviors, such as gclient incorrectly creating local tracking
> branches for static code review changes. Failing to adhere to this typically
> results in **Branch Pollution / Sync Conflict**.

**Trap 1: Assuming any reference starting with 'refs/' is a branch.**

**Don't:**

```python
# BAD: Treats Gerrit changes as local branches
if revision.startswith('refs/'):
    rev_type = "branch"
```

**Do:**

```python
# GOOD: Narrow branch definition, handle changes explicitly as hashes
if revision.startswith('refs/heads/'):
    rev_type = "branch"
elif revision.startswith('refs/changes/'):
    # Treat refs for changes as hash since it's not a local branch
    rev_type = "hash"
```

--------------------------------------------------------------------------------

#### T1-08: Strict Gitlink SHA-1 Validation Post-Fetch

> **Rule:** Validate fetched Gitlink revisions against strict 40-character SHA-1
> regex before attempting local repository verification to avoid crashing on
> Gerrit refs.
>
> **What:** Gclient must explicitly verify that a requested Gitlink revision
> exists in the local mirror after a fetch. However, it must use strict SHA-1
> regex validation to avoid incorrectly verifying Gerrit `refs/changes/*` as
> standard hashes.
>
> **Applies To:** gclient source control management (`gclient_scm.py`);
> dependency mirroring and sync logic.
>
> **Why:** Gclient failed to catch bad Gitlink revisions, allowing broken
> dependencies to silently pass the sync phase and fail randomly downstream. A
> fix was added to verify the hash post-fetch, but it incorrectly treated
> `refs/changes/*` as hashes, which caused valid syncs to fail because Gerrit
> refs aren't standard local commits. Failing to adhere to this typically
> results in **Silent Build Failure / Sync Crash**.

**Trap 1: Assuming all revisions classified as a 'hash' are valid SHA-1 commits
that can be verified locally.**

**Don't:**

```python
# BAD: Treating Gerrit refs as checkable hashes
if rev_type == 'hash' and not mirror.contains_revision(revision):
    raise gclient_utils.Error(f'Failed to fetch {revision}.')
```

**Do:**

```python
# GOOD: Explicitly validating the revision is a 40-character SHA-1 before checking existence
is_sha = gclient_utils.IsFullGitSha(revision)
if rev_type == 'hash' and is_sha and not mirror.contains_revision(revision):
    raise gclient_utils.Error(f'Failed to fetch {revision}.')
```

**Exceptions:** Gerrit change references (`refs/changes/*`) which do not
correspond to standard local commit hashes in the git mirror.

--------------------------------------------------------------------------------

#### T1-09: Superproject Git Push Option Aggregation

> **Rule:** Always aggregate dynamically generated superproject push options
> with any existing developer-supplied `git push` options rather than
> overwriting them.
>
> **What:** When generating automated `git push` commands, generated
> superproject push options (e.g., `rootRepo:$host/$repo`) must be concatenated
> with any user-supplied push options, not overwrite them.
>
> **Applies To:** Git CL wrapper (`git_cl.py`); Gerrit push operations.
>
> **Why:** The introduction of automated superproject metadata to Gerrit push
> options initially failed to properly combine with existing push options passed
> by developers, causing metadata to be dropped during the upload. Failing to
> adhere to this typically results in **Dropped Metadata / Server Reject**.

**Trap 1: Executing the push command using only the newly generated metadata or
the user options independently.**

**Don't:**

```python
# BAD: Overwriting or dropping user options
push_cmd = ['git', 'push', remote_url, refspec]
if superproject_option := _prepare_superproject_push_option():
    push_cmd.extend(['-o', superproject_option])
# Ignores git_push_options provided by user
```

**Do:**

```python
# GOOD: Aggregating all push options
all_push_options = []
if git_push_options:
    all_push_options.extend(git_push_options)
if superproject_option := _prepare_superproject_push_option():
    all_push_options.append(superproject_option)
```

--------------------------------------------------------------------------------

#### T1-10: Legacy Git Subcommand Syntax Compatibility

> **Rule:** Use option-based Git subcommand syntax (e.g., `--list`) rather than
> modern non-hyphenated subcommands to maintain compatibility with legacy Git
> distributions.
>
> **What:** When invoking Git configuration operations via sub-processes in
> cross-platform tools, scripts must use option-based syntax (e.g., `--list`,
> `--unset`) rather than the newer subcommand syntax (e.g., `list`, `unset`).
>
> **Applies To:** Depot Tools bootstrap scripts (`bootstrap.py`) and environment
> management utilities interfacing with the global Git environment.
>
> **Why:** A refactor migrated configuration queries to the newer `git config
> list` and `git config unset` subcommands introduced in Git 2.46. This broke
> the depot_tools Windows bootstrap process because the bundled Git version was
> 2.41.0, which only supports the `--list` syntax. Failing to adhere to this
> typically results in **Subprocess Exit 128 / Script Crash**.

**Trap 1: Using Git 2.46+ specific subcommand syntax for configuration queries
to avoid hyphens.**

**Don't:**

```python
# BAD: Fails on Git < 2.46
stdout, _ = _check_call([git_path, 'config', 'list', '--global', '-z'])
```

**Do:**

```python
# GOOD: Backward compatible syntax
stdout, _ = _check_call([git_path, 'config', '--list', '--global', '-z'])
```

**Exceptions:** Environments strictly controlled and verified to run Git 2.46.0
or higher.

--------------------------------------------------------------------------------

#### T1-11: Null-Terminated Parsing for Git Configuration Values

> **Rule:** Always execute global git configuration queries with null-byte
> termination (`-z`) and split by `\0` to safely handle multi-line configuration
> values.
>
> **What:** When parsing the output of global Git configurations via
> subprocesses, always use the `-z` (null-byte termination) flag and split the
> output by `\0` instead of standard newline parsing.
>
> **Applies To:** Python scripts reading Git configurations via
> `subprocess.PIPE` across arbitrary user environments.
>
> **Why:** Standard line splitting (`splitlines()`) caused parsing errors and
> corrupted state tracking when users had multi-line Git configuration values,
> such as complex custom aliases or paths. Failing to adhere to this typically
> results in **Parsing Failure / Config Corruption**.

**Trap 1: Iterating over `git config` output line-by-line using standard string
splitting logic.**

**Don't:**

```python
# BAD: Breaks on multiline values
stdout, _ = _check_call([git_path, 'config', '--list', '--global'])
for line in stdout.splitlines():
    entry = line.strip().split('=', 1)
```

**Do:**

```python
# GOOD: Safely parse multiline values using null-bytes
stdout, _ = _check_call([git_path, 'config', '--list', '--global', '-z'])
for line in stdout.split('\0'):
    entry = line.split('\n', 1)
```

--------------------------------------------------------------------------------

#### T1-12: Mixed Case-Sensitivity Handling for Git Configuration Keys

> **Rule:** Implement Git's native mixed case-sensitivity mapping logic
> (case-insensitive sections/names, case-sensitive subsections) when caching or
> comparing configuration states.
>
> **What:** Configuration parsers must explicitly implement Git's mixed
> case-sensitivity rules during lookups: section and variable names are
> case-insensitive, while subsection headers are case-sensitive.
>
> **Applies To:** Internal Python dictionaries and validation logic representing
> Git configuration state.
>
> **Why:** Direct string comparisons of Git configuration keys caused redundant
> configuration updates. Python string comparison is strictly case-sensitive,
> triggering false mismatches when users defined Git configurations with
> differing capitalization that Git itself interprets as identical. Failing to
> adhere to this typically results in **Redundant State Updates**.

**Trap 1: Using standard Python dictionaries for mapping and comparing user Git
configuration keys against expected states.**

**Don't:**

```python
# BAD: Strict case matching triggers false positives
if current_config.get(key) != target_config.get(key):
    update_config(key)
```

**Do:**

```python
# GOOD: Normalize sections and names, preserve subsections
class GitConfigDict(collections.UserDict):
    @staticmethod
    def _to_case_compliant_key(config_key):
        parts = config_key.split('.')
        section = parts[0].lower()
        subsection_parts = parts[1:-1] # Case-sensitive
        name = parts[-1].lower()
        return '.'.join([section] + subsection_parts + [name])
```

--------------------------------------------------------------------------------

#### T1-13: Explicit State Directives in Configuration Warnings

> **Rule:** Output the exact, copy-pasteable CLI commands required to align
> developer environments instead of issuing generic configuration approval
> prompts.
>
> **What:** When a CLI tool warns users about sub-optimal global configurations,
> it must print the exact, copy-pasteable CLI commands required to manually
> align the environment, avoiding generic approval prompts.
>
> **Applies To:** CLI initialization, depot_tools bootstrapping routines, and
> user-facing environment audits.
>
> **Why:** Users were confused and hesitant to enable an opaque
> `allowGlobalGitConfig` automation flag because they did not know exactly what
> global git settings would be altered on their host machines. Failing to adhere
> to this typically results in **User Confusion / Stalled Onboarding**.

**Trap 1: Logging a generic warning that the tool wants to automatically alter
the global environment.**

**Don't:**

*   Log a generic warning: "depot_tools would like to update your global Git
    config. Allow this by running: git config --global allowGlobalGitConfig
    true"

**Do:**

*   Print exact commands: "depot_tools recommends setting the following:\n $ git
    config --global core.autocrlf false\n You can silence this message by
    setting these recommended values."

--------------------------------------------------------------------------------

#### T1-14: Idempotent Exact-Match Versioning for Configurations

> **Rule:** Enforce exact-match equality (`==`) rather than inclusive bound
> (`>=`) checks for configuration versions to ensure seamless workflow
> rollbacks.
>
> **What:** Bootstrapping scripts that apply global system or tool
> configurations must use exact-match equality (`==`) rather than inclusive
> bound (`>=`) checks for configuration versions.
>
> **Applies To:** Global git configuration bootstrapping, state synchronization
> scripts, and post-processing tools.
>
> **Why:** If a developer needed to roll back to a previous checkout that
> required an older configuration standard, a `>=` check would silently ignore
> the downgrade, leaving the developer on a broken or incompatible configuration
> state. Failing to adhere to this typically results in **Inconsistent State /
> Rollback Failure**.

**Trap 1: Preventing state application if the existing version is equal to or
newer than the target version.**

**Don't:**

```python
# BAD: Prevents rollbacks
if postprocess_version >= GIT_POSTPROCESS_VERSION:
    return
```

**Do:**

```python
# GOOD: Ensures the state perfectly matches the current codebase requirement
if postprocess_version == GIT_POSTPROCESS_VERSION:
    return
```

**Exceptions:** Scenarios where configuration versioning is strictly
backwards-compatible and rolling back tooling explicitly forbids mutating
external environment settings.

--------------------------------------------------------------------------------

#### T1-15: Scope-Aware Git Configuration Batch Fetching

> **Rule:** Batch-fetch all git submodule configurations and their scopes in a
> single subprocess call (`git config --list -z --show-scope`) to eliminate
> redundant invocations and avoid global overrides.
>
> **What:** When querying git configuration across numerous submodules, retrieve
> all configurations and their scopes (local/global/system) in a single batch
> subprocess call using `git config --list -z --show-scope` instead of querying
> per submodule.
>
> **Applies To:** gclient_scm.py, scm.py, and all scripts executing git config
> checks across submodules.
>
> **Why:** Historically, checking configuration (like `diff.ignoreSubmodules`)
> for each submodule individually caused 100+ separate git invocations, adding
> significant seconds to sync operations on platforms like Windows. Furthermore,
> failing to check the scope caused silent overwriting of user-specified global
> configs because the tool couldn't distinguish a local override from a global
> default. Failing to adhere to this typically results in **Sync Degradation /
> Silent Config Overwrite**.

**Trap 1: Invoking a subprocess to fetch configuration repeatedly for every
submodule inside a loop.**

**Don't:**

```python
for submodule in submodules:
    val = scm.GIT.GetConfig(path, 'diff.ignoresubmodules')
```

**Do:**

```python
# Fetch all configs with scope in one call
rawConfig = GIT.Capture(['config', '--list', '-z', '--show-scope'], cwd=root)
# Parse and cache into a dictionary keyed by scope and config key
```

**Trap 2: Assuming a returned config value is local when it was actually
inherited from the global scope, leading to unintended local overrides.**

**Don't:**

```python
ignore_submodules = scm.GIT.GetConfig(checkout_path, 'diff.ignoreSubmodules')
if ignore_submodules != 'dirty':
    config_updates.append(('diff.ignoreSubmodules', 'dirty'))
```

**Do:**

```python
ignore_submodules = scm.GIT.GetConfig(checkout_path, 'diff.ignoreSubmodules', scope='local')
if ignore_submodules is None:
    config_updates.append(('diff.ignoreSubmodules', 'dirty'))
```

**Exceptions:** When backward compatibility requires falling back to reading all
scopes (e.g., `scope='default'`) if the explicit scope isn't provided by legacy
callers.

--------------------------------------------------------------------------------

#### T1-16: Encapsulation of Environment-Specific Validation Logic

> **Rule:** Encapsulate virtualized filesystem checks and environment
> validations directly inside the core utility functions rather than delegating
> them to the caller.
>
> **What:** Validation utilities (e.g., git version checking) must
> self-determine whether their checks are applicable to the current execution
> environment (e.g., virtualized filesystems) rather than forcing callers to
> implement environment checks.
>
> **Applies To:** git_common.py and all client-facing validation utilities.
>
> **Why:** Misleading git upgrade warnings were frequently printed for users
> operating inside virtualized development environments (like Cog) where local
> git versioning operates differently. This created log noise because individual
> call sites failed to check the environment. Failing to adhere to this
> typically results in **False-Positive Alerts / Log Noise**.

**Trap 1: Relying on the caller to evaluate the environment before invoking a
core validation utility.**

**Don't:**

```python
# Caller script
if not gclient_utils.IsEnvVirtual():
    recommendation = git_common.check_git_version()
    if recommendation:
        print(recommendation)
```

**Do:**

```python
# Inside git_common.check_git_version()
if gclient_utils.IsEnvVirtual():
    return None # Utility self-aborts based on context

# Caller just calls check_git_version() directly
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T2 | Gclient Dependency Resolution & Execution - *SCM wrappers
    rely on DEPS resolution pipelines to establish configuration boundaries and
    submodule states.*
*   **Downstream:** T4 | Presubmit Infrastructure & Telemetry - *Generated SCM
    configurations dictate the files evaluated and excluded by canned presubmit
    checks.*
*   **Downstream:** T5 | Formatter & Linter Orchestration - *Explicit git diff
    prefixes generated by SCM wrappers are required for accurate line boundary
    computations in formatters.*

## Chapter: Gclient Dependency Resolution & Execution

**Context:** This domain governs cross-platform dependency resolution, CIPD
external path targeting, and multithreaded ExecutionQueue management. It
strictly enforces hermetic caching, parallel hook concurrency, and accurate DEPS
parsing to guarantee consistent build environments.

### Summary

| Rule ID   | Principle /        | Priority | Primary Symptom / Trap           |
:           : Constraint         :          :                                  :
| :-------- | :----------------- | :------- | :------------------------------- |
| **T2-01** | Conditional Local  | High     | Retrieving and resolving the     |
:           : HEAD Verification  :          : local `origin/HEAD` branch       :
:           : for Dependency URL :          : regardless of URL drift.         :
:           : Switches           :          :                                  :
| **T2-02** | Content-Based      | Medium   | Relying on bash file age         |
:           : Caching over MTime :          : operators to evaluate if a       :
:           : Comparison         :          : cached dependency is stale.      :
| **T2-03** | Exception          | Critical | Terminating the script from      |
:           : Propagation in     :          : within a task meant to run in a  :
:           : Multithreaded      :          : thread pool.                     :
:           : Execution Queues   :          :                                  :
| **T2-04** | Duration-Based     | High     | Resetting the stall-detection    |
:           : Silence Detection  :          : timer solely based on a polling  :
:           : for Subprocess     :          : loop interval rather than the    :
:           : Stalls             :          : last recorded I/O event.         :
| **T2-05** | CIPD Version File  | High     | Opening the version file         |
:           : Path Resolution in :          : directly via its declared path,  :
:           : Nested             :          : implicitly assuming the tool is  :
:           : Sub-Dependencies   :          : run from the exact directory     :
:           :                    :          : containing the file.             :
| **T2-06** | Opt-In Dependency  | Medium   | Enforcing a global, inescapable  |
:           : Review Workflows   :          : review policy for every new      :
:           :                    :          : dependency.                      :
| **T2-07** | Conditional        | Medium   | Unconditionally appending a new  |
:           : Configuration      :          : configuration field to a managed :
:           : Writing for Staged :          : file before the upstream         :
:           : Rollouts           :          : repository has fully adopted it. :
| **T2-08** | Workspace-Isolated | High     | Relying on a global environment  |
:           : CIPD Root          :          : variable to dictate the internal :
:           : Configuration      :          : state of a toolchain, leading to :
:           :                    :          : cross-workspace interference.    :
| **T2-09** | Strict Subprocess  | Medium   | Echoing internal state or        |
:           : Stdout Suppression :          : resolved file paths from deeply  :
:           : in CLI Tooling     :          : nested initialization scripts    :
:           :                    :          : without parent interception.     :

--------------------------------------------------------------------------------

### Rules

#### T2-01: Conditional Local HEAD Verification for Dependency URL Switches

> **Rule:** Always verify the local checkout's upstream URL matches the
> requested remote URL before trusting the local HEAD branch for fetch
> operations.
>
> **What:** During a cache-backed Gclient sync, the default branch (HEAD) of the
> local repository must not be trusted or used for fetch/reset operations if the
> requested remote URL does not match the local checkout's current upstream URL.
>
> **Applies To:** Gclient SCM synchronization (gclient_scm.py) and Git submodule
> updates.
>
> **Why:** When a dependency's DEPS URL changed to a new mirror whose default
> branch was 'master' instead of 'main', `gclient` fetched the wrong default
> branch because it trusted the old checkout's `refs/remotes/origin/HEAD` before
> completing the URL switch. Failing to adhere to this typically results in
> **Fetch Failure / Incorrect Branch Reset**.

**Trap 1: Retrieving and resolving the local `origin/HEAD` branch regardless of
URL drift.**

**Don't:**

```python
revision = scm.GIT.GetRemoteHeadRef(self.checkout_path, self.url, self.remote)
```

**Do:**

```python
# Verify the local URL matches the expected URL before trusting local HEAD
use_local_head = (strp_current_url.rstrip('/') == strp_expected_url.rstrip('/'))
revision = scm.GIT.GetRemoteHeadRef(self.checkout_path, self.url, self.remote, use_local=use_local_head)
```

--------------------------------------------------------------------------------

#### T2-02: Content-Based Caching over MTime Comparison

> **Rule:** Must use strict file content comparison (`cmp`) instead of file
> modification timestamps (`mtime`) to evaluate cache invalidation.
>
> **What:** Cache validation logic in build scripts must rely on content
> comparison rather than file modification times (mtime) to determine
> invalidation.
>
> **Applies To:** Gclient dependency resolution, CIPD execution scripts, and
> CI/CD bot bootstrapping.
>
> **Why:** Using mtime for cache evaluation caused frequent false-positive cache
> misses on CI bots because git checkouts natively reset modification times,
> leading to hundreds of milliseconds of redundant latency per dependency
> operation. Failing to adhere to this typically results in **False-Positive
> Cache Miss**.

**Trap 1: Relying on bash file age operators to evaluate if a cached dependency
is stale.**

**Don't:**

```bash
# BAD: Using timestamp comparison for cache invalidation
if [ "$ENSURE_FILE" -nt "$CACHED_ENSURE" ]; then
    run_cipd_ensure
fi
```

**Do:**

```bash
# GOOD: Using strict content comparison (cmp)
if ! cmp -s "$ENSURE_FILE" "$CACHED_ENSURE"; then
    run_cipd_ensure
fi
```

--------------------------------------------------------------------------------

#### T2-03: Exception Propagation in Multithreaded Execution Queues

> **Rule:** Never invoke `sys.exit()` within an ExecutionQueue worker thread;
> always raise exceptions or return explicit error codes.
>
> **What:** Worker threads managed by an ExecutionQueue must bubble up failures
> via exceptions or return codes rather than invoking system-level exit
> functions.
>
> **Applies To:** Parallel gclient hook execution
> (`gclient_utils.ExecutionQueue`) and multithreaded task management.
>
> **Why:** When gclient hooks were parallelized, hooks that previously relied on
> `sys.exit()` to abort on failure started terminating only their local worker
> thread. The `ExecutionQueue` did not catch this thread termination as a
> failure, causing the main process to silently return a success exit code (0)
> despite critical build steps failing. Failing to adhere to this typically
> results in **Silent Failure / False Success**.

**Trap 1: Terminating the script from within a task meant to run in a thread
pool.**

**Don't:**

```python
# BAD: Calling sys.exit() inside a threaded worker
def run(self):
    if hook_failed:
        sys.exit(1)
```

**Do:**

```python
# GOOD: Raising an exception or returning an error code for the queue manager
def run(self):
    if hook_failed:
        raise HookExecutionError("Hook failed")
```

--------------------------------------------------------------------------------

#### T2-04: Duration-Based Silence Detection for Subprocess Stalls

> **Rule:** Must evaluate subprocess stalls against the absolute time elapsed
> since the last output event, rather than relying on the duration of polling
> intervals.
>
> **What:** Stall detection mechanisms for long-running operations must check
> the absolute time elapsed since the last output/event, rather than relying on
> loop iterations or boolean flags.
>
> **Applies To:** Gclient subprocess execution, build logs, and continuous
> integration observability.
>
> **Why:** An initial stall detection implementation failed to detect hanging
> processes if the process outputted initial text but stalled later. The polling
> loop only checked if any output occurred during the polling window, missing
> mid-task lockups. Failing to adhere to this typically results in **Undetected
> Process Hangs**.

**Trap 1: Resetting the stall-detection timer solely based on a polling loop
interval rather than the last recorded I/O event.**

**Don't:**

```python
# BAD: Fails to catch stalls that happen after initial output
if (now - self.last_join > stall_timeout):
    print_stall_diagnostics()
```

**Do:**

```python
# GOOD: explicitly verifying silence duration against the last subprocess output
if (now - self.last_join > stall_timeout and
    now - self.last_subproc_output > stall_timeout):
    print_stall_diagnostics()
```

--------------------------------------------------------------------------------

#### T2-05: CIPD Version File Path Resolution in Nested Sub-Dependencies

> **Rule:** Always resolve paths for external version files in CIPD
> sub-dependencies relative to the root `.gclient` directory, never the current
> working directory.
>
> **What:** Path resolution for external version files in CIPD dependencies must
> be calculated relative to the root `.gclient` directory and the specific
> parent dependency's relative path, rather than relying on the process's
> current working directory (CWD).
>
> **Applies To:** Gclient Dependency Resolution (`gclient.py`); specifically
> `CipdDependency` class and DEPS file parsing logic.
>
> **Why:** When a CIPD version file was specified inside a nested dependency
> (sub-DEPS), the gclient process attempted to read the file relative to the
> CWD. This caused 'file not found' errors or incorrect version parsing across
> different project structures. Failing to adhere to this typically results in
> **File Not Found**.

**Trap 1: Opening the version file directly via its declared path, implicitly
assuming the tool is run from the exact directory containing the file.**

**Don't:**

```python
if dep_value.get('version_file'):
    version = gclient_utils.FileRead(dep_value['version_file'])
```

**Do:**

```python
if dep_value.get('version_file'):
    version = gclient_utils.FileRead(
        os.path.join(parent.root.root_dir, dep_value['version_file']))
```

--------------------------------------------------------------------------------

#### T2-06: Opt-In Dependency Review Workflows

> **Rule:** Avoid mandatory architectural reviews for routine dependencies; must
> enforce low-friction, opt-in policies for `include_rules` review gates.
>
> **What:** When enforcing architectural boundary reviews (like OWNERS approval
> for new include directives), default to low friction unless the directory
> explicitly opts in, to avoid widespread reviewer fatigue.
>
> **Applies To:** DEPS file evaluation (`gclient_eval.py`), checkdeps tooling,
> and automated code review requirement policies.
>
> **Why:** Mandatory architectural review for every single cross-module
> dependency addition led to thousands of 'rubber stamp' approvals, degrading
> the signal-to-noise ratio of code reviews. Failing to adhere to this typically
> results in **Reviewer Fatigue / Developer Friction**.

**Trap 1: Enforcing a global, inescapable review policy for every new
dependency.**

**Don't:**

*   Automatically flag every `include_rules` modification across the entire
    repository to block submission until a senior architect explicitly approves.

**Do:**

*   Default to allowing routine dependency additions, but introduce an opt-in
    variable (e.g., `new_usages_require_review = True`) that sensitive modules
    can place in their DEPS files to request mandatory oversight.

**Exceptions:** Highly sensitive cross-domain security boundaries which may
strictly require a whitelist rather than an opt-in model.

--------------------------------------------------------------------------------

#### T2-07: Conditional Configuration Writing for Staged Rollouts

> **Rule:** Must conditionally write new fields in tracked configuration files
> based on their prior state to prevent state churn during phased toolchain
> rollouts.
>
> **What:** When introducing new fields to tracked configuration files, tooling
> must conditionally write the field based on the prior state of the file rather
> than forcing it unconditionally, preventing flip-flopping during rollout
> phases.
>
> **Applies To:** gclient.py (and tools managing version-controlled dotfiles
> like `.gitmodules`).
>
> **Why:** During the rollout of the `gclient-recursedeps` feature, users with
> updated infrastructure tools but older repository states experienced
> continuous local diff churn ('flip-flopping'). The tool would append the
> config, and then subsequent checkouts or syncs would revert it. Failing to
> adhere to this typically results in **Local State Churn / Dirty Worktree**.

**Trap 1: Unconditionally appending a new configuration field to a managed file
before the upstream repository has fully adopted it.**

**Don't:**

```python
f.write(f'\tgclient-recursedeps = true\n')
```

**Do:**

```python
# Only set if it already existed in the file (or file is brand new)
if 'gclient-recursedeps = true' in content_output_gitmodules:
    f.write(f'\tgclient-recursedeps = true\n')
```

**Exceptions:** When the tracked file does not exist at all, it is safe to write
the new configuration natively.

--------------------------------------------------------------------------------

#### T2-08: Workspace-Isolated CIPD Root Configuration

> **Rule:** Always bind CIPD root paths to workspace-scoped local files and
> route caching to system-local temporary directories to prevent multi-checkout
> collisions.
>
> **What:** CIPD root paths must be configurable via local, workspace-scoped
> files rather than global environment variables, and caching directories should
> be routed to performant, system-local temporary storage rather than
> virtualized filesystems.
>
> **Applies To:** CIPD setup scripts (e.g., `cipd_bin_setup.sh`), Depot Tools
> bootstrapping, and configurations interacting with virtual file systems (e.g.,
> Cog).
>
> **Why:** Using global environment variables for CIPD configuration caused
> state conflicts when multiple checkout toolchains were active simultaneously
> (e.g., a system-level preinstalled toolchain vs. one embedded in the
> repository). Additionally, defaulting package installation into virtualized
> workspaces caused severe I/O bottlenecks and cache eviction issues. Failing to
> adhere to this typically results in **State Corruption / IO Bottleneck**.

**Trap 1: Relying on a global environment variable to dictate the internal state
of a toolchain, leading to cross-workspace interference.**

**Don't:**

```bash
# BAD: Global env var dictates state, breaking concurrent setups
export DEPOT_TOOLS_CIPD_ROOT_OVERRIDE="/tmp/cipd_cache"
```

**Do:**

```bash
# GOOD: Read configuration from a workspace-local hidden file
CIPD_ROOT_OVERRIDE_FILE="${MYPATH}/.cipd_client_root"
if [ -f "${CIPD_ROOT_OVERRIDE_FILE}" ]; then
    ROOT=$(<"${CIPD_ROOT_OVERRIDE_FILE}")
fi
```

--------------------------------------------------------------------------------

#### T2-09: Strict Subprocess Stdout Suppression in CLI Tooling

> **Rule:** Must strictly redirect or capture standard output in internally
> executed setup scripts to prevent leaking debug paths to the terminal.
>
> **What:** Internal setup and initialization shell scripts executed by CLI
> tooling must strictly suppress or capture standard output to prevent leaking
> internal debug paths or configuration details to the user's terminal.
>
> **Applies To:** Subprocess invocation and shell scripts executed during
> commands like `gclient sync` or bootstrap operations.
>
> **Why:** Adding an `echo` statement inside an internal setup script leaked
> local file paths into the terminal UI of high-level user commands, causing
> unnecessary distraction and polluting scriptable CLI outputs. Failing to
> adhere to this typically results in **CLI Output Pollution**.

**Trap 1: Echoing internal state or resolved file paths from deeply nested
initialization scripts without parent interception.**

**Don't:**

```bash
# BAD: Leaking internal resolved state directly to the terminal stdout
echo $ROOT
```

**Do:**

*   Ensure parent orchestrators (like Python CLI wrappers) redirect output from
    bootstrap subprocesses to `/dev/null` or parse/capture the standard output
    instead of letting it pass through to the user's TTY.

**Exceptions:** Commands explicitly run with verbose logging flags (`-v` or
`--verbose`).

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | SCM Wrapper & Git Configuration Management - *Provides
    the core git configurations, submodule abstractions, and local repository
    metadata required to execute remote synchronization.*
*   **Downstream:** T6 | Resource Concurrency & Cache Optimization - *Relies on
    precise cache invalidation models and isolated dependency resolution paths
    to prevent multithreaded fetching bottlenecks.*

## Chapter: Hermetic Python Environments (vpython)

**Context:** This chapter governs the configuration and execution of hermetic
Python environments across Depot Tools. It strictly defines `.vpython3`
dependency management, namespace isolation, and legacy Python version
compatibility requirements to ensure consistent, cross-platform toolchain
execution.

### Summary

| Rule ID   | Principle / Constraint          | Priority | Primary Symptom |
:           :                                 :          : / Trap          :
| :-------- | :------------------------------ | :------- | :-------------- |
| **T3-01** | Hermetic Namespacing for        | Critical | Relying on      |
:           : Bundled Python Dependencies     :          : sys.path        :
:           :                                 :          : modification    :
:           :                                 :          : and top-level   :
:           :                                 :          : directory names :
:           :                                 :          : that overlap    :
:           :                                 :          : with common     :
:           :                                 :          : project         :
:           :                                 :          : structures.     :
| **T3-02** | Custom Registry Propagation for | Critical | Assuming public |
:           : Hermetic Python Pipelines       :          : registries      :
:           :                                 :          : (PyPI) can act  :
:           :                                 :          : as an           :
:           :                                 :          : equivalent      :
:           :                                 :          : fallback for    :
:           :                                 :          : internal        :
:           :                                 :          : artifact        :
:           :                                 :          : registries in   :
:           :                                 :          : Chromium        :
:           :                                 :          : builds.         :
| **T3-03** | Formatter Dependency Isolation  | Medium   | Importing a     |
:           : from Global CLI Execution       :          : specialized     :
:           :                                 :          : formatter       :
:           :                                 :          : module at the   :
:           :                                 :          : top of a        :
:           :                                 :          : general-purpose :
:           :                                 :          : CLI tool, tying :
:           :                                 :          : the tool to the :
:           :                                 :          : formatter's     :
:           :                                 :          : dependency      :
:           :                                 :          : tree.           :
| **T3-04** | Removal of Redundant            | Medium   | Importing basic |
:           : concurrent.futures.TimeoutError :          : built-in        :
:           : Import                          :          : exceptions from :
:           :                                 :          : specific        :
:           :                                 :          : modules like    :
:           :                                 :          : they are custom :
:           :                                 :          : objects.        :
| **T3-05** | Legacy Compatibility for Python | Medium   | Using the       |
:           : Type Hints                      :          : Python 3.10+    :
:           :                                 :          : pipe operator   :
:           :                                 :          : for type        :
:           :                                 :          : hinting         :
:           :                                 :          : Optional or     :
:           :                                 :          : Union values.   :
| **T3-06** | Global vpython3 Dependency      | High     | Adding a        |
:           : Resolution for Presubmit        :          : dependency      :
:           : Scripts                         :          : needed by a     :
:           :                                 :          : presubmit       :
:           :                                 :          : script to a     :
:           :                                 :          : project-level   :
:           :                                 :          : `.vpython3`     :
:           :                                 :          : file, expecting :
:           :                                 :          : depot_tools to  :
:           :                                 :          : pick it up      :
:           :                                 :          : during          :
:           :                                 :          : presubmit.      :
| **T3-07** | Platform-Specific Python Wheel  | Medium   | Demanding all   |
:           : Exclusions                      :          : dependencies be :
:           :                                 :          : available on    :
:           :                                 :          : all             :
:           :                                 :          : architectures,  :
:           :                                 :          : blocking entire :
:           :                                 :          : toolchains due  :
:           :                                 :          : to a single     :
:           :                                 :          : missing binary  :
:           :                                 :          : wheel.          :
| **T3-08** | Legacy-Compatible Python 3 Type | Medium   | Importing       |
:           : Hinting Modernization           :          : capitalized     :
:           :                                 :          : aliases from    :
:           :                                 :          : the `typing`    :
:           :                                 :          : module, rather  :
:           :                                 :          : than deferring  :
:           :                                 :          : the evaluation  :
:           :                                 :          : of modern       :
:           :                                 :          : built-in        :
:           :                                 :          : generics.       :

--------------------------------------------------------------------------------

### Rules

#### T3-01: Hermetic Namespacing for Bundled Python Dependencies

> **Rule:** Always isolate bundled internal dependencies using a custom module
> loader to prevent `sys.path` namespace collisions.
>
> **What:** Bundled internal dependencies (e.g., `third_party` modules) must be
> loaded using a custom module loader that isolates them in a unique namespace,
> avoiding standard `sys.path` top-level imports.
>
> **Applies To:** Python environment management (vpython), PRESUBMIT scripts,
> and depot_tools package integration.
>
> **Why:** Using standard imports for `third_party` modules caused unresolvable
> `sys.path` collisions when the executing environment (like Chromium's
> PRESUBMIT.py) also contained a `third_party` directory, leading to version
> mismatches and ImportError exceptions. Failing to adhere to this typically
> results in **ImportError / sys.path Collision**.

**Trap 1: Relying on sys.path modification and top-level directory names that
overlap with common project structures.**

**Don't:**

```python
import sys
sys.path.insert(0, os.path.join(DIR, 'third_party'))
import colorama  # Prone to collision if another third_party exists
```

**Do:**

```python
# Use a custom loader to prefix and isolate the import namespace
from from_third_party import import_module
colorama = import_module('colorama')
# Internally registers as '_depot_tools_third_party_colorama'
```

--------------------------------------------------------------------------------

#### T3-02: Custom Registry Propagation for Hermetic Python Pipelines

> **Rule:** Must inject explicit proxy bypasses and environment variables to
> authenticate with internal Artifact Registries instead of attempting to fall
> back to PyPI.
>
> **What:** When shifting Python dependencies to an internal Artifact Registry
> (AR), the environment variables required for proxy traversal and the custom
> registry URL must be injected into all bootstrapping and vpython stages, and
> users cannot simply fall back to PyPI.
>
> **Applies To:** Vpython root generation, CIPD manifests, and Python module
> resolution.
>
> **Why:** Changing the vpython repository from PyPI to a Google Artifact
> Registry caused 404s and connection timeouts for international users behind
> proxies. Furthermore, attempting to fall back to PyPI failed because
> Chromium-specific patched modules (e.g., `pyyaml==5.4.1+chromium.1`) did not
> exist publicly. Failing to adhere to this typically results in **Package
> Resolution Failure / Connection Timeout**.

**Trap 1: Assuming public registries (PyPI) can act as an equivalent fallback
for internal artifact registries in Chromium builds.**

**Don't:**

*   Setting `VPYTHON_AR_URL=https://pypi.org/simple/` to bypass internal
    registry proxy blocks.

**Do:**

*   Configuring explicit proxy bypasses (`http_proxy`, `https_proxy`) to
    authenticate with the internal Artifact Registry, ensuring custom-suffixed
    packages (`+chromium.1`) resolve correctly.

--------------------------------------------------------------------------------

#### T3-03: Formatter Dependency Isolation from Global CLI Execution

> **Rule:** Never globally import heavy formatter dependencies in the main CLI
> entry point; always invoke formatting tools via isolated subprocesses.
>
> **What:** Heavy formatter dependencies must not be globally imported in the
> main CLI entry point. Instead, formatting tools should run via isolated
> subprocesses with their own `vpython3` specifications, while lightweight
> configuration discovery remains in a core utility module.
>
> **Applies To:** Formatter Orchestration (`git_cl.py`); Vpython environments
> and CLI tool architectures.
>
> **Why:** Adding a global import for a markdown formatter broke the `git cl`
> tool because the formatter's wheels were only defined in the local script's
> vpython block. Forcing these heavy dependencies into the global environment
> would have slowed down every invocation of `git cl`. Failing to adhere to this
> typically results in **ModuleNotFoundError / Slow Startup**.

**Trap 1: Importing a specialized formatter module at the top of a
general-purpose CLI tool, tying the tool to the formatter's dependency tree.**

**Don't:**

```python
# Inside git_cl.py
import mdformat

def _RunMarkdownFormat():
    return mdformat.format(...)
```

**Do:**

```python
# Inside utils.py (lightweight config finder)
def find_config_file(path):
    pass

# Inside git_cl.py (subprocess invocation)
import utils
subprocess.call(['vpython3', 'markdown_format.py', ...])
```

--------------------------------------------------------------------------------

#### T3-04: Removal of Redundant concurrent.futures.TimeoutError Import

> **Rule:** Avoid explicit imports of `TimeoutError` from the
> `concurrent.futures` module and rely solely on the Python 3 standard built-in
> exception.
>
> **What:** Do not explicitly import `TimeoutError` from the
> `concurrent.futures` module. Standardize on the built-in `TimeoutError`
> natively available in Python 3.
>
> **Applies To:** Python scripts and test files (`siso_test.py`) running in
> modern hermetic python environments.
>
> **Why:** Explicitly importing `TimeoutError` from `concurrent.futures` caused
> a presubmit failure (likely a linting collision/redefined-builtin) because
> modern Python environments already include `TimeoutError` as a standard
> language built-in. Failing to adhere to this typically results in **Linting
> Violation / CI Failure**.

**Trap 1: Importing basic built-in exceptions from specific modules like they
are custom objects.**

**Don't:**

```python
# BAD: Redundant import in modern Python
from concurrent.futures import TimeoutError
```

**Do:**

```python
# GOOD: Rely on the built-in exception class
# (No import required)
try:
    # ...
except TimeoutError:
    pass
```

**Exceptions:** Legacy Python 2 execution environments where `TimeoutError` was
not a built-in.

--------------------------------------------------------------------------------

#### T3-05: Legacy Compatibility for Python Type Hints

> **Rule:** Never use Python 3.10+ syntax features like the `|` union operator
> for type hints when targeting backwards-compatible environments.
>
> **What:** Avoid Python 3.10+ syntax features (such as the `|` union operator)
> in module type hints to maintain strict backward compatibility with older
> presubmit linters and runtime environments.
>
> **Applies To:** Python scripts across depot_tools (e.g., autoninja.py,
> siso.py) subject to pylint-2.7 validation.
>
> **Why:** Depot tools scripts are evaluated by legacy presubmit systems (like
> pylint-2.7) which fail to parse the `|` operator for Union types, throwing an
> 'unsupported operand type' error. Failing to adhere to this typically results
> in **Linter Syntax Error**.

**Trap 1: Using the Python 3.10+ pipe operator for type hinting Optional or
Union values.**

**Don't:**

```python
# BAD: Python 3.10+ specific syntax
def _main_inner(input_args, build_id, telemetry_cfg: build_telemetry.Config | None = None):
```

**Do:**

```python
# GOOD: Legacy-compatible type hinting
from typing import Optional

def _main_inner(input_args, build_id, telemetry_cfg: Optional[build_telemetry.Config] = None):
```

**Exceptions:** Scripts explicitly guaranteed to execute exclusively inside a
hermetic Python 3.11+ vpython environment, completely isolated from legacy
linters.

--------------------------------------------------------------------------------

#### T3-06: Global vpython3 Dependency Resolution for Presubmit Scripts

> **Rule:** Always define Python dependencies required by depot_tools presubmit
> checks within the global depot_tools `.vpython3` specification.
>
> **What:** Presubmit checks executed via depot_tools evaluate their Python
> dependencies against the global depot_tools `.vpython3` specification rather
> than the local project's `.vpython3` file.
>
> **Applies To:** Depot Tools vpython environments; Presubmit script execution
> contexts.
>
> **Why:** Historically, developers attempting to introduce new Python
> dependencies (like `lxml` or `hjson`) for local presubmit validation placed
> the dependency in their local project's `.vpython3`, causing the presubmit
> script to fail locally with missing module errors. Failing to adhere to this
> typically results in **ModuleNotFoundError / Dependency Resolution Failure**.

**Trap 1: Adding a dependency needed by a presubmit script to a project-level
`.vpython3` file, expecting depot_tools to pick it up during presubmit.**

**Don't:**

```python
# BAD: Adding dependency to //src/.vpython3 for a presubmit check
wheel: <
  name: "infra/python/wheels/lxml/${vpython_platform}"
  version: "version:4.9.3"
>
```

**Do:**

```python
# GOOD: Adding the dependency to the depot_tools root .vpython3 specification
# (or explicitly updating the script's execution path to utilize a different context)
wheel: <
  name: "infra/python/wheels/lxml/${vpython_platform}"
  version: "version:4.9.3"
>
```

--------------------------------------------------------------------------------

#### T3-07: Platform-Specific Python Wheel Exclusions

> **Rule:** Must apply the `not_match_tag` attribute to gracefully bypass
> missing secondary dependency wheels on newly supported architectures.
>
> **What:** Hermetic python environments (`.vpython3`) must use `not_match_tag`
> to explicitly exclude platforms for dependencies lacking pre-compiled wheels
> on new architectures, allowing core tools to initialize while bypassing
> peripheral missing libraries.
>
> **Applies To:** vpython configuration files (`.vpython3`) defining
> dependencies for multi-architecture deployments (e.g., linux_riscv64).
>
> **Why:** Developers adopting RISC-V devices were completely blocked from using
> core repository tools because the environment bootstrapper rigidly demanded a
> `brotli` wheel, which was not compiled for the `linux_riscv64` architecture.
> Failing to adhere to this typically results in **Environment Bootstrap
> Failure**.

**Trap 1: Demanding all dependencies be available on all architectures, blocking
entire toolchains due to a single missing binary wheel.**

**Don't:**

```protobuf
wheel: <
  name: "infra/python/wheels/brotli/${vpython_platform}"
  version: "version:1.0.9"
>
```

**Do:**

```protobuf
wheel: <
  name: "infra/python/wheels/brotli/${vpython_platform}"
  version: "version:1.0.9"
  not_match_tag: "linux_riscv64"
>
```

**Exceptions:** If the missing dependency is strictly required for the core
execution of the tool, a wheel must be built. Exclusion is only viable if the
dependency is secondary (e.g., telemetry/requests).

--------------------------------------------------------------------------------

#### T3-08: Legacy-Compatible Python 3 Type Hinting Modernization

> **Rule:** Always use `from __future__ import annotations` and explicit `assert
> isinstance()` narrowing when employing modern PEP 585 generics in mixed
> platform execution environments.
>
> **What:** When updating a codebase to use PEP 585 built-in generics (like
> `list` and `tuple` instead of `typing.List`) and typing untyped subprocess
> output, scripts must utilize `from __future__ import annotations` and explicit
> `assert isinstance()` type narrowing to remain compatible with legacy
> execution environments.
>
> **Applies To:** Python scripts operating in mixed environments, particularly
> those mapped to `.vpython3` specifications but executing natively on older
> platform OS versions (e.g., ChromeOS using Python 3.8).
>
> **Why:** Although toolchain manifests declared Python 3.11 support, native
> platforms (like ChromeOS test bots) still defaulted to invoking the scripts
> with Python 3.8. Introducing modern lowercase typing paradigms without future
> imports caused runtime syntax errors, while implicit string-type assumptions
> on subprocess captures led to strict static analysis failures. Failing to
> adhere to this typically results in **SyntaxError / Type Ambiguity**.

**Trap 1: Importing capitalized aliases from the `typing` module, rather than
deferring the evaluation of modern built-in generics.**

**Don't:**

```python
# BAD: Relying on legacy typing module imports for collections
from typing import List, Tuple

def get_config_list(key: str) -> List[str]:
    pass
```

**Do:**

```python
# GOOD: Deferring annotation evaluation for Python 3.8 compatibility
from __future__ import annotations

def get_config_list(key: str) -> list[str]:
    pass
```

**Trap 2: Assuming subprocess wrappers natively return strings instead of
narrowing the ambiguous `str | bytes` returns for type checkers.**

**Don't:**

```python
# BAD: Using raw capture results directly
status = GIT.Capture(command, cwd)
for statusline in status.splitlines():
    ...
```

**Do:**

```python
# GOOD: Explicit runtime type narrowing
status = GIT.Capture(command, cwd)
assert isinstance(status, str)
for statusline in status.splitlines():
    ...
```

**Exceptions:** Standalone scripts strictly executed inside isolated hermetic
environments (like vpython containers) that mathematically guarantee Python 3.9+
execution.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T4 | Presubmit Infrastructure & Telemetry - *Automated
    presubmit scripts rely on T3's globally resolved `.vpython3` dependency
    environments to execute correctly.*
*   **Downstream:** T5 | Formatter & Linter Orchestration - *Formatter tool
    architectures must utilize T3's isolated `vpython3` subprocesses rather than
    polluting global dependencies.*

## Chapter: Presubmit Infrastructure & Telemetry

**Context:** This subsystem governs the strict constraints for automated
repository validation and CI telemetry reporting. It mandates standardized
metadata propagation, precise environment isolation, and accurate git-state
parsing to ensure presubmit checks are reliable, fast, and Gerrit-compatible.

### Summary

| Rule ID   | Principle /          | Priority | Primary Symptom / Trap         |
:           : Constraint           :          :                                :
| :-------- | :------------------- | :------- | :----------------------------- |
| **T4-01** | Mode-Aware Submodule | High     | Using `--name-only` and        |
:           : Diffing via Git Raw  :          : attempting to infer submodule  :
:           : Trees                :          : boundaries from path names.    :
| **T4-02** | Presubmit Recipe     | Critical | Landing infrastructure updates |
:           : Bootstrap Circular   :          : and their corresponding        :
:           : Dependencies         :          : consumption in the exact same  :
:           :                      :          : Change List.                   :
| **T4-03** | Temporal Grace       | Medium   | Strictly enforcing the         |
:           : Periods for License  :          : system's current datetime year :
:           : Year Presubmit       :          : on all touched files without   :
:           : Checks               :          : considering when the work was  :
:           :                      :          : originally authored.           :
| **T4-04** | Gerrit API Timestamp | High     | Assuming API response          |
:           : Parsing to Datetime  :          : properties are automatically   :
:           :                      :          : hydrated into native Python    :
:           :                      :          : types and calling object       :
:           :                      :          : methods on them.               :
| **T4-05** | Relative Path        | High     | Passing absolute local paths   |
:           : Resolution for Git   :          : directly to git commands.      :
:           : Submodule Scans      :          :                                :
| **T4-06** | Sanitization and     | Medium   | Dumping unparsed, un-sanitized |
:           : Granularity of       :          : stdout bytes directly into a   :
:           : Subprocess Linter    :          : single aggregated presubmit    :
:           : Outputs              :          : error message.                 :
| **T4-07** | Preserving Full Git  | High     | Truncating the target branch   |
:           : References for       :          : reference to a short name and  :
:           : TurboCI Gerrit       :          : omitting the fully qualified   :
:           : Changes              :          : git ref.                       :
| **T4-08** | Backward-Compatible  | Medium   | Deleting a canned check        |
:           : Presubmit Check      :          : function entirely because it's :
:           : Deprecation          :          : no longer used in the main     :
:           :                      :          : project's default suite.       :
| **T4-09** | Strict               | High     | Extracting non-standard tags   |
:           : Colon-Separated Git  :          : using generic tag lookups and  :
:           : Footer Validation    :          : equals signs.                  :
| **T4-10** | Execution Context    | Critical | Accessing Gerrit tryserver     |
:           : Guarding for         :          : metadata unconditionally after :
:           : Presubmit Telemetry  :          : a step execution.              :
| **T4-11** | Structured Location  | High     | Returning a list of strings    |
:           : Metadata in          :          : indicating where a presubmit   :
:           : Presubmit Results    :          : error occurred.                :
| **T4-12** | Platform-Independent | High     | Using the OS-native path       |
:           : Path Separators in   :          : joining utilities to construct :
:           : Git Presubmits       :          : paths intended for Git         :
:           :                      :          : comparisons.                   :
| **T4-13** | Type Safety in       | High     | Reassigning the iteration      |
:           : Presubmit            :          : variable to a string path      :
:           : AffectedFile         :          : before calling class-specific  :
:           : Variable Shadowing   :          : helper methods on it.          :
| **T4-14** | Delimiting           | Medium   | Writing JSON directly to       |
:           : Structured JSON in   :          : stdout without considering the :
:           : Noisy Output Streams :          : presence of other diagnostic   :
:           :                      :          : print statements.              :
| **T4-15** | Multi-Owner          | High     | Constructing a regex that      |
:           : Declaration Support  :          : aggressively anchors a single  :
:           : in OWNERS Parsing    :          : email format to the end of the :
:           :                      :          : line.                          :
| **T4-16** | Magic String Literal | Medium   | Defining a static analysis     |
:           : Obfuscation in       :          : target string as a single,     :
:           : Linter               :          : contiguous string literal in   :
:           : Configurations       :          : the scanner's source code.     :
| **T4-17** | Dependency Isolation | Medium   | Attempting to import and use   |
:           : in Recipe Resource   :          : recipe-native APIs within a    :
:           : Scripts              :          : standalone resource Python     :
:           :                      :          : script invoked via standard    :
:           :                      :          : execution.                     :
| **T4-18** | Distinguishing Empty | High     | Relying on implicit truthiness |
:           : vs Missing SCM Diffs :          : to check for the presence of a :
:           :                      :          : diff, treating an empty diff   :
:           :                      :          : identically to a missing diff. :
| **T4-19** | Strict               | Medium   | Catching file lookup           |
:           : Short-Circuiting on  :          : exceptions and substituting an :
:           : Missing Repository   :          : empty mock object to force     :
:           : Manifests            :          : execution to proceed.          :

--------------------------------------------------------------------------------

### Rules

#### T4-01: Mode-Aware Submodule Diffing via Git Raw Trees

> **Rule:** Always utilize `git diff --raw` to detect gitlink entries
> (mode 160000) when identifying and expanding modified files inside git
> submodules.
>
> **What:** To correctly identify and expand modified files inside git
> submodules for telemetry or test optimization, systems must utilize `git diff
> --raw` to detect gitlink entries (mode 160000), rather than relying on
> `--name-only` outputs.
>
> **Applies To:** Tryserver API recipes, Presubmit file analyzers (GN analyze).
>
> **Why:** Build systems attempting to selectively run tests (GN analyze) failed
> to properly detect changes within submodules because `git diff --name-only`
> obscured file modes, preventing the build system from knowing it needed to
> traverse into the submodule pointer. Failing to adhere to this typically
> results in **Build Inefficiency / Broken Telemetry**.

**Trap 1: Using `--name-only` and attempting to infer submodule boundaries from
path names.**

**Don't:**

```python
# Fails to distinguish standard directories from gitlinks
subprocess.check_output(['git', 'diff', '--cached', '--name-only'])
```

**Do:**

```python
# Use --raw and parse the 160000 mode to explicitly branch submodule recursion logic
step_result = subprocess.check_output(['git', 'diff', '--cached', '--raw'])
for mode, old_sha, new_sha, rel_path in parse_raw_diff(step_result):
    if mode == '160000':
        expand_submodule(rel_path, old_sha, new_sha)
```

**Exceptions:** Submodules missing a local `.git` directory (unchecked out by
gclient) or newly deleted submodules (new SHA is entirely zeroes).

--------------------------------------------------------------------------------

#### T4-02: Presubmit Recipe Bootstrap Circular Dependencies

> **Rule:** Never introduce a new presubmit canned check and consume it within
> the local repository's `PRESUBMIT.py` in the exact same Change List.
>
> **What:** New presubmit canned checks cannot be introduced and consumed by a
> repository's internal `PRESUBMIT.py` in the same Change List. The check must
> land first, followed by a dependent CL to consume it.
>
> **Applies To:** Presubmit Infrastructure (`presubmit_canned_checks.py`); CI/CD
> pipelines managed by recipes.
>
> **Why:** A developer added a new `CheckSkillFiles` canned check and called it
> in the local `agents/PRESUBMIT.py` within the same patch. Because the CQ
> presubmit recipe module resolves core presubmit scripts from the installed
> bundle rather than the pending checkout, it triggered an `AttributeError`.
> Failing to adhere to this typically results in **AttributeError / Presubmit
> Crash**.

**Trap 1: Landing infrastructure updates and their corresponding consumption in
the exact same Change List.**

**Don't:**

*   Adding a new function to `presubmit_canned_checks.py` and immediately
    invoking it in `PRESUBMIT.py` in the same CL.

**Do:**

*   Removing the local `PRESUBMIT.py` modification from the CL, landing the
    infrastructure change first, and deploying the usage in a subsequent,
    dependent CL.

--------------------------------------------------------------------------------

#### T4-03: Temporal Grace Periods for License Year Presubmit Checks

> **Rule:** Must incorporate a temporal grace period based on Gerrit CL creation
> dates when enforcing the current year in license header validations.
>
> **What:** Presubmit checks validating the current year in license headers must
> incorporate a temporal grace period (e.g., checking Gerrit CL creation dates)
> to prevent false-positive failures across the New Year boundary.
>
> **Applies To:** Presubmit Infrastructure (`CheckLicense`); Compliance and
> formatting validations.
>
> **Why:** During the January transition, developers modifying or landing CLs
> that were created in the previous year were being blocked by strict
> current-year license checks, causing developer friction. Failing to adhere to
> this typically results in **False-Positive Presubmit Block**.

**Trap 1: Strictly enforcing the system's current datetime year on all touched
files without considering when the work was originally authored.**

**Don't:**

```python
current_year = datetime.datetime.now().year
if license_year != current_year:
    fail("License year must be current")
```

**Do:**

```python
if issue := input_api.change.issue:
    info = input_api.gerrit.GetChangeInfo(issue)
    # Check if created_time is from the preceding year during January
    allow_previous_year(info.created)
```

**Exceptions:** Completely new files created natively in the current calendar
year.

--------------------------------------------------------------------------------

#### T4-04: Gerrit API Timestamp Parsing to Datetime

> **Rule:** Always parse raw string timestamps returned from Gerrit API
> endpoints into native Python `datetime` objects before applying date
> manipulations.
>
> **What:** Data returned from Gerrit API endpoints (e.g., timestamps) must be
> parsed from their raw string format into native Python `datetime` objects
> before applying date manipulation methods.
>
> **Applies To:** Presubmit check scripts (`presubmit_canned_checks.py`)
> interacting with Gerrit API objects.
>
> **Why:** Presubmit scripts attempting to extract the year from a CL creation
> date crashed because the Gerrit API `created` field returned a raw
> ISO-formatted string, not a datetime object, causing `.strftime()` calls to
> fail. Failing to adhere to this typically results in **AttributeError /
> Runtime Crash**.

**Trap 1: Assuming API response properties are automatically hydrated into
native Python types and calling object methods on them.**

**Don't:**

```python
# BAD: Calling strftime directly on the raw API string
created_time = info.created
cl_creation_year = int(created_time.strftime('%Y'))
```

**Do:**

```python
# GOOD: Explicitly parse the ISO string into a datetime object first
import datetime
created_time = datetime.datetime.fromisoformat(info.created)
cl_creation_year = created_time.year
```

--------------------------------------------------------------------------------

#### T4-05: Relative Path Resolution for Git Submodule Scans

> **Rule:** Must normalize file paths relative to the explicit repository root
> when executing `git ls-tree` commands inside presubmit checks.
>
> **What:** When executing `git ls-tree` commands inside presubmit checks, file
> paths must be normalized relative to the repository root to ensure
> compatibility regardless of the user's current working directory.
>
> **Applies To:** Git path handling in presubmit infrastructure
> (`presubmit_canned_checks.py`), especially submodule discovery logic.
>
> **Why:** Running a git command against specific files failed to identify
> submodules correctly when the developer invoked the presubmit from a
> subdirectory, because the generated paths were not properly anchored to the
> root. Failing to adhere to this typically results in **Path Resolution
> Error**.

**Trap 1: Passing absolute local paths directly to git commands.**

**Don't:**

```python
# BAD: Assumes the cwd is the repo root
files_to_check = [f.AbsoluteLocalPath() for f in affected_files]
cmd = ['git', 'ls-tree', '-z', 'HEAD', '--'] + files_to_check
```

**Do:**

```python
# GOOD: Compute relative paths using the explicitly defined repository root
repo_root = input_api.change.RepositoryRoot()
files_to_check = [
    input_api.os_path.relpath(f.AbsoluteLocalPath(), repo_root)
    for f in affected_files
]
cmd = ['git', 'ls-tree', '-z', 'HEAD', '--'] + files_to_check
```

--------------------------------------------------------------------------------

#### T4-06: Sanitization and Granularity of Subprocess Linter Outputs

> **Rule:** Always strip terminal-specific ANSI escape codes and emit individual
> presubmit items for each subprocess linter finding.
>
> **What:** When ingesting output from external diagnostic tools (e.g.,
> `alint`), the presubmit wrapper must strip terminal-specific ANSI escape
> codes, remove redundant severity prefixes (like `ERROR:`), and emit individual
> `PresubmitError`/`PresubmitPromptWarning` objects for each finding.
>
> **Applies To:** Canned checks integrating third-party analyzers (`CheckAyeAye`
> in `presubmit_canned_checks.py`).
>
> **Why:** Raw stdout from the AyeAye linter was dumped entirely into a single
> PresubmitError object. This garbled the Gerrit UI with raw ANSI color codes
> (`\x1b[31m`) and duplicated the word 'ERROR' (since the presubmit framework
> already labels the object type). Failing to adhere to this typically results
> in **Garbled UI / Poor Readability**.

**Trap 1: Dumping unparsed, un-sanitized stdout bytes directly into a single
aggregated presubmit error message.**

**Don't:**

```python
# BAD: Raw output with ANSI codes lumped together
stdout, _ = process.communicate()
if error_found:
    return [output_api.PresubmitError(stdout)]
```

**Do:**

```python
# GOOD: Strip ANSI codes, parse lines, remove prefix, and yield individual objects
def _strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

for line in stdout.splitlines():
    clean_line = _strip_ansi_codes(line).strip()
    if clean_line.startswith("ERROR:"):
        results.append(output_api.PresubmitError(clean_line))
```

--------------------------------------------------------------------------------

#### T4-07: Preserving Full Git References for TurboCI Gerrit Changes

> **Rule:** Must explicitly provide the full git reference alongside the short
> branch name when constructing `GerritChangeInfo` payloads for CI metadata
> reporting.
>
> **What:** When constructing GerritChangeInfo payloads for CI metadata
> reporting, the full git reference must be explicitly provided in addition to
> the short branch name to ensure accurate tracking of non-standard namespaces.
>
> **Applies To:** CI integration modules (e.g., bot_update recipe module)
> interacting with Gerrit API Protos and TurboCI.
>
> **Why:** Previously, the branch field was populated by stripping the
> 'refs/heads/' prefix. This inadvertently corrupted or misidentified changes
> targeting other namespaces (like 'refs/branch-heads/*') because they could no
> longer be represented accurately in the ChangeInfo structure. Failing to
> adhere to this typically results in **Branch Misidentification**.

**Trap 1: Truncating the target branch reference to a short name and omitting
the fully qualified git ref.**

**Don't:**

```python
# BAD: Only populating the truncated branch name
changes.append(gerrit_change_info_pb2.GerritChangeInfo(
    branch=target_ref.removeprefix('refs/heads/'),
    change_number=gerrit_change.change
))
```

**Do:**

```python
# GOOD: Populate both the short branch and the full_branch ref
changes.append(gerrit_change_info_pb2.GerritChangeInfo(
    branch=target_ref.removeprefix('refs/heads/'),
    full_branch=target_ref,
    change_number=gerrit_change.change
))
```

--------------------------------------------------------------------------------

#### T4-08: Backward-Compatible Presubmit Check Deprecation

> **Rule:** Never delete the function definition of a globally enforced
> presubmit check when deprecating it from the central project suite.
>
> **What:** When deprecating a globally enforced presubmit check, the function
> definition must remain intact to preserve backward compatibility for
> downstream repositories that explicitly import and invoke it.
>
> **Applies To:** Centralized presubmit logic (`PanProjectChecks` and
> `presubmit_canned_checks.py`).
>
> **Why:** A strict presubmit check (`CheckChangeWasUploaded`) was removed to
> support modern offline workflows (like Jujutsu). However, deleting the
> function definition entirely broke external third-party repositories whose
> `PRESUBMIT.py` scripts still invoked it. Failing to adhere to this typically
> results in **Downstream CI Breakage**.

**Trap 1: Deleting a canned check function entirely because it's no longer used
in the main project's default suite.**

**Don't:**

*   Removing `def CheckChangeWasUploaded(input_api, output_api):` completely
    from `presubmit_canned_checks.py`.

**Do:**

*   Removing the invocation of `CheckChangeWasUploaded` from the central
    `PanProjectChecks` list, but preserving the `def
    CheckChangeWasUploaded(...)` stub in the library file.

**Exceptions:** Once all dependent projects have been migrated off the
deprecated function.

--------------------------------------------------------------------------------

#### T4-09: Strict Colon-Separated Git Footer Validation

> **Rule:** Always enforce the colon-separated Git footer standard (Key: Value)
> and use native extraction APIs for presubmit bypass flags.
>
> **What:** Presubmit bypass flags must utilize the colon-separated Git footer
> standard (Key: Value) and rely on native footer extraction APIs, eschewing
> non-standard formats.
>
> **Applies To:** Presubmit checks parsing commit message metadata (e.g.,
> `CheckLicense`).
>
> **Why:** A presubmit script suggested bypassing an error using an equals-sign
> syntax (`IGNORE_LICENSE=<reason>`). Gerrit UI and Git trailer tools do not
> natively parse equals-separated strings as valid footers, breaking standard
> metadata flows. Failing to adhere to this typically results in **Unrecognized
> Bypass Metadata**.

**Trap 1: Extracting non-standard tags using generic tag lookups and equals
signs.**

**Don't:**

```python
# BAD: Non-standard footer format and manual tag lookup
reason = input_api.change.tags.get('IGNORE_LICENSE')
error_msg = 'Provide reason in "IGNORE_LICENSE=<reason>"'
```

**Do:**

```python
# GOOD: Gerrit-compliant colon-separated footer
reasons = input_api.change.GitFootersFromDescription().get('Bypass-Check-License', [])
error_msg = 'Provide reason in "Bypass-Check-License: <reason>"'
```

**Exceptions:** Legacy commit parsing logic strictly maintained for parsing
ancient repository histories.

--------------------------------------------------------------------------------

#### T4-10: Execution Context Guarding for Presubmit Telemetry

> **Rule:** Always verify execution is running in a tryserver environment before
> interacting with or accessing Gerrit change metadata.
>
> **What:** Any logic that interacts with Gerrit change metadata (e.g.,
> uploading presubmit findings) must verify it is running in a tryserver
> environment before accessing Gerrit properties.
>
> **Applies To:** Presubmit recipe modules
> (`recipes/recipe_modules/presubmit/api.py`); CI/CD post-submit builders.
>
> **Why:** A change was introduced to upload presubmit results as findings to
> Gerrit. Because it assumed it was always running on a Gerrit-triggered tryjob,
> it unconditionally accessed `self.m.tryserver.gerrit_change.host`. This caused
> post-submit and non-Gerrit recipe runs to crash. Failing to adhere to this
> typically results in **AttributeError / Recipe Crash**.

**Trap 1: Accessing Gerrit tryserver metadata unconditionally after a step
execution.**

**Don't:**

```python
# BAD: Unconditionally accessing gerrit_change properties
if step_json := presubmit_step.json.output:
  raw_result.summary_markdown = _createSummaryMarkdown(step_json)
  self._upload_findings_from_result(step_json)
```

**Do:**

```python
# GOOD: Guarding metadata access with is_tryserver
if step_json := presubmit_step.json.output:
  raw_result.summary_markdown = _createSummaryMarkdown(step_json)
  if self.m.tryserver.is_tryserver:
    self._upload_findings_from_result(step_json)
```

--------------------------------------------------------------------------------

#### T4-11: Structured Location Metadata in Presubmit Results

> **Rule:** Must utilize the `_PresubmitResultLocation` dataclass to report
> highly granular, line-specific findings rather than unstructured generic
> strings.
>
> **What:** Presubmit checks must utilize the `_PresubmitResultLocation`
> dataclass to report specific line and column ranges, rather than unstructured
> strings in the `items` array. Paths must be relative to the repository root or
> use the `/COMMIT_MSG` constant.
>
> **Applies To:** Presubmit API (`presubmit_support.py`), specifically the
> `_PresubmitResult` class.
>
> **Why:** Presubmit results were outputting raw string items which downstream
> tools (like Gerrit) could not automatically parse to drop inline code
> comments. Transitioning to a structured data format allowed for automated,
> line-specific findings. Failing to adhere to this typically results in
> **Unparsable Telemetry / Poor DX**.

**Trap 1: Returning a list of strings indicating where a presubmit error
occurred.**

**Don't:**

```python
# BAD: Unstructured string output
return [OutputApi.PresubmitError(
    "Missing copyright header",
    items=["path/to/file.py:10"]
)]
```

**Do:**

```python
# GOOD: Structured location metadata
return [OutputApi.PresubmitError(
    "Missing copyright header",
    locations=[
        OutputApi.PresubmitResultLocation(file_path="path/to/file.py", start_line=10)
    ]
)]
```

**Trap 2: Using raw internal file paths or magic strings to refer to the commit
message.**

**Don't:**

```python
# BAD: Using hardcoded magic paths
OutputApi.PresubmitResultLocation(file_path="/COMMIT_MSG", start_line=1)
```

**Do:**

```python
# GOOD: Using framework constants
OutputApi.PresubmitResultLocation(file_path=OutputApi.COMMIT_MSG_PATH, start_line=1)
```

--------------------------------------------------------------------------------

#### T4-12: Platform-Independent Path Separators in Git Presubmits

> **Rule:** Must normalize OS-queried submodule paths to use forward slashes (/)
> before evaluating them against Git-flavored config formats.
>
> **What:** Submodule paths queried via local OS APIs must be normalized to use
> forward slashes (/) before being compared against Git-flavored dependency
> configuration files (e.g., DEPS, recursedeps).
>
> **Applies To:** Presubmit infrastructure, specifically dependency validation
> checks evaluating local submodules against DEPS specifications.
>
> **Why:** On Windows, local filesystem queries returned paths separated by
> backslashes, which failed string comparisons against the forward-slash
> formatted paths found in DEPS files, causing global presubmit blocks. Failing
> to adhere to this typically results in **False Positive Presubmit Error**.

**Trap 1: Using the OS-native path joining utilities to construct paths intended
for Git comparisons.**

**Don't:**

```python
# BAD: Generates backslashes on Windows
existing_deps = set(
    input_api.os_path.join(relpath, p)
    for p in existing_deps
)
```

**Do:**

```python
# GOOD: Forces forward slashes for Git configuration compatibility
existing_deps = set(
    '/'.join(gclient_relpath_toks + (p.replace(input_api.os_path.sep, '/'), ))
    for p in existing_deps
)
```

--------------------------------------------------------------------------------

#### T4-13: Type Safety in Presubmit AffectedFile Variable Shadowing

> **Rule:** Never shadow `AffectedFile` object references with string variables,
> as it destroys access to essential path utility methods provided by the
> framework.
>
> **What:** Presubmit scripts must not shadow `AffectedFile` object references
> with string representations of their paths, as this destroys access to
> essential path utility methods provided by the framework.
>
> **Applies To:** Custom presubmit checks iterating over `AffectedFiles()`
> inside `PRESUBMIT.py`.
>
> **Why:** A variable representing the `AffectedFile` object was reassigned to
> the string output of its `.AbsoluteLocalPath()` method. Subsequent attempts to
> call `.Extension()` on that variable triggered a fatal `AttributeError`.
> Failing to adhere to this typically results in **AttributeError Crash**.

**Trap 1: Reassigning the iteration variable to a string path before calling
class-specific helper methods on it.**

**Don't:**

```python
for path in affected_manifests:
    path = path.AbsoluteLocalPath()
    # Crashes because 'path' is now a string
    if path.Extension() == '.txt':
        tests.append(...)
```

**Do:**

```python
for file_obj in affected_manifests:
    if file_obj.Extension() == '.txt':
        absolute_path = file_obj.AbsoluteLocalPath()
        tests.append(...)
```

--------------------------------------------------------------------------------

#### T4-14: Delimiting Structured JSON in Noisy Output Streams

> **Rule:** Must enclose structured JSON datasets within explicit, verifiable
> boundary markers when emitting to a stdout stream containing arbitrary
> application logs.
>
> **What:** Structured data (e.g., JSON) written directly to standard output
> must be enclosed within explicit, reliable textual delimiters if the executing
> tool also emits unstructured logs to the same stream.
>
> **Applies To:** Command-line wrappers and presubmit engines generating JSON
> output for automated clients while sharing stdout with loggers.
>
> **Why:** Presubmit execution logs mixed arbitrarily with the final JSON result
> output on stdout, breaking automated JSON parsers that expected a pristine
> data stream. Failing to adhere to this typically results in **JSON Parsing
> Failure**.

**Trap 1: Writing JSON directly to stdout without considering the presence of
other diagnostic print statements.**

**Don't:**

```python
# BAD: JSON mixed with unstructured print statements
if json_output == '-':
    sys.stdout.write(json.dumps(results))
```

**Do:**

```python
# GOOD: Wrapping JSON payload in verifiable boundary markers
if json_output == '-':
    sys.stdout.write('**** Presubmit Results ****\n')
    sys.stdout.write(json.dumps(results))
    sys.stdout.write('\n**** End of Presubmit Results ****\n')
```

**Exceptions:** Tools where logging is strictly isolated to stderr and stdout is
exclusively reserved for structural payloads.

--------------------------------------------------------------------------------

#### T4-15: Multi-Owner Declaration Support in OWNERS Parsing

> **Rule:** Must account for multiple, comma-separated email addresses on a
> single `per-file` declaration line when parsing OWNERS configs.
>
> **What:** Regular expressions and parsers built to extract reviewers from
> Gerrit `OWNERS` files must account for multiple, comma-separated email
> addresses on a single `per-file` declaration line.
>
> **Applies To:** Presubmit canned checks evaluating repository ownership and
> required reviewer enforcement.
>
> **Why:** Previous parsers assumed a single email address per line, which
> caused false negative reviews when projects grouped multiple required
> reviewers on one line according to valid OWNERS syntax. Failing to adhere to
> this typically results in **Bypassed Required Reviews**.

**Trap 1: Constructing a regex that aggressively anchors a single email format
to the end of the line.**

**Don't:**

```python
# BAD: Only matches one email address
required_reviewer_re = re.compile(r"^per-file DEPS=([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]+)\s*$")
```

**Do:**

```python
# GOOD: Match any content on the line, then split by commas during evaluation
# (or explicitly testing parsing against: 'per-file DEPS=baz@chromium.org, quc@chromium.org')
```

--------------------------------------------------------------------------------

#### T4-16: Magic String Literal Obfuscation in Linter Configurations

> **Rule:** Must obfuscate static analysis target strings (e.g., magic
> identifiers) within a linter's own source file to prevent self-triggering
> scans.
>
> **What:** When configuring presubmit checks or linters that scan source code
> for specific "magic strings" (e.g., LINT.ThenChange), the string literal must
> be obfuscated within the linter's own source file to prevent self-triggering.
>
> **Applies To:** Static analysis tools, presubmit scripts, and linter
> definitions (`presubmit_canned_checks.py`).
>
> **Why:** The string 'LINT.ThenChange' followed immediately by an open
> parentheses was present in the list of
> parsing exceptions in the presubmit configuration script. This caused the CI
> pipeline to incorrectly flag the presubmit script itself for violating the
> linting rule whenever the file was modified. Failing to adhere to this
> typically results in **False Positive Presubmit Failure**.

**Trap 1: Defining a static analysis target string as a single, contiguous
string literal in the scanner's source code.**

**Don't:**

```python
# BAD: in real code this is ONE contiguous literal, which makes the linter
# flag its own source. (Split here so this guide does not self-trigger the
# very linter it describes.)
CPP_EXCEPTIONS = ('#define', '#endif', '// LI' 'NT.ThenChan' 'ge(')
```

**Do:**

```python
# GOOD: Obfuscate the target string
LINT_THEN_CHANGE_EXCEPTION = ('LI' + 'NT.ThenChange(')
CPP_EXCEPTIONS = ('#define', '#endif', '// ' + LINT_THEN_CHANGE_EXCEPTION)
```

--------------------------------------------------------------------------------

#### T4-17: Dependency Isolation in Recipe Resource Scripts

> **Rule:** Must utilize standard library modules and stdout text manipulation
> instead of internal Recipe framework APIs when writing standalone resource
> scripts.
>
> **What:** Scripts executed as isolated resource subprocesses within the Recipe
> Engine cannot import or invoke internal Recipe APIs (like
> `recipe_engine.file`) to emit structured build steps. They must utilize
> standard library modules and stdout text manipulation.
>
> **Applies To:** CI/CD Bots, `bot_update.py` resource scripts, and external
> Python files executed by the Recipe framework.
>
> **Why:** A reviewer requested modifying a cleanup script to use the Recipe
> `file` API so the cleanup would appear natively as a distinct build step in
> the CI UI. The author had to decline because the script runs as an isolated
> resource payload, meaning the `recipe_engine` module is not in its `sys.path`.
> Failing to adhere to this typically results in **Import Error / Execution
> Crash**.

**Trap 1: Attempting to import and use recipe-native APIs within a standalone
resource Python script invoked via standard execution.**

**Don't:**

```python
# BAD: Will raise ImportError in resource execution context
from recipe_engine import file
file.rmtree('cleanup', cleanup_dir)
```

**Do:**

```python
# GOOD: Use standard library and print statements for recipe parsing
import shutil
print('Removing cleanup_dir %s' % cleanup_dir)
shutil.rmtree(cleanup_dir, ignore_errors=True)
```

--------------------------------------------------------------------------------

#### T4-18: Distinguishing Empty vs Missing SCM Diffs

> **Rule:** Must explicitly differentiate between a completely absent diff
> (`None`) and an explicitly provided empty diff (`""`) by executing explicit
> identity checks.
>
> **What:** Presubmit and validation logic must explicitly differentiate between
> a completely absent diff (None) and an explicitly provided empty diff (empty
> string) to prevent bypasses or incorrect validation failures.
>
> **Applies To:** Presubmit support scripts, commit-queue validation, and
> diff-parsing utilities.
>
> **Why:** Presubmit processes were relying on standard Python truthiness checks
> (e.g., `if diff:`) causing changes containing legitimately empty diff
> representations to throw unexpected validation errors or completely bypass
> mandatory change-processing pipelines. Failing to adhere to this typically
> results in **Presubmit Bypass / Failure**.

**Trap 1: Relying on implicit truthiness to check for the presence of a diff,
treating an empty diff identically to a missing diff.**

**Don't:**

```python
# BAD: Evaluates to False if diff is an empty string
if diff:
    return ProvidedDiffChange(*change_args, diff=diff)
```

**Do:**

```python
# GOOD: Explicitly check against None to allow empty string diffs
if diff is not None:
    return ProvidedDiffChange(*change_args, diff=diff)
```

--------------------------------------------------------------------------------

#### T4-19: Strict Short-Circuiting on Missing Repository Manifests

> **Rule:** Must short-circuit and return immediately upon failing to resolve
> project manifest files rather than suppressing the error with an empty mock
> object.
>
> **What:** Presubmit scripts reliant on project manifest files must
> short-circuit and return immediately upon failure to resolve the manifest,
> rather than continuing execution with a default/empty mock object.
>
> **Applies To:** Presubmit checks parsing configuration files like `DEPS`
> (e.g., `presubmit_canned_checks.py`).
>
> **Why:** A script attempted to proceed with an empty dictionary when `git show
> HEAD:DEPS` failed. This caused subsequent DEPS-specific checks (like gitlink
> detection) to execute erroneously on repositories that intentionally lacked a
> DEPS file, triggering false-positive failures. Failing to adhere to this
> typically results in **False-Positive Presubmit Failure**.

**Trap 1: Catching file lookup exceptions and substituting an empty mock object
to force execution to proceed.**

**Don't:**

```python
try:
    deps_content = subprocess.check_output(['git', 'show', 'HEAD:DEPS'])
    deps = _ParseDeps(deps_content)
except Exception:
    deps = {} # Execution continues and processes empty mock
```

**Do:**

```python
if not os.path.isfile(deps_file):
    # No DEPS file, carry on!
    return [] # Early exit bypasses check entirely
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | SCM Wrapper & Git Configuration Management - *Presubmit
    git-state parsers, submodules, and footer metadata validation strictly rely
    on Git abstractions and bootstrapping behaviors governed here.*
*   **Upstream:** T2 | Gclient Dependency Resolution & Execution - *Presubmit
    checks comparing local configurations to manifest files (`DEPS`) require
    accurate gclient file resolution paths to execute reliably.*
*   **Downstream:** T5 | Formatter & Linter Orchestration - *Code formatters and
    subprocess linters emit diagnostic outputs which presubmit infrastructure
    wraps into structural metadata elements (`_PresubmitResultLocation`) for
    Gerrit.*

## Chapter: Formatter & Linter Orchestration

**Context:** This domain orchestrates language-agnostic and language-specific
code formatters across multiple platforms. It enforces strict project boundary
traversal, granular syntax exclusion, precise dependency validation, and
diff-based execution logic to prevent configuration leakage and silent tool
failures.

### Summary

| Rule ID   | Principle /          | Priority | Primary Symptom /    |
:           : Constraint           :          : Trap                 :
| :-------- | :------------------- | :------- | :------------------- |
| **T5-01** | Explicit Project     | High     | Stopping the         |
:           : Root Bounding for    :          : configuration search :
:           : Formatter            :          : only when the        :
:           : Configurations       :          : filesystem root is   :
:           :                      :          : reached, causing     :
:           :                      :          : environment-specific :
:           :                      :          : configuration        :
:           :                      :          : leakage.             :
| **T5-02** | Syntax-Aware         | Medium   | Applying a formatter |
:           : Exclusions for       :          : blindly based on     :
:           : Global Formatting    :          : file extension       :
:           : Rollouts             :          : without allowing     :
:           :                      :          : project-level or     :
:           :                      :          : pattern-specific     :
:           :                      :          : opt-outs.            :
| **T5-03** | Wrapper Naming for   | Medium   | Naming the           |
:           : Executable Isolation :          : executable           :
:           :                      :          : identically to the   :
:           :                      :          : upstream binary when :
:           :                      :          : distributing a       :
:           :                      :          : modified or wrapper  :
:           :                      :          : version in the       :
:           :                      :          : system path.         :
| **T5-04** | Explicit Dependency  | High     | Using a generic      |
:           : Validation for Java  :          : wildcard/glob search :
:           : Formatter            :          : to verify if a       :
:           :                      :          : tool's core          :
:           :                      :          : dependencies are     :
:           :                      :          : present.             :
| **T5-05** | Preventing           | Medium   | Manually appending   |
:           : Positional Argument  :          : directory scopes to  :
:           : Conflicts in git cl  :          : tools that already   :
:           : format               :          : rely on internal     :
:           :                      :          : diff logic, leading  :
:           :                      :          : to CLI conflicts.    :
| **T5-06** | Conditional          | Medium   | Adding               |
:           : Delegation of        :          : language-specific    :
:           : Language-Specific    :          : formatter binaries   :
:           : Formatters           :          : directly into the    :
:           :                      :          : universal            :
:           :                      :          : `depot_tools`        :
:           :                      :          : repository.          :
| **T5-07** | Single-Dash Long     | Medium   | Assuming all         |
:           : Options for          :          : external scripts     :
:           : clang-format-diff.py :          : adhere to            :
:           :                      :          : double-dash          :
:           :                      :          : GNU/POSIX standards  :
:           :                      :          : for multi-character  :
:           :                      :          : argument flags.      :
| **T5-08** | Inclusion of         | High     | Filtering git diffs  |
:           : Renamed/Copied Files :          : strictly to Added    :
:           : in Formatting Diffs  :          : and Modified files,  :
:           :                      :          : missing              :
:           :                      :          : Renamed/Copied       :
:           :                      :          : files.               :

--------------------------------------------------------------------------------

### Rules

#### T5-01: Explicit Project Root Bounding for Formatter Configurations

> **Rule:** Always terminate directory traversal algorithms seeking formatter
> configurations exactly at the project root boundary. Never traverse up to the
> OS filesystem root to prevent environment-specific configuration leakage.
>
> **What:** Directory traversal algorithms seeking formatter configurations
> (like `.ruff.toml` or `.style.yapf`) must strictly terminate at the explicit
> project root boundary rather than continuing up to the filesystem root.
>
> **Applies To:** Code formatting orchestrators (`ruff_chromium`, `git_cl.py`,
> `yapf`).
>
> **Why:** A heuristic traversal mechanism failed to stop at the project root.
> On developer machines, this occasionally pulled in unrelated formatting
> configs from parent directories outside the workspace, causing presubmit to
> pass locally but fail in CI environments (where the parent paths differed).
> Failing to adhere to this typically results in **Presubmit Failure /
> Configuration Drift**.

**Trap 1: Stopping the configuration search only when the filesystem root is
reached, causing environment-specific configuration leakage.**

**Don't:**

```python
parent_dir = os.path.dirname(search_dir)
if parent_dir == search_dir:
    break
search_dir = parent_dir
```

**Do:**

```python
if _is_vcs_root(search_dir) or search_dir == top_dir:
    break
parent_dir = os.path.dirname(search_dir)
if parent_dir == search_dir:
    break
search_dir = parent_dir
```

--------------------------------------------------------------------------------

#### T5-02: Syntax-Aware Exclusions for Global Formatting Rollouts

> **Rule:** Must implement granular exclusion mechanisms when enabling automated
> file formatting globally for a file extension. Protect files containing
> specialized or unsupported syntax from blind formatting passes.
>
> **What:** When enabling automatic file formatting globally for a file
> extension (e.g., JS/TS), specific granular exclusion mechanisms must be
> implemented to protect files containing specialized or unsupported syntax.
>
> **Applies To:** git cl format, clang-format definitions, JS/TS codebases.
>
> **Why:** Enabling clang-format by default for all `.js` and `.ts` files
> mangled WebAssembly FileCheck expectations and V8 "natives syntax" embedded in
> comments, breaking critical unit tests. It also negatively impacted
> multi-language `.html.ts` files. Failing to adhere to this typically results
> in **Syntax Corruption / Test Failures**.

**Trap 1: Applying a formatter blindly based on file extension without allowing
project-level or pattern-specific opt-outs.**

**Don't:**

```python
if opts.js:
    formatters.append((['.js', '.ts'], _RunClangFormatDiff))
```

**Do:**

```python
# Provide granular file-type exclusions (.html.ts) and flags (--no-js) for specialized syntax projects
if opts.js:
    formatters.append((['.js', '.ts'], _RunClangFormatDiff, ['.html.ts']))
```

**Exceptions:** Projects with uniformly enforced, standard syntax where
clang-format handles all edge cases natively.

--------------------------------------------------------------------------------

#### T5-03: Wrapper Naming for Executable Isolation

> **Rule:** Uniquely name wrapper executables distributed through infrastructure
> pipelines. Never use the exact upstream binary name to prevent overriding a
> user's globally installed system tools.
>
> **What:** When distributing generalized tooling (like Ruff) through a specific
> infrastructure pipeline (like depot_tools), the executable must be uniquely
> named to avoid silently overriding a user's globally installed system tools.
>
> **Applies To:** Executable distribution in depot_tools and vpython
> configurations.
>
> **Why:** Creating an executable simply named `ruff` in depot_tools would
> intercept commands intended for the user's personal `ruff` installation.
> Because the depot_tools version strictly enforced local config file presence
> and occasionally fell back to YAPF, it silently broke developers' non-Chromium
> workflows. Failing to adhere to this typically results in **Tooling Conflicts
> / Silent Behavioral Breaks**.

**Trap 1: Naming the executable identically to the upstream binary when
distributing a modified or wrapper version in the system path.**

**Don't:**

*   Depot Tools executable named `ruff`.

**Do:**

*   Depot Tools executable explicitly named `ruff_chromium` to ensure users must
    opt-in via integration scripts (like `git cl format`).

**Exceptions:** Tools where the behavior is exactly identical to the upstream
binary, or tools that are required to be overridden globally (e.g., `gn` or
`ninja` in the Chromium context).

--------------------------------------------------------------------------------

#### T5-04: Explicit Dependency Validation for Java Formatter

> **Rule:** Always verify the precise filename of target dependencies during
> formatter readiness checks. Avoid generic glob patterns that can trigger false
> positives on unrelated files.
>
> **What:** Formatter readiness checks must explicitly verify the existence of
> the exact target dependency file rather than relying on broad glob patterns.
>
> **Applies To:** Formatter orchestration scripts (e.g., git cl format)
> integrating with toolchain binaries on all platforms.
>
> **Why:** A broad glob (`*.jar`) check returned true on platforms like Windows
> and Mac due to the presence of an unrelated file (`chromium-overrides.jar`).
> This caused the formatter to attempt execution even when its core CIPD
> dependency (`google-java-format.jar`) was completely missing, leading to tool
> failures. Failing to adhere to this typically results in **Formatter Execution
> Failure**.

**Trap 1: Using a generic wildcard/glob search to verify if a tool's core
dependencies are present.**

**Don't:**

```python
# BAD: Can false-positive on unrelated jars
if not glob.glob(os.path.join(tool_dir, '*.jar')):
    print('google-java-format not found')
    return 0
```

**Do:**

```python
# GOOD: Explicitly check for the required tool jar
if not os.path.exists(os.path.join(tool_dir, 'cipd', 'google-java-format.jar')):
    print('google-java-format not found')
    return 0
```

**Exceptions:** Environments utilizing dummy placeholder JARs for testing must
rename them to precisely match the target dependency name.

--------------------------------------------------------------------------------

#### T5-05: Preventing Positional Argument Conflicts in git cl format

> **Rule:** Never append local presubmit paths as positional arguments when
> orchestrating formatters that rely on diff-based flags. Delegate target file
> resolution to the formatting tool's internal diff logic to avoid CLI
> conflicts.
>
> **What:** When orchestrating formatting tools programmatically, avoid
> dynamically appending the local presubmit path as a positional argument if
> diff-based flags (`--input_diff`) might also be active, to prevent
> command-line parsing conflicts.
>
> **Applies To:** presubmit_canned_checks.py and any integration code invoking
> `git cl format`.
>
> **Why:** When a presubmit ran inside a sub-repository, it appended
> `input_api.PresubmitLocalPath()` as a positional argument. This conflicted
> with standard `git cl format` inputs (like `--input_diff`), causing the tool
> to fail silently because the return code was swallowed by an aggressive
> warning bypass. Failing to adhere to this typically results in **Silent
> Formatter Failure**.

**Trap 1: Manually appending directory scopes to tools that already rely on
internal diff logic, leading to CLI conflicts.**

**Don't:**

```python
# BAD: Injecting positional path argument
if presubmit_subdir:
    cmd.append(input_api.PresubmitLocalPath())
code, _ = git_cl.RunGitWithCode(cmd, suppress_stderr=bypass_warnings)
```

**Do:**

```python
# GOOD: Let the formatting tool manage target file resolution
code, _ = git_cl.RunGitWithCode(cmd, suppress_stderr=bypass_warnings)
```

--------------------------------------------------------------------------------

#### T5-06: Conditional Delegation of Language-Specific Formatters

> **Rule:** Conditionally resolve platform-specific formatters through host
> project dependency definitions. Never bundle language-specific binaries
> globally within universal tooling repositories.
>
> **What:** Platform-specific code formatters must not be bundled in universal
> tooling repositories; instead, they should be conditionally downloaded in the
> host project tree and dynamically resolved.
>
> **Applies To:** Formatter orchestration (`git cl format`, `swift-format`,
> `rustfmt`).
>
> **Why:** Bundling tools like `swift-format` globally within `depot_tools`
> caused unnecessary download bloat for developers on platforms (like
> Windows/Linux) who didn't work on iOS/macOS. It was mitigated by fetching via
> host-project DEPS. Failing to adhere to this typically results in **Toolchain
> Bloat / Redundant Downloads**.

**Trap 1: Adding language-specific formatter binaries directly into the
universal `depot_tools` repository.**

**Don't:**

*   Checking in `swift-format` binaries to `depot_tools` or adding a global
    download hook that executes on all checkouts regardless of OS.

**Do:**

*   Configuring the binary as a conditional DEPS download (e.g., triggering only
    if iOS variables are set) in the host repository (`chromium/src`) and
    resolving the path dynamically via `gclient_paths`.

**Exceptions:** Formatters for universally adopted languages used strictly by
the tooling itself (e.g., Python formatters like YAPF).

--------------------------------------------------------------------------------

#### T5-07: Single-Dash Long Options for clang-format-diff.py

> **Rule:** Must use a single-dash prefix for long options passed to external
> Clang format scripts. Do not assume these specific scripts adhere to standard
> POSIX double-dash argument conventions.
>
> **What:** When passing long options to the external `clang-format-diff.py`
> script, arguments must use a single-dash prefix rather than the standard POSIX
> double-dash prefix.
>
> **Applies To:** Formatting orchestration scripts (`git_cl.py`) interacting
> with Clang toolchain Python wrappers.
>
> **Why:** Due to the specific command-line parsing implementation inside the
> external Clang format script, passing `--sort-includes` failed to be
> recognized, requiring a hardcoded single dash `-sort-includes`. Failing to
> adhere to this typically results in **Command Arguments Ignored**.

**Trap 1: Assuming all external scripts adhere to double-dash GNU/POSIX
standards for multi-character argument flags.**

**Don't:**

```python
# BAD: Uses standard double dash for long arguments
cmd = ['vpython3', script, '--sort-includes', '-p0']
```

**Do:**

```python
# GOOD: Matches the specific optparse implementation of the tool
cmd = ['vpython3', script, '-sort-includes', '-p0']
```

--------------------------------------------------------------------------------

#### T5-08: Inclusion of Renamed/Copied Files in Formatting Diffs

> **Rule:** Always configure git diff filters to explicitly include moved and
> copied files during automated formatting passes. Avoid strict exclusionary
> filters that cause renamed files to bypass format checks.
>
> **What:** When filtering `git diff` to identify files for automated
> formatting, the filter must include moved (renamed) and copied files, rather
> than relying on strict exclusionary filters.
>
> **Applies To:** git cl format; Formatter & Linter Orchestration.
>
> **Why:** A change optimized formatting tool performance by using
> `--diff-filter=crd`. This inadvertently excluded moved or copied files.
> Consequently, files that were moved and modified bypassed formatting checks
> completely and were merged with poor formatting. Failing to adhere to this
> typically results in **Unformatted Code Merge**.

**Trap 1: Filtering git diffs strictly to Added and Modified files, missing
Renamed/Copied files.**

**Don't:**

```bash
git diff --diff-filter=AM
# or exclusionary filters that drop them
git diff --diff-filter=crd
```

**Do:**

```bash
# Explicitly include Renamed (R) and Copied (C) files
git diff --diff-filter=AMRC
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T3 | Hermetic Python Environments (vpython) - *Python-based
    formatters depend on isolated environments and correct package resolution to
    execute deterministically.*
*   **Upstream:** T2 | Gclient Dependency Resolution & Execution - *External
    platform-specific formatters rely on DEPS resolution and CIPD package
    management for availability.*
*   **Downstream:** T4 | Presubmit Infrastructure & Telemetry - *Formatter
    outputs integrate directly into automated checks, contributing to repository
    gatekeeping and result telemetry.*

## Chapter: Resource Concurrency & Cache Optimization

**Context:** This domain governs the synchronization and optimization of shared
developer resources, defining strict constraints for high-concurrency git cache
access, dynamic thread scaling, and atomic, per-repository file locking.

### Summary

| Rule ID   | Principle / Constraint    | Priority | Primary Symptom / Trap   |
| :-------- | :------------------------ | :------- | :----------------------- |
| **T6-01** | Canonical URL Resolution  | Medium   | Performing conditional   |
:           : for Aliased Git Caches    :          : checks directly on the   :
:           :                           :          : un-normalized repository :
:           :                           :          : URL.                     :
| **T6-02** | Dynamic Concurrency       | Medium   | Using low, hardcoded     |
:           : Scaling for I/O Bound     :          : concurrency limits for   :
:           : Tasks                     :          : high-latency network     :
:           :                           :          : operations.              :
| **T6-03** | Per-Repository Atomic     | High     | Fetching remote metadata |
:           : Caching for Network-Bound :          : on every invocation, or  :
:           : API Checks                :          : using a global,          :
:           :                           :          : non-thread-safe state    :
:           :                           :          : file.                    :
| **T6-04** | Configurable Lock         | High     | Hardcoding low timeouts  |
:           : Timeouts for Git Cache    :          : for shared file locks    :
:           : Operations                :          : instead of allowing      :
:           :                           :          : caller-defined           :
:           :                           :          : scalability.             :

--------------------------------------------------------------------------------

### Rules

#### T6-01: Canonical URL Resolution for Aliased Git Caches

> **Rule:** Always derive canonical repository URLs prior to cache directory
> assignment or bootstrap bucket resolution to enable resource sharing across
> aliases.
>
> **What:** Git cache directory assignment and bootstrap bucket resolution must
> rely on canonical repository URLs rather than raw input URLs to enable
> resource sharing across mirrored aliases.
>
> **Applies To:** Depot Tools git_cache.py and any multi-repository checkout
> systems managing mirror aliases.
>
> **Why:** Historically, checking the raw repository host against a bucket list
> prevented internal mirrors from sharing the upstream repository's git cache
> and Google Storage bootstrap snapshots, leading to duplicate cache creation
> and slower checkout times. Failing to adhere to this typically results in
> **Cache Duplication / Disk Exhaustion**.

**Trap 1: Performing conditional checks directly on the un-normalized repository
URL.**

**Don't:**

```python
u = urllib.parse.urlparse(self.url)
if u.netloc in self.BOOTSTRAP_BUCKET_HOSTS:
    return 'chromium-git-cache'
```

**Do:**

```python
# Derive canonical URL from the cache directory which already handles aliases
cache_dir_url = self.CacheDirToUrl(self.basedir)
u = urllib.parse.urlparse(cache_dir_url)
if u.netloc in self.BOOTSTRAP_BUCKET_HOSTS:
    return 'chromium-git-cache'
```

--------------------------------------------------------------------------------

#### T6-02: Dynamic Concurrency Scaling for I/O Bound Tasks

> **Rule:** Must dynamically scale concurrency limits based on local CPU core
> counts for I/O and network-bound parallel tasks.
>
> **What:** Parallelized tasks subject to network latency or I/O waits must
> scale concurrency limits dynamically based on local CPU core counts rather
> than relying on static, hardcoded semaphores.
>
> **Applies To:** Git cache bootstrapping (`git_cache.py`) and large-scale
> repository syncs.
>
> **Why:** A hardcoded semaphore value of 2 was unnecessarily throttling the
> fetching of hundreds of small repositories during git cache bootstrapping,
> artificially extending sync times to 40-60 minutes on high-bandwidth corporate
> networks. Failing to adhere to this typically results in **Thread Starvation /
> Latency Bottleneck**.

**Trap 1: Using low, hardcoded concurrency limits for high-latency network
operations.**

**Don't:**

```python
# BAD: Hardcoded bottleneck
concurrency_semaphore = Semaphore(2)
```

**Do:**

```python
# GOOD: Dynamic scaling based on hardware resources
concurrency_semaphore = Semaphore(max(8, multiprocessing.cpu_count()))
```

**Exceptions:** Operations against highly fragile third-party endpoints that
strictly enforce low rate limits.

--------------------------------------------------------------------------------

#### T6-03: Per-Repository Atomic Caching for Network-Bound API Checks

> **Rule:** Always cache expensive, network-bound API queries atomically on a
> per-repository basis using file-level locking.
>
> **What:** Expensive, network-bound API queries that rarely change (like Gerrit
> code-owner enablement status) must be cached to disk per-repository using
> atomic writes (temporary file + rename) and file-level locking (`lockfile`) to
> ensure safety in highly concurrent environments.
>
> **Applies To:** Gerrit API interaction layers (`gerrit_cache.py`,
> `gerrit_util.py`), and any presubmit step querying external configuration.
>
> **Why:** Running `git cl presubmit` incurred a consistent 1.5s latency penalty
> entirely due to un-cached Gerrit API authentication handshakes and
> project-config queries. An initial attempt to cache this globally caused
> invalidation conflicts when developers operated on multiple repositories
> simultaneously. Failing to adhere to this typically results in **Excessive
> Presubmit Latency**.

**Trap 1: Fetching remote metadata on every invocation, or using a global,
non-thread-safe state file.**

**Don't:**

```python
# BAD: Incurs network latency on every presubmit run
def check_owners_enabled(repo):
    return ReadHttpJsonResponse(host, path)
```

**Do:**

```python
# GOOD: Use file locking, atomic tempfile renaming, and per-repo cache keys
with lockfile.lock(cache_path, timeout=1):
    data[key] = value
    with _AtomicFileWriter(cache_path, 'w') as f:
        json.dump(data, f)
```

**Exceptions:** Environments where disk access is strictly prohibited or
read-only.

--------------------------------------------------------------------------------

#### T6-04: Configurable Lock Timeouts for Git Cache Operations

> **Rule:** Never hardcode timeout values for shared file locks; always expose a
> configurable timeout parameter to callers.
>
> **What:** All git cache operations (including read-only metadata checks like
> `contains_revision`) must respect user-defined or scalable lock timeout
> configurations to prevent high-concurrency race conditions.
>
> **Applies To:** git_cache.py, lockfile integrations, and gclient
> synchronization processes.
>
> **Why:** A hardcoded 20-second cache lock timeout caused chronic `LockError`
> exceptions on high-CPU build bots (e.g., ChromeOS). With over 30 parallel
> processes polling the same cache lock during `gclient sync`, the arbitrary
> 20-second timeout was insufficient. Failing to adhere to this typically
> results in **LockError (Resource Unavailable)**.

**Trap 1: Hardcoding low timeouts for shared file locks instead of allowing
caller-defined scalability.**

**Don't:**

```python
# BAD: Hardcoded timeout
def contains_revision(self, revision):
    with lockfile.lock(self.mirror_path, timeout=20):
        # ... read operation ...
```

**Do:**

```python
# GOOD: Pass-through configurable timeout with a sensible default
def contains_revision(self, revision, timeout=20):
    with lockfile.lock(self.mirror_path, timeout=timeout):
        # ... read operation ...

# Caller injects config:
mirror.contains_revision(revision, timeout=options.lock_timeout)
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T2 | Gclient Dependency Resolution & Execution -
    *High-concurrency parallel hook execution drives the need for configurable
    lock timeouts in shared caches.*
*   **Downstream:** T4 | Presubmit Infrastructure & Telemetry - *Per-repository
    atomic caching directly prevents severe latency bottlenecks during automated
    presubmit operations.*

## Chapter: Platform-Specific Build Toolchains (Windows)

**Context:** This chapter dictates Windows-specific execution constraints,
governing filesystem limits, PowerShell boundary invocations, path resolution
across multi-drive or Cygwin environments, and the strict handling of NTFS
directory junctions.

### Summary

| Rule ID   | Principle / Constraint       | Priority | Primary Symptom / Trap |
| :-------- | :--------------------------- | :------- | :--------------------- |
| **T7-01** | Visual Studio Toolchain      | High     | Comparing the vswhere  |
:           : Internal Filesystem Version  :          : version marker output  :
:           : Detection                    :          : directly against the   :
:           :                              :          : 4-digit release year.  :
| **T7-02** | PowerShell Subprocess        | Critical | Using the `-File`      |
:           : Invocation via Windows Batch :          : parameter and          :
:           :                              :          : expecting batch        :
:           :                              :          : variables to expand    :
:           :                              :          : cleanly across the     :
:           :                              :          : boundary without       :
:           :                              :          : quoting issues.        :
| **T7-03** | Command-Line Length Bound    | Critical | Appending unbounded    |
:           : Safety on Windows            :          : lists of files to a    :
:           :                              :          : command string without :
:           :                              :          : checking the length or :
:           :                              :          : item count.            :
| **T7-04** | Safe Mutability of Windows   | High     | Unconditionally        |
:           : Toolchain Junctions          :          : deleting the toolchain :
:           :                              :          : directory to ensure a  :
:           :                              :          : clean slate for the    :
:           :                              :          : directory junction.    :
| **T7-05** | Avoid Directory Junctions    | Critical | Standardizing paths by |
:           : for Shared Windows Build     :          : creating directory     :
:           : Toolchains                   :          : junctions to a single  :
:           :                              :          : shared toolchain root. :
| **T7-06** | Safe Multi-Drive Path        | High     | Using                  |
:           : Resolution on Windows        :          : character-by-character :
:           :                              :          : string matching, which :
:           :                              :          : creates false          :
:           :                              :          : positives for          :
:           :                              :          : similarly named        :
:           :                              :          : directories.           :
| **T7-07** | Absolute Path Resolution     | High     | Calling `cygpath`      |
:           : Workarounds for Cygwin Mount :          : directly on the target :
:           : Points                       :          : binary directory.      :

--------------------------------------------------------------------------------

### Rules

#### T7-01: Visual Studio Toolchain Internal Filesystem Version Detection

> **Rule:** Always parse `vswhere.exe` output targeting the internal filesystem
> major version number. Never attempt to detect the toolchain via its commercial
> release year.
>
> **What:** When parsing `vswhere.exe` output for toolchain detection on
> Windows, the script must match against the internal filesystem major version
> number rather than the commercial release year.
>
> **Applies To:** Windows Toolchain Scripts
> (`win_toolchain/package_from_installed.py`); Environment discovery.
>
> **Why:** The output structure of `vswhere.exe` changed, placing the internal
> filesystem version (e.g., '18') in the `catalog_productLineVersion` field
> instead of the expected commercial release year (e.g., '2026'), causing the
> toolchain packaging script to fail. Failing to adhere to this typically
> results in **Toolchain Detection Failure**.

**Trap 1: Comparing the vswhere version marker output directly against the
4-digit release year.**

**Don't:**

```python
_vs_version = '2026'
if line[len(vs_version_marker):] == _vs_version:
    matching_vs_path = vs_path
```

**Do:**

```python
SUPPORTED_VS_FILESYSTEM_NAME = '18'
if line[len(vs_version_marker):] == SUPPORTED_VS_FILESYSTEM_NAME:
    matching_vs_path = vs_path
```

**Exceptions:** Legacy versions of Visual Studio where the tool output structure
natively used the year-based format.

--------------------------------------------------------------------------------

#### T7-02: PowerShell Subprocess Invocation via Windows Batch

> **Rule:** Must pass complex parameters to PowerShell using the `-Command` flag
> with escaped double quotes. Avoid the `-File` parameter entirely when
> boundary-crossing variables are present.
>
> **What:** When invoking PowerShell from a Windows Batch script, complex
> parameters must be passed using the `-Command` flag with escaped double
> quotes, avoiding the `-File` parameter to prevent unintended path parsing and
> dot-sourcing bugs.
>
> **Applies To:** Windows bootstrapping scripts (`cipd.bat`), platform-specific
> setup logic.
>
> **Why:** Using the `-File` flag for PowerShell invocations in Windows Batch
> scripts caused execution failures due to mishandling of spaces, single quotes,
> and unintended dot-sourcing behavior in specific installation paths. Failing
> to adhere to this typically results in **Script Execution Failure**.

**Trap 1: Using the `-File` parameter and expecting batch variables to expand
cleanly across the boundary without quoting issues.**

**Don't:**

```batch
:: BAD: -File triggers dot-sourcing and mishandles spaces in %~dp0
powershell -NoProfile -ExecutionPolicy RemoteSigned ^
    -File "%~dp0.cipd_impl.ps1" ^
    -CipdBinary "%CIPD_BINARY%"
```

**Do:**

```batch
:: GOOD: Build the command string with escaped single quotes inside double quotes, execute with -Command
set "EXECUTE_CIPD_IMPL=& '%CIPD_IMPL%'"
set "EXECUTE_CIPD_IMPL=%EXECUTE_CIPD_IMPL% -CipdBinary '%CIPD_BINARY%'"
powershell -NoProfile -ExecutionPolicy RemoteSigned ^
  -Command "%EXECUTE_CIPD_IMPL%" ^
  <nul
```

--------------------------------------------------------------------------------

#### T7-03: Command-Line Length Bound Safety on Windows

> **Rule:** Always implement explicit count or length thresholds when
> constructing subprocess arguments dynamically. Must enforce a fallback
> execution mode before breaching the Windows kernel limits.
>
> **What:** Scripts dynamically constructing subprocess arguments using file
> lists must detect when the total command string length approaches the Windows
> limit (8,191 characters) and fallback to a full-tree execution mode.
>
> **Applies To:** Cross-platform subprocess invocation, particularly Git
> integrations (`presubmit_canned_checks.py`).
>
> **Why:** The `win-presubmit` autoroller failed completely when a change
> modified a massive number of files, because the array of file names pushed the
> command string length past the Windows kernel limit. Failing to adhere to this
> typically results in **OS Command Line Limit Crash**.

**Trap 1: Appending unbounded lists of files to a command string without
checking the length or item count.**

**Don't:**

```python
# BAD: Will crash on Windows if affected_files is very large
cmd = ['git', 'ls-tree'] + affected_files
subprocess.check_output(cmd)
```

**Do:**

```python
# GOOD: Implement a safety threshold to fallback to full-tree parsing
if len(affected_files) < 1000:
    cmd = ['git', 'ls-tree'] + files_to_check
else:
    # Fallback to scanning everything
    cmd = ['git', 'ls-tree', '-r', '--full-tree']
```

**Exceptions:** Environments strictly isolated to POSIX-compliant systems where
ARG_MAX is significantly higher, though defensive bounds are still recommended.

--------------------------------------------------------------------------------

#### T7-04: Safe Mutability of Windows Toolchain Junctions

> **Rule:** Never destructively execute `RmDir` on a target directory without
> explicitly confirming junction status first.
>
> **What:** When configuring a shared Windows toolchain directory via NTFS
> directory junctions (`mklink /J`), scripts must not destructively call `RmDir`
> on the target directory without confirming it is safe to overwrite, to avoid
> redownloading massive toolchain payloads.
>
> **Applies To:** Windows toolchain bootstrapping
> (`win_toolchain/get_toolchain_if_necessary.py`); NTFS Filesystem management.
>
> **Why:** A change implemented to share a single Visual Studio toolchain across
> multiple checkouts deleted the existing `vs_files` directory unconditionally
> before creating a junction. This resulted in corrupted caches and forced full
> re-downloads of the toolchain in downstream builds (e.g., Dart, BoringSSL)
> that were not expecting the destructive directory swap. Failing to adhere to
> this typically results in **Cache Corruption / Mass Redownload**.

**Trap 1: Unconditionally deleting the toolchain directory to ensure a clean
slate for the directory junction.**

**Don't:**

```python
# BAD: Unconditional deletion
if os.path.exists('vs_files'):
    RmDir('vs_files')
RunCommand(['cmd.exe', '/c', 'mklink', '/J', 'vs_files', toolchain_dir])
```

**Do:**

```python
# GOOD: Validate junction status before destructive actions
if not _IsJunctionTo('vs_files', toolchain_dir):
    RmDir('vs_files')
    RunCommand(['cmd.exe', '/c', 'mklink', '/J', 'vs_files', toolchain_dir])
```

--------------------------------------------------------------------------------

#### T7-05: Avoid Directory Junctions for Shared Windows Build Toolchains

> **Rule:** Avoid mapping toolchain binaries via directory junctions (`mklink
> /J`). Always prefer explicit absolute paths parsed natively by the build
> system.
>
> **What:** Avoid using Windows directory junctions (`mklink /J`) to map
> toolchain binaries into standardized relative paths across multiple build
> environments.
>
> **Applies To:** Windows toolchain bootstrapping scripts, specifically handling
> of `vs_files` mapping within depot_tools.
>
> **Why:** Creating junctions to standardized `vs_files` directories caused
> severe cache corruption on persistent build bots and resulted in
> 'FileNotFoundError' for system DLLs in Dart and BoringSSL CI pipelines.
> Failing to adhere to this typically results in **Cache Corruption /
> FileNotFoundError**.

**Trap 1: Standardizing paths by creating directory junctions to a single shared
toolchain root.**

**Don't:**

*   Automatically using `mklink /J` to map the Visual Studio toolchain to
    `depot_tools\win_toolchain\vs_files` to simplify build configurations.

**Do:**

*   Utilizing explicit absolute paths natively within the build tool, or
    explicitly disabling junction creation (e.g., via a `--no-junction` flag) to
    prevent persistent cache corruption across bots.

--------------------------------------------------------------------------------

#### T7-06: Safe Multi-Drive Path Resolution on Windows

> **Rule:** Always execute explicit component-based path checks and natively
> catch `ValueError` cross-drive exceptions. Never employ string-based prefix
> comparisons.
>
> **What:** When resolving or comparing filesystem paths on Windows, logic must
> safely handle cross-drive comparisons without failing abruptly, while avoiding
> inherently unsafe string-based prefix checks.
>
> **Applies To:** Python scripts operating in Windows environments, specifically
> path-membership checks like `os.path.commonpath`.
>
> **Why:** When scripts attempted to verify if a given execution path was within
> the repository suite on Windows, developers whose `PATH` environment variable
> contained directories across multiple drives experienced fatal crashes.
> Failing to adhere to this typically results in **Unhandled Exception /
> ValueError**.

**Trap 1: Using character-by-character string matching, which creates false
positives for similarly named directories.**

**Don't:**

```python
# BAD: Fails safely but matches incorrect paths like 'C:\depot_tools_old'
return os.path.commonprefix([os.path.abspath(path), ROOT_DIR]) == ROOT_DIR
```

**Do:**

```python
# GOOD: Explicitly catch the multi-drive ValueError while maintaining accurate component-based path matching
try:
    return os.path.commonpath([os.path.abspath(path), ROOT_DIR]) == ROOT_DIR
except ValueError:
    # Paths are on different drives
    return False
```

--------------------------------------------------------------------------------

#### T7-07: Absolute Path Resolution Workarounds for Cygwin Mount Points

> **Rule:** Must execute path resolution routines against the parent directory
> to prevent mount-point root anomalies.
>
> **What:** Path conversion tools (like `cygpath`) must be executed against
> parent directories rather than the mount point directory directly to prevent
> incorrect path resolution anomalies.
>
> **Applies To:** Bash template scripts, Git for Windows integrations, and
> Cygwin/MSYS2 environment setups.
>
> **Why:** Because the Git installation directory serves as a root mount point
> in Cygwin/MSYS2 emulation environments, running `cygpath` directly against the
> Git absolute directory incorrectly returns `/`, which breaks all subsequent
> binary lookups. Failing to adhere to this typically results in **Path
> Resolution Error / Binary Not Found**.

**Trap 1: Calling `cygpath` directly on the target binary directory.**

**Don't:**

```bash
# BAD: Resolves to '/' if GIT_BIN_ABSDIR is the mount point
UNIX_GIT=`cygpath "${GIT_BIN_ABSDIR}"`
"$UNIX_GIT/bin/bash.exe" "$@"
```

**Do:**

```bash
# GOOD: Resolve the parent path and append the basename
WIN_GIT_PARENT=`dirname "${GIT_BIN_ABSDIR}"`
UNIX_GIT_PARENT=`cygpath "$WIN_GIT_PARENT"`
BASE_GIT=`basename "${GIT_BIN_ABSDIR}"`
UNIX_GIT="$UNIX_GIT_PARENT/$BASE_GIT"
"$UNIX_GIT/bin/bash.exe" "$@"
```

**Exceptions:** Native environments completely independent of Cygwin or MSYS2
path mapping rules.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T2 | Gclient Dependency Resolution & Execution - Bootstrapping
    mechanisms like `cipd.bat` rely on strict PowerShell environment rules to
    safely deploy and execute external binaries across Windows systems.
*   **Downstream:** T4 | Presubmit Infrastructure & Telemetry - Git subprocess
    aggregations executed by canned presubmit checks must respect Windows kernel
    bounds to prevent command-line crashes.
