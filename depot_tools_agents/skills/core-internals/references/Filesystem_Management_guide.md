# Filesystem Management Engineering Guide

## Executive Summary

Welcome to the authoritative engineering guide for Filesystem
Management. This repository of tribal knowledge exists to capture historical
context, prevent the regression of known failure modes, and standardize the
architectural boundaries of our automation and tooling environments. Over time,
recurring pitfalls—such as accidental data deletion from improper path bounding,
workflow breakages from abrupt CLI deprecations, and orphaned background
processes—have necessitated a formalized set of defensive engineering
constraints.

The chapters detailed below cover a broad spectrum of technical domains
essential to robust subsystem design. They establish strict protocols for
destructive path validation, system configuration transactionality, and the
seamless integration of OS-native system calls for critical performance
optimizations. Additionally, the guide outlines mechanisms for executing
least-privilege system diagnostics, gracefully modernizing legacy interfaces,
and ensuring cross-platform stability when handling version control metadata.

By adhering to these standards, engineers will ensure that tooling remains
resilient, scalable, and safe across diverse execution topologies. This document
serves as the foundational entry point for understanding the safeguards required
to build high-performance, fault-tolerant filesystem operations within the
Android ecosystem.

## Summary

| Chapter Theme / Title                | Scope & Objective                     |
| :----------------------------------- | :------------------------------------ |
| **Destructive Path Validation**      | Defines mandatory constraints for     |
:                                      : defensibly normalizing and verifying  :
:                                      : filesystem bounds before executing    :
:                                      : destructive operations like recursive :
:                                      : deletion. Ensures environmental       :
:                                      : conditions (e.g., Python optimization :
:                                      : flags) cannot silently bypass         :
:                                      : critical safety checks.               :
| **Graceful CLI Deprecation and       | Defines mechanisms for evolving       |
: Modernization**                      : command-line interfaces while         :
:                                      : preserving backward compatibility for :
:                                      : automation. Mandates the use of       :
:                                      : framework-native suppression,         :
:                                      : explicit boolean toggles, and         :
:                                      : targeted stderr warnings to prevent   :
:                                      : workflow regressions.                 :
| **Cross-Platform Path Constraints**  | Defines rules for handling            |
:                                      : OS-specific path limitations and      :
:                                      : mitigating failures stemming from     :
:                                      : environment nuances like Windows      :
:                                      : drive boundaries. Mandates strict     :
:                                      : sanitization when translating native  :
:                                      : file paths into formats consumed by   :
:                                      : strict external interfaces like VCS.  :
| **OS-Native Syscalls and Performance | Governs the integration of native     |
: Optimization**                       : OS-level system calls via Foreign     :
:                                      : Function Interfaces (FFI) to bypass   :
:                                      : standard shell utilities for          :
:                                      : performance-critical filesystem       :
:                                      : operations. Strictly mandates         :
:                                      : preserving exact CLI semantic         :
:                                      : behaviors (ACLs, symlink              :
:                                      : constraints).                         :
| **System Configuration               | Ensures system and workspace          |
: Transactionality**                   : initialization procedures employ      :
:                                      : transactional safety mechanisms to    :
:                                      : prevent corrupted or half-initialized :
:                                      : states upon failure. Requires strict  :
:                                      : configuration backups prior to        :
:                                      : destructive changes and top-level     :
:                                      : execution rollbacks.                  :
| **Least-Privilege System             | Mandates probing filesystem and       |
: Diagnostics**                        : hardware states exclusively through   :
:                                      : user-space metadata and native system :
:                                      : interfaces. Avoids elevated           :
:                                      : privileges and external shell         :
:                                      : execution to ensure robust,           :
:                                      : non-interactive diagnostics.          :
| **Subprocess Lifecycle and Resource  | Ensures system processes and          |
: Management**                         : resource-locking daemons (e.g.,       :
:                                      : wake-locks) have their lifecycles     :
:                                      : strictly bound to the execution scope :
:                                      : of the caller. Prevents parent        :
:                                      : process failures or abrupt            :
:                                      : terminations from leaving orphaned    :
:                                      : daemons draining resources.           :
| **VCS Metadata Handling and Edge     | Defines constraints for securely      |
: Cases**                              : parsing and interacting with version  :
:                                      : control metadata across diverse       :
:                                      : environment topologies. Mandates      :
:                                      : structural agnosticism for `.git`     :
:                                      : entries to support worktrees and      :
:                                      : requires defensive exception handling :
:                                      : for expected non-zero exits.          :

--------------------------------------------------------------------------------
--------------------------------------------------------------------------------

## Chapter: Destructive Path Validation

**Context:** This domain defines mandatory constraints for defensibly
normalizing and verifying filesystem bounds before executing destructive
operations like recursive deletion. It ensures environmental conditions, such as
Python optimization flags, cannot silently bypass critical safety checks.

### Summary

