# Build System Infrastructure Engineering Guide

## Executive Summary

Welcome to the Build System Infrastructure Engineering Guide. This authoritative
repository captures essential tribal knowledge and historical context
surrounding the build environment. Its primary objective is to prevent
the regression of known failure modes, codify hard-won operational constraints,
and strictly standardize the architectural boundaries across our tooling
ecosystem. For incoming engineers, this guide serves as a foundational compass
for navigating the complexities of our build wrappers, telemetry daemons, and
cross-process orchestrations without repeating the costly mistakes of the past.

The build infrastructure operates at the critical intersection of developer
experience and OS-level system administration. The chapters herein prescribe
precise methodologies for handling CLI flag propagation, managing the lifecycle
and security of background IPC daemons, and extracting execution strategies
deterministically from declarative state files. Furthermore, it outlines robust
testing paradigms and OS-level resource normalization techniques—ranging from
file descriptor escalation to mount namespace virtualization—ensuring
consistent, high-fidelity builds regardless of the underlying host or headless
AI environment.

## Summary

| Chapter Theme / Title               | Scope & Objective                      |
| :---------------------------------- | :------------------------------------- |
| **CLI Flag Propagation & Order      | Governs the precise interception,      |
: Resolution**                        : mutation, and propagation of           :
:                                     : command-line arguments across Python   :
:                                     : wrappers and downstream build          :
:                                     : binaries. Establishes constraints for  :
:                                     : dynamic capability probing, strict     :
:                                     : subcommand segregation, and OS-safe    :
:                                     : argument serialization to prevent      :
:                                     : silent parsing failures and execution  :
:                                     : drift.                                 :
| **Daemon Process Orchestration &    | Defines the constraints for managing   |
: Health Polling**                    : the lifecycle of background sidecar    :
:                                     : processes and telemetry daemons.       :
:                                     : Mandates strict process isolation,     :
:                                     : cross-platform health polling, and     :
:                                     : deterministic cleanup to prevent       :
:                                     : global state pollution and orphaned    :
:                                     : processes.                             :
| **IPC Socket Safety & Constraints** | Governs the lifecycle, security, and   |
:                                     : cleanup of Unix domain sockets used    :
:                                     : for inter-process communication.       :
:                                     : Establishes strict constraints for     :
:                                     : OS-level path length limits,           :
:                                     : user-specific isolation, and resilient :
:                                     : cleanup mechanisms to prevent stale    :
:                                     : artifacts and binding failures.        :
| **Identity & Telemetry              | Enforces strict execution boundaries   |
: Authorization**                     : to safely govern telemetry tracking,   :
:                                     : ensuring user privacy and robust       :
:                                     : multi-factor authentication. Mandates  :
:                                     : explicit opt-ins, silent failures for  :
:                                     : unauthenticated contributors, and safe :
:                                     : state encapsulation across process     :
:                                     : boundaries.                            :
| **Declarative Build State           | Requires build orchestration           |
: Extraction**                        : mechanisms to deterministically        :
:                                     : extract execution strategies from      :
:                                     : declarative configuration files rather :
:                                     : than imperatively executing external   :
:                                     : scripts. Ensures robust environment    :
:                                     : initialization and prevents cascading  :
:                                     : failures in uninitialized tool states. :
| **OS-Level Resource Normalization** | Establishes mandatory constraints for  |
:                                     : normalizing the build environment      :
:                                     : prior to tool execution, encompassing  :
:                                     : file descriptor escalations, path      :
:                                     : virtualization, and process priority   :
:                                     : tuning to prevent arbitrary cache      :
:                                     : invalidations and resource exhaustion. :
| **High-Fidelity Infrastructure      | Dictates the design of unit tests for  |
: Testing**                           : build infrastructure wrappers and      :
:                                     : telemetry components. Mandates relying :
:                                     : on physical mock files and hermetic    :
:                                     : environments over brittle internal     :
:                                     : function patching to ensure end-to-end :
:                                     : parsing is reliably validated.         :
| **AI Agent Environment Adaptation** | Governs the detection and              |
:                                     : normalization of headless, AI-driven   :
:                                     : environments to optimize build tool    :
:                                     : interactions. Enforces safe execution  :
:                                     : parameter mutation to preserve non-TTY :
:                                     : performance paths while emitting       :
:                                     : deterministic signals to prevent LLM   :
:                                     : context exhaustion or hallucination.   :

## Chapter: CLI Flag Propagation & Order Resolution

**Context:** This chapter governs the precise interception, mutation, and
propagation of command-line arguments across Python wrappers and downstream
build binaries. It establishes constraints for dynamic capability probing,
strict subcommand segregation, and OS-safe argument serialization to prevent
silent parsing failures and execution drift.

### Summary

| Rule ID   | Principle /        | Priority | Primary Symptom / |
:           : Constraint         :          : Trap              :
| :-------- | :----------------- | :------- | :---------------- |
| **T1-01** | Windows Batch      | High     | Unconditionally   |
:           : Wrapper Argument   :          : stripping the     :
:           : Serialization      :          : trailing double   :
:           :                    :          : quote from        :
:           :                    :          : arguments on      :
:           :                    :          : Windows, which    :
:           :                    :          : breaks            :
:           :                    :          : legitimately      :
:           :                    :          : quoted flags      :
:           :                    :          : containing exact  :
:           :                    :          : match strings.    :
| **T1-02** | Token-Based        | Medium   | Using a Python    |
:           : Toolchain Feature  :          : substring check   :
:           : Detection          :          : (`in`) to verify  :
:           :                    :          : if a flag exists  :
:           :                    :          : in the raw CLI    :
:           :                    :          : output stream.    :
| **T1-03** | Dynamic CLI        | High     | Extracting        |
:           : Subcommand         :          : subcommands by    :
:           : Discovery          :          : simply finding    :
:           :                    :          : the first         :
:           :                    :          : argument that     :
:           :                    :          : does not start    :
:           :                    :          : with a hyphen.    :
| **T1-04** | Passthrough of     | Medium   | Creating an       |
:           : Native Help Flags  :          : ArgumentParser in :
:           : in CLI Wrappers    :          : a wrapper script  :
:           :                    :          : without disabling :
:           :                    :          : the default help  :
:           :                    :          : action.           :
| **T1-05** | Granular Feature   | High     | Checking only for |
:           : Detection via Flag :          : a subcommand's    :
:           : Probing            :          : existence to      :
:           :                    :          : assume full       :
:           :                    :          : support for a new :
:           :                    :          : feature set.      :
| **T1-06** | Localized          | High     | Directly mutating |
:           : Environment        :          : the global        :
:           : Variable Mutation  :          : environment       :
:           :                    :          : variables to pass :
:           :                    :          : telemetry         :
:           :                    :          : configurations to :
:           :                    :          : a sidecar.        :
| **T1-07** | Explicit Flag      | Medium   | Attempting to     |
:           : Overrides for      :          : disable a boolean :
:           : Downstream         :          : feature by        :
:           : Binaries           :          : plucking its      :
:           :                    :          : positive flag out :
:           :                    :          : of a list.        :
| **T1-08** | Dynamic CLI        | Medium   | Duplicating the   |
:           : Argument List      :          : subprocess        :
:           : Construction       :          : execution call    :
:           :                    :          : just to append    :
:           :                    :          : one flag.         :
| **T1-09** | Exit Code          | Medium   | Grepping or       |
:           : Validation for     :          : substring         :
:           : Subcommand Support :          : matching against  :
:           :                    :          : general CLI help  :
:           :                    :          : text.             :
| **T1-10** | Strict Ordering    | Medium   | Using unordered   |
:           : Validation for CLI :          : list comparisons  :
:           : Argument           :          : to validate CLI   :
:           : Generation         :          : argument lists.   :
| **T1-11** | Post-Subcommand    | High     | Appending         |
:           : Argument Injection :          : environment or    :
:           :                    :          : telemetry flags   :
:           :                    :          : blindly to the    :
:           :                    :          : base tool         :
:           :                    :          : invocation.       :
| **T1-12** | Tool-Specific      | Medium   | Passing raw       |
:           : Argument Interface :          : `input_args` down :
:           : Segregation        :          : to all execution  :
:           :                    :          : paths             :
:           :                    :          : indiscriminately. :
| **T1-13** | Robust CLI Flag    | Medium   | Using basic       |
:           : Detection via      :          : `startswith()` or :
:           : Assignment Syntax  :          : `not in` checks   :
:           :                    :          : that fail to      :
:           :                    :          : account for       :
:           :                    :          : variable          :
:           :                    :          : assignment        :
:           :                    :          : syntaxes.         :
| **T1-14** | Robust Parsing of  | High     | Assuming the      |
:           : Directory          :          : change-directory  :
:           : Traversal (-C)     :          : flag is always    :
:           : Flags              :          : followed by a     :
:           :                    :          : space-separated   :
:           :                    :          : argument.         :
| **T1-15** | Segregation of     | Medium   | Blindly appending |
:           : Global and         :          : all parsed config :
:           : Subcommand Flags   :          : file arguments    :
:           : in Configuration   :          : into a single     :
:           : Files              :          : global array      :
:           :                    :          : applied           :
:           :                    :          : universally to    :
:           :                    :          : the command.      :
| **T1-16** | Sequence-Dependent | Medium   | Setting override  |
:           : Evaluation of      :          : environment       :
:           : Build Override     :          : variables         :
:           : Flags              :          : immediately upon  :
:           :                    :          : parsing a         :
:           :                    :          : command-line      :
:           :                    :          : flag, before the  :
:           :                    :          : default tool      :
:           :                    :          : states are        :
:           :                    :          : finalized.        :
| **T1-17** | Selective          | Medium   | Applying remote   |
:           : Bypassing of       :          : execution         :
:           : Execution Wrappers :          : wrappers          :
:           : for Local          :          : unconditionally   :
:           : Sub-Commands       :          : to all commands   :
:           :                    :          : passed to the     :
:           :                    :          : build binary.     :
| **T1-18** | Structured         | Medium   | Splitting         |
:           : Subprocess         :          : subprocess output :
:           : Interrogation      :          : by lines and      :
:           :                    :          : using             :
:           :                    :          : text-matching     :
:           :                    :          : heuristics to     :
:           :                    :          : deduce            :
:           :                    :          : programmatic      :
:           :                    :          : state.            :
| **T1-19** | Unified Build      | Medium   | Passing execution |
:           : Invocation         :          : identifiers       :
:           : Correlation        :          : strictly via      :
:           :                    :          : tool-specific CLI :
:           :                    :          : arguments,        :
:           :                    :          : leading to        :
:           :                    :          : synchronization   :
:           :                    :          : drift.            :

--------------------------------------------------------------------------------

### Rules

#### T1-01: Windows Batch Wrapper Argument Serialization