| Rule ID   | Principle /        | Priority | Primary Symptom / Trap           |
:           : Constraint         :          :                                  :
| :-------- | :----------------- | :------- | :------------------------------- |
| **T1-01** | Strict Destructive | High     | Using standard assertions for    |
:           : Path Validation    :          : critical destructive boundary    :
:           : and                :          : checks.                          :
:           : Optimization-Proof :          :                                  :
:           : Assertions         :          :                                  :
| **T1-02** | Canonicalization   | High     | Passing user-provided raw string |
:           : of Destructive and :          : paths directly into filesystem   :
:           : Traversal Paths    :          : traversal or validation logic.   :

--------------------------------------------------------------------------------

### Rules

#### T1-01: Strict Destructive Path Validation and Optimization-Proof Assertions

> **Rule:** Always normalize paths and explicitly validate hierarchical bounds
> using standard flow control before performing destructive operations. Never
> rely on `assert` statements for critical safety checks.
>
> **What:** Defensive normalization of paths using `os.path.realpath` and
> bounded validation using `os.path.commonpath` must be performed prior to
> destructive operations (e.g., `shutil.rmtree`). Furthermore, these checks must
> use standard flow control (`ValueError`) rather than `assert` statements.
>
> **Applies To:** Python filesystem automation tools executing destructive
> operations on dynamically resolved paths (e.g., submodule or workspace
> cleanup).
>
> **Why:** Unsafe path resolution without strict bounding checks risked
> accidental deletion outside the intended workspace root (e.g., if a nested
> directory was a symlink). Additionally, relying on `assert` for these critical
> bounds checks was dangerous because executing Python with the `-O` (optimize)
> flag completely disables assertions, bypassing the safety mechanisms. Failing
> to adhere to this typically results in **Accidental Data Deletion**.

**Trap 1: Using standard assertions for critical destructive boundary checks.**

**Don't:**

```python
# BAD: Asserts are removed when python is run with -O
assert workdir != args.new_workdir
shutil.rmtree(workdir)
```

**Do:**

```python
# GOOD: Explicit conditional checks raising exceptions
if workdir == args.new_workdir:
    raise ValueError("Safety check failed: cannot delete root")
shutil.rmtree(workdir)
```

**Trap 2: Comparing raw path strings without normalizing them or validating
their canonical bounds.**

**Don't:**

```python
# BAD: Raw path string comparison
if os.path.exists(workdir) and workdir != args.new_workdir:
    shutil.rmtree(workdir)
```

**Do:**

```python
# GOOD: Normalizing paths and checking common hierarchy bounds
if os.path.commonpath([args.new_workdir, os.path.abspath(workdir)]) == args.new_workdir:
    shutil.rmtree(workdir)
```

#### T1-02: Canonicalization of Destructive and Traversal Paths

> **Rule:** Must strictly canonicalize user-provided file paths by resolving all
> symbolic links and relative path tokens immediately upon script entry.
>
> **What:** User-provided file paths must be strictly canonicalized (resolving
> all symbolic links and relative path tokens) immediately upon script entry to
> ensure traversal logic and state validation behave correctly.
>
> **Applies To:** Filesystem management scripts and command-line utilities
> operating on user-provided directory paths.
>
> **Why:** When generating a new Git workdir, using relative paths or symlinked
> source directories without normalization caused the script to exit early. It
> successfully identified file system capabilities but generated an empty
> destination folder because relative path manipulation broke down during tree
> traversal. Failing to adhere to this typically results in **Incomplete
> Execution / Empty Output**.

**Trap 1: Passing user-provided raw string paths directly into filesystem
traversal or validation logic.**

**Don't:**

```python
def main():
    args = parse_options()
    # BAD: Using raw paths for filesystem checks
    if try_btrfs_subvol_snapshot(args.repository, args.new_workdir):
        pass
```

**Do:**