> **Rule:** Always conditionally verify if trailing quotes are balanced before
> stripping them in Windows batch argument pipelines.
>
> **What:** Robust argument string processing to correctly handle backslash
> escaping when forwarding command-line parameters from Windows batch scripts
> (`.bat`) to Python wrappers.
>
> **Applies To:** CLI wrappers handling pass-through execution on Windows,
> specifically where batch scripts use `"%*"` to forward arguments.
>
> **Why:** When a Windows batch file passes arguments ending in a directory
> separator (e.g., `out\Default\`), the Windows command interpreter treats the
> trailing backslash as an escape sequence for the closing quote. This causes
> the closing quote to be read as a literal character in Python, corrupting
> subsequent flags. Failing to adhere to this typically results in **Argument
> Parsing Failure**.

**Trap 1: Unconditionally stripping the trailing double quote from arguments on
Windows, which breaks legitimately quoted flags containing exact match
strings.**

**Don't:**

```python
# BAD: Corrupts flags like --flag="value"
if sys.platform == "win32" and arg.endswith('"'):
    arg = arg[:-1]
```

**Do:**

```python
# GOOD: Only strip the trailing quote if the argument contains an unbalanced (odd) number of quotes
if sys.platform == "win32" and arg.endswith('"') and arg.count('"') % 2 != 0:
    arg = arg[:-1]
```

#### T1-02: Token-Based Toolchain Feature Detection

> **Rule:** Must use discrete string tokenization when evaluating capabilities
> of underlying binaries via help manifests.
>
> **What:** Detecting capabilities of an underlying CLI tool by parsing its help
> output using discrete string tokenization rather than contiguous substring
> matching.
>
> **Applies To:** Wrapper scripts and integrators dynamically probing external
> binaries for feature flag support.
>
> **Why:** Using a generic substring check (`in res.stdout`) against the tool's
> help text caused false positives when the targeted flag name appeared merely
> as a description or as a subset of a newer, longer flag (e.g., matching
> `-namespace` inside `--namespace-separator`). Failing to adhere to this
> typically results in **False Positive Detection**.

**Trap 1: Using a Python substring check (`in`) to verify if a flag exists in
the raw CLI output stream.**

**Don't:**

```python
# BAD: Susceptible to substring false-positives
res = subprocess.run([siso_path, "help", "ninja"], capture_output=True, text=True)
return "-namespace" in res.stdout
```

**Do:**

```python
# GOOD: Split output into tokens to guarantee an exact flag match
res = subprocess.run([siso_path, "help", "ninja"], capture_output=True, text=True)
return any(
    part in ["-namespace"]
    for line in res.stdout.splitlines()
    for part in line.split()
)
```

#### T1-03: Dynamic CLI Subcommand Discovery

> **Rule:** Always extract CLI subcommands dynamically by querying the
> underlying tool for recognized commands, avoiding positional or omission-based
> guessing.
>
> **What:** A wrapper script must dynamically query the underlying tool for
> valid subcommands (e.g., via its `help` command) rather than relying on
> positional heuristics to parse complex flags.
>
> **Applies To:** CLI wrapper scripts (like `siso.py`) parsing arguments to
> conditionally inject telemetry or configurations based on the subcommand.
>
> **Why:** The wrapper previously used a fragile heuristic assuming the first
> non-hyphenated argument was the subcommand. When users passed global boolean
> flags or flags with values before the subcommand, the parsing logic failed,
> resulting in telemetry gaps. Failing to adhere to this typically results in
> **Argument Parsing Failure**.

**Trap 1: Extracting subcommands by simply finding the first argument that does
not start with a hyphen.**

**Don't:**

```python
# BAD: Fails if a global flag takes a non-hyphenated value
subcmd = ''
for arg in args:
    if not arg.startswith("-") and not subcmd:
        subcmd = arg
        break
```

**Do:**

```python
# GOOD: Query the tool for a definitive list of valid subcommands
valid_subcmds = _get_siso_subcmds(siso_path)
subcmd = ''
for arg in args:
    if arg in valid_subcmds:
        subcmd = arg
        break
```

#### T1-04: Passthrough of Native Help Flags in CLI Wrappers

> **Rule:** Never intercept generic `-h` or `--help` flags in proxy wrappers;
> explicitly suppress internal help evaluation.
>
> **What:** Python CLI wrappers using `argparse` solely for partial argument
> inspection must instantiate the parser with `add_help=False` to prevent
> intercepting `-h`/`--help` flags intended for the wrapped binary.
>
> **Applies To:** Any Python script acting as a transparent proxy or wrapper to
> an underlying compiled tool.
>
> **Why:** The wrapper script's internal `argparse.ArgumentParser` was capturing
> the user's `-h` and `--help` flags to print the script's minimal help,
> blocking users from seeing the full command manual provided by the underlying
> binary. Failing to adhere to this typically results in **Truncated Help
> Output**.

**Trap 1: Creating an ArgumentParser in a wrapper script without disabling the
default help action.**

**Don't:**

```python
# BAD: Intercepts -h/--help and blocks it from reaching the wrapped tool
parser = argparse.ArgumentParser()
parser.add_argument("-project", "--project")
known_args, _ = parser.parse_known_args(args)
```

**Do:**

```python
# GOOD: Explicitly disable the internal help flag so the tool catches it
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("-project", "--project")
known_args, _ = parser.parse_known_args(args)
```

#### T1-05: Granular Feature Detection via Flag Probing

> **Rule:** Must verify specific argument flags exist within the target
> subcommand before injecting overriding parameters.
>
> **What:** When wrapping third-party binaries or delegating commands, feature
> support must be verified by probing for specific flag availability in help
> outputs, rather than solely checking for subcommand existence.
>
> **Applies To:** Build wrapper scripts handling CLI argument propagation (e.g.,
> configuring telemetry flags for underlying tools).
>
> **Why:** Previously, the wrapper inferred that if a subcommand existed, all
> associated flags were supported. This caused build regressions for users with
> older versions of the binary, resulting in "flag provided but not defined"
> errors. Failing to adhere to this typically results in **Build Regression /
> Unrecognized Flag**.

**Trap 1: Checking only for a subcommand's existence to assume full support for
a new feature set.**

**Don't:**

```python
if _is_subcommand_present(binary_path, "collector"):
    telemetry_flags.append("enable_collector")
```

**Do:**

```python
if "collector_address" in _subcommand_help(binary_path, "collector"):
    if "collector_address" in _subcommand_help(binary_path, "ninja"):
        telemetry_flags.append("enable_collector")
```

#### T1-06: Localized Environment Variable Mutation

> **Rule:** Never mutate the global `os.environ` array when orchestrating daemon
> environments.
>
> **What:** Process orchestration functions must avoid modifying the global
> `os.environ`. Instead, they should accept a local environment dictionary, copy
> it, and return the modified state for downstream subprocess invocation.
>
> **Applies To:** Configuration preparation and daemon startup routines passing
> state to child processes.
>
> **Why:** Mutating global environment variables during sidecar initialization
> occasionally leaked variables to other concurrent functions or left the system
> in an unpredictable state when initialization failed. Failing to adhere to
> this typically results in **Downstream State Pollution**.

**Trap 1: Directly mutating the global environment variables to pass telemetry
configurations to a sidecar.**

**Don't:**

```python
def start_collector():
    os.environ["COLLECTOR_ADDRESS"] = endpoint
    # ... launch process ...
```

**Do:**

```python
def _handle_collector(args, env: dict[str, str]) -> dict[str, str]:
    local_env = env.copy()
    local_env["COLLECTOR_ADDRESS"] = endpoint
    started = _start_collector(..., local_env)
    if not started:
        local_env.pop("COLLECTOR_ADDRESS", None)
    return local_env
```

#### T1-07: Explicit Flag Overrides for Downstream Binaries

> **Rule:** Always inject an explicit negating flag (e.g., `=false`) at the tail
> of the argument array instead of attempting to parse and delete positive
> assignments.
>
> **What:** When a wrapper script needs to forcefully disable a feature in a
> downstream binary, it must explicitly append the negative/false flag to the
> argument list rather than just attempting to remove the positive flag.
>
> **Applies To:** Command-line argument propagation to child processes.
>
> **Why:** Simply removing a flag like `-enable_collector` from `sys.argv`
> failed to disable the feature if the user passed it multiple times or in an
> unexpected format. Appending a definitive `false` flag leverages standard
> 'last flag wins' parsing. Failing to adhere to this typically results in
> **Undesired Feature Activation**.

**Trap 1: Attempting to disable a boolean feature by plucking its positive flag
out of a list.**

**Don't:**

```python
if "-enable_collector" in args:
    args.remove("-enable_collector")
```

**Do:**

```python
args.append("--enable_collector=false")
```

#### T1-08: Dynamic CLI Argument List Construction

> **Rule:** Must dynamically aggregate configuration arguments onto a base
> command list to avoid maintaining duplicate `subprocess` invocations.
>
> **What:** Subprocess execution lists must be constructed dynamically by
> appending optional arguments to a base list, rather than duplicating the
> entire `subprocess.Popen` block for each condition.
>
> **Applies To:** Any block constructing commands for `subprocess.run` or
> `subprocess.Popen`.
>
> **Why:** Branching execution paths for a single optional command-line flag led
> to logic duplication and an increased risk of divergent execution contexts.
> Failing to adhere to this typically results in **Code Duplication / Divergent
> Logic**.

**Trap 1: Duplicating the subprocess execution call just to append one flag.**

**Don't:**

```python
if sockets_file:
    subprocess.Popen([path, "cmd", "--opt", sockets_file])
else:
    subprocess.Popen([path, "cmd"])
```

**Do:**

```python
cmd = [path, "cmd"]
if sockets_file:
    cmd += ["--opt", sockets_file]
subprocess.Popen(cmd)
```

#### T1-09: Exit Code Validation for Subcommand Support

> **Rule:** Evaluate subcommand support strictly by validating the exact exit
> code of an active test invocation, never by searching standard output.
>
> **What:** Validate the support of a specific CLI subcommand by executing the
> help menu for that exact subcommand and checking the deterministic exit code,
> rather than executing a general help command and parsing the stdout string.
>
> **Applies To:** CLI flag propagation, wrapper script subcommand routing, and
> dynamic help parsing.
>
> **Why:** Checking if a subcommand string existed in the raw output of a
> general `help` command was brittle and prone to false positives if the target
> string accidentally matched a description or an unrelated flag name. Failing
> to adhere to this typically results in **False Positive Routing**.

**Trap 1: Grepping or substring matching against general CLI help text.**

**Don't:**

```python
def _is_subcommand_present(path: str, subc: str) -> bool:
    return subc in str(subprocess.check_output([path, "help"]))
```

**Do:**

```python
def _is_subcommand_present(path: str, subc: str) -> bool:
    # exit=0 if exists, exit!=0 otherwise
    return subprocess.call([path, "help", subc], stdout=subprocess.DEVNULL) == 0
```

#### T1-10: Strict Ordering Validation for CLI Argument Generation

> **Rule:** Always employ sequence-dependent assertions when validating
> deterministic argument construction arrays in unit tests.
>
> **What:** Unit tests verifying command-line argument generators must use
> strict ordered assertions (`assertEqual`) to ensure flags are injected with
> correct precedence, preventing overrides.
>
> **Applies To:** Test suites for wrapper scripts that parse and inject CLI
> flags.
>
> **Why:** Using unordered assertions allowed subtle bugs to pass CI, where
> automatically injected flags were placed in the wrong order relative to
> user-provided flags, breaking precedence configurations. Failing to adhere to
> this typically results in **Flag Precedence Violation**.

**Trap 1: Using unordered list comparisons to validate CLI argument lists.**

**Don't:**

```python
got = siso.apply_metrics_labels(args)
self.assertCountEqual(got, expected_args)
```

**Do:**

```python
got = siso.apply_metrics_labels(args)
self.assertEqual(got, expected_args) # Order matters
```

#### T1-11: Post-Subcommand Argument Injection

> **Rule:** Must isolate telemetry injections specifically to the subcommand's
> argument parameter space, bypassing the overarching global scope.
>
> **What:** Global flags and telemetry flags must be appended to the specific
> subcommand rather than the global binary invocation.
>
> **Applies To:** CLI Wrapper Scripts (e.g., siso.py) invoking underlying
> multi-command tools.
>
> **Why:** Injecting telemetry flags generally into the global execution space
> caused subcommands like `metrics summary` to crash because they lacked support
> for flags meant explicitly for the core build subcommand. Failing to adhere to
> this typically results in **Unrecognized Argument Crash**.

**Trap 1: Appending environment or telemetry flags blindly to the base tool
invocation.**

**Don't:**

```python
# BAD: Applying flags to the global invocation
new_args = global_flags
if should_collect_logs:
    new_args = apply_telemetry_flags(new_args)
new_args = apply_rc(new_args, subcmd_flags, args[1:])
```

**Do:**

```python
# GOOD: Applying flags explicitly to the subcommand block
new_args = apply_rc(global_flags, subcmd_flags, args[1:])
if subcmd == "ninja":
    if should_collect_logs:
        new_args = apply_telemetry_flags(new_args)
```

**Exceptions:** Flags that are universally supported by all subcommands (e.g.,
`--help` or generic authentication overrides).

#### T1-12: Tool-Specific Argument Interface Segregation

> **Rule:** Always sanitize and strip target-specific parameters before passing
> command lists directly to secondary legacy systems.
>
> **What:** Wrapper scripts that proxy requests to multiple underlying backends
> must explicitly strip tool-specific flags before passing arguments to legacy
> tools that do not support them.
>
> **Applies To:** CLI orchestration logic where a single frontend wrapper
> supports both legacy (Ninja) and modern (Siso) execution paths.
>
> **Why:** Passing `-o` or `--offline` arguments—which were intended strictly
> for managing the remote execution capabilities of the modern backend—to the
> legacy backend caused instant CLI parsing failures. Failing to adhere to this
> typically results in **Argument Parsing Error**.

**Trap 1: Passing raw `input_args` down to all execution paths
indiscriminately.**

**Don't:**

```python
# BAD: Blindly passing flags
ninja_args = ['ninja']
ninja_args.extend(input_args[1:])
```

**Do:**

```python
# GOOD: Stripping unsupported arguments for the legacy path
input_args = [arg for arg in input_args if arg not in ("-o", "--offline")]
ninja_args.extend(input_args[1:])
```

#### T1-13: Robust CLI Flag Detection via Assignment Syntax

> **Rule:** Must perform combined evaluations against both exact match
> signatures and `=` assignment declarations when inspecting arbitrary flag
> prefixes.
>
> **What:** Command-line parsers intercepting user arguments must check for both
> exact flag matches and prefix matches using the `=` assignment operator to
> prevent false positives.
>
> **Applies To:** Command-line parsing and argument interception routines.
>
> **Why:** The wrapper failed to inject required telemetry flags when a user
> passed unrelated flags that shared a prefix string (false positive), or it
> overwrote user-specified metadata when it failed to detect the `flag=value`
> notation. Failing to adhere to this typically results in **Missing Telemetry /
> Overwritten Config**.

**Trap 1: Using basic `startswith()` or `not in` checks that fail to account for
variable assignment syntaxes.**

**Don't:**

```python
# BAD: Misses -flag=value syntax, or triggers false positives on -flag_extended
if f"-{flag}" not in args and f"--{flag}" not in args:
    flag_to_add.append(f"--{flag}")
```

**Do:**

```python
# GOOD: Explicitly checking exact match or assignment suffix
for arg in args:
    if arg == f"-{flag}" or arg.startswith(f"-{flag}="):
        break
```

**Trap 2: Failing to account for both single-dash and double-dash conventions
when intercepting user flags.**

**Don't:**

```python
if arg == "--metrics_labels":
```

**Do:**

```python
if arg.startswith("--metrics_labels") or arg.startswith("-metrics_labels"):
```

#### T1-14: Robust Parsing of Directory Traversal (-C) Flags

> **Rule:** Avoid rigid offset assumptions; always bounds-check index queries
> when reading sequential flag properties.
>
> **What:** When parsing Ninja or Siso command-line arguments, the parser must
> correctly handle both space-separated and concatenated directory flag
> variants, enforcing strict bounds checking on trailing flags.
>
> **Applies To:** CLI Argument Parsing Modules (e.g., `ninja.py`,
> `autoninja.py`).
>
> **Why:** Refactoring the parsing logic introduced regressions where standard
> flags like `-Cout/Release` or a trailing detached `-C` flag caused empty
> directory resolution or unhandled IndexError crashes, breaking path-dependent
> telemetry and build systems. Failing to adhere to this typically results in
> **IndexError / Build Path Resolution Failure**.

**Trap 1: Assuming the change-directory flag is always followed by a
space-separated argument.**

**Don't:**

```python
if arg == "-C":
    out_dir = args[i+1]
```

**Do:**

```python
if arg == "-C" and i < len(args) - 1:
    out_dir = args[i+1]
elif arg.startswith("-C") and len(arg) > 2:
    out_dir = arg[2:]
```

**Trap 2: Throwing an IndexError if the flag is the final argument or
arbitrarily short-circuiting on short command lines.**

**Don't:**

```python
if len(args) < 3:
    return
# ... fails if `args` ends with [..., "-C"]
```

**Do:**

```python
# Remove arbitrary length checks and rely on strict bounds checking per flag.
if arg == "-C" and i < len(args) - 1:
    out_dir = args[i+1]
```

#### T1-15: Segregation of Global and Subcommand Flags in Configuration Files

> **Rule:** Maintain structural isolation between pre-flight wrapper context and
> discrete subcommand directives inside text-based parsers.
>
> **What:** Configuration parsers (like `.sisorc`) must structurally
> differentiate between global flags applied to the wrapper itself and
> subcommand-specific flags appended to underlying binary calls.
>
> **Applies To:** CLI Wrappers and Config File Parsers.
>
> **Why:** A `.sisorc` configuration syntax was designed to persist default
> execution flags. It mandated segregating flags starting with hyphens (global)
> from words (subcommand identifiers) to avoid polluting global execution states
> with incompatible subcommand arguments. Failing to adhere to this typically
> results in **Invalid CLI Argument Execution**.

**Trap 1: Blindly appending all parsed config file arguments into a single
global array applied universally to the command.**

**Don't:**

```python
# BAD: Mixing global wrapper flags and subcommand flags
with open(rcfile) as f:
    for line in f:
        args.extend(shlex.split(line))
```

**Do:**

```python
# GOOD: Segregating based on leading hyphens vs strings
with open(rcfile) as f:
    for line in f:
        args = shlex.split(line.strip())
        if line.startswith("-"):
            global_flags.extend(args)
        else:
            subcmd_flags[args[0]] = args[1:]
```

#### T1-16: Sequence-Dependent Evaluation of Build Override Flags

> **Rule:** Wait for external file system variables to finalize prior to
> interpreting overarching command-line behavioral negations.
>
> **What:** Global environment overrides (like offline modes) must be evaluated
> after all context-specific and project-level configurations have been fully
> parsed and finalized.
>
> **Applies To:** Command-line flag propagation, environment variable
> configuration, and build tool wrappers.
>
> **Why:** The `--offline` flag was intended to disable remote compilation.
> However, the logic checking this flag was placed before the script finished
> reading project-level build arguments. As a result, the offline override was
> either applied inconsistently or ignored entirely. Failing to adhere to this
> typically results in **Build Configuration Mismatch**.

**Trap 1: Setting override environment variables immediately upon parsing a
command-line flag, before the default tool states are finalized.**

**Don't:**

```python
# BAD: Evaluated before use_reclient is finalized from args.gn
if offline:
    os.environ["RBE_remote_disabled"] = "1"

use_reclient = _get_use_reclient_value(output_dir)
```

**Do:**

```python
# GOOD: Evaluated after all states are finalized
use_reclient = _get_use_reclient_value(output_dir)

if offline and use_reclient:
    os.environ["RBE_remote_disabled"] = "1"
```

#### T1-17: Selective Bypassing of Execution Wrappers for Local Sub-Commands

> **Rule:** Implement strict bypass thresholds, averting extensive network
> overhead routines when encountering localized single-function arguments (e.g.,
> `-t`).
>
> **What:** Build tool wrappers configured for remote execution must parse
> command line flags to detect and bypass remote proxy logic for local sub-tools
> (e.g., `-t` flags invoking native Ninja tools like `clean` or `deps`).
>
> **Applies To:** CLI argument passing and tool orchestration within
> `autoninja.py` and `ninja.py`.
>
> **Why:** When users executed utility tools (like `ninja -t clean`), the
> command was incorrectly routed through the Remote Build Execution (RBE)
> wrapper. This invoked unnecessary telemetry, authentication checks, and
> potential failures for commands that only manipulate local files. Failing to
> adhere to this typically results in **Remote Overhead / Hangs**.

**Trap 1: Applying remote execution wrappers unconditionally to all commands
passed to the build binary.**

**Don't:**

```python
# BAD: Unconditionally using the remote wrapper
if use_remoteexec:
    if use_reclient:
        return reclient_helper.run_siso(['siso', 'ninja'] + input_args)
```

**Do:**

```python
# GOOD: Detecting the local tool flag and bypassing the wrapper
if use_remoteexec:
    if use_reclient and not t_specified:
        return reclient_helper.run_siso(['siso', 'ninja'] + input_args)
```

**Exceptions:** Cloud logging might still be desired for local tools in the
future, requiring a separate 'online local' mode.

#### T1-18: Structured Subprocess Interrogation

> **Rule:** Must extract subprocess telemetry strictly via encoded dictionary
> objects over unstructured text pattern matching.
>
> **What:** Data extraction from external CLI utilities must utilize structured,
> machine-readable output formats (e.g., JSON) to maintain resilience against
> formatting changes in standard output streams.
>
> **Applies To:** Subprocess wrappers, identity and credential validation,
> parsing logic for tool integration.
>
> **Why:** Interrogating authentication utilities by parsing raw stdout lines
> and checking for specific prefixes proved highly fragile when the upstream
> utility modified its text output styling, leading to broken validation checks.
> Failing to adhere to this typically results in **Parsing Failure**.

**Trap 1: Splitting subprocess output by lines and using text-matching
heuristics to deduce programmatic state.**

**Don't:**

```python
# BAD: Relies on exact text phrasing and order
lines = process.stdout.splitlines()
if lines[0].startswith("Logged in as "):
    return True
```

**Do:**

```python
# GOOD: Request and parse a structured data schema
try:
    auth_data = json.loads(process.stdout)
    return auth_data.get("logged_in", False)
except json.JSONDecodeError:
    return False
```

**Exceptions:** Interfacing with legacy utilities that completely lack
structured output flags.

#### T1-19: Unified Build Invocation Correlation

> **Rule:** Pass subsystem traceability IDs entirely through cohesive
> environment declarations instead of explicit CLI payloads stringed together
> manually.
>
> **What:** Distinct tools executing within the same logical build pipeline must
> correlate telemetry using a standardized environment variable rather than
> relying on disparate, fragmented CLI flag propagation.
>
> **Applies To:** Build context managers (`reclient_helper.py`), tool execution
> wrappers (`autoninja`, `siso`).
>
> **Why:** Independent build backends were historically passed build IDs via
> specialized command-line flags, fracturing log correlation across complex
> hybrid build orchestrations (e.g., Siso running Ninja subsets). Failing to
> adhere to this typically results in **Orphaned Telemetry Logs**.

**Trap 1: Passing execution identifiers strictly via tool-specific CLI
arguments, leading to synchronization drift.**

**Don't:**

```python
# BAD: Hardcoding flag parameters per-tool
subprocess.run(["siso", f"-build_id={execution_id}"])
subprocess.run(["ninja"])
```

**Do:**

```python
# GOOD: Injecting standard environment variables across the pipeline
with build_context(invocation_id=execution_id):
    # Context manager sets os.environ["RBE_invocation_id"]
    subprocess.run(["siso"])
    subprocess.run(["ninja"])
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T5 | Declarative Build State Extraction - *Provides the
    finalized context flags (e.g., use_reclient) needed to evaluate conditional
    execution arguments.*
*   **Downstream:** T2 | Daemon Process Orchestration & Health Polling -
    *Receives the safely localized environment dictionary overrides and
    structured argument payloads initialized by the wrapper.*
*   **Downstream:** T4 | Identity & Telemetry Authorization - *Relies on
    accurate flag extraction to enable/disable telemetry without polluting
    upstream interfaces.*
*   **Downstream:** T7 | High-Fidelity Infrastructure Testing - *Enforces strict
    bounds and positional validation for the CLI parsers implemented in this
    domain.*

## Chapter: Daemon Process Orchestration & Health Polling

**Context:** This chapter defines the constraints for managing the lifecycle of
background sidecar processes and telemetry daemons. It mandates strict process
isolation, cross-platform health polling, and deterministic cleanup to prevent
global state pollution and orphaned processes.

### Summary

| Rule ID   | Principle /    | Priority | Primary Symptom / Trap          |
:           : Constraint     :          :                                 :
| :-------- | :------------- | :------- | :------------------------------ |
| **T2-01** | Windows Daemon | Medium   | Combining generic Windows       |
:           : Process        :          : detachment flags, inadvertently :
:           : Detachment     :          : rendering a visible terminal    :
:           : Optimization   :          : flash.                          :
| **T2-02** | Subprocess     | Medium   | Mutating `os.environ` directly  |
:           : Environment    :          : before invoking a child         :
:           : Variable       :          : process.                        :
:           : Isolation      :          :                                 :
| **T2-03** | Fail-Fast      | Medium   | Blindly waiting for the full    |
:           : Daemon Health  :          : timeout duration when a daemon  :
:           : Polling        :          : reports a permanent             :
:           :                :          : configuration error.            :
| **T2-04** | Daemon Process | High     | Starting a background daemon    |
:           : Decoupling and :          : without altering its process    :
:           : Signal         :          : group.                          :
:           : Isolation      :          :                                 :
| **T2-05** | Synchronous    | Medium   | Using a ThreadPoolExecutor      |
:           : Time-Bounded   :          : exclusively to bound the time   :
:           : Health Polling :          : of a background polling loop.   :
| **T2-06** | Strict Type    | High     | Accessing JSON dictionary items |
:           : Checking in    :          : via dot notation and comparing  :
:           : Health API     :          : literal booleans to strings.    :
:           : Payloads       :          :                                 :
| **T2-07** | Fail-Fast on   | Medium   | Blindly starting a new daemon   |
:           : Daemon         :          : process without verifying the   :
:           : Termination    :          : old one successfully            :
:           : Failure        :          : terminated.                     :
| **T2-08** | Explicit       | Medium   | Suppressing stdout but allowing |
:           : Silencing of   :          : standard error to inherit the   :
:           : Background     :          : parent's file descriptor.       :
:           : Daemon Output  :          :                                 :
| **T2-09** | Standard       | High     | Using external libraries like   |
:           : Library        :          : `psutil` to iterate over system :
:           : Utilities for  :          : processes and network           :
:           : Process        :          : connections.                    :
:           : Discovery      :          :                                 :
| **T2-10** | Explicit       | Medium   | Catching                        |
:           : Return Code    :          : `subprocess.CalledProcessError` :
:           : Evaluation for :          : for an expected non-zero exit   :
:           : Expected       :          : code.                           :
:           : Subprocess     :          :                                 :
:           : Failures       :          :                                 :
| **T2-11** | Cross-Platform | Medium   | Omitting the session detachment |
:           : Session        :          : flag out of fear of Windows     :
:           : Detachment for :          : incompatibility.                :
:           : Background     :          :                                 :
:           : Tasks          :          :                                 :

--------------------------------------------------------------------------------

### Rules

#### T2-01: Windows Daemon Process Detachment Optimization

> **Rule:** Must use `subprocess.CREATE_NO_WINDOW` instead of generic POSIX or
> grouped detachment flags to silently spawn background workers on Windows.
>
> **What:** Properly utilizing native `subprocess.Popen` process creation flags
> to spawn non-blocking daemon background workers silently on Windows without
> spawning disruptive terminal GUI artifacts.
>
> **Applies To:** Background telemetry collectors, daemon services, and detached
> subprocess invocation on `win32` platforms.
>
> **Why:** Background metrics workers spawned using POSIX patterns or specific
> Windows grouping flags like `DETACHED_PROCESS` caused brief console windows to
> 'flash' on the screen upon execution, distracting users. Furthermore, relying
> on POSIX variables like `start_new_session` falsely implied behavioral
> coverage on Windows, where they are actively ignored. Failing to adhere to
> this typically results in **GUI Artifact Flashing**.

**Trap 1: Combining generic Windows detachment flags, inadvertently rendering a
visible terminal flash.**

**Don't:**

```python
# BAD: Causes a visible window flash on Windows
creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
subprocess.Popen(cmd, creationflags=creationflags)
```

**Do:**

```python
# GOOD: Ensures the background process runs completely invisibly
creationflags = subprocess.CREATE_NO_WINDOW
subprocess.Popen(cmd, creationflags=creationflags)
```

**Trap 2: Conditionally setting platform-independent flags like
`start_new_session`, which litters code with unnecessary OS-checks.**

**Don't:**

```python
subprocess.Popen(cmd, start_new_session=(sys.platform != "win32"))
```

**Do:**

```python
# Standard library inherently ignores this on Windows
subprocess.Popen(cmd, start_new_session=True)
```

#### T2-02: Subprocess Environment Variable Isolation

> **Rule:** Always pass a localized `env` dictionary to subprocess calls rather
> than mutating the global `os.environ`.
>
> **What:** When injecting runtime configuration state into a background daemon
> or underlying build tool, pass a localized `env` dictionary to the execution
> call instead of mutating the global `os.environ`.
>
> **Applies To:** Process orchestration scripts spawning subprocesses (e.g.,
> launching an OpenTelemetry collector sidecar).
>
> **Why:** The script modified `os.environ` to set addresses for background
> daemon components. This created a risk of state leakage, potentially polluting
> the execution environment for other parallel tasks or wrapper logic. Failing
> to adhere to this typically results in **Global State Pollution**.

**Trap 1: Mutating `os.environ` directly before invoking a child process.**

**Don't:**

```python
# BAD: Modifies the environment globally for the parent Python process
os.environ["SISO_COLLECTOR_ADDRESS"] = f"unix://{sockets_file}"
subprocess.Popen(cmd)
```

**Do:**

```python
# GOOD: Localize the environment modifications to the subprocess
env = os.environ.copy()
env["SISO_COLLECTOR_ADDRESS"] = f"unix://{sockets_file}"
subprocess.Popen(cmd, env=env)
```

#### T2-03: Fail-Fast Daemon Health Polling

> **Rule:** Health polling loops must bypass timeout budgets and fail
> immediately upon detecting unrecoverable daemon configuration errors.
>
> **What:** Daemon polling loops must distinguish between transient
> initialization states (unhealthy/booting) and unrecoverable configuration
> errors. Unrecoverable states must bypass the timeout budget and fail
> immediately.
>
> **Applies To:** Sidecar lifecycle orchestration and health-polling loops.
>
> **Why:** The wrapper script suffered unnecessary delays because it waited out
> a full 1-second timeout loop even when the daemon explicitly reported a
> non-retriable, misconfigured endpoint. Failing to adhere to this typically
> results in **Unnecessary Initialization Latency**.

**Trap 1: Blindly waiting for the full timeout duration when a daemon reports a
permanent configuration error.**

**Don't:**

```python
while time.time() - start < 1:
    status = collector_status()
    if status == Status.HEALTHY:
        return True
    time.sleep(0.02)
return False
```

**Do:**

```python
while time.time() - start < 1:
    status = collector_status()
    if status == Status.HEALTHY:
        return True
    if status == Status.WRONG_ENDPOINT:
        return False # Fail-fast on non-retriable errors
    time.sleep(0.02)
return False
```

#### T2-04: Daemon Process Decoupling and Signal Isolation

> **Rule:** Always spawn background processes in a new process group or session
> to shield them from parent lifecycle signals.
>
> **What:** Background processes must be spawned in a new process group or
> session to prevent them from receiving lifecycle signals (like SIGINT/Ctrl+C)
> intended only for the parent.
>
> **Applies To:** Spawning background sidecar processes (e.g., telemetry
> collectors).
>
> **Why:** Background processes tied to the parent's process group would
> unexpectedly terminate when the developer interrupted the parent build script
> via the terminal. Failing to adhere to this typically results in **Premature
> Daemon Termination**.

**Trap 1: Starting a background daemon without altering its process group.**

**Don't:**

```python
subprocess.Popen(["collector", "--project", project])
```

**Do:**

```python
creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0
subprocess.Popen(cmd, start_new_session=True, creationflags=creationflags)
```

#### T2-05: Synchronous Time-Bounded Health Polling

> **Rule:** Implement daemon readiness probes as simple synchronous loops rather
> than using concurrency primitives for low-latency checks.
>
> **What:** Probing daemon readiness must be implemented as a simple,
> time-bounded synchronous loop rather than using heavy concurrency primitives
> like ThreadPoolExecutor, provided the expected latency is minimal (<50ms).
>
> **Applies To:** IPC daemon initialization and readiness probes.
>
> **Why:** Complex ThreadPoolExecutors were used solely for timeout enforcement.
> This caused testability friction and unnecessary overhead, which benchmarking
> proved was unwarranted since startup latency was virtually zero. Failing to
> adhere to this typically results in **Main Thread Hang / Testability
> Friction**.

**Trap 1: Using a ThreadPoolExecutor exclusively to bound the time of a
background polling loop.**

**Don't:**

```python
with ThreadPoolExecutor(max_workers=1) as executor:
    future = executor.submit(wait_until_online)
    return future.result(timeout=time_budget)
```

**Do:**

```python
start = time.time()
while time.time() - start < 1:
    if collector_status() == Status.HEALTHY:
        return True
    time.sleep(0.05)
return False
```

#### T2-06: Strict Type Checking in Health API Payloads

> **Rule:** You must parse JSON health responses using dictionary bracket
> notation and strictly evaluate explicit boolean types.
>
> **What:** JSON responses from health endpoints must be accessed via dictionary
> bracket notation and checked against exact boolean types, not strings.
>
> **Applies To:** Parsing JSON outputs from HTTP endpoints or daemon probes.
>
> **Why:** Comparing a JSON boolean property to a string (`"true"`), and
> accessing dictionary fields via attribute dot-notation, caused silent logic
> failures and runtime exceptions. Failing to adhere to this typically results
> in **AttributeError / False Status**.

**Trap 1: Accessing JSON dictionary items via dot notation and comparing literal
booleans to strings.**

**Don't:**

```python
status = json.loads(response.read())
if status.healthy != "true":
    return Status.UNHEALTHY
```

**Do:**

```python
status = json.loads(response.read())
if not status["healthy"]:
    return Status.UNHEALTHY
```

#### T2-07: Fail-Fast on Daemon Termination Failure

> **Rule:** Abort the initialization of new service instances if the
> orchestration script fails to forcefully kill existing unhealthy instances.
>
> **What:** Process orchestration scripts must abort starting a new service
> instance if they fail to gracefully or forcefully kill an existing unhealthy
> instance.
>
> **Applies To:** Process orchestration and lifecycle cleanup.
>
> **Why:** Ignoring the result of a process termination command led to multiple
> daemon instances attempting to bind to the same port or socket, causing
> undefined behavior. Failing to adhere to this typically results in **Port
> Conflict / Orphaned Processes**.

**Trap 1: Blindly starting a new daemon process without verifying the old one
successfully terminated.**

**Don't:**

```python
_kill_collector()
start_collector()
```

**Do:**

```python
if not _kill_collector():
    return False
start_collector()
```

#### T2-08: Explicit Silencing of Background Daemon Output

> **Rule:** Explicitly route both standard output and standard error to
> `DEVNULL` to prevent background tasks from polluting the parent terminal.
>
> **What:** Background processes and probing tools must explicitly suppress both
> stdout and stderr (by pointing them to DEVNULL) to prevent pollution of the
> parent terminal output.
>
> **Applies To:** Background telemetry collectors and subprocess probing
> functions.
>
> **Why:** Background tasks or internal existence checks (`subprocess.call`)
> wrote errors directly to standard output or standard error, injecting noisy
> artifacts into the user's build stream. Failing to adhere to this typically
> results in **Terminal Output Pollution**.

**Trap 1: Suppressing stdout but allowing standard error to inherit the parent's
file descriptor.**

**Don't:**

```python
subprocess.call([path, "help"], stdout=subprocess.DEVNULL)
```

**Do:**

```python
subprocess.call([path, "help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
```

**Trap 2: Routing daemon standard error into the parent's standard out/error
stream.**

**Don't:**

```python
subprocess.Popen(cmd, stderr=subprocess.STDOUT)
```

**Do:**

```python
subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
```

**Exceptions:** Debugging scenarios where the daemon fails to start and
diagnostic output is strictly necessary.

#### T2-09: Standard Library Utilities for Process Discovery

> **Rule:** Rely exclusively on standard library invocations of native OS tools
> rather than introducing third-party dependencies like `psutil`.
>
> **What:** Avoid third-party libraries (e.g., `psutil`) for process discovery
> in core build scripts. Rely on standard library `subprocess` calls to native
> OS tools (`lsof` on Unix-like systems, `netstat` and `taskkill` on Windows) to
> prevent virtual environment startup overhead.
>
> **Applies To:** Core build wrapper scripts (`autoninja.py`, `siso.py`,
> `ninja.py`) and background daemon health polling.
>
> **Why:** Introducing non-standard libraries required virtual environment
> (`vpython3`) initialization, which added severe startup latency to frequently
> invoked, critical-path build tools. Failing to adhere to this typically
> results in **Excessive Startup Latency**.

**Trap 1: Using external libraries like `psutil` to iterate over system
processes and network connections.**

**Don't:**

```python
import psutil

for pid in psutil.pids():
    proc = psutil.Process(pid)
    for conn in proc.net_connections(kind='inet'):
        if conn.laddr.port == 13133:
            proc.kill()
```

**Do:**

```python
import subprocess
import platform

if platform.system() in ["Linux", "Darwin"]:
    output = subprocess.run(['lsof', '-t', '-i:13133'], capture_output=True)
    # Parse output to get PIDs
```

#### T2-10: Explicit Return Code Evaluation for Expected Subprocess Failures

> **Rule:** Use `subprocess.run` and evaluate the `returncode` attribute
> directly for non-critical commands instead of wrapping calls in broad
> exception handlers.
>
> **What:** Use `subprocess.run` and evaluate the `returncode` attribute
> directly for non-critical system commands where failure is an expected state,
> rather than wrapping `subprocess.check_output` or `check=True` in broad
> exception handlers.
>
> **Applies To:** Subprocess execution, particularly daemon cleanup, teardowns,
> and health polling tasks.
>
> **Why:** Using exceptions for expected control flows (e.g., attempting to kill
> a process that has already terminated) caused overly broad `try/except` scopes
> that masked unrelated logic bugs and silently swallowed fatal environmental
> errors. Failing to adhere to this typically results in **Silent Logic
> Masking**.

**Trap 1: Catching `subprocess.CalledProcessError` for an expected non-zero exit
code.**

**Don't:**

```python
try:
    subprocess.check_output(['lsof', '-t', '-i:13133'])
except subprocess.CalledProcessError:
    return # Process not found
```

**Do:**

```python
output = subprocess.run(['lsof', '-t', '-i:13133'], capture_output=True)
if output.returncode != 0:
    print(f"Warning: failed to fetch processes: {output.stderr}")
    return
```

#### T2-11: Cross-Platform Session Detachment for Background Tasks

> **Rule:** Always utilize `start_new_session=True` unconditionally across all
> platforms when orchestrating background tasks intended to survive the parent.
>
> **What:** Background processes (such as telemetry uploaders) spawned by a CLI
> tool must utilize `start_new_session=True` via `subprocess.Popen` to ensure
> they survive the termination of the parent process, without conditionally
> excluding Windows.
>
> **Applies To:** Daemon process orchestration, specifically logging and
> telemetry uploaders executed after the main tool finishes.
>
> **Why:** Background log uploaders were tied to the parent's process session.
> If the user interrupted the build tool, the uploader died. Reviewers validated
> that `start_new_session=True` functions safely on Windows as well as POSIX
> systems, eliminating the need for conditional logic. Failing to adhere to this
> typically results in **Orphaned Processes / Lost Telemetry**.

**Trap 1: Omitting the session detachment flag out of fear of Windows
incompatibility.**

**Don't:**

```python
# BAD: Uploader dies if parent receives SIGINT
subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
```

**Do:**

```python
# GOOD: Safely detach session on all platforms
subprocess.Popen(
    cmd,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True
)
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T4 | Identity & Telemetry Authorization - *Execution
    environment authorization dictates whether background telemetry daemons are
    spawned.*
*   **Downstream:** T3 | IPC Socket Safety & Constraints - *Daemon lifecycle
    directly dictates the creation and cleanup lifecycle of their backing IPC
    Unix domain sockets.*

## Chapter: IPC Socket Safety & Constraints

**Context:** This chapter governs the lifecycle, security, and cleanup of Unix
domain sockets used for inter-process communication. It establishes strict
constraints for OS-level path length limits, user-specific isolation, and
resilient cleanup mechanisms to prevent stale artifacts and binding failures.

### Summary

| Rule ID   | Principle /        | Priority | Primary Symptom / Trap   |
:           : Constraint         :          :                          :
| :-------- | :----------------- | :------- | :----------------------- |
| **T3-01** | Protocol Prefix    | Medium   | Attempting to execute    |
:           : Stripping for File :          : file system operations   :
:           : Operations         :          : directly on a URI        :
:           :                    :          : containing a protocol    :
:           :                    :          : prefix.                  :
| **T3-02** | Resilient IPC      | Medium   | Performing strict        |
:           : Socket Path        :          : equality checks on IPC   :
:           : Verification       :          : endpoints that might     :
:           :                    :          : inconsistently drop      :
:           :                    :          : protocol prefixes.       :
| **T3-03** | Stale IPC Socket   | High     | Starting an IPC daemon   |
:           : Purging Prior to   :          : without proactively      :
:           : Initialization     :          : unlinking stale socket   :
:           :                    :          : files left behind by     :
:           :                    :          : crashed executions.      :
| **T3-04** | Singleton IPC      | Critical | Using relative,          |
:           : Socket Path        :          : build-directory-specific :
:           : Normalization &    :          : paths for socket         :
:           : Permissions        :          : communication with a     :
:           :                    :          : singleton sidecar, or    :
:           :                    :          : granting world access to :
:           :                    :          : the directory.           :
| **T3-05** | Explicit URI       | High     | Passing raw file paths   |
:           : Scheme for Unix    :          : to a service expecting a :
:           : Domain Sockets     :          : dialable endpoint        :
:           :                    :          : format.                  :
| **T3-06** | User-Specific IPC  | High     | Using a hardcoded,       |
:           : Socket Isolation   :          : global path for          :
:           : and Path Length    :          : temporary IPC sockets    :
:           : Limits             :          : without considering      :
:           :                    :          : multi-tenancy.           :
| **T3-07** | Pre-Initialization | High     | Using `isfile` to detect |
:           : Stale Socket       :          : stale socket objects.    :
:           : Cleanup            :          :                          :

--------------------------------------------------------------------------------

### Rules

#### T3-01: Protocol Prefix Stripping for File Operations

> **Rule:** Always strip URI protocol prefixes (like `unix://`) from endpoint
> strings before attempting OS-level file system operations.
>
> **What:** When cleaning up or interacting with Unix domain sockets via file
> system APIs, URI protocol prefixes (like `unix://`) must be explicitly
> stripped from endpoint strings.
>
> **Applies To:** Inter-process communication setup involving Unix domain
> sockets and OS-level file manipulation.
>
> **Why:** The cleanup routine was mistakenly passed the full gRPC endpoint URI.
> Because the file system path retained the `unix://` prefix, the stale socket
> file was never found or deleted, blocking new bind attempts. Failing to adhere
> to this typically results in **Stale Socket Leak**.

**Trap 1: Attempting to execute file system operations directly on a URI
containing a protocol prefix.**

**Don't:**

```python
if os.path.exists(expected_endpoint):
    os.remove(expected_endpoint)
```

**Do:**

```python
if os.path.exists(sockets_file := expected_endpoint.removeprefix("unix://")):
    os.remove(sockets_file)
```

#### T3-02: Resilient IPC Socket Path Verification

> **Rule:** Must use suffix matching (`endswith`) instead of exact string
> equality when verifying configured IPC endpoints.
>
> **What:** Health checks comparing configured IPC endpoints against active
> listening endpoints must use suffix matching (`endswith`) instead of exact
> string equality due to inconsistent protocol prefix handling across standard
> libraries.
>
> **Applies To:** Health-checking services that communicate over Unix domain
> sockets.
>
> **Why:** A discrepancy between how the gRPC framework requires socket strings
> (`unix://...`) and how the internal health API reports them (without
> `unix://`) caused valid running sidecars to be incorrectly flagged as broken.
> Failing to adhere to this typically results in **False-Negative Health
> Check**.

**Trap 1: Performing strict equality checks on IPC endpoints that might
inconsistently drop protocol prefixes.**

**Don't:**

```python
if endpoint != expected_endpoint:
    return Status.WRONG_ENDPOINT
```

**Do:**

```python
# Collector is liable to drop unix:// part from socks.
if not expected_endpoint.endswith(endpoint):
    return Status.WRONG_ENDPOINT
```

#### T3-03: Stale IPC Socket Purging Prior to Initialization

> **Rule:** Always proactively check for and unlink stale socket files at the
> target path before spawning an IPC daemon.
>
> **What:** Before attempting to spawn a daemon that listens on a Unix domain
> socket, the orchestrating script must proactively check for and remove any
> stale socket files at the target path.
>
> **Applies To:** Orchestrating daemons or services that bind to static
> file-based Unix sockets.
>
> **Why:** If an old process crashed without cleaning up its Unix domain socket,
> the new process would hit an "Address already in use" error. Adding proactive
> unlinking stabilized daemon restarts. Failing to adhere to this typically
> results in **Bind Failure / Address In Use**.

**Trap 1: Starting an IPC daemon without proactively unlinking stale socket
files left behind by crashed executions.**

**Don't:**

```python
cmd = [siso_path, "collector", "--otel_socket", sockets_file]
subprocess.Popen(cmd, ...)
```

**Do:**

```python
if os.path.isfile(sockets_file) or os.path.islink(sockets_file):
    try:
        os.remove(sockets_file)
    except OSError as e:
        # Emit error to stderr and fail fast or fall back
cmd = [siso_path, "collector", "--otel_socket", sockets_file]
subprocess.Popen(cmd, ...)
```

#### T3-04: Singleton IPC Socket Path Normalization & Permissions

> **Rule:** Must isolate singleton Unix domain sockets in shared, OS-agnostic
> temporary directories with strict `0o700` user-only permissions.
>
> **What:** For sidecar daemons that must act as singletons (due to port
> limitations), Unix domain sockets must be placed in a shared, OS-agnostic
> temporary directory (e.g., `/tmp/<user>/`) with strict `0o700` user-only
> permissions, rather than placed in ephemeral build directories.
>
> **Applies To:** Multi-user build environments utilizing sidecar daemons for
> telemetry or caching.
>
> **Why:** Sockets were initially placed in per-build output directories
> (`out/Default/otel.sock`), leading to redundant collector restarts across
> projects, port conflicts, and security concerns with overly permissive file
> modes (0o777). Failing to adhere to this typically results in **Port
> Contention / Privilege Escalation**.

**Trap 1: Using relative, build-directory-specific paths for socket
communication with a singleton sidecar, or granting world access to the
directory.**

**Don't:**

```python
path = os.path.abspath(out_dir)
os.makedirs(path, mode=0o777, exist_ok=True)
sockets_file = os.path.join(path, "otel_collector.sock")
```

**Do:**

```python
path = os.path.join("/tmp", getpass.getuser(), "siso")
os.makedirs(path, mode=0o700, exist_ok=True)
sockets_file = os.path.join(path, f"{project}.sock")
```

#### T3-05: Explicit URI Scheme for Unix Domain Sockets

> **Rule:** Always prefix socket file paths explicitly with their transport
> protocol scheme (e.g., `unix://`) for networking or IPC configuration flags.
>
> **What:** Socket file paths passed to networking or IPC configuration flags
> must be explicitly prefixed with their respective transport protocol scheme.
>
> **Applies To:** Command-line argument generation for background telemetry
> daemons and IPC services.
>
> **Why:** Dialing logic could misinterpret raw file paths as TCP endpoints if
> not explicitly prefixed, leading to IPC connection failures. Failing to adhere
> to this typically results in **IPC Connection Failure**.

**Trap 1: Passing raw file paths to a service expecting a dialable endpoint
format.**

**Don't:**

```python
args.append(f"--collector_address={sockets_file}")
```

**Do:**

```python
args.append(f"--collector_address=unix://{sockets_file}")
```

#### T3-06: User-Specific IPC Socket Isolation and Path Length Limits

> **Rule:** Must dynamically enforce OS-level path length constraints and
> isolate sockets per user to prevent binding failures and naming collisions.
>
> **What:** Unix domain sockets must be isolated per user with restricted
> permissions (0o700) and must dynamically respect OS-level path length
> constraints (max 104-108 chars).
>
> **Applies To:** Unix domain socket creation on shared Unix/Linux/macOS
> systems.
>
> **Why:** Using global directories (`/tmp`) caused naming collisions and
> permission conflicts between users. Furthermore, constructing long socket
> paths caused the OS to silently truncate the address or fail binding. Failing
> to adhere to this typically results in **Socket Binding Failure / Permission
> Denied**.

**Trap 1: Using a hardcoded, global path for temporary IPC sockets without
considering multi-tenancy.**

**Don't:**

```python
# BAD: Global path without user isolation
path = "/tmp"
os.makedirs(path, mode=0o777, exist_ok=True)
sockets_file = os.path.join(path, "otel_collector.sock")
```

**Do:**

```python
# GOOD: User-specific subdirectory with restricted permissions
user = getpass.getuser()
path = os.path.join("/tmp", user, "siso")
os.makedirs(path, mode=0o700, exist_ok=True)
```

**Trap 2: Blindly constructing socket paths without calculating or enforcing the
OS-level socket path length limits.**

**Don't:**

```python
# BAD: Project name could push path over the ~104 char limit
sockets_file = os.path.join(path, f"{project}.sock")
```

**Do:**

```python
# GOOD: Dynamically calculate remaining buffer and slice identifier
allowed_length = 104 - len(path) - 6
sockets_file = os.path.join(path, f"{project[:allowed_length]}.sock")
```

#### T3-07: Pre-Initialization Stale Socket Cleanup

> **Rule:** Always use `os.path.exists()` exclusively within the daemon startup
> branch to detect and actively clean up stale Unix domain socket files.
>
> **What:** Stale Unix domain socket files must be actively cleaned up
> immediately before spawning a new daemon instance. Validation checks must use
> `os.path.exists()`, not `os.path.isfile()`.
>
> **Applies To:** Daemon startup sequences that bind to a local Unix domain
> socket.
>
> **Why:** Leftover socket files from abnormally terminated previous runs
> prevented new daemons from binding. Using `os.path.isfile()` silently bypassed
> the cleanup step entirely because sockets are not regular files. Failing to
> adhere to this typically results in **Address Already In Use**.

**Trap 1: Using `isfile` to detect stale socket objects.**

**Don't:**

```python
if os.path.isfile(sockets_file):
    os.remove(sockets_file)
```

**Do:**

```python
if os.path.exists(sockets_file):
    os.remove(sockets_file)
```

**Trap 2: Cleaning up the socket file globally during path resolution, risking
deletion of an active socket used by a healthy daemon.**

**Don't:**

*   Execute socket file deletion synchronously during the command-line argument
    parsing phase.

**Do:**

*   Execute socket file deletion exclusively inside the daemon startup execution
    branch, immediately before invoking `subprocess.Popen`.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | CLI Flag Propagation & Order Resolution - *Command-line
    argument parsing dictates how IPC endpoint URIs are initially ingested and
    passed to sidecar binaries.*
*   **Downstream:** T2 | Daemon Process Orchestration & Health Polling - *Socket
    initialization directly unblocks daemon startup routines and health polling
    checks.*

## Chapter: Identity & Telemetry Authorization

**Context:** Enforce strict execution boundaries to safely govern telemetry
tracking, ensuring user privacy and robust multi-factor authentication. Must
mandate explicit opt-ins, fail silently for unauthenticated contributors, and
encapsulate state across process boundaries to prevent UI clutter and data
leakage.

### Summary

| Rule ID   | Principle /       | Priority | Primary Symptom / Trap            |
:           : Constraint        :          :                                   :
| :-------- | :---------------- | :------- | :-------------------------------- |
| **T4-01** | Multi-Factor      | Medium   | Assuming a valid corporate email  |
:           : Corporate         :          : suffix guarantees the execution   :
:           : Environment       :          : environment is a fully managed    :
:           : Detection         :          : corporate host.                   :
| **T4-02** | Multi-Tiered      | Critical | Failing to check environment      |
:           : Resolution for    :          : variables as a fallback source of :
:           : Cloud Telemetry   :          : truth for telemetry routing.      :
:           : Project Flags     :          :                                   :
| **T4-03** | Telemetry State   | High     | Relying on global method calls in |
:           : Encapsulation     :          : both the parent and child script, :
:           : Across Process    :          : causing isolated state            :
:           : Boundaries        :          : initialization.                   :
| **T4-04** | Canonicalization  | Medium   | Directly injecting raw platform   |
:           : of                :          : library outputs into telemetry    :
:           : Platform-Specific :          : payloads.                         :
:           : Telemetry         :          :                                   :
:           : Metadata          :          :                                   :
| **T4-05** | Safe Standard     | High     | Emitting errors during early      |
:           : Error Emission    :          : OS-level resource fetching using  :
:           : During Early      :          : the standard logging framework.   :
:           : Telemetry         :          :                                   :
:           : Initialization    :          :                                   :
| **T4-06** | Explicit Bot      | Medium   | Adding new build lab network      |
:           : Opt-In for        :          : domains to a static authorization :
:           : Telemetry         :          : allowlist for telemetry           :
:           : Authorization     :          : collection.                       :
| **T4-07** | Lightweight       | High     | Bootstrapping an entire virtual   |
:           : Authentication    :          : environment and importing heavy   :
:           : Validation for    :          : external libraries to execute     :
:           : Build Wrappers    :          : simple identity validation.       :
| **T4-08** | Unconditional     | Medium   | Placing user cohort identity      |
:           : Access to         :          : checks at the very beginning of a :
:           : Telemetry Opt-Out :          : script, effectively hiding        :
:           :                   :          : utility subcommands from certain  :
:           :                   :          : users.                            :
| **T4-09** | Silent Failure    | Medium   | Calling external authentication   |
:           : for Background    :          : binaries for optional background  :
:           : Telemetry         :          : telemetry without intercepting    :
:           : Authentication    :          : and suppressing stderr.           :
| **T4-10** | Path-Aware        | Critical | Employing standard string         |
:           : Telemetry Data    :          : `.replace()` methods to strip out :
:           : Redaction         :          : short dynamic strings like local  :
:           :                   :          : user identifiers across broad     :
:           :                   :          : data payloads.                    :
| **T4-11** | Forced Re-Consent | High     | Appending newly tracked variables |
:           : for Telemetry     :          : to the analytics payload without  :
:           : Payload Expansion :          : invalidating prior user opt-in    :
:           :                   :          : agreements.                       :

--------------------------------------------------------------------------------

### Rules

#### T4-01: Multi-Factor Corporate Environment Detection

> **Rule:** Must verify the host machine configuration (e.g., `gcert`) in
> addition to user identity before activating internal-only telemetry features.
>
> **What:** Telemetry collection and features intended strictly for internal
> corporate use must verify the host machine configuration (e.g., checking for
> `gcert`) in addition to user identity.
>
> **Applies To:** Telemetry authorization flags and identity verification
> scripts.
>
> **Why:** Relying solely on a specific email suffix falsely activated telemetry
> logic on corporate employees' personal, unmanaged machines, degrading the
> developer experience with unexpected error logs. Failing to adhere to this
> typically results in **Erroneous Telemetry Logs**.

**Trap 1: Assuming a valid corporate email suffix guarantees the execution
environment is a fully managed corporate host.**

**Don't:**

```python
def is_corp_environment(self):
    return self.user.endswith("@google.com")
```

**Do:**

```python
def is_corp_environment(self):
    return self.user.endswith("@google.com") and shutil.which("gcert") is not None
```

--------------------------------------------------------------------------------

#### T4-02: Multi-Tiered Resolution for Cloud Telemetry Project Flags

> **Rule:** Must resolve destination metrics projects using a strict fallback
> priority sequence to prevent routing data to unauthorized endpoints.
>
> **What:** Dynamic telemetry injection must resolve the destination metrics
> project using a strict priority fallback: 1) direct metrics environment
> variable, 2) direct metrics flag, 3) fallback general project flag, 4)
> fallback general project environment variable.
>
> **Applies To:** Identity and telemetry authorization logic
> (`apply_telemetry_flags`).
>
> **Why:** A regression occurred when the script began automatically appending
> cloud telemetry flags to older binaries without properly inheriting the
> general project identity. This resulted in the metrics being sent to an
> unauthorized default project endpoint. Failing to adhere to this typically
> results in **RPC PermissionDenied Error**.