```python
def main():
    args = parse_options()
    # GOOD: Canonicalize paths immediately upon ingestion
    args.repository = os.path.realpath(args.repository)
    args.new_workdir = os.path.realpath(args.new_workdir)

    if try_btrfs_subvol_snapshot(args.repository, args.new_workdir):
        pass
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Downstream:** T4 | OS-Native Syscalls and Performance Optimization -
    *Canonicalizing paths early prevents resolution failures when passing
    targets to highly-optimized OS-level system calls like BTRFS subvolume
    snapshots.*

## Chapter: Graceful CLI Deprecation and Modernization

**Context:** This domain defines mechanisms for evolving command-line interfaces
while preserving backward compatibility for existing automation. It mandates the
use of framework-native suppression, explicit boolean toggles, and targeted
stderr warnings to prevent workflow regressions during flag deprecation or
default state reversals.

### Summary

| Rule ID   | Principle /           | Priority | Primary Symptom / Trap |
:           : Constraint            :          :                        :
| :-------- | :-------------------- | :------- | :--------------------- |
| **T2-01** | Graceful Boolean CLI  | Medium   | Removing old flags     |
:           : Flag Deprecation      :          : entirely or leaving    :
:           :                       :          : them fully visible in  :
:           :                       :          : the help menu during a :
:           :                       :          : deprecation            :
:           :                       :          : transition.            :
| **T2-02** | Default State         | Medium   | Deleting the legacy    |
:           : Reversal and Explicit :          : flag entirely when the :
:           : Opt-Ins               :          : default behavior is    :
:           :                       :          : flipped.               :
| **T2-03** | Strict Validation of  | Medium   | Defining state-bound   |
:           : Enumerated CLI Flags  :          : command line arguments :
:           :                       :          : as free-form text      :
:           :                       :          : fields.                :
| **T2-04** | CLI Boolean Antonym   | Medium   | Manually adding a      |
:           : Generation via        :          : negated flag (like     :
:           : BooleanOptionalAction :          : `--no-feature`) with   :
:           :                       :          : `action='store_false'` :
:           :                       :          : to override a default  :
:           :                       :          : behavior.              :
| **T2-05** | Graceful CLI Flag     | Medium   | Completely removing an |
:           : Deprecation with      :          : obsolete argument from :
:           : Stderr Suppression    :          : the parser, or leaving :
:           :                       :          : its old functionality  :
:           :                       :          : description intact     :
:           :                       :          : while disabling the    :
:           :                       :          : backend                :
:           :                       :          : implementation.        :

--------------------------------------------------------------------------------

### Rules

#### T2-01: Graceful Boolean CLI Flag Deprecation

> **Rule:** Must use `argparse.BooleanOptionalAction`, hide legacy aliases with
> `argparse.SUPPRESS`, and inject explicit stderr warnings to seamlessly
> transition deprecated CLI flags.
>
> **What:** Command-line arguments being renamed or deprecated must utilize
> `argparse.BooleanOptionalAction` to reduce boilerplate, suppress the
> deprecated aliases from the help output using `argparse.SUPPRESS`, and safely
> inject deprecation warnings directly via `sys.argv` inspection.
>
> **Applies To:** Python CLI tools utilizing `argparse` transitioning legacy
> flags (e.g., `--reflink` to `--copy-on-write`).
>
> **Why:** Evolving technical terminology in CLI flags abruptly broke existing
> automation scripts that relied on the old nomenclature. In environments where
> the native `argparse` deprecation parameter (added in Python 3.13) was not
> available (e.g., Python 3.11), manual deprecation wrappers had to be
> implemented to provide a safe migration path. Failing to adhere to this
> typically results in **Automation Breakage / Silent Failures**.

**Trap 1: Removing old flags entirely or leaving them fully visible in the help
menu during a deprecation transition.**

**Don't:**

```python
# BAD: Leaving deprecated flags fully visible in help
parser.add_argument('--reflink', action='store_true', help='Deprecated: use --copy-on-write')
```

**Do:**

```python
# GOOD: Aliasing the dest, suppressing help, and intercepting sys.argv
parser.add_argument('--reflink', action=argparse.BooleanOptionalAction, dest='copy_on_write', help=argparse.SUPPRESS)
if '--reflink' in sys.argv:
    print('Warning: --reflink is deprecated.', file=sys.stderr)
```

**Trap 2: Manually defining positive and negative boolean pairs instead of using
built-in actions.**

**Don't:**

```python
# BAD: Manual verbose inverse flags
parser.add_argument('--reflink', action='store_true')
parser.add_argument('--no-reflink', action='store_false', dest='reflink')
```

**Do:**

```python
# GOOD: Leveraging standard library automatic inverse generation
parser.add_argument('--copy-on-write', action=argparse.BooleanOptionalAction)
```

--------------------------------------------------------------------------------

#### T2-02: Default State Reversal and Explicit Opt-Ins

> **Rule:** Never delete a legacy opt-out flag when reversing a CLI tool's
> default state; always retain it alongside a newly introduced explicit opt-in
> flag.
>
> **What:** When reversing the default behavior of a CLI tool, retain the legacy
> opt-out flag to preserve backward compatibility, but map it alongside a newly
> introduced explicit opt-in flag.
>
> **Applies To:** Command-line interface parameter design across automation
> tools.
>
> **Why:** Transitioning a tool's default sync behavior (e.g., making
> dependencies unmanaged by default) risked silently changing the behavior of CI
> pipelines. Keeping the legacy `--unmanaged` flag functional while flipping the
> internal boolean default and adding `--managed` prevented workflow
> regressions. Failing to adhere to this typically results in **Unexpected
> Workflow Changes**.

**Trap 1: Deleting the legacy flag entirely when the default behavior is
flipped.**

**Don't:**

*   Removing `--unmanaged` because the tool now defaults to unmanaged behavior.

**Do:**

*   Retaining `--unmanaged` (even if it matches the new default) and adding
    `--managed` to allow explicit opt-in to the alternative state.

--------------------------------------------------------------------------------

#### T2-03: Strict Validation of Enumerated CLI Flags

> **Rule:** Must enforce strictly enumerated string identifier constraints
> natively using `choices` at the CLI parser boundary to prevent arbitrary
> payload injection.
>
> **What:** Script flags that expect a specific enumerated set of string
> identifiers must enforce these constraints explicitly at the CLI boundary
> using native parser mechanics (e.g., `choices`), rather than silently passing
> string pollution downstream.
>
> **Applies To:** Telemetry uploaders, argument parsers, and command-line
> interfaces.
>
> **Why:** A telemetry metadata uploader was accepting arbitrary strings for an
> operational state field. To prevent malformed strings from polluting the
> downstream backend schema, strict CLI-level enumeration enforcement was
> required. Failing to adhere to this typically results in **Schema Pollution /
> Silent Validation Failures**.

**Trap 1: Defining state-bound command line arguments as free-form text
fields.**

**Don't:**

```python
# BAD: Allows arbitrary unvalidated text input
parser.add_argument("--edit_monitor_state", default="")
```

**Do:**

```python
# GOOD: Fails immediately with help text if input is out of bounds
parser.add_argument("--edit_monitor_state", choices=["control", "enabled"])
```

--------------------------------------------------------------------------------

#### T2-04: CLI Boolean Antonym Generation via BooleanOptionalAction

> **Rule:** Always leverage `argparse.BooleanOptionalAction` for opt-out CLI
> behaviors to automatically generate matched boolean flag pairs.
>
> **What:** When designing opt-out CLI behaviors, use
> `argparse.BooleanOptionalAction` to automatically generate a matched pair of
> flags (e.g., `--flag` and `--no-flag`) acting on the same underlying boolean
> value, rather than manually defining negated flags.
>
> **Applies To:** Python CLI argument parsing (`argparse` configuration) for
> tools requiring opt-in/opt-out toggles.
>
> **Why:** Developers used to manually create separate, potentially conflicting
> arguments for enabling and disabling a feature, leading to bloated parser
> configuration, inconsistent flag naming, and ambiguous state if both were
> provided. Failing to adhere to this typically results in **Argument
> Collision**.

**Trap 1: Manually adding a negated flag (like `--no-feature`) with
`action='store_false'` to override a default behavior.**

**Don't:**

```python
# BAD: Manually defining the negative action
parser.add_argument('--no-caffeinate', dest='caffeinate', action='store_false')
```

**Do:**

```python
# GOOD: Letting argparse generate the paired antonym natively
parser.add_argument('--caffeinate', action=argparse.BooleanOptionalAction, default=True)
```

**Exceptions:** Legacy scripts strictly constrained to Python versions older
than 3.9 where `argparse.BooleanOptionalAction` is unavailable.

--------------------------------------------------------------------------------

#### T2-05: Graceful CLI Flag Deprecation with Stderr Suppression

> **Rule:** Never remove obsolete arguments outright; always map them to a no-op
> state with a deprecation warning in the parser to preserve CI/CD
> compatibility.
>
> **What:** When deprecating command-line flags, retain the flag in the parser
> but replace its functionality and help text with a clear deprecation warning
> indicating that the flag has no effect, preserving backward compatibility for
> automated scripts.
>
> **Applies To:** CLI argument definitions and runtime configuration evaluations
> in long-lived system utilities.
>
> **Why:** Removing deprecated flags outright caused automated CI/CD usages and
> wrapper scripts to break immediately with 'invalid argument' errors.
> Conversely, leaving the original description confused users into thinking the
> flag still functioned. Failing to adhere to this typically results in
> **Automation Breakage**.

**Trap 1: Completely removing an obsolete argument from the parser, or leaving
its old functionality description intact while disabling the backend
implementation.**

**Don't:**

```python
# BAD: Leaving the misleading help text intact
parser.add_option('--no_auth', help='Skip auth checking. Use if target bucket is public.')
```

**Do:**

```python
# GOOD: Explicitly defining it as a no-op to avoid breaking wrappers
parser.add_option('--no_auth', action='store_true', help='DEPRECATED: this flag has no effect.')

if options.no_auth:
    print('--no_auth is deprecated, this flag has no effect.')
```

**Exceptions:** Private or experimental flags intended strictly for temporary
local testing (e.g., `--update_readme`) can be removed outright without a formal
deprecation phase.

## Chapter: Cross-Platform Path Constraints

**Context:** This domain defines the rules for handling operating
system-specific path limitations, mitigating failures stemming from environment
nuances like Windows drive boundaries. It mandates strict sanitization when
translating native file paths into formats consumed by strict external
interfaces, such as version control references.

### Summary

| Rule ID   | Principle / Constraint | Priority | Primary Symptom / Trap      |
| :-------- | :--------------------- | :------- | :-------------------------- |
| **T3-01** | Cross-Platform Path    | Critical | Using raw filesystem path   |
:           : Separator Sanitization :          : strings directly within     :
:           : for Git References     :          : dynamically constructed Git :
:           :                        :          : branch names.               :

--------------------------------------------------------------------------------

### Rules

#### T3-01: Cross-Platform Path Separator Sanitization for Git References

> **Rule:** Always sanitize OS-specific path separators before injecting
> filesystem paths into Version Control System references. Never use raw,
> platform-dependent path strings when constructing Git branch names.
>
> **What:** Path strings dynamically converted into Version Control System (VCS)
> references (e.g., Git branch names) must sanitize OS-specific path separators
> (such as Windows backslashes `\`) to comply with strict VCS formatting rules.
>
> **Applies To:** Branch generation logic; any system combining dynamic file
> paths with Git metadata formatting rules.
>
> **Why:** Auto-generating Git branch names from common directory paths resulted
> in invalid reference formats on Windows, as `os.path.commonpath` returns
> backslashes which are explicitly forbidden by `git-check-ref-format`. Failing
> to adhere to this typically results in **Invalid Reference Format**.

**Trap 1: Using raw filesystem path strings directly within dynamically
constructed Git branch names.**

**Don't:**

```python
# BAD: Yields 'prefix_foo\bar' on Windows (Illegal Git branch)
common_path = os.path.commonpath(file_names)
branch_name = f"{prefix}_{common_path}_split"
```

**Do:**

```python
# GOOD: Normalizing delimiters to safe characters
common_path = os.path.commonpath(file_names).replace(os.path.sep, '_')
branch_name = f"{prefix}_{common_path}_split"
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Downstream:** T8 | VCS Metadata Handling and Edge Cases - *Path
    sanitization constraints directly ensure that dynamically generated metadata
    remains valid before being passed into strict VCS handling layers.*