**Trap 1: Failing to check environment variables as a fallback source of truth
for telemetry routing.**

**Don't:**

```python
if known_args.project:
    flags.append(f"--metrics_project={known_args.project}")
# Missing environment variable fallback entirely
return flags
```

**Do:**

```python
if known_args.project:
    flags.append(f"--metrics_project={known_args.project}")
elif project_env_var in env:
    flags.append(f"--metrics_project={env[project_env_var]}")
return flags
```

--------------------------------------------------------------------------------

#### T4-03: Telemetry State Encapsulation Across Process Boundaries

> **Rule:** Always load privacy opt-in states once and pass them via dependency
> injection to prevent redundant cross-process evaluations.
>
> **What:** Privacy opt-in states and consent notices must be loaded once and
> passed down via dependency injection to avoid redundant executions and
> duplicated warnings.
>
> **Applies To:** Telemetry initialization and logging modules invoked across
> multiple processes (wrapper -> build tool).
>
> **Why:** Calling the telemetry enablement checker independently across the
> wrapper script and the spawned subprocess resulted in the privacy notice being
> printed to the developer's terminal multiple times per build. Failing to
> adhere to this typically results in **Duplicate UI Clutter**.

**Trap 1: Relying on global method calls in both the parent and child script,
causing isolated state initialization.**

**Don't:**

```python
# BAD: Calling initialization in both files
# autoninja.py
if build_telemetry.enabled():
    should_collect_logs = True

# siso.py
def main(args):
    if build_telemetry.enabled():
        apply_telemetry_flags()
```

**Do:**

```python
# GOOD: Injecting state configuration
# autoninja.py
telemetry_cfg = build_telemetry.load_config()
siso.main(args, telemetry_cfg)

# siso.py
def main(args, telemetry_cfg):
    if telemetry_cfg and telemetry_cfg.enabled():
        apply_telemetry_flags()
```

--------------------------------------------------------------------------------

#### T4-04: Canonicalization of Platform-Specific Telemetry Metadata

> **Rule:** Must normalize raw OS and architecture strings into a canonical
> taxonomy before injecting them into observability payloads.
>
> **What:** Operating system and host architecture strings extracted from system
> libraries must be normalized into standard, canonical formats before being
> injected into observability metadata.
>
> **Applies To:** Telemetry tracking logic and environment variable detection
> components.
>
> **Why:** Raw outputs from Python's platform module caused fragmentation in the
> monitoring dashboards, generating distinct metrics categories for identical
> platforms (e.g., 'Darwin' vs 'mac', 'Linux' vs 'linux'). Failing to adhere to
> this typically results in **Fragmented Telemetry Data**.