## Chapter: OS-Native Syscalls and Performance Optimization

**Context:** This chapter governs the integration of native OS-level system
calls via Foreign Function Interfaces (FFI) to bypass standard shell utilities
for performance-critical filesystem operations. It strictly mandates preserving
exact CLI semantic behaviors, such as Access Control List preservation and
symlink constraints, when utilizing these low-level APIs.

### Summary

| Rule ID   | Principle / Constraint   | Priority | Primary Symptom / Trap     |
| :-------- | :----------------------- | :------- | :------------------------- |
| **T4-01** | Native APFS Clonefile    | Medium   | Spawning heavy             |
:           : Syscall Integration      :          : subprocesses for OS-native :
:           :                          :          : high-performance file      :
:           :                          :          : operations.                :
| **T4-02** | Foreign Function         | Medium   | Relying on standard shell  |
:           : Interface (FFI)          :          : utilities in a subprocess  :
:           : Integration for OS-Level :          : loop to perform native     :
:           : Copying                  :          : filesystem optimizations.  :
| **T4-03** | Semantic Consistency in  | High     | Passing default 0 flags to |
:           : Native Syscall Emulation :          : system API wrappers        :
:           :                          :          : without mapping the        :
:           :                          :          : semantic requirements of   :
:           :                          :          : the operation.             :

--------------------------------------------------------------------------------

### Rules

#### T4-01: Native APFS Clonefile Syscall Integration

> **Rule:** Always utilize Python's `ctypes` library to directly invoke the
> native APFS `clonefile` C function on macOS rather than delegating
> copy-on-write functionality to standard shell subprocesses.
>
> **What:** On macOS, bypass standard `cp` subprocess calls for copy-on-write
> functionality. Instead, use Python's `ctypes` library to invoke the native
> APFS `clonefile` C function directly.
>
> **Applies To:** Python tools on macOS (Darwin) handling large-scale file
> duplication or Git worktree initialization.
>
> **Why:** Spawning subprocesses to run `cp -a -c` for copy-on-write operations
> on macOS caused massive performance overhead (workspace creation took over 10
> minutes). Directly linking to the underlying C library via Foreign Function
> Interface (FFI) dropped execution time to seconds. Failing to adhere to this
> typically results in **High Performance Overhead / CPU Starvation**.

**Trap 1: Spawning heavy subprocesses for OS-native high-performance file
operations.**

**Don't:**

```python
# BAD: High overhead from subprocess spawning and non-optimized copying
subprocess.check_call(['cp', '-a', '-c', src, dest])
```

**Do:**

```python
# GOOD: Using FFI to invoke zero-copy OS internals directly
libc_path = ctypes.util.find_library("c")
_libc = ctypes.CDLL(libc_path, use_errno=True)
res = _libc.clonefile(os.fsencode(src), os.fsencode(dst), 0)
```

**Exceptions:** Linux systems, which still rely on `cp --reflink` via
subprocess.

--------------------------------------------------------------------------------

#### T4-02: Foreign Function Interface (FFI) Integration for OS-Level Copying

> **Rule:** Must execute high-performance filesystem operations by directly
> invoking native OS system calls via FFI, avoiding standard shell utilities
> like `cp` within subprocess loops.
>
> **What:** High-performance filesystem operations, such as Copy-on-Write
> cloning, should directly invoke native OS system calls (e.g., `clonefile` on
> Darwin via `ctypes`) rather than delegating to shell subprocesses like `cp`.
>
> **Applies To:** Cross-platform performance-critical python scripts,
> specifically when optimizing for modern OS-specific filesystems (APFS).
>
> **Why:** Spawning subprocesses for shell-based copying on macOS was taking up
> to 10 minutes to duplicate large repositories, whereas direct FFI calls to the
> native `clonefile` system API reduced the execution time to 20 seconds.
> Failing to adhere to this typically results in **Severe Performance
> Degradation**.

**Trap 1: Relying on standard shell utilities in a subprocess loop to perform
native filesystem optimizations.**

**Don't:**

```python
# BAD: Slow and spawns a shell process per invocation
subprocess.check_call(['cp', '-a', '-c', src, dest])
```

**Do:**

```python
# GOOD: Invoking native C library directly
_libc.clonefile(os.fsencode(src), os.fsencode(dst), 0)
```

**Exceptions:** If the native API fails (e.g., raising an `OSError`), a fallback
to the standard system CLI utility (`cp -a -c`) is permitted for fault
tolerance.