**Trap 1: Directly injecting raw platform library outputs into telemetry
payloads.**

**Don't:**

```python
# BAD: Raw un-normalized OS string
result.append(f"host_os={platform.system()}")
```

**Do:**

```python
# GOOD: Using a canonicalization dictionary
system_dict = {"Windows": "windows", "Darwin": "mac", "Linux": "linux"}
user_system = system_dict.get(platform.system(), platform.system())
result.append(f"host_os={user_system}")
```

--------------------------------------------------------------------------------

#### T4-05: Safe Standard Error Emission During Early Telemetry Initialization

> **Rule:** Avoid using the standard logging framework during early system
> resource initialization; always write errors directly to `sys.stderr`.
>
> **What:** System resource detection and early telemetry setup code must avoid
> relying on the standard `logging` module to report errors, favoring direct
> writes to `sys.stderr`.
>
> **Applies To:** Telemetry Initialization modules (`infra_lib/telemetry`),
> System Resource Detectors.
>
> **Why:** Using standard warning loggers during early process initialization
> caused issues because the logging subsystem itself could be uninitialized,
> inappropriately routed, or circularly dependent on the telemetry system
> currently being configured. Failing to adhere to this typically results in
> **Deadlock / Circular Dependency Crash**.

**Trap 1: Emitting errors during early OS-level resource fetching using the
standard logging framework.**

**Don't:**

```python
try:
    contents = PROC_MEMINFO_PATH.read_text(encoding="utf-8")
except OSError as e:
    logging.warning("Encountered an issue reading /proc/meminfo: %s", e)
```

**Do:**

```python
try:
    contents = PROC_MEMINFO_PATH.read_text(encoding="utf-8")
except OSError as e:
    print("Encountered an issue reading /proc/meminfo: %s" % e, file=sys.stderr)
```

--------------------------------------------------------------------------------

#### T4-06: Explicit Bot Opt-In for Telemetry Authorization

> **Rule:** Never hardcode specific lab domain suffixes to authorize bot
> telemetry; mandate explicit programmatic flags instead.
>
> **What:** Authorization for telemetry collection on automated CI bots must
> rely on explicit command-line or configuration flags rather than hardcoding
> lab domain suffixes.
>
> **Applies To:** Telemetry Enablement Logic, Build Recipes, and Bot
> Provisioning.
>
> **Why:** Engineers attempted to add specific testing lab domains to a static
> authorization allowlist, but this was blocked because network topologies
> change frequently, making hardcoded domains difficult to discover and
> maintain. Failing to adhere to this typically results in **Missing Telemetry /
> Maintenance Overhead**.

**Trap 1: Adding new build lab network domains to a static authorization
allowlist for telemetry collection.**

**Don't:**

```python
# BAD: Hardcoding specific lab subdomains
_GOOGLE_HOSTNAME_SUFFIX = ('.google.com', '.golo.chromium.org')
```

**Do:**

*   Provide an explicit CLI flag (e.g., `--bot-enable`) in the automated recipe
    that programmatically overrides the hostname check.

--------------------------------------------------------------------------------

#### T4-07: Lightweight Authentication Validation for Build Wrappers

> **Rule:** Avoid bootstrapping heavy virtual python environments for simple
> authentication checks; prefer lightweight system binary executions.
>
> **What:** Core build wrapper scripts should avoid relying on heavy virtual
> environments (e.g., `vpython`) or heavy external libraries for authentication
> checks to minimize startup latency and dependency fragility.
>
> **Applies To:** Build invocation scripts (`autoninja.py`), dependency
> configuration files (`.vpython3`), pre-flight authentication validators.
>
> **Why:** Using a virtual python environment to pull down complex
> authentication libraries just to verify user status added noticeable startup
> latency, polluted local caching, and introduced unnecessary wheel
> dependencies. Failing to adhere to this typically results in **High Startup
> Latency**.

**Trap 1: Bootstrapping an entire virtual environment and importing heavy
external libraries to execute simple identity validation.**

**Don't:**

```python
# BAD: Heavy dependencies imported for simple verification
import google.auth
credentials, project = google.auth.default()
```

**Do:**

```python
# GOOD: Using standard python3 and lightweight process checks
import subprocess
result = subprocess.run(['gcertstatus'], capture_output=True)
if result.returncode == 0:
    # Proceed as authenticated
```

--------------------------------------------------------------------------------

#### T4-08: Unconditional Access to Telemetry Opt-Out

> **Rule:** Must evaluate configuration-mutating command handlers before
> enforcing any identity-based early returns.
>
> **What:** Command-line handlers that mutate user preferences (such as metrics
> opt-outs) must be evaluated prior to any identity-based early exits to ensure
> preference persistence works for all user cohorts.
>
> **Applies To:** CLI argument parsing for telemetry scripts, configuration file
> writers, privacy modules.
>
> **Why:** An early-return check designed to bypass metrics collection for
> external users inadvertently blocked those users from accessing the `opt-out`
> subcommand, causing the tool to re-evaluate and write files redundantly on
> every run. Failing to adhere to this typically results in **Redundant State
> Evaluation**.

**Trap 1: Placing user cohort identity checks at the very beginning of a script,
effectively hiding utility subcommands from certain users.**

**Don't:**

```python
# BAD: Blocks unauthenticated users from using preference subcommands
if not is_internal_user():
    return

if command == 'opt-out':
    save_preference_and_exit()
```

**Do:**

```python
# GOOD: Handle user intent first, then enforce execution bounds
if command == 'opt-out':
    save_preference_and_exit()

if not is_internal_user():
    return
```

**Exceptions:** Commands that structurally require privileged network access to
execute properly.

--------------------------------------------------------------------------------

#### T4-09: Silent Failure for Background Telemetry Authentication

> **Rule:** Always suppress background subprocess standard error emissions
> during optional authentication checks.
>
> **What:** Background subprocesses executing optional authentication checks for
> telemetry must pipe standard error to `DEVNULL` to avoid corrupting standard
> user workflows with irrelevant warnings.
>
> **Applies To:** Identity checks, subprocess invocations for optional tooling
> dependencies, CLI output managers.
>
> **Why:** Background checks validating user authentication status for optional
> metric reporting spammed the terminals of non-authenticated contributors with
> 'Not logged in' errors, severely degrading their toolchain experience. Failing
> to adhere to this typically results in **Terminal Output Pollution**.

**Trap 1: Calling external authentication binaries for optional background
telemetry without intercepting and suppressing stderr.**

**Don't:**

```python
# BAD: Leaks expected, harmless authentication failures to user stdout/stderr
try:
    subprocess.run(['auth-tool', 'status'], check=True)
except subprocess.CalledProcessError as e:
    print(f"WARNING: Failed to auth: {e}")
```

**Do:**

```python
# GOOD: Ensure optional checks fail silently without spamming the user
subprocess.run(
    ['auth-tool', 'status'],
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL
)
```

**Exceptions:** Explicitly requested authentication subcommands (e.g., `login`
or `status`) where the user initiated the action.

--------------------------------------------------------------------------------

#### T4-10: Path-Aware Telemetry Data Redaction

> **Rule:** Must use strict string boundaries or regex matching when redacting
> PII to prevent accidental collateral replacements.
>
> **What:** When scrubbing Personally Identifiable Information (PII) like
> usernames from telemetry payloads, the redaction logic must enforce string
> boundaries or use path-aware matching to avoid corrupting legitimate data.
>
> **Applies To:** Telemetry log serializers, PII scrubbers, build configuration
> extractors.
>
> **Why:** A naive global substring replacement meant to mask user identities
> accidentally replaced single letters inside unrelated configuration strings if
> the local machine had a single-character username, mutating analytical data
> destructively. Failing to adhere to this typically results in **Telemetry Data
> Corruption**.

**Trap 1: Employing standard string `.replace()` methods to strip out short
dynamic strings like local user identifiers across broad data payloads.**

**Don't:**

```python
# BAD: Replaces partial strings blindly
config_value = config_value.replace(os.getlogin(), "$USER")
# If username is "r", "release" becomes "$USERelease"
```

**Do:**

```python
# GOOD: Match using regex word boundaries to prevent collateral replacements
import re
username = re.escape(os.getlogin())
config_value = re.sub(rf'\b{username}\b', "$USER", config_value)
```

--------------------------------------------------------------------------------

#### T4-11: Forced Re-Consent for Telemetry Payload Expansion

> **Rule:** Must increment the telemetry schema version forcibly triggering user
> re-consent whenever new fields are appended to the collected payload.
>
> **What:** Adding new programmatic fields, experiment flags, or environment
> variables to telemetry collection mandates a telemetry version bump to
> forcibly trigger re-consent prompts for existing users.
>
> **Applies To:** Telemetry infrastructure (`metrics_utils.py`), client-side
> data schema versioning.
>
> **Why:** When developers attempted to silently piggyback on existing telemetry
> payloads to track new experiment flags via environment variables, reviewers
> required a schema version increment to ensure informed user consent. Failing
> to adhere to this typically results in **Unconsented Data Collection**.

**Trap 1: Appending newly tracked variables to the analytics payload without
invalidating prior user opt-in agreements.**

**Don't:**

```python
# BAD: Adding fields without notifying users
CURRENT_VERSION = 2
def get_metrics():
    return {"base": data, "new_experiment_flags": get_flags()}
```

**Do:**

```python
# GOOD: Increment version and clearly state the new collection scope
CURRENT_VERSION = 3
def get_consent_text(version):
    if version == 3:
        return ["We will start collecting metrics for experiment flags."]
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Downstream:** T1 | CLI Flag Propagation & Order Resolution - *Resolved
    telemetry configuration endpoints and opt-in status flags must be safely
    parsed and dynamically appended to underlying build tools.*

## Chapter: Declarative Build State Extraction

**Context:** Build orchestration mechanisms must deterministically extract
execution strategies from declarative configuration files rather than
imperatively executing external scripts. This ensures robust environment
initialization, eliminates silent configuration fallbacks, and prevents
cascading failures in uninitialized tool states.

### Summary

| Rule ID   | Principle / Constraint    | Priority | Primary Symptom / Trap    |
| :-------- | :------------------------ | :------- | :------------------------ |
| **T5-01** | Hardcoded Build Strategy  | High     | Relying on manual text    |
:           : Resolution Over Brittle   :          : parsing of external build :
:           : File Parsing              :          : definition files to set   :
:           :                           :          : internal script execution :
:           :                           :          : behavior.                 :
| **T5-02** | Comment-Aware Declarative | High     | Matching target variable  |
:           : Configuration Parsing     :          : names in a file           :
:           :                           :          : line-by-line without      :
:           :                           :          : respecting the specific   :
:           :                           :          : syntax's comment          :
:           :                           :          : character.                :
| **T5-03** | Graceful Fallback for     | Medium   | Assuming the              |
:           : Uninitialized Build Tool  :          : tool-selection state flag :
:           : State                     :          : is always set during      :
:           :                           :          : standard build            :
:           :                           :          : initialization before     :
:           :                           :          : checking its value.       :
| **T5-04** | Declarative Extraction of | High     | Dynamically importing     |
:           : Remote Execution          :          : internal build scripts    :
:           : Configuration             :          : via Python's import       :
:           :                           :          : mechanisms just to        :
:           :                           :          : extract boolean defaults. :
| **T5-05** | Defensive Path Joining    | High     | Assuming a workspace      |
:           : and State Evaluation for  :          : resolution function will  :
:           : Missing Workspaces        :          : always return a valid     :
:           :                           :          : path string and passing   :
:           :                           :          : it directly to an OS path :
:           :                           :          : operation.                :
| **T5-06** | Strict Validation of      | Medium   | Using native OS path      |
:           : Build System Import Path  :          : libraries to enforce or   :
:           : Semantics                 :          : validate domain-specific  :
:           :                           :          : build system path         :
:           :                           :          : semantics.                :
| **T5-07** | Tristate Logic for        | High     | Defaulting unknown state  |
:           : Auto-Detected Build       :          : resolutions to False and  :
:           : Configurations            :          : throwing assertions if    :
:           :                           :          : user-provided overrides   :
:           :                           :          : contradict it.            :
| **T5-08** | Explicit Type Validation  | Medium   | Catching generic          |
:           : and Exception Wrapping in :          : exceptions during dynamic :
:           : Dynamic Imports           :          : imports without enriching :
:           :                           :          : the error with file path  :
:           :                           :          : context.                  :
| **T5-09** | Ahead-of-Time Regex       | Medium   | Compiling regex           |
:           : Compilation in File       :          : statements inside a       :
:           : Parsers                   :          : high-frequency loop or    :
:           :                           :          : generator.                :

--------------------------------------------------------------------------------

### Rules

#### T5-01: Hardcoded Build Strategy Resolution Over Brittle File Parsing

> **Rule:** Must determine execution strategies via explicit flag state matrices
> rather than imperatively parsing external `.gni` files that are subject to
> deprecation.
>
> **What:** Build orchestration logic should determine execution strategies via
> explicit flag state matrices rather than imperatively parsing external `.gni`
> files that are subject to deprecation.
>
> **Applies To:** Build wrapper scripts determining remote execution fallbacks.
>
> **Why:** The script used regex to parse `remoteexec_defaults.gni`. As that
> file was scheduled for deletion, maintaining the parser would have resulted in
> accidental and silent fallbacks to the deprecated Reclient backend. Failing to
> adhere to this typically results in **Incorrect Build Execution Path**.

**Trap 1: Relying on manual text parsing of external build definition files to
set internal script execution behavior.**

**Don't:**

```python
# BAD: Parsing external configs
values = _get_remoteexec_defaults(output_dir)
if use_siso:
    use_reclient = values["use_reclient_on_siso"]
```

**Do:**

```python
# GOOD: State derived from core tool flags
if use_siso:
    use_reclient = False
else:
    use_reclient = True
```

--------------------------------------------------------------------------------

#### T5-02: Comment-Aware Declarative Configuration Parsing

> **Rule:** Always strip commented-out text prior to evaluating matches when
> parsing declarative configuration files.
>
> **What:** When reading declarative configuration files (e.g., `.gn`,
> `remoteexec_default`) manually via regex or line-by-line parsing, the
> interpreter must strip commented-out text to prevent false-positive feature
> activation.
>
> **Applies To:** Build state extraction tools, environment config parsers
> (`autoninja.py`, GN helpers).
>
> **Why:** The build wrapper would incorrectly enable experimental toolchains or
> remote execution behaviors because it matched variables that users had
> explicitly commented out (e.g., `# use_siso = true`) in their configuration
> files. Failing to adhere to this typically results in **Erroneous Build
> Configuration**.

**Trap 1: Matching target variable names in a file line-by-line without
respecting the specific syntax's comment character.**

**Don't:**

```python
for line in config_file:
    if "use_siso = true" in line:
        enable_siso = True
```

**Do:**

```python
for line in config_file:
    line = line.split("#")[0] # Strip comments
    if "use_siso = true" in line:
        enable_siso = True
```

--------------------------------------------------------------------------------

#### T5-03: Graceful Fallback for Uninitialized Build Tool State

> **Rule:** Must safely fall back to default configurations if standard
> initialization criteria are absent to prevent failures in stateless
> subcommands.
>
> **What:** Build wrappers must safely fall back to default configurations if
> standard initialization criteria (like an explicit build output directory) are
> absent, ensuring non-build subcommands operate correctly.
>
> **Applies To:** Build tool execution routing (`autoninja.py`).
>
> **Why:** Running stateless commands like `--help` without a build directory
> (`-C`) left the core tool-choice variable uninitialized (None). Subsequent
> checks relying on a boolean evaluation triggered crashes. Failing to adhere to
> this typically results in **NoneType Exceptions / Tool Crash**.

**Trap 1: Assuming the tool-selection state flag is always set during standard
build initialization before checking its value.**

**Don't:**

```python
# crashes if use_siso was never initialized due to missing output_dir
if use_siso:
    run_siso_backend()
```

**Do:**

```python
# explicitly handle uninitialized state before checking
if use_siso is None:
    use_siso = _get_use_siso_default(output_dir)

if use_siso:
    run_siso_backend()
```

--------------------------------------------------------------------------------

#### T5-04: Declarative Extraction of Remote Execution Configuration

> **Rule:** Never execute imperative scripts to determine remote execution
> configurations; parse static declarative files instead.
>
> **What:** Build systems should parse remote execution defaults from simple,
> static declarative configuration files rather than executing imperative
> scripts during the initialization phase.
>
> **Applies To:** Build configuration extraction (e.g., determining
> `use_reclient` or `use_remoteexec`).
>
> **Why:** The system previously relied on dynamically importing and executing a
> Python script (`use_reclient_value.py`) just to determine standard
> configuration flags, which proved brittle and slow. It was replaced with
> regex-based parsing of a static config file. Failing to adhere to this
> typically results in **Script Import Failures / Sluggish Initialization**.

**Trap 1: Dynamically importing internal build scripts via Python's import
mechanisms just to extract boolean defaults.**

**Don't:**

```python
script = _import_from_path("use_reclient_value", script_path)
try:
    return script.use_reclient_value(output_dir)
```

**Do:**

```python
pattern = re.compile(r"(^|\s*)([^=\s]*)\s*=\s*(\S*)\s*$")
with open(default_file, encoding="utf-8") as f:
    for line in f:
        line = line.split("#")[0]
        m = pattern.match(line)
        if m:
            values[m.group(2)] = m.group(3)
```

--------------------------------------------------------------------------------

#### T5-05: Defensive Path Joining and State Evaluation for Missing Workspaces