--------------------------------------------------------------------------------

#### T4-03: Semantic Consistency in Native Syscall Emulation

> **Rule:** Always enforce the exact semantic behavior of the original CLI
> tools—specifically preserving Access Control Lists and preventing symlink
> traversal—via explicit syscall bitmask flags when substituting shell utilities
> with native syscalls.
>
> **What:** When replacing shell utilities (like `cp -a`) with native syscalls
> via `ctypes`, the exact semantic behavior of the original CLI tool (preserving
> ACLs, preventing symlink traversal) must be explicitly enforced via syscall
> bitmask flags.
>
> **Applies To:** Darwin `clonefile` invocations and similar OS-level file
> manipulation bindings.
>
> **Why:** Replacing a `cp -a` subprocess with macOS's `clonefile(src, dst, 0)`
> broke behavioral parity because passing the default integer (0) inadvertently
> followed symlinks and dropped Access Control Lists, unlike the original
> archive copy command. Failing to adhere to this typically results in
> **Permission Loss / Symlink Corruption**.

**Trap 1: Passing default 0 flags to system API wrappers without mapping the
semantic requirements of the operation.**

**Don't:**

```python
# BAD: Default flags lose ACLs and follow symlinks
res = _libc.clonefile(os.fsencode(src), os.fsencode(dst), 0)
```

**Do:**

```python
# GOOD: Passing exact bitmask flags to emulate 'cp -a'
# CLONE_NOFOLLOW (0x0001) | CLONE_ACL (0x0004) = 5
res = _libc.clonefile(os.fsencode(src), os.fsencode(dst), 5)
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Downstream:** T8 | VCS Metadata Handling and Edge Cases - *Git worktree
    initialization routines directly depend on these low-level native syscall
    optimizations to efficiently duplicate large repository structures.*

## Chapter: System Configuration Transactionality

**Context:** System and workspace initialization procedures must employ
transactional safety mechanisms to prevent corrupted or half-initialized states
upon failure. This requires strict configuration backups prior to destructive
changes and top-level execution rollbacks for multi-step filesystem operations.

### Summary

| Rule ID   | Principle / Constraint    | Priority | Primary Symptom / Trap    |
| :-------- | :------------------------ | :------- | :------------------------ |
| **T5-01** | Transactional fstab       | Critical | Unconditionally appending |
:           : Modification and Rollback :          : or modifying fstab        :
:           :                           :          : without creating a        :
:           :                           :          : recovery backup.          :
| **T5-02** | Transactional Scope for   | High     | Iterating over            |
:           : Workspace Initialization  :          : directories and issuing   :
:           :                           :          : sequential shell commands :
:           :                           :          : without an error recovery :
:           :                           :          : boundary.                 :

--------------------------------------------------------------------------------

### Rules

#### T5-01: Transactional fstab Modification and Rollback

> **Rule:** Always generate a `.bak` file and execute pattern-matching
> validation before modifying critical system configuration files. Never append
> directly to boot configurations without safeguarding the prior working state.
>
> **What:** Automated `/etc/fstab` modifications must strictly include
> pre-modification pattern matching, user confirmation for overwrites, and the
> generation of a `.bak` backup file prior to any deletion or append operation.
>
> **Applies To:** Bash or system configuration scripts automating the setup of
> persistent loopback mounts or filesystems.
>
> **Why:** Automated modification of `/etc/fstab` without user confirmation or
> backup generation frequently caused fatal system boot failures if the regex
> replacement failed or the appended string was malformed. Failing to adhere to
> this typically results in **System Unbootable / Kernel Panic**.

**Trap 1: Unconditionally appending or modifying fstab without creating a
recovery backup.**

**Don't:**

```bash
# BAD: Blindly appending or sed-ing critical boot configurations
echo "${FSTAB_LINE}" | sudo tee -a /etc/fstab
```

**Do:**

```bash
# GOOD: Backup, clean up old entries, then append
sudo cp /etc/fstab /etc/fstab.bak
sudo sed -i -E "\| ${MOUNT_POINT} |d" /etc/fstab
echo "${FSTAB_LINE}" | sudo tee -a /etc/fstab
```

--------------------------------------------------------------------------------

#### T5-02: Transactional Scope for Workspace Initialization

> **Rule:** Must wrap multi-step structural scripts in a top-level
> `try...except` block with mandatory filesystem cleanup. Always explicitly
> destroy partially initialized outputs if a mid-execution failure occurs.
>
> **What:** Multi-step structural scripts must wrap their core execution in a
> top-level execution scope with a mandatory cleanup block to gracefully destroy
> partially initialized outputs upon unexpected failures.
>
> **Applies To:** Scripts modifying disk state, creating directories, or
> orchestrating source control commands sequentially.
>
> **Why:** If a network or filesystem operation failed mid-execution, the script
> aborted and left behind a half-created directory, putting the local git
> repository in a broken state that corrupted subsequent attempts. Failing to
> adhere to this typically results in **Corrupted Workspace / Orphaned
> Resources**.

**Trap 1: Iterating over directories and issuing sequential shell commands
without an error recovery boundary.**

**Don't:**

```python
# BAD: Fails midway leaving artifacts behind
os.makedirs(args.new_workdir)
for root in directories:
    subprocess.check_call(['git', 'checkout', '-f'], cwd=root)
```

**Do:**

```python
# GOOD: Top-level rollback on any failure
try:
    # Initialize workspace...
    for root in directories:
        subprocess.check_call(['git', 'checkout', '-f'], cwd=root)
except:
    # Clean up destination on failure
    shutil.rmtree(args.new_workdir)
    raise
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | Destructive Path Validation - *Rollback mechanisms
    utilizing destructive filesystem operations (e.g., `shutil.rmtree`) must
    implement defensive path validation to prevent catastrophic over-deletion
    during cleanup.*

## Chapter: Least-Privilege System Diagnostics

**Context:** Probe filesystem and hardware states exclusively through user-space
metadata and native system interfaces. Avoid elevated privileges and external
shell execution to ensure robust, non-interactive diagnostics.

### Summary

| Rule ID   | Principle / Constraint  | Priority | Primary Symptom / Trap     |
| :-------- | :---------------------- | :------- | :------------------------- |
| **T6-01** | Unprivileged Filesystem | Medium   | Shelling out to retrieve   |
:           : Metadata Probing        :          : system state or relying on :
:           :                         :          : privileged administrative  :
:           :                         :          : utilities for simple       :
:           :                         :          : metadata.                  :

--------------------------------------------------------------------------------

### Rules

#### T6-01: Unprivileged Filesystem Metadata Probing

> **Rule:** Always use native Python functions like `os.stat` to probe
> filesystem metadata instead of invoking external shell utilities. Never rely
> on administrative commands that trigger privilege escalation constraints.
>
> **What:** Avoid elevated system calls (sudo) or brittle shell commands
> (`shell=True`) when probing filesystem types or states. Rely on native
> `os.stat` inode checks and unprivileged system commands.
>
> **Applies To:** Python scripts diagnosing local filesystem types (e.g.,
> detecting Btrfs subvolumes).
>
> **Why:** Using commands like `btrfs subvolume show` or `stat -c %i` through a
> shell required `sudo` or failed with 'Operation not permitted', even for
> user-owned subvolumes. This broke non-interactive usage and caused developers
> to rabbit-hole into privilege escalation issues. Failing to adhere to this
> typically results in **Permission Denied / Privilege Escalation**.

**Trap 1: Shelling out to retrieve system state or relying on privileged
administrative utilities for simple metadata.**

**Don't:**

```python
# BAD: Requires root or is prone to shell injection
subprocess.run(f"stat -c %i '{path}'", shell=True)
# or
subprocess.check_call(['btrfs', 'subvolume', 'show', path])
```

**Do:**

```python
# GOOD: Native Python stat calls (Btrfs subvolume roots always have inode 256)
return os.stat(path).st_ino == 256
```

## Chapter: Subprocess Lifecycle and Resource Management

**Context:** System processes and resource-locking daemons (e.g., wake-locks)
must have their lifecycles strictly bound to the execution scope of the caller.
This ensures that parent process failures or abrupt terminations do not leave
orphaned daemons draining system resources.

### Summary

| Rule ID   | Principle / Constraint | Priority | Primary Symptom / Trap       |
| :-------- | :--------------------- | :------- | :--------------------------- |
| **T7-01** | Scope-Bound Subprocess | Critical | Firing off a background      |
:           : Power State Monitoring :          : power daemon without         :
:           :                        :          : tracking its PID or          :
:           :                        :          : attaching it to a            :
:           :                        :          : `try...finally` block.       :
| **T7-02** | Strict Subprocess      | High     | Spawning a subprocess for an |
:           : Lifecycle Binding via  :          : environmental side effect    :
:           : Context Managers       :          : without wrapping its         :
:           :                        :          : lifecycle or guaranteeing    :
:           :                        :          : its termination upon parent  :
:           :                        :          : exit.                        :

--------------------------------------------------------------------------------

### Rules

#### T7-01: Scope-Bound Subprocess Power State Monitoring

> **Rule:** Always couple the lifecycle of resource-locking daemons to the exact
> executing context and guarantee termination upon scope exit or failure.
>
> **What:** Utilities that assert wake-locks (prevent system sleep during long
> operations) must tightly couple the locking daemon's lifecycle to the exact
> executing context and terminate the daemon upon scope exit or failure.
>
> **Applies To:** Long-running daemon wrappers, network fetch tasks, and
> power-management hooks (e.g., macOS `caffeinate`).
>
> **Why:** A background fetch task crashed due to a GitHub HTTP 503 error.
> Because the wake-lock process was properly scoped and tracked by PID, the
> script successfully terminated the daemon, allowing the device to sleep
> instead of causing a permanent wake-lock leak. Failing to adhere to this
> typically results in **Battery Drain / Wake-Lock Leak**.

**Trap 1: Firing off a background power daemon without tracking its PID or
attaching it to a `try...finally` block.**

**Don't:**

```python
# BAD: If fetch crashes, device never sleeps
subprocess.Popen(['caffeinate', '-i'])
run_long_fetch_operation()
```

**Do:**

```python
# GOOD: Bound to a context manager explicitly watching the current process
with caffeinate.scope():
    run_long_fetch_operation()
```