> **Rule:** Always validate workspace directories against `None` before
> executing path joins or querying state dictionaries.
>
> **What:** Scripts retrieving root workspace directories must account for
> environments where a formal checkout definition (e.g., `.gclient`) is missing,
> explicitly checking for `None` before executing path joins or state queries.
>
> **Applies To:** Build initialization scripts, specifically when determining
> repository paths (e.g., `gclient_paths.GetPrimarySolutionPath()`).
>
> **Why:** When the build tool was invoked in standalone components or
> non-standard environments (like building LLVM directly), the function
> resolving the workspace root returned `None`. This caused `TypeError` crashes
> during `os.path.join` and dictionary lookups, completely blocking execution.
> Failing to adhere to this typically results in **TypeError / Script Crash**.

**Trap 1: Assuming a workspace resolution function will always return a valid
path string and passing it directly to an OS path operation.**

**Don't:**

```python
# BAD: Assumes GetPrimarySolutionPath() always returns a string
root_dir = gclient_paths.GetPrimarySolutionPath()
return os.path.exists(os.path.join(root_dir, "internal", ".git"))
```

**Do:**

```python
# GOOD: Explicitly check for None before joining paths
root_dir = gclient_paths.GetPrimarySolutionPath()
if not root_dir:
    return False
return os.path.exists(os.path.join(root_dir, "internal", ".git"))
```

**Trap 2: Attempting to index a dictionary or retrieve state from a function
that returns None in edge-case environments.**

**Don't:**

```python
# BAD: Unconditional dictionary indexing
use_reclient = values["use_reclient_on_ninja"]
```

**Do:**

```python
# GOOD: Validate the variable before acting on it
if values is None:
    use_reclient = False
else:
    use_reclient = values.get("use_reclient_on_ninja", False)
```

--------------------------------------------------------------------------------

#### T5-06: Strict Validation of Build System Import Path Semantics

> **Rule:** Must strictly differentiate between native OS absolute paths and
> domain-specific build system path semantics during validation.
>
> **What:** When parsing build configuration files (e.g., GN files), path
> resolution logic must strictly differentiate between native OS absolute paths
> and the build system's specific syntax for absolute repository paths (e.g.,
> starting with `/` or `//`).
>
> **Applies To:** Build configuration parsers, specifically custom python
> scripts extracting directives from `.gn` or `.gni` files.
>
> **Why:** A parser attempting to validate GN import paths used native
> `os.path.isabs()`. On Windows, standard OS absolute paths do not necessarily
> begin with a `/`, causing valid absolute OS paths to be incorrectly flagged or
> processed as invalid GN paths. Failing to adhere to this typically results in
> **Path Resolution Failure**.

**Trap 1: Using native OS path libraries to enforce or validate domain-specific
build system path semantics.**

**Don't:**

```python
# BAD: Mixing OS path validation with GN semantics
if os.path.isabs(raw_import_path):
    import_path = raw_import_path
```

**Do:**

```python
# GOOD: Check specific GN path syntax before OS path validation
elif raw_import_path.startswith('/'):
    if sys.platform.startswith('win32'):
        import_path = raw_import_path[1:]
    if not os.path.isabs(import_path):
        raise Exception('Wrong absolute path for import %s' % raw_import_path)
```

--------------------------------------------------------------------------------

#### T5-07: Tristate Logic for Auto-Detected Build Configurations

> **Rule:** Must utilize Tristate logic (`True`, `False`, `None`) for
> auto-detected build capabilities to allow unhindered user overrides.
>
> **What:** Auto-detection logic for build capabilities must utilize a Tristate
> (`True`, `False`, `None`) rather than defaulting to `False`. `None` indicates
> the environment cannot be determined and should defer to user configurations
> without enforcing hard assertions.
>
> **Applies To:** Environment detection scripts and `args.gn` variable parsing.
>
> **Why:** The build tool introduced strict assertions to ensure user-defined
> configurations matched auto-detected defaults. Because the script defaulted to
> `False` when directories were clean or on non-corporate machines, the
> assertions violently crashed local builds for standard developer workflows.
> Failing to adhere to this typically results in **Assertion Error / Build
> Abortion**.

**Trap 1: Defaulting unknown state resolutions to False and throwing assertions
if user-provided overrides contradict it.**

**Don't:**

```python
# BAD: Defaulting to False and asserting against overrides
def get_use_siso():
    if not root_dir: return False
# ... later ...
if k == 'use_siso' and v == 'true':
    assert use_siso != False
    use_siso = True
```

**Do:**

```python
# GOOD: Default to None, allowing graceful overrides without assertions
def get_use_siso():
    if not root_dir: return None
# ... later ...
if k == 'use_siso' and v == 'true':
    use_siso = True
```

--------------------------------------------------------------------------------

#### T5-08: Explicit Type Validation and Exception Wrapping in Dynamic Imports

> **Rule:** Always wrap dynamic import exceptions with specific file path
> context and strictly validate the returned data types.
>
> **What:** When dynamically importing external scripts to resolve configuration
> states, callers must wrap generic execution exceptions into context-aware
> errors (e.g., `ImportError`, `RuntimeError` with file paths) and strictly
> validate the returned data types.
>
> **Applies To:** Dynamic python module loading (`importlib`) and external
> script execution within build tools.
>
> **Why:** The tool dynamically loaded a remote script to determine default
> build settings. When the script failed to load or executed improperly, it
> yielded an obscure stack trace without identifying the problematic file.
> Furthermore, if the script returned unexpected data (like None instead of a
> boolean), it caused downstream type errors. Failing to adhere to this
> typically results in **Cryptic Stack Trace / TypeError**.

**Trap 1: Catching generic exceptions during dynamic imports without enriching
the error with file path context.**

**Don't:**

```python
# BAD: Swallowing context in dynamic imports
try:
    r = script.use_siso_default(output_dir)
except Exception:
    raise RuntimeError('Could not call method')
```

**Do:**

```python
# GOOD: Providing explicit path context and validating return types
try:
    r = script.use_siso_default(output_dir)
except Exception:
    raise RuntimeError('Could not call method "use_siso_default" in "{}"'.format(script_path))

if not isinstance(r, bool):
    raise TypeError('Method in "{}" returned invalid result; expected bool, got "{}"'.format(script_path, type(r)))
```

--------------------------------------------------------------------------------

#### T5-09: Ahead-of-Time Regex Compilation in File Parsers

> **Rule:** Must pre-compile regular expressions at the module-level before
> entering iterative line-scanning loops.
>
> **What:** When scanning large configuration files line-by-line, regular
> expressions must be pre-compiled into a module-level variable outside of the
> loop rather than evaluated inline.
>
> **Applies To:** Python scripts parsing `args.gn` or other large build
> configuration files.
>
> **Why:** A generator parsing `args.gn` files was compiling a regular
> expression for import directives internally on every single line iteration,
> causing unnecessary CPU overhead. Failing to adhere to this typically results
> in **Suboptimal Parsing Performance**.

**Trap 1: Compiling regex statements inside a high-frequency loop or
generator.**

**Don't:**

```python
# BAD: Compiling regex on every line iteration
for line in f:
    if re.search(r'\s*import\("(.*)"\)', line):
        pass
```

**Do:**

```python
# GOOD: Pre-compiling the regex outside the loop
import_re = re.compile(r'\s*import\("(.*)"\)')
for line in f:
    match = import_re.match(line)
    if match:
        pass
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | CLI Flag Propagation & Order Resolution - *Provides the
    initial execution flags and output directory variables required by
    declarative state extraction wrappers to locate initialization targets.*
*   **Downstream:** T7 | High-Fidelity Infrastructure Testing - *Validates the
    logic of state extraction parsers and mock file readers through concrete
    physical environment verification.*

## Chapter: OS-Level Resource Normalization

**Context:** This chapter establishes mandatory constraints for normalizing the
build environment prior to tool execution, encompassing file descriptor
escalations, path virtualization, and process priority tuning. Adhering to these
platform-specific optimizations prevents arbitrary cache invalidations and
ensures execution stability against OS-level resource exhaustion.

### Summary

| Rule ID   | Principle /          | Priority | Primary Symptom  |
:           : Constraint           :          : / Trap           :
| :-------- | :------------------- | :------- | :--------------- |
| **T6-01** | Mount Namespace      | Medium   | Allowing local   |
:           : Build Path           :          : build            :
:           : Normalization        :          : configurations   :
:           :                      :          : to dictate       :
:           :                      :          : dynamic          :
:           :                      :          : execution paths  :
:           :                      :          : without          :
:           :                      :          : abstraction,     :
:           :                      :          : losing cache     :
:           :                      :          : efficiency       :
:           :                      :          : across multiple  :
:           :                      :          : copies of        :
:           :                      :          : identical trees. :
| **T6-02** | Proactive OS-Level   | Critical | Assuming the     |
:           : File Descriptor      :          : host OS          :
:           : Limit Escalation     :          : environment has  :
:           :                      :          : sufficient       :
:           :                      :          : out-of-the-box   :
:           :                      :          : resource limits  :
:           :                      :          : for              :
:           :                      :          : high-concurrency :
:           :                      :          : tasks.           :
| **T6-03** | Defensive OS         | Medium   | Using exact      |
:           : Platform String      :          : string equality  :
:           : Matching             :          : to evaluate the  :
:           :                      :          : system platform  :
:           :                      :          : identifier.      :
| **T6-04** | Platform-Specific    | Medium   | Applying         |
:           : Isolation of Remote  :          : experimental     :
:           : Execution Heuristics :          : performance      :
:           :                      :          : tunings          :
:           :                      :          : indiscriminately :
:           :                      :          : across all       :
:           :                      :          : operating        :
:           :                      :          : systems.         :
| **T6-05** | Legacy Unit Parsing  | Medium   | Converting units |
:           : in procfs            :          : from Linux       :
:           :                      :          : filesystem       :
:           :                      :          : pseudo-files     :
:           :                      :          : based on modern  :
:           :                      :          : strict SI        :
:           :                      :          : abbreviation     :
:           :                      :          : standards.       :
| **T6-06** | Explicit             | Medium   | Permitting       |
:           : Environment-Specific :          : silent fallbacks :
:           : Tooling Warnings     :          : to unoptimized   :
:           :                      :          : local build      :
:           :                      :          : execution when a :
:           :                      :          : known slow       :
:           :                      :          : environment is   :
:           :                      :          : detected.        :

--------------------------------------------------------------------------------

### Rules

#### T6-01: Mount Namespace Build Path Normalization

> **Rule:** Must bind-mount disparate physical workspaces to a canonical virtual
> path using Linux mount namespaces (`unshare`) prior to cache-sensitive build
> execution. Never expose the virtual path definitions to arbitrary user
> mutation via dynamic flags.
>
> **What:** Leveraging Linux mount namespaces (`unshare`) to bind-mount
> disparate physical workspace directories to a consistent virtual path prior to
> executing cached build tasks.
>
> **Applies To:** Local build orchestration and wrapper scripts operating on
> Linux environments interacting with cache-sensitive toolchains.
>
> **Why:** Creating new workspaces using copy-on-write filesystem snapshots
> (e.g., btrfs) cloned the artifacts perfectly, but the differing physical paths
> triggered massive cache invalidations, forcing the build engine into a 3-4
> minute file re-evaluation phase and redownloading RBE objects. Failing to
> adhere to this typically results in **Cache Invalidation**.

**Trap 1: Allowing local build configurations to dictate dynamic execution paths
without abstraction, losing cache efficiency across multiple copies of identical
trees.**

**Don't:**

*   Execute the build tool directly against varying absolute paths like
    `/home/user/workspace1/src` and `/home/user/workspace2/src`.

**Do:**

*   Virtualize the execution environment using `unshare --mount --map-root-user
    bash -c "mount --bind <physical_path> <canonical_virtual_path> && cd
    <canonical_virtual_path> && execute_build"`.

**Trap 2: Exposing the target virtual path via a dynamic CLI flag, resulting in
cache fragmentation when different users or scripts select arbitrary directory
names.**

**Don't:**

```bash
python siso.py --virtual-build-path=/tmp/my_custom_workspace
```

**Do:**

*   Use a boolean trigger flag (`--virtual-build-path`) and hardcode a stable
    system-wide default path (`/tmp/siso_virtual_build_path`), permitting
    overrides strictly via environment variables to discourage arbitrary
    mutation.

**Exceptions:** Platform environments outside of Linux (Windows, macOS) where
the `unshare` utility is unavailable.

--------------------------------------------------------------------------------

#### T6-02: Proactive OS-Level File Descriptor Limit Escalation

> **Rule:** Always escalate OS-level file descriptor limits (`RLIMIT_NOFILE`) to
> the hardware maximum at the top-level script before diverging into specific
> build tool executions.
>
> **What:** Build wrapper scripts must proactively boost OS-level resource
> limits (RLIMIT_NOFILE) to the hard maximum and optimize process priority
> before delegating to the underlying build tool.
>
> **Applies To:** Cross-platform daemon and build orchestrators (autoninja.py,
> siso.py) running on macOS and Linux.
>
> **Why:** Large concurrent builds routinely crashed on macOS because the
> default file descriptor limit is strictly capped at a very low threshold (256)
> by the OS. Failing to adhere to this typically results in **Resource
> Exhaustion / Crash**.

**Trap 1: Assuming the host OS environment has sufficient out-of-the-box
resource limits for high-concurrency tasks.**

**Don't:**

```python
# BAD: Running the high-concurrency tool directly
subprocess.Popen(["ninja", "-j", str(j_value)])
```

**Do:**

```python
# GOOD: Normalizing limits prior to execution
if sys.platform in ["darwin", "linux"]:
    import resource
    fileno_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
    if fileno_limit < hard_limit:
        resource.setrlimit(resource.RLIMIT_NOFILE, (hard_limit, hard_limit))
```

**Trap 2: Applying limits only for one specific tool backend, causing failures
when the backend is switched.**

**Don't:**

*   Executing `resource.setrlimit()` only inside the legacy `ninja` code path,
    leaving `siso` builds vulnerable.

**Do:**

*   Moving the resource modification to the top-level script setup before tool
    divergence.

--------------------------------------------------------------------------------

#### T6-03: Defensive OS Platform String Matching

> **Rule:** Must use prefix matching (`startswith`) instead of exact string
> equality when evaluating `sys.platform` to ensure variant distributions are
> reliably detected.
>
> **What:** When determining the underlying operating system via `sys.platform`,
> scripts must use prefix matching (`startswith`) rather than exact string
> equality.
>
> **Applies To:** Platform-specific branches in build scripts, file descriptor
> optimization, and resource telemetry.
>
> **Why:** Using exact string matches for 'linux' failed in some environments or
> older Python configurations where `sys.platform` returns variants like
> 'linux2', silently skipping critical setup logic. Failing to adhere to this
> typically results in **Silent Logic Bypass / Incorrect Platform Detection**.

**Trap 1: Using exact string equality to evaluate the system platform
identifier.**

**Don't:**