--------------------------------------------------------------------------------

#### T7-02: Strict Subprocess Lifecycle Binding via Context Managers

> **Rule:** Must strictly bind the execution lifecycles of system daemons to the
> caller's scope using context managers to prevent orphaned processes.
>
> **What:** Long-running system daemons or resource-locking processes (like
> sleep prevention utilities) must have their execution lifecycles strictly
> bound to the caller's scope using context managers, ensuring they do not
> outlive the parent process.
>
> **Applies To:** Subprocess management utilities; specifically sleep-prevention
> wrappers (e.g., macOS `caffeinate`).
>
> **Why:** Historically, spawning a detached sleep-prevention process during a
> fetch operation could result in orphaned processes holding wake locks
> indefinitely if the parent application crashed or was terminated abnormally.
> Failing to adhere to this typically results in **Orphaned Processes**.

**Trap 1: Spawning a subprocess for an environmental side effect without
wrapping its lifecycle or guaranteeing its termination upon parent exit.**

**Don't:**

```python
# BAD: Subprocess could outlive parent if exception occurs
subprocess.Popen(['caffeinate', '-i'])
```

**Do:**

```python
# GOOD: Bound strictly to context manager with cleanup guarantee
@contextlib.contextmanager
def scope():
    proc = subprocess.Popen(['caffeinate', '-i', '-w', str(os.getpid())])
    try:
        yield True
    finally:
        proc.terminate()
```

## Chapter: VCS Metadata Handling and Edge Cases

**Context:** This chapter defines constraints for securely parsing and
interacting with version control metadata across diverse environment topologies.
It mandates structural agnosticism for `.git` entries to support worktrees and
requires defensive exception handling for expected non-zero exits during
subprocess VCS queries.

### Summary

| Rule ID   | Principle / Constraint  | Priority | Primary Symptom / Trap      |
| :-------- | :---------------------- | :------- | :-------------------------- |
| **T8-01** | VCS Metadata Structure  | High     | Assuming `.git` is always a |
:           : Agnosticism             :          : directory for initialized   :
:           :                         :          : repositories.               :
| **T8-02** | Handling Non-Zero       | High     | Capturing subprocess output |
:           : Subprocess Exits in VCS :          : for a configuration read    :
:           : Configuration Queries   :          : without wrapping it in an   :
:           :                         :          : exception handler for       :
:           :                         :          : acceptable non-zero return  :
:           :                         :          : codes.                      :

--------------------------------------------------------------------------------

### Rules

#### T8-01: VCS Metadata Structure Agnosticism

> **Rule:** Always use structure-agnostic existence checks when verifying
> version control metadata entries to support modern pointer-based layouts.
>
> **What:** Scripts traversing submodule or repository metadata must check for
> the existence of the `.git` entry (which could be a file or a directory),
> rather than strictly asserting it is a directory.
>
> **Applies To:** Version control scripts parsing submodules, git worktrees, or
> hybrid Git/Jujutsu (jj) environments.
>
> **Why:** In Git worktrees and modern submodule layouts, `.git` is often a
> plain text file containing a path pointer to a shared central `.git`
> directory. Checking `path.is_dir()` explicitly broke compatibility with these
> layouts, throwing uninitialized submodule errors. Failing to adhere to this
> typically results in **Uninitialized Submodule Error**.

**Trap 1: Assuming `.git` is always a directory for initialized repositories.**

**Don't:**

```python
# BAD: Fails on git worktrees where .git is a file
if path.is_dir() and (path / '.git').is_dir():
    yield path
```

**Do:**

```python
# GOOD: Agnostic existence check
if path.is_dir() and (path / '.git').exists():
    yield path
```

--------------------------------------------------------------------------------

#### T8-02: Handling Non-Zero Subprocess Exits in VCS Configuration Queries

> **Rule:** Must explicitly catch and handle exception states resulting from
> expected non-zero exit codes during version control configuration queries.
>
> **What:** When querying VCS configuration via subprocess (e.g., `git config`),
> expected state absences (like no matches found) return non-zero exit codes.
> These must be caught explicitly using exceptions like `CalledProcessError`
> rather than allowing the application to crash.
>
> **Applies To:** Subprocess wrappers interfacing with Git (e.g., extracting
> submodule paths, checking config keys).
>
> **Why:** Querying `.gitmodules` for paths using `git config --get-regexp`
> returns a 1 exit code when no matches are found, which resulted in uncaught
> exceptions breaking script execution when repositories lacked the specific
> configuration. Failing to adhere to this typically results in **Uncaught
> CalledProcessError**.

**Trap 1: Capturing subprocess output for a configuration read without wrapping
it in an exception handler for acceptable non-zero return codes.**

**Don't:**

```python
# BAD: Will crash if exit code is 1 (no matches)
config_output = GIT.Capture(['config', '--file', '.gitmodules', '--get-regexp', 'path'])
```

**Do:**

```python
# GOOD: Catch the specific process error and return a safe default
try:
    config_output = GIT.Capture(['config', '--file', '.gitmodules', '--get-regexp', 'path'])
except subprocess2.CalledProcessError:
    return []
```