```python
if sys.platform == 'linux':
    execute_linux_optimizations()
```

**Do:**

```python
if sys.platform.startswith('linux'):
    execute_linux_optimizations()
```

--------------------------------------------------------------------------------

#### T6-04: Platform-Specific Isolation of Remote Execution Heuristics

> **Rule:** Always gate aggressive, unverified performance tuning parameters
> behind strict platform checks until thoroughly benchmarked on alternate
> architectures.
>
> **What:** Aggressive performance tuning parameters (e.g., local resource
> racing, resource fractioning) must be explicitly gated by platform checks
> until they are benchmarked on alternative OSes.
>
> **Applies To:** Remote build execution initialization, specifically
> configuring environment variables for Reclient/RBE.
>
> **Why:** New racing defaults for remote execution were introduced globally.
> Reviewers noted that these parameters were only proven on Linux, risking CPU
> exhaustion or slow-downs on Windows and macOS architectures. Failing to adhere
> to this typically results in **Resource Exhaustion / Latency Regressions**.

**Trap 1: Applying experimental performance tunings indiscriminately across all
operating systems.**

**Don't:**

```python
# BAD: Applying aggressive racing bounds globally
def set_racing_defaults():
    os.environ.setdefault("RBE_local_resource_fraction", "0.4")
    os.environ.setdefault("RBE_racing_bias", "0.7")
```

**Do:**

```python
# GOOD: Gating unverified optimizations behind platform checks
def set_racing_defaults():
    if sys.platform == 'linux':
        os.environ.setdefault("RBE_local_resource_fraction", "0.4")
        os.environ.setdefault("RBE_racing_bias", "0.7")
    else:
        os.environ.setdefault("RBE_local_resource_fraction", "0.2")
        os.environ.setdefault("RBE_racing_bias", "0.95")
```

--------------------------------------------------------------------------------

#### T6-05: Legacy Unit Parsing in procfs

> **Rule:** Must apply a base-2 multiplier (1024) instead of standard base-10 SI
> units when parsing legacy kibibyte abbreviations (`kB`) explicitly from Linux
> `/proc/meminfo`.
>
> **What:** When parsing system memory statistics from Linux `/proc/meminfo`,
> the unit `kB` must be multiplied by 1024 (kibibytes) rather than the standard
> SI unit base-10 multiplier of 1000.
>
> **Applies To:** System observability modules, telemetry data collectors,
> hardware resource detectors.
>
> **Why:** The Linux kernel historically uses `kB` to denote kibibytes in
> `/proc/meminfo`. Strict adherence to modern SI conventions without
> domain-specific validation results in a ~2.4% error rate in memory metric
> normalization. Failing to adhere to this typically results in **Inaccurate
> Telemetry Data**.

**Trap 1: Converting units from Linux filesystem pseudo-files based on modern
strict SI abbreviation standards.**

**Don't:**

```python
# BAD: Treating kB as base-10 standard kilobyte
if unit == 'kB':
    return size * 1000
```

**Do:**

```python
# GOOD: Using legacy base-2 multiplier for /proc/meminfo specifically
if unit == 'kB':
    return size * 1024
```

--------------------------------------------------------------------------------

#### T6-06: Explicit Environment-Specific Tooling Warnings

> **Rule:** Always emit clear, actionable console warnings detailing exact
> configuration overrides when executing inside a known suboptimal virtualized
> environment.
>
> **What:** Build tools detecting execution within highly specialized virtual
> environments must emit clear, actionable warnings providing the exact
> configuration overrides required when performance heuristics are misaligned.
>
> **Applies To:** Build orchestration scripts, environment abstraction layers,
> configuration parsers.
>
> **Why:** Users executing builds inside virtualized workspace file systems
> without explicitly enabling remote caching tools experienced significantly
> degraded IO performance without clear feedback indicating why. Failing to
> adhere to this typically results in **Degraded Build Performance**.

**Trap 1: Permitting silent fallbacks to unoptimized local build execution when
a known slow environment is detected.**

**Don't:**

```python
# BAD: Silently executing sub-optimally
if detect_virtual_env() and not remote_enabled:
    execute_local_build()
```

**Do:**

```python
# GOOD: Provide explicit mitigation instructions for the specific environment
if detect_virtual_env() and not remote_enabled:
    print("WARNING: Virtual environment detected. Local build will be slow.")
    print("Please add 'use_remoteexec=true' to your args.gn configuration.")
    execute_local_build()
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | CLI Flag Propagation & Order Resolution - *Dynamic CLI
    flags passed to wrappers dictate which virtual execution paths are
    initialized prior to environment optimization.*
*   **Upstream:** T5 | Declarative Build State Extraction - *Build state
    parameters extracted from files like args.gn determine whether
    environment-specific mitigation warnings must be fired.*
*   **Downstream:** T2 | Daemon Process Orchestration & Health Polling -
    *Background sidecars and polling mechanisms inherit the normalized OS-level
    file descriptor limits established by the orchestrator.*

## Chapter: High-Fidelity Infrastructure Testing

**Context:** This chapter dictates the design of unit tests for build
infrastructure wrappers and telemetry components. It mandates relying on
physical mock files and environments over brittle internal function patching to
ensure end-to-end configuration parsing is reliably validated.

### Summary

| Rule ID   | Principle / Constraint    | Priority | Primary Symptom / Trap    |
| :-------- | :------------------------ | :------- | :------------------------ |
| **T7-01** | High-Fidelity File System | High     | Using a mocking library   |
:           : Fixtures over Internal    :          : to bypass the internal    :
:           : Mocking                   :          : configuration loading     :
:           :                           :          : logic.                    :
| **T7-02** | OS-Agnostic Path          | Medium   | Hardcoding Unix-style     |
:           : Construction in Tests     :          : separators or manually    :
:           :                           :          : replacing separators to   :
:           :                           :          : assert path correctness.  :
| **T7-03** | Hermetic Environment      | High     | Asserting or modifying    |
:           : Variable Mocking          :          : the global environment    :
:           :                           :          : directly in test logic    :
:           :                           :          : without context managers. :
| **T7-04** | Isolation of Environment  | Medium   | Inlining HTTP requests to |
:           : Metadata Extraction for   :          : internal metadata servers :
:           : Mockability               :          : directly inside the main  :
:           :                           :          : reporting workflow.       :

--------------------------------------------------------------------------------

### Rules

#### T7-01: High-Fidelity File System Fixtures over Internal Mocking

> **Rule:** Always simulate actual file system state for build wrapper unit
> tests instead of patching internal configuration-fetching logic.
>
> **What:** Unit tests for build wrappers must simulate actual file system state
> (e.g., writing dummy `.sisoenv`, `.sisorc`, or `.gclient` files to a temporary
> directory) rather than patching internal configuration-fetching Python
> functions.
>
> **Applies To:** Test infrastructure for configuration parsers, build wrappers,
> and telemetry components.
>
> **Why:** Tests were historically written by mocking internal logic like
> `_fetch_metrics_project` and `load_sisorc`. This masked real-world file path
> resolution bugs and metadata parsing errors. The suite was refactored to
> construct high-fidelity temporary directories reflecting realistic CIPD path
> structures. Failing to adhere to this typically results in **False Positive
> Tests**.

**Trap 1: Using a mocking library to bypass the internal configuration loading
logic.**

**Don't:**

```python
# BAD: Tests the mock, not the parser behavior
mocker.patch("siso.load_sisorc", return_value=(["-gflag"], {}))
mocker.patch("siso._fetch_metrics_project", return_value="test-project")
```

**Do:**

```python
# GOOD: Simulate the physical file state for end-to-end coverage
sisoenv_dir = tmp_path / "build" / "config" / "siso"
sisoenv_dir.mkdir(parents=True, exist_ok=True)
(sisoenv_dir / ".sisoenv").write_text("SISO_PROJECT=test-project\n")

(tmp_path / ".sisorc").write_text("global_flags = ['-gflag']\n")
```

**Exceptions:** External subprocess execution limits where network/process
isolation is strictly required (e.g., mock the final `subprocess.run` output
instead).

--------------------------------------------------------------------------------

#### T7-02: OS-Agnostic Path Construction in Tests

> **Rule:** Must utilize `os.path.join` natively in unit tests validating path
> construction instead of hardcoding platform-specific path separators.
>
> **What:** Unit tests verifying path construction logic must utilize
> `os.path.join` natively instead of hardcoding platform-specific path
> separators (like `/`) and subsequently attempting manual string replacements
> to force cross-platform parity.
>
> **Applies To:** Test suites validating output directories, IPC socket
> generation, or dependency resolution.
>
> **Why:** Cross-platform test definitions included hardcoded forward slashes
> inside parameterization data structures, requiring messy `replace(os.sep,
> '/')` calls that masked real edge cases. Failing to adhere to this typically
> results in **Cross-Platform Test Failure**.

**Trap 1: Hardcoding Unix-style separators or manually replacing separators to
assert path correctness.**

**Don't:**

```python
pytest.param(['ninja', '-C', 'out/Default'], id='test')
# inside test:
assert result.replace(os.sep, '/') == 'out/Default'
```

**Do:**

```python
pytest.param(['ninja', '-C', os.path.join('out', 'Default')], id='test')
# inside test:
assert result == os.path.join('out', 'Default')
```

--------------------------------------------------------------------------------

#### T7-03: Hermetic Environment Variable Mocking

> **Rule:** Always wrap tests that assert or alter environment variables with
> `mock.patch.dict('os.environ', ...)` to guarantee state isolation.
>
> **What:** Unit tests that mock, assert, or alter environment variables must
> use `mock.patch.dict('os.environ', ...)` to guarantee state isolation and
> prevent pollution across the test suite.
>
> **Applies To:** Unit testing infrastructure for flag application and build
> telemetry setup.
>
> **Why:** Directly mutating `os.environ` during test execution caused
> subsequent, unrelated tests to inherit the modified global state, leading to
> non-deterministic behavior and flakiness in the CI pipeline. Failing to adhere
> to this typically results in **Test Suite Flakiness**.

**Trap 1: Asserting or modifying the global environment directly in test logic
without context managers.**

**Don't:**

```python
def test_telemetry_flags(self):
    os.environ["SISO_PROJECT"] = "test_proj"
    # test logic here
```

**Do:**

```python
@mock.patch.dict('os.environ', {})
def test_telemetry_flags(self):
    os.environ["SISO_PROJECT"] = "test_proj"
    # test logic here
```

--------------------------------------------------------------------------------

#### T7-04: Isolation of Environment Metadata Extraction for Mockability

> **Rule:** Isolate network-dependent metadata gathering into independent,
> mockable functions instead of embedding them within large aggregation
> routines.
>
> **What:** Network-dependent metadata gathering (such as querying a cloud
> provider's internal metadata server) must be isolated into independent
> functions, rather than embedded within large, untestable data aggregation
> routines.
>
> **Applies To:** Telemetry and logging scripts collecting environment details
> (e.g., GCE metadata servers).
>
> **Why:** Google Compute Engine metadata logic was deeply intertwined with the
> main log upload dictionary assembly. Reviewers requested dedicated tests,
> prompting the refactoring of the GCE network call into an isolated, mockable
> `_getGCEInfo()` method. Failing to adhere to this typically results in
> **Untestable Telemetry Logic**.

**Trap 1: Inlining HTTP requests to internal metadata servers directly inside
the main reporting workflow.**

**Don't:**

```python
# BAD: Mixing telemetry assembly with network calls
def get_metadata():
    data = {"os": "linux"}
    response = urllib.request.urlopen("http://metadata...")
    data["gce_type"] = json.loads(response.read())
    return data
```

**Do:**

```python
# GOOD: Isolating the network call into a dedicated function for mockability
def _getGCEInfo():
    try:
        return json.loads(urllib.request.urlopen("http://metadata...").read())
    except Exception:
        return None

def get_metadata():
    data = {"os": "linux"}
    gce = _getGCEInfo()
    if gce:
        data["gce_type"] = gce
    return data
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T5 | Declarative Build State Extraction - *Test environments
    must physically emulate the declarative configuration files (`.gclient`,
    `.sisoenv`) governed by this domain.*
*   **Upstream:** T4 | Identity & Telemetry Authorization - *Metadata isolation
    strategies established here dictate how telemetry setup payloads and
    authorization constraints are verified.*

## Chapter: AI Agent Environment Adaptation

**Context:** This domain governs the detection and normalization of headless,
AI-driven environments to optimize build tool interactions. It enforces safe
execution parameter mutation to preserve non-TTY performance paths while
emitting deterministic signals to prevent LLM context exhaustion or
hallucination.

### Summary

| Rule ID   | Principle / Constraint  | Priority | Primary Symptom / Trap      |
| :-------- | :---------------------- | :------- | :-------------------------- |
| **T8-01** | Headless AI Agent       | Medium   | Forcibly appending          |
:           : Execution Normalization :          : automation flags to the end :
:           :                         :          : of the argument list,       :
:           :                         :          : actively overriding user or :
:           :                         :          : agent attempts to negate    :
:           :                         :          : them.                       :

--------------------------------------------------------------------------------

### Rules

#### T8-01: Headless AI Agent Execution Normalization

> **Rule:** Always prepend AI-specific automation flags to ensure trailing user
> arguments take precedence, and emit deterministic success signals for
> automated agents.
>
> **What:** Safely mutating build invocation arguments when automated AI
> execution environments are detected, optimizing performance without breaking
> standard interactivity paradigms.
>
> **Applies To:** Build wrapper entry points evaluating shell invocation
> parameters (`autoninja.py`, `siso.py`).
>
> **Why:** When AI assistants executed build commands, the lack of an
> interactive TTY caused the underlying engine to disable fast-path heuristics
> (fast_local, fast_nop). This significantly slowed AI-driven builds.
> Conversely, generating standard terminal output overwhelmed LLM context
> windows, but omitting all output caused agents to 'hallucinate' that silent
> failures had occurred. Failing to adhere to this typically results in
> **Context Window Exhaustion**.

**Trap 1: Forcibly appending automation flags to the end of the argument list,
actively overriding user or agent attempts to negate them.**

**Don't:**

```python
if is_ai_agent:
    input_args.append('--quiet')
```

**Do:**

```python
if is_ai_agent:
    # Prepend flags to allow user-supplied trailing flags to take precedence
    subcmd_args = ['--quiet', '--batch=false'] + subcmd_args
```

**Trap 2: Executing `--quiet` builds completely silently, leading automated
agents to believe the system hung or the script failed.**

**Don't:**

*   Return silently upon a `0` exit code under `--quiet`.

**Do:**

*   Emit an explicit, deterministic signal (e.g., printing 'Success')
    specifically for the AI agent if and only if the build exits successfully,
    providing absolute verification without polluting context.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | CLI Flag Propagation & Order Resolution - *Provides the
    core argument modification and resolution lifecycle that AI environment
    adaptations must hook into.*
