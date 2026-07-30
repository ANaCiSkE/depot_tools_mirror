# Code Style and Documentation Engineering Guide

## Executive Summary

Welcome to the authoritative engineering guide for Code Style and Documentation.
This repository serves as the definitive source of tribal knowledge for the
subsystem, compiled specifically to prevent the regression of known failure
modes, eliminate subjective debates during code review, and standardize critical
architectural boundaries. By codifying these historical lessons, this guide
ensures that incoming engineers can rapidly onboard and contribute safely to the
codebase.

This guide establishes strict mandates across several core technical domains. It
enforces a modernized, declarative approach to Python scripting—mandating Python
3 idioms, comprehensive static type hinting (PEP 484/604), and
resource-optimized lazy evaluation. It also defines the structural and aesthetic
hygiene required for code formatting, ensuring that all source files remain
universally readable and compatible with our automated linting and formatting
pipelines.

Furthermore, this guide rigorously governs version control and documentation
standards. It dictates exact schemas for commit message metadata, bug
traceability, and git tooling orchestration to guarantee seamless CI/CD
integration. Paired with strict expectations for grammatical correctness and
docstring formatting, these practices preserve vital engineering rationale and
ensure that the codebase remains highly maintainable for future generations of
developers.

## Summary

| Chapter Theme / Title               | Scope & Objective                      |
| :---------------------------------- | :------------------------------------- |
| **Python Language Idioms &          | This domain dictates the strict        |
: Modernization**                     : transition away from verbose           :
:                                     : imperative logic and legacy Python 2   :
:                                     : syntax toward declarative, PEP-8       :
:                                     : compliant Python 3 paradigms. It       :
:                                     : specifically governs the use of native :
:                                     : features like f-strings, the walrus    :
:                                     : operator, zero-argument super calls,   :
:                                     : and intrinsic truthiness evaluations   :
:                                     : to maximize execution efficiency and   :
:                                     : readability.                           :
| **Commit Message Metadata &         | This domain enforces rigorous version  |
: Hygiene**                           : control history standards by mandating :
:                                     : strict 50/72 character limits,         :
:                                     : explicit bug traceability, and         :
:                                     : intent-focused documentation. These    :
:                                     : practices guarantee automated tooling  :
:                                     : compatibility and preserve critical    :
:                                     : architectural rationale for future     :
:                                     : maintainers.                           :
| **Static Type Hinting & Safety**    | This chapter enforces the precise      |
:                                     : application of PEP 484 and PEP 604     :
:                                     : type annotations to guarantee strict   :
:                                     : structural safety. It establishes      :
:                                     : patterns for explicitly handling       :
:                                     : nullables, enforcing symmetric         :
:                                     : constraints on inputs/outputs, and     :
:                                     : utilizing robust parameterized         :
:                                     : collections to eliminate static        :
:                                     : analysis blindspots.                   :
| **Execution Efficiency & Resource   | This domain governs the execution      |
: Optimization**                      : efficiency of Python infrastructure    :
:                                     : tooling by strictly enforcing native   :
:                                     : library invocations over subprocesses, :
:                                     : lazy evaluation over eager memory      :
:                                     : allocation, and the elimination of     :
:                                     : redundant data structure conversions.  :
| **Code Formatting & Structural      | This domain governs the structural     |
: Style**                             : consistency and aesthetic hygiene of   :
:                                     : the codebase, strictly enforcing       :
:                                     : automated formatter adherence, precise :
:                                     : line length constraints, and import    :
:                                     : ordering. It ensures uniform           :
:                                     : readability across development         :
:                                     : environments while eliminating         :
:                                     : subjective stylistic churn.            :
| **Technical Documentation & Comment | This domain establishes strict         |
: Quality**                           : standards for internal code            :
:                                     : documentation, enforcing proper        :
:                                     : formatting, typographical accuracy,    :
:                                     : and grammatical correctness. Adherence :
:                                     : ensures clear, professional, and       :
:                                     : easily parsable technical              :
:                                     : documentation across all internal      :
:                                     : scripts, configuration files, and      :
:                                     : READMEs.                               :
| **Data Validation & Regular         | This chapter dictates the mechanisms   |
: Expression Management**             : for string validation and regular      :
:                                     : expression management. It mandates the :
:                                     : use of deterministic error schemas,    :
:                                     : raw literals for escape sequences, and :
:                                     : the consolidation of verbose string    :
:                                     : checks into rigorously documented      :
:                                     : regular expressions.                   :
| **Git Tooling & Build System        | This domain governs the orchestration  |
: Orchestration**                     : of version control configurations,     :
:                                     : build system artifacts, and CLI        :
:                                     : environments within Chromium           :
:                                     : infrastructure. It enforces correct    :
:                                     : metadata ordering, documentation       :
:                                     : synchronization, and file execution    :
:                                     : permissions to ensure seamless and     :
:                                     : deterministic developer workflows.     :

--------------------------------------------------------------------------------
--------------------------------------------------------------------------------

## Chapter: Python Language Idioms & Modernization

**Context:** This domain dictates the strict transition away from verbose
imperative logic and legacy Python 2 syntax toward declarative, PEP-8 compliant
Python 3 paradigms. It specifically governs the use of native features like
f-strings, the walrus operator, zero-argument super calls, and intrinsic
truthiness evaluations to maximize execution efficiency and readability.

### Summary

| Rule ID   | Principle /       | Priority | Primary Symptom / |
:           : Constraint        :          : Trap              :
| :-------- | :---------------- | :------- | :---------------- |
| **T1-01** | String            | Medium   | Using the modulo  |
:           : Interpolation via :          : `%` operator to   :
:           : F-Strings         :          : inject variables  :
:           :                   :          : into a template   :
:           :                   :          : string.           :
| **T1-02** | Imperative Loops  | Medium   | Chaining `set()`, |
:           : over Complex      :          : `filter()`,       :
:           : Functional        :          : `lambda`, and     :
:           : Pipelines         :          : `map()` to        :
:           :                   :          : collect           :
:           :                   :          : validation        :
:           :                   :          : errors.           :
| **T1-03** | Explicit Sentinel | Medium   | Placing error     |
:           : Checks over       :          : handling in an    :
:           : For-Else          :          : `else` block tied :
:           : Constructs        :          : to a `for` loop.  :
| **T1-04** | Descriptive Tuple | Medium   | Retrieving data   |
:           : Unpacking         :          : via hardcoded     :
:           :                   :          : array index       :
:           :                   :          : inside a loop.    :
| **T1-05** | Structural        | Medium   | Conditionally     |
:           : Uniformity in     :          : parsing a tuple   :
:           : Configuration     :          : based on its      :
:           : Lists             :          : length.           :
| **T1-06** | Removal of        | Medium   | Calling           |
:           : Redundant String  :          : `.strip()` again  :
:           : Normalization     :          : on a string that  :
:           :                   :          : has already had   :
:           :                   :          : its whitespace    :
:           :                   :          : stripped prior to :
:           :                   :          : a                 :
:           :                   :          : `.removeprefix()` :
:           :                   :          : call.             :
| **T1-07** | Modernized String | Medium   | Using the modulo  |
:           : Formatting        :          : operator to       :
:           :                   :          : inject variables  :
:           :                   :          : into strings.     :
| **T1-08** | State Encodings   | Medium   | Using a           |
:           : via StrEnum       :          : `frozenset` of    :
:           :                   :          : strings to        :
:           :                   :          : validate states   :
:           :                   :          : instead of an     :
:           :                   :          : enumeration.      :
| **T1-09** | Single-Expression | Medium   | Calling a method  |
:           : Variable          :          : in an             :
:           : Assignment        :          : if-condition and  :
:           : (Walrus Operator) :          : then calling it   :
:           :                   :          : again inside the  :
:           :                   :          : if-block.         :
| **T1-10** | Idiomatic         | High     | Using manual      |
:           : Declarative       :          : loops and         :
:           : Iteration and     :          : condition checks  :
:           : Truthiness        :          : to assert a       :
:           :                   :          : condition holds   :
:           :                   :          : for all items.    :
| **T1-11** | Pythonic Sequence | Medium   | Comparing the     |
:           : Truthiness        :          : output of `len()` :
:           : Evaluation        :          : against zero to   :
:           :                   :          : determine if a    :
:           :                   :          : list is empty.    :
| **T1-12** | Singleton         | Medium   | Checking if a     |
:           : Identity          :          : variable is not   :
:           : Validation        :          : null by using the :
:           :                   :          : inequality        :
:           :                   :          : operator.         :
| **T1-13** | Zero-Argument     | Medium   | Explicitly        |
:           : Parent Invocation :          : passing the class :
:           :                   :          : identity and      :
:           :                   :          : `self` to         :
:           :                   :          : `super()` inside  :
:           :                   :          : overridden        :
:           :                   :          : methods.          :
| **T1-14** | Compound          | Medium   | Packing extensive |
:           : Conditional       :          : evaluation        :
:           : Decomposition     :          : clauses into a    :
:           :                   :          : single,           :
:           :                   :          : multi-line `if`   :
:           :                   :          : block.            :
| **T1-15** | Control Flow      | Medium   | Nesting one       |
:           : Nesting Reduction :          : if-statement      :
:           :                   :          : purely to check a :
:           :                   :          : secondary         :
:           :                   :          : condition         :
:           :                   :          : immediately       :
:           :                   :          : following the     :
:           :                   :          : first.            :
| **T1-16** | Utilization of    | Medium   | Fetching a key    |
:           : the Walrus        :          : from a dictionary :
:           : Operator for Loop :          : to check a        :
:           : Conditions        :          : condition, then   :
:           :                   :          : fetching it again :
:           :                   :          : inside the loop   :
:           :                   :          : body.             :
| **T1-17** | Direct Membership | Medium   | Explicitly        |
:           : Testing on        :          : calling `.keys()` :
:           : Dictionary-Like   :          : to verify key     :
:           : Objects           :          : existence.        :
| **T1-18** | Truthiness        | Medium   | Using an explicit |
:           : Fallback for      :          : `is not None`     :
:           : Optional          :          : conditional block :
:           : Iterables         :          : to safely         :
:           :                   :          : instantiate an    :
:           :                   :          : iterable from an  :
:           :                   :          : Optional value.   :
| **T1-19** | Implicit          | Medium   | Explicitly        |
:           : Truthiness of     :          : wrapping regex    :
:           : Match Objects     :          : match operations  :
:           :                   :          : in `bool()`.      :
| **T1-20** | Omission of       | Medium   | Including a       |
:           : Shebangs in       :          : shebang in a file :
:           : Library Modules   :          : that purely       :
:           :                   :          : exposes           :
:           :                   :          : functions/classes :
:           :                   :          : and has no script :
:           :                   :          : entrypoint.       :
| **T1-21** | Substitution of   | Medium   | Using the `%`     |
:           : Modulus String    :          : operator to       :
:           : Formatting with   :          : inject variables  :
:           : f-strings         :          : into a print      :
:           :                   :          : statement.        :
| **T1-22** | Elimination of    | Medium   | Returning the     |
:           : Redundant Return  :          : computed object   :
:           : Statements        :          : at the end of the :
:           :                   :          : `try` block while :
:           :                   :          : a fallback        :
:           :                   :          : identical return  :
:           :                   :          : exists outside    :
:           :                   :          : the block.        :
| **T1-23** | Idiomatic List    | Medium   | Using the         |
:           : Extensions        :          : augmented         :
:           :                   :          : assignment        :
:           :                   :          : operator `+=`     :
:           :                   :          : with a newly      :
:           :                   :          : constructed list  :
:           :                   :          : to add an         :
:           :                   :          : element.          :
| **T1-24** | Zero-Argument     | Medium   | Passing the       |
:           : Super Method      :          : explicit class    :
:           : Initialization    :          : and `self`        :
:           :                   :          : instance when     :
:           :                   :          : calling parent    :
:           :                   :          : lifecycle         :
:           :                   :          : methods.          :
| **T1-25** | Mutable Object    | Medium   | Using `nonlocal`  |
:           : Scope Resolution  :          : before calling    :
:           :                   :          : mutating methods  :
:           :                   :          : on outer-scope    :
:           :                   :          : lists or dicts.   :
| **T1-26** | Idiomatic         | Medium   | Using `if         |
:           : Fallback          :          : len(val) == 0\:`  :
:           : Assignment via    :          : to assign a       :
:           : Truthiness        :          : default string    :
:           :                   :          : state.            :
| **T1-27** | Safe DefaultDict  | High     | Using bracket     |
:           : Access to Prevent :          : notation to read  :
:           : Side-effects      :          : a potentially     :
:           :                   :          : absent key from a :
:           :                   :          : defaultdict       :
:           :                   :          : during a          :
:           :                   :          : read-only lookup. :
| **T1-28** | Idiomatic         | Medium   | Explicitly        |
:           : Falsyness Checks  :          : checking equality :
:           :                   :          : against `None`    :
:           :                   :          : for variables     :
:           :                   :          : that could be     :
:           :                   :          : empty strings or  :
:           :                   :          : iterables.        :
| **T1-29** | Truthiness for    | Medium   | Evaluating a      |
:           : String Validation :          : string variable   :
:           :                   :          : explicitly        :
:           :                   :          : against an empty  :
:           :                   :          : string after a    :
:           :                   :          : truthy check.     :
| **T1-30** | Idiomatic         | Medium   | Validating the    |
:           : Truthiness        :          : absence of items  :
:           : Validation for    :          : in a list by      :
:           : Collections       :          : explicitly        :
:           :                   :          : measuring its     :
:           :                   :          : length.           :
| **T1-31** | Removal of Legacy | Medium   | Including a utf-8 |
:           : Source Encoding   :          : encoding header   :
:           : Declarations      :          : directly beneath  :
:           :                   :          : the script        :
:           :                   :          : shebang.          :

--------------------------------------------------------------------------------

### Rules

#### T1-01: String Interpolation via F-Strings

> **Rule:** Always use Python 3 f-strings for variable interpolation. Never use
> the legacy `%` operator or manual string concatenation (`+`).
>
> **What:** Use Python 3 f-strings (PEP 498) instead of the legacy `%` operator
> or manual string concatenation (`+`) for variable interpolation.
>
> **Applies To:** All Python scripting, especially string builders for warnings,
> errors, and CLI outputs.
>
> **Why:** Legacy formatting and string concatenation created hard-to-read,
> error-prone message builders, reducing code maintainability.. Failing to
> adhere to this typically results in **Readability Degradation**.

**Trap 1: Using the modulo `%` operator to inject variables into a template
string.**

**Don't:**

```python
msg = 'failed to open %s' % file_path
```

**Do:**

```python
msg = f'failed to open {file_path}'
```

**Trap 2: Manually concatenating strings across multiple lines.**

**Don't:**

```python
warning_message = 'diff is not set '\n'for this repository:\n' + checkout_path
```

**Do:**

```python
warning_message = f'diff is not set for this repository:\n{checkout_path}'
```

--------------------------------------------------------------------------------

#### T1-02: Imperative Loops over Complex Functional Pipelines

> **Rule:** Avoid heavily nested functional transformations like `map` and
> `filter`. Always prefer explicit imperative loops utilizing the walrus
> operator (`:=`) for clarity.
>
> **What:** Avoid heavily nested functional transformations (map, filter,
> lambda). Prefer explicit imperative loops utilizing the walrus operator (`:=`)
> for clarity.
>
> **Applies To:** Data processing and validation pipelines in Python scripts.
>
> **Why:** Deeply nested functional paradigms caused cognitive overload and made
> it difficult for maintainers to trace the exact source of a validation failure
> during debugging.. Failing to adhere to this typically results in
> **Maintainability Degradation**.

**Trap 1: Chaining `set()`, `filter()`, `lambda`, and `map()` to collect
validation errors.**

**Don't:**

```python
validation_errors = set(filter(lambda x: x, map(_url_error, urls)))
```

**Do:**

```python
error_messages = []
for url in urls:
    if error := _url_error(url):
        error_messages.append(error)
```

--------------------------------------------------------------------------------

#### T1-03: Explicit Sentinel Checks over For-Else Constructs

> **Rule:** Avoid the Python `for...else` syntax. Always initialize a sentinel
> variable before the loop and evaluate it explicitly afterward.
>
> **What:** Avoid the Python `for...else` syntax. Instead, initialize a sentinel
> variable (like `None`) before the loop, break when the condition is met, and
> evaluate the sentinel explicitly after the loop.
>
> **Applies To:** Python iterators and search loops.
>
> **Why:** The `for...else` construct is considered an unintuitive Python idiom
> that frequently caused logic regressions when future maintainers misread the
> execution flow.. Failing to adhere to this typically results in **Logic
> Regression / Readability**.

**Trap 1: Placing error handling in an `else` block tied to a `for` loop.**

**Don't:**

```python
for item in collection:
    if condition(item):
        result = item
        break
else:
    DieWithError('Not found')
```

**Do:**

```python
result = None
for item in collection:
    if condition(item):
        result = item
        break
if result is None:
    DieWithError('Not found')
```

--------------------------------------------------------------------------------

#### T1-04: Descriptive Tuple Unpacking

> **Rule:** Always unpack tuples into descriptively named variables during
> iteration. Never use opaque numeric indexing.
>
> **What:** When iterating over complex compound types (like list of tuples),
> avoid opaque numeric indexing (`tuple[0]`). Unpack the tuple into
> descriptively named variables.
>
> **Applies To:** Python configuration arrays, iterators, and data pipelines.
>
> **Why:** Accessing tuple data by magic numeric indices made the loop body
> brittle and heavily dependent on knowing the upstream schema layout, slowing
> down code reviews.. Failing to adhere to this typically results in **Index
> Brittleness**.

**Trap 1: Retrieving data via hardcoded array index inside a loop.**

**Don't:**

```python
for item in formatters:
    file_types = item[0]
    format_func = item[1]
```

**Do:**

```python
for file_types, format_func, exclude_types in formatters:
    pass
```

--------------------------------------------------------------------------------

#### T1-05: Structural Uniformity in Configuration Lists

> **Rule:** Must maintain a uniform N-tuple structure for configuration arrays.
> Avoid variable-length tuples that necessitate runtime type and length
> assertions.
>
> **What:** Data structures representing a schema or configuration list should
> maintain a uniform structure (e.g., uniform N-tuples). Do not use
> variable-length tuples that necessitate runtime type/length assertions.
>
> **Applies To:** Python configuration mappings and dispatch tables.
>
> **Why:** Supporting both 2-tuples and 3-tuples in a formatter list forced
> complex `Union` type hinting and required conditional `len()` checks during
> runtime iterations, increasing cognitive load.. Failing to adhere to this
> typically results in **Type Verification Complexity**.

**Trap 1: Conditionally parsing a tuple based on its length.**

**Don't:**

```python
for item in formatters:
    exclude = item[2] if len(item) > 2 else []
```

**Do:**

```python
formatters = [ (A, B, []), (C, D, ['.html']) ]
for types, func, exclude in formatters:
    pass
```

--------------------------------------------------------------------------------

#### T1-06: Removal of Redundant String Normalization

> **Rule:** Always evaluate string manipulation chains for redundancy. Remove
> operations like `strip()` if the string has already been cleanly evaluated.
>
> **What:** String manipulation chains must be evaluated for redundancy to
> prevent unnecessary processing cycles, specifically regarding leading/trailing
> whitespace removal.
>
> **Applies To:** Python string processing logic across all internal tooling.
>
> **Why:** When chained operations remove subsets of strings, earlier global
> operations (like strip) might be sufficient, but developers often defensively
> add subsequent identical operations, causing minor performance and readability
> drag.. Failing to adhere to this typically results in **Redundant
> Operations**.

**Trap 1: Calling `.strip()` again on a string that has already had its
whitespace stripped prior to a `.removeprefix()` call.**

**Don't:**

```python
return value.strip().removeprefix("LicenseRef-").strip()
```

**Do:**

```python
return value.removeprefix("LicenseRef-").strip()
# Alternatively: value.strip().removeprefix("LicenseRef-")
```

--------------------------------------------------------------------------------

#### T1-07: Modernized String Formatting

> **Rule:** Avoid the legacy `%` string formatting operator. Must utilize modern
> Python f-strings for dynamic variable insertion.
>
> **What:** Codebases must avoid the legacy `%` string formatting operator and
> utilize modern Python f-strings for dynamic variable insertion.
>
> **Applies To:** All Python logging, diagnostics, and stdout printing.
>
> **Why:** The `%` operator leads to poor readability and frequent tuple-packing
> errors when variables increase, whereas f-strings provide inline variable
> execution.. Failing to adhere to this typically results in **Readability
> Degradation**.

**Trap 1: Using the modulo operator to inject variables into strings.**

**Don't:**

```python
print("[%s] STALL DETECTED: gclient has been silent for 5 minutes." % elapsed)
```

**Do:**

```python
print(f"[{elapsed}] STALL DETECTED: gclient has been silent for 5 minutes.")
```

--------------------------------------------------------------------------------

#### T1-08: State Encodings via StrEnum

> **Rule:** Always manage fixed sets of string identifiers using the `StrEnum`
> class. Never rely on raw string literals or ad-hoc sets.
>
> **What:** Fixed sets of string identifiers (such as application states) must
> be managed using the `StrEnum` class instead of raw string literals or ad-hoc
> sets.
>
> **Applies To:** State machines, telemetry, and configuration management.
>
> **Why:** Storing valid states as raw strings in a `frozenset` led to
> hard-coded magic strings scattered throughout the codebase, increasing typo
> risks and complicating refactors.. Failing to adhere to this typically results
> in **Magic String Proliferation**.

**Trap 1: Using a `frozenset` of strings to validate states instead of an
enumeration.**

**Don't:**

```python
VALID_EDIT_MONITOR_STATES = frozenset({'control', 'enabled'})
if state in VALID_EDIT_MONITOR_STATES:
    return state
```

**Do:**

```python
class EditMonitorState(StrEnum):
    CONTROL = 'control'
    ENABLED = 'enabled'

if state in EditMonitorState:
    return state
```

--------------------------------------------------------------------------------

#### T1-09: Single-Expression Variable Assignment (Walrus Operator)

> **Rule:** Always use the walrus operator (`:=`) to capture conditional return
> values inline. Never invoke the same method or calculation twice in a single
> conditional execution block.
>
> **What:** The Python walrus operator (`:=`) should be used to capture
> conditional return values inline, preventing the need to invoke the same
> method or calculation twice.
>
> **Applies To:** Conditional logic in Python scripts.
>
> **Why:** Previously, developers either made redundant, expensive method calls
> or explicitly declared single-use variables above an if-statement, adding
> boilerplate.. Failing to adhere to this typically results in **Redundant
> Execution**.

**Trap 1: Calling a method in an if-condition and then calling it again inside
the if-block.**

**Don't:**

```python
if self.GetBranch():
    args.extend(['--name', self.GetBranch()])
```

**Do:**

```python
if branch := self.GetBranch():
    args.extend(['--name', branch])
```

--------------------------------------------------------------------------------

#### T1-10: Idiomatic Declarative Iteration and Truthiness

> **Rule:** Replace imperative `for` loops used for simple filtering with
> declarative constructs like list comprehensions or `all()`.
>
> **What:** Imperative `for` loops used for simple collection filtering,
> mapping, or Boolean evaluations should be replaced with Pythonic declarative
> constructs (`list(filter(...))`, list comprehensions, or `all()`).
>
> **Applies To:** All Python iteration, filtering, and data transformation
> logic.
>
> **Why:** Manual imperative loops and lambda combinations inflated code size,
> reduced readability, and increased cognitive load by obfuscating simple
> condition checks.. Failing to adhere to this typically results in **High
> Cognitive Load / Code Bloat**.

**Trap 1: Using manual loops and condition checks to assert a condition holds
for all items.**

**Don't:**

```python
for license in self._extract_licenses(value):
    if not is_allowed(license):
        return False
return True
```

**Do:**

```python
return all(is_allowed(lic) for lic in self._extract_licenses(value))
```

**Trap 2: Using lambdas with filter instead of straightforward list
comprehensions.**

**Don't:**

```python
pids = list(filter(lambda x: x != 0, pids))
```

**Do:**

```python
pids = [pid for pid in pids if pid != 0]
```

**Trap 3: Checking `bool(collection)` instead of utilizing native collection
truthiness.**

**Don't:**

```python
if bool(labels) and _contains_review_enforcement_label(labels):
```

**Do:**

```python
# _contains_review_enforcement_label safely returns False for empty sets
if labels and _contains_review_enforcement_label(labels):
```

**Exceptions:** Complex control flow mechanisms involving `if-break` or
multi-step error handling that cannot be cleanly captured in a comprehension.

--------------------------------------------------------------------------------

#### T1-11: Pythonic Sequence Truthiness Evaluation

> **Rule:** Always leverage Python's implicit boolean context to evaluate
> sequences. Never explicitly check their length against zero.
>
> **What:** Leveraging Python's implicit boolean context to evaluate sequences
> (lists, strings, dicts) instead of explicitly checking their length against
> zero.
>
> **Applies To:** All Python scripts; specifically conditional statements
> evaluating sequences.
>
> **Why:** Reviewers consistently enforce PEP-8 Pythonic idioms to prevent
> verbose and non-idiomatic explicit length checks for sequence emptiness..
> Failing to adhere to this typically results in **Idiom Violation**.

**Trap 1: Comparing the output of `len()` against zero to determine if a list is
empty.**

**Don't:**

```python
if len(reasons) > 0:
    # ...
```

**Do:**

```python
if reasons:
    # ...
```

**Exceptions:** When distinguishing between an explicitly empty list `[]` and
`None` is semantically critical and not handled safely earlier in the flow.

--------------------------------------------------------------------------------

#### T1-12: Singleton Identity Validation

> **Rule:** Must enforce the use of identity operators (`is`, `is not`) when
> comparing objects against the `None` singleton.
>
> **What:** Enforcing the use of identity operators (`is`, `is not`) when
> comparing objects against the `None` singleton.
>
> **Applies To:** All Python scripts.
>
> **Why:** Relying on equality operators (`==`, `!=`) for singletons violates
> PEP-8 and can trigger unintended behaviors if classes override the `__eq__`
> method.. Failing to adhere to this typically results in **Type Checking
> Bypass**.

**Trap 1: Checking if a variable is not null by using the inequality operator.**

**Don't:**

```python
if reason != None:
    # ...
```

**Do:**

```python
if reason is not None:
    # ...
```

--------------------------------------------------------------------------------

#### T1-13: Zero-Argument Parent Invocation

> **Rule:** Always utilize Python 3's zero-argument `super()` call. Never
> explicitly pass the current class and instance parameters.
>
> **What:** Utilizing Python 3's zero-argument `super()` call instead of
> explicitly passing the current class and instance.
>
> **Applies To:** Python 3 classes, specifically overridden lifecycle methods in
> test suites.
>
> **Why:** Legacy Python 2 syntax persisted in the codebase, introducing
> unnecessary verbosity and boilerplate that obscures the core logic.. Failing
> to adhere to this typically results in **Boilerplate Accumulation**.

**Trap 1: Explicitly passing the class identity and `self` to `super()` inside
overridden methods.**

**Don't:**

```python
class SisoTest(trial_dir.TestCase):
    def setUp(self):
        super(SisoTest, self).setUp()
```

**Do:**

```python
class SisoTest(trial_dir.TestCase):
    def setUp(self):
        super().setUp()
```

--------------------------------------------------------------------------------

#### T1-14: Compound Conditional Decomposition

> **Rule:** Always break down dense, multi-part boolean logic into discrete,
> descriptively named intermediate variables.
>
> **What:** Breaking down dense, multi-part boolean logic into discrete,
> descriptively named intermediate variables.
>
> **Applies To:** Validation engines, parsing logic, and complex state
> evaluations.
>
> **Why:** Inline compound conditionals scaling multiple lines became nearly
> impossible to read or debug effectively without extreme cognitive load..
> Failing to adhere to this typically results in **Logic Obfuscation**.

**Trap 1: Packing extensive evaluation clauses into a single, multi-line `if`
block.**

**Don't:**

```python
if (cpe_prefix and not util.is_unknown(cpe_prefix) and (not version_value or util.is_not_applicable(version_value)) and not cpe_prefix_util.has_version_component(cpe_prefix)):
    # Error handling
```

**Do:**

```python
cpe_provided = cpe_prefix and not util.is_unknown(cpe_prefix)
cpe_has_version = cpe_prefix and cpe_prefix_util.has_version_component(cpe_prefix)
version_is_valid = version and not util.is_not_applicable(version)

if cpe_provided and not (version_is_valid or cpe_has_version):
    # Error handling
```

**Exceptions:** Simple, two-clause conditionals that easily fit within standard
line length limits.

--------------------------------------------------------------------------------

#### T1-15: Control Flow Nesting Reduction

> **Rule:** Always collapse adjacent conditional statements using logical `and`
> operators to reduce indentation depth.
>
> **What:** Collapsing adjacent conditional statements using logical `and`
> operators to reduce indentation depth.
>
> **Applies To:** Python conditional blocks.
>
> **Why:** Deeply nested code creates a visual pyramid of doom, increasing
> cognitive overhead and restricting horizontal screen space.. Failing to adhere
> to this typically results in **Increased Cognitive Load**.

**Trap 1: Nesting one if-statement purely to check a secondary condition
immediately following the first.**

**Don't:**

```python
if self.version:
    if self.url_is_git_clonable:
        return "sufficient"
```

**Do:**

```python
if self.version and self.url_is_git_clonable:
    return "sufficient"
```

**Exceptions:** When the secondary condition entails a side effect or requires
complex intermediate variable assignments.

--------------------------------------------------------------------------------

#### T1-16: Utilization of the Walrus Operator for Loop Conditions

> **Rule:** Must use the assignment expression (`:=`) to simultaneously assign
> and evaluate a variable within a `while` loop condition.
>
> **What:** Use the assignment expression (walrus operator `:=`) to
> simultaneously assign and evaluate a variable within a `while` loop condition,
> avoiding redundant dictionary lookups or function calls.
>
> **Applies To:** Python scripts (Python 3.8+), specifically loops dependent on
> API pagination or dynamic state fetching.
>
> **Why:** Loops polling paginated APIs previously performed multiple `.get()`
> calls per iteration to check conditions and assign values, resulting in
> unnecessarily verbose code.. Failing to adhere to this typically results in
> **Redundant Execution**.

**Trap 1: Fetching a key from a dictionary to check a condition, then fetching
it again inside the loop body.**

**Don't:**

```python
last_result = fetch(query_params)
while last_result.get('next') and len(commits) < limit:
  query_params['s'] = last_result.get('next')
```

**Do:**

```python
last_result = fetch(query_params)
while (next_page := last_result.get('next', '')) and len(commits) < limit:
  query_params['s'] = next_page
```

--------------------------------------------------------------------------------

#### T1-17: Direct Membership Testing on Dictionary-Like Objects

> **Rule:** Perform `in` checks directly on dictionary-like objects. Never
> invoke `.keys()` for existence verification.
>
> **What:** When checking if a key exists in a dictionary or dictionary-like
> object (e.g., `os.environ`), perform the `in` check directly on the object
> rather than invoking `.keys()`.
>
> **Applies To:** Python scripting, particularly environment variable checks.
>
> **Why:** Developers used `.keys()` on `os.environ`, which creates an
> unnecessary list in Python 2 or a view object in Python 3, slightly impacting
> performance and degrading idiomatic readability.. Failing to adhere to this
> typically results in **Suboptimal Performance**.

**Trap 1: Explicitly calling `.keys()` to verify key existence.**

**Don't:**

```python
if os.path.isfile(RC_FILE) and 'PYLINTRC' not in os.environ.keys():
    os.environ['PYLINTRC'] = RC_FILE
```

**Do:**

```python
if os.path.isfile(RC_FILE) and 'PYLINTRC' not in os.environ:
    os.environ['PYLINTRC'] = RC_FILE
```

--------------------------------------------------------------------------------

#### T1-18: Truthiness Fallback for Optional Iterables

> **Rule:** Always use the logical `or` operator to provide a safe default for
> iterables that may return `None`.
>
> **What:** Use the logical `or` operator to provide a safe default for
> iterables that may return `None`, replacing multi-line conditional `None`
> checks.
>
> **Applies To:** Python scripts; specifically when initializing collections
> (like sets or lists) from properties or function returns that evaluate to
> Optional types.
>
> **Why:** Code originally instantiated an empty set and selectively updated it
> via a conditional block if the returned property was not None, resulting in
> unnecessary boilerplate.. Failing to adhere to this typically results in
> **Unnecessary Branching**.

**Trap 1: Using an explicit `is not None` conditional block to safely
instantiate an iterable from an Optional value.**

**Don't:**

```python
mitigated_values = self._return_as_property(known_fields.MITIGATED)
mitigated_ids = set()
if mitigated_values is not None:
    mitigated_ids = set(mitigated_values)
```

**Do:**

```python
mitigated_values = self._return_as_property(known_fields.MITIGATED)
mitigated_ids = set(mitigated_values or [])
```

--------------------------------------------------------------------------------

#### T1-19: Implicit Truthiness of Match Objects

> **Rule:** Always leverage native truthiness evaluation for regex match
> objects. Never explicitly cast them to boolean values via `bool()`.
>
> **What:** Leverage Python's native truthiness evaluation instead of explicitly
> casting regex match objects to boolean values.
>
> **Applies To:** Python conditionals evaluating `re.match()`, `re.search()`, or
> `re.fullmatch()`.
>
> **Why:** A regex validation check wrapped the return value of `.match()` in a
> `bool()` call, creating unnecessary overhead since non-empty match objects
> inherently evaluate to True.. Failing to adhere to this typically results in
> **Redundant Type Casting**.

**Trap 1: Explicitly wrapping regex match operations in `bool()`.**

**Don't:**

```python
if bool(_VULN_ID_PATTERN.match(cve_stripped)):
    valid_cves.append(cve_stripped)
```

**Do:**

```python
if _VULN_ID_PATTERN.match(cve_stripped):
    valid_cves.append(cve_stripped)
```

--------------------------------------------------------------------------------

#### T1-20: Omission of Shebangs in Library Modules

> **Rule:** Never include a shebang in Python modules designed solely for import
> by other scripts.
>
> **What:** Python modules designed solely for import and consumption by other
> scripts (lacking a `if __name__ == '__main__':` block) must not include a
> shebang (`#!/usr/bin/env python3`) at the top of the file.
>
> **Applies To:** Python library helper files (e.g.,
> `android_build_server_helper.py`).
>
> **Why:** Placing shebangs in non-executable files created ambiguity regarding
> the module's execution paradigm, suggesting it could be run directly when it
> had no entrypoint logic.. Failing to adhere to this typically results in
> **Conflicting Execution Paradigm**.

**Trap 1: Including a shebang in a file that purely exposes functions/classes
and has no script entrypoint.**

**Don't:**

```python
#!/usr/bin/env python3
# Copyright 2024 The Chromium Authors.

import os

def helper():
    pass
```

**Do:**

```python
# Copyright 2024 The Chromium Authors.

import os

def helper():
    pass
```

**Exceptions:** Files designed to be executed directly from the command line.

--------------------------------------------------------------------------------

#### T1-21: Substitution of Modulus String Formatting with f-strings

> **Rule:** Must refactor legacy modulus (`%`) based string interpolation to use
> modern Python f-strings.
>
> **What:** Legacy modulus (`%`) based string interpolation must be refactored
> to use modern Python f-strings.
>
> **Applies To:** All Python 3 scripting logic, particularly in logging and
> print statements.
>
> **Why:** The codebase relied heavily on `%r` and `%s` formatting, which is
> less readable and more error-prone than PEP 498 formatted string literals..
> Failing to adhere to this typically results in **Deprecated Language
> Construct**.

**Trap 1: Using the `%` operator to inject variables into a print statement.**

**Don't:**

```python
print('Using Gerrit host: %r' % host)
```

**Do:**

```python
print(f'Using Gerrit host: {host!r}')
```

--------------------------------------------------------------------------------

#### T1-22: Elimination of Redundant Return Statements

> **Rule:** Always remove redundant return statements nested at the end of a
> `try` block if the identical variable is returned unconditionally immediately
> after.
>
> **What:** Redundant return statements nested at the end of a `try` block must
> be removed if the identical variable is returned unconditionally immediately
> after the block.
>
> **Applies To:** Exception handling blocks (`try`/`except`) in Python scripts.
>
> **Why:** Developers duplicated return logic both inside and outside of `try`
> blocks, which cluttered the control flow and provided no functional
> advantage.. Failing to adhere to this typically results in **Dead/Redundant
> Code**.

**Trap 1: Returning the computed object at the end of the `try` block while a
fallback identical return exists outside the block.**

**Don't:**

```python
try:
    spec.loader.exec_module(module)
    return module
except Exception:
    raise
return module
```

**Do:**

```python
try:
    spec.loader.exec_module(module)
except Exception:
    raise
return module
```

--------------------------------------------------------------------------------

#### T1-23: Idiomatic List Extensions

> **Rule:** Always use the idiomatic `list.append()` or `.extend()` when
> appending items to a list. Avoid the inline concatenation operator (`+=`) for
> single elements.
>
> **What:** When appending items to a list, use the idiomatic `list.append()`
> (or `.extend()`) rather than the inline concatenation operator (`+=`).
>
> **Applies To:** Python list modification operations, specifically when
> building command-line argument arrays.
>
> **Why:** Creating single-element lists purely to use the `+=` operator creates
> unnecessary intermediate array allocations and is considered unidiomatic in
> modern Python.. Failing to adhere to this typically results in **Suboptimal
> Memory Allocation**.

**Trap 1: Using the augmented assignment operator `+=` with a newly constructed
list to add an element.**

**Don't:**

```python
cmd = ['ls-remote']
if tags:
    cmd += ['-t']
```

**Do:**

```python
cmd = ['ls-remote']
if tags:
    cmd.append('-t')
```

**Exceptions:** When concatenating two pre-existing lists of dynamically sized
data.

--------------------------------------------------------------------------------

#### T1-24: Zero-Argument Super Method Initialization

> **Rule:** Must utilize the parameterless `super()` syntax for Python 3 class
> initializers and lifecycle hooks.
>
> **What:** Python 3 class initializers and lifecycle hooks must utilize the
> parameterless `super()` syntax instead of passing class names and instances
> explicitly.
>
> **Applies To:** Object-oriented Python configurations, specifically `setUp`
> and `tearDown` methods in Unittest definitions.
>
> **Why:** The codebase contained legacy Python 2 era `super(Class, self)`
> declarations which are verbose, redundant, and more prone to maintenance
> errors if class names change.. Failing to adhere to this typically results in
> **Boilerplate Redundancy**.

**Trap 1: Passing the explicit class and `self` instance when calling parent
lifecycle methods.**

**Don't:**

```python
def setUp(self):
    super(GnHelperTest, self).setUp()
```

**Do:**

```python
def setUp(self):
    super().setUp()
```

--------------------------------------------------------------------------------

#### T1-25: Mutable Object Scope Resolution

> **Rule:** Never use the `nonlocal` keyword when mutating an existing mutable
> object inside a nested function.
>
> **What:** When mutating an existing mutable object (such as appending to a
> list) inside a nested function, the `nonlocal` keyword is unnecessary and
> should be omitted.
>
> **Applies To:** Nested functions in Python modifying mutable outer-scope
> collections.
>
> **Why:** A developer used `nonlocal` for a list variable before calling
> `.append()`, implying a reassignment in the outer scope, which is
> syntactically unnecessary and reduces idiomatic clarity.. Failing to adhere to
> this typically results in **Redundant Syntax / Scope Confusion**.

**Trap 1: Using `nonlocal` before calling mutating methods on outer-scope lists
or dicts.**

**Don't:**

```python
def _mock_urlopen(request, timeout=0):
    nonlocal mock_open_times
    mock_open_times.append(datetime.datetime.now())
```

**Do:**

```python
def _mock_urlopen(request, timeout=0):
    mock_open_times.append(datetime.datetime.now())
```

--------------------------------------------------------------------------------

#### T1-26: Idiomatic Fallback Assignment via Truthiness

> **Rule:** Always use the `or` operator to provide fallback values for falsy
> objects. Avoid multi-line conditional length checks.
>
> **What:** Use the `or` operator to provide fallback values for falsy objects
> instead of writing multi-line conditional length checks.
>
> **Applies To:** Python variable initialization, default assignments, and
> string parsing logic.
>
> **Why:** Code unnecessarily checked string length to conditionally assign a
> default fallback value, increasing vertical verbosity without adding
> conceptual clarity.. Failing to adhere to this typically results in **Verbose
> Non-Idiomatic Syntax**.

**Trap 1: Using `if len(val) == 0:` to assign a default string state.**

**Don't:**

```python
tag = '.'.join(str(x) for x in get_git_version())
if len(tag) == 0:
    tag = 'unknown'
```

**Do:**

```python
tag = '.'.join(str(x) for x in get_git_version()) or 'unknown'
```

**Exceptions:** When an empty string is a valid, required state that should
explicitly override a fallback.

--------------------------------------------------------------------------------

#### T1-27: Safe DefaultDict Access to Prevent Side-effects

> **Rule:** Always use the `.get()` method instead of bracket notation when
> querying a `defaultdict` to prevent unintended instantiation.
>
> **What:** When querying a `defaultdict`, use the `.get()` method instead of
> bracket notation to prevent unintended instantiation of default elements.
>
> **Applies To:** Python dictionary access, particularly when interacting with
> lazily-loaded configuration caches or graphs.
>
> **Why:** Using bracket access `["default"]` on a cached `defaultdict`
> accidentally modified its state during a read-only operation, creating a
> dangling key.. Failing to adhere to this typically results in **Unintended
> State Mutation / Memory Leak**.

**Trap 1: Using bracket notation to read a potentially absent key from a
defaultdict during a read-only lookup.**

**Don't:**

```python
return list(self._maybe_load_config()["default"].get(key, ()))
```

**Do:**

```python
return list(self._maybe_load_config().get('default', {}).get(key, ()))
```

**Exceptions:** When dynamically building or explicitly populating the
`defaultdict`.

--------------------------------------------------------------------------------

#### T1-28: Idiomatic Falsyness Checks

> **Rule:** Must use the `not` keyword to evaluate truthiness or missing data.
> Avoid explicit `== None` checks unless differentiating from falsy values is
> required.
>
> **What:** Use the `not` keyword to evaluate truthiness or missing data instead
> of explicit `== None` checks unless differentiating between `None` and other
> falsy values is structurally required.
>
> **Applies To:** Python conditional logic evaluating scopes, uninitialized
> variables, or collections.
>
> **Why:** A developer used `== None` extensively, which fails to trap implicit
> truthiness checks for empty strings or empty collections, leading to
> potentially fragile state evaluations.. Failing to adhere to this typically
> results in **Brittle State Evaluation / Non-Idiomatic Syntax**.

**Trap 1: Explicitly checking equality against `None` for variables that could
be empty strings or iterables.**

**Don't:**

```python
if scope == None:
    scope = "local"
```

**Do:**

```python
if not scope:
    scope = "local"
```

**Exceptions:** When `False`, `0`, or `""` are strictly valid semantic states
that must bypass a `None` check.

--------------------------------------------------------------------------------

#### T1-29: Truthiness for String Validation

> **Rule:** Never explicitly check a string against `""` if a truthiness check
> has already guaranteed it is not empty.
>
> **What:** Python string variables inherently evaluate to `False` if they are
> empty strings (`""`). Avoid explicitly checking `!= ""` when a simple
> truthiness check has already executed.
>
> **Applies To:** String validation in Python conditional statements.
>
> **Why:** A string check evaluated `(value and value != "")`, which redundantly
> verified the variable was not empty after the `value` truthiness check had
> already guaranteed it.. Failing to adhere to this typically results in
> **Non-Idiomatic Syntax**.

**Trap 1: Evaluating a string variable explicitly against an empty string after
a truthy check.**

**Don't:**

```python
if key in SENSITIVE_CONFIGS and (value and value != ""):
```

**Do:**

```python
if key in SENSITIVE_CONFIGS and value:
```

--------------------------------------------------------------------------------

#### T1-30: Idiomatic Truthiness Validation for Collections

> **Rule:** Always utilize Python's inherent truthiness to verify if a
> collection is empty. Never explicitly check its length against zero or one.
>
> **What:** When verifying if a collection (e.g., a list of arguments) is empty,
> utilize Python's inherent truthiness instead of explicitly checking its length
> against zero or one.
>
> **Applies To:** Python control flow; evaluating standard collections like
> Lists, Dicts, and Sets.
>
> **Why:** Developers previously chained redundant `not X` and `len(X) < 1`
> conditions, creating overly verbose boilerplate that violated PEP 8 idiomatic
> guidelines.. Failing to adhere to this typically results in **Verbose
> Anti-Pattern**.

**Trap 1: Validating the absence of items in a list by explicitly measuring its
length.**

**Don't:**

```python
if not args.package or len(args.package) < 1:
    parser.error('No packages specified')
```

**Do:**

```python
if not args.package:
    parser.error('No packages specified')
```

--------------------------------------------------------------------------------

#### T1-31: Removal of Legacy Source Encoding Declarations

> **Rule:** Must remove explicit `# coding=utf-8` pragmas at the top of Python 3
> files.
>
> **What:** Explicit `# coding=utf-8` pragmas at the top of Python files are
> redundant in modern Python 3, which assumes UTF-8 by default, and must be
> removed.
>
> **Applies To:** Python 3 module headers.
>
> **Why:** Code ported from Python 2 retained explicit encoding declarations,
> adding unnecessary boilerplate that provided no operational benefit in the
> Python 3 runtime.. Failing to adhere to this typically results in
> **Boilerplate Bloat**.

**Trap 1: Including a utf-8 encoding header directly beneath the script
shebang.**

**Don't:**

```python
#!/usr/bin/env vpython3
# coding=utf-8
# Copyright...
```

**Do:**

```python
#!/usr/bin/env vpython3
# Copyright...
```

**Exceptions:** If the source file relies on a non-standard, legacy character
encoding (which is generally discouraged).

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T3 | Static Type Hinting & Safety - *Uniform data structures
    enforced here prevent complex Union type definitions and simplify static
    type validation overhead.*
*   **Downstream:** T5 | Code Formatting & Structural Style - *Modernizing
    syntax via f-strings and walrus operators intrinsically alters line lengths
    and structural style constraints.*

## Chapter: Commit Message Metadata & Hygiene

**Context:** This domain enforces rigorous version control history standards by
mandating strict 50/72 character limits, explicit bug traceability, and
intent-focused documentation. These practices guarantee automated tooling
compatibility and preserve critical architectural rationale for future
maintainers.

### Summary

| Rule ID   | Principle / Constraint    | Priority | Primary Symptom / Trap    |
| :-------- | :------------------------ | :------- | :------------------------ |
| **T2-01** | Contiguous Git Footer     | High     | Placing a newline between |
:           : Formatting                :          : the Bug tracker ID and    :
:           :                           :          : the Change-Id.            :
| **T2-02** | Intent-Focused Commit     | Medium   | Writing commit messages   |
:           : Message Structuring       :          : that document the         :
:           :                           :          : discarded implementations :
:           :                           :          : or granular syntax        :
:           :                           :          : changes instead of the    :
:           :                           :          : goal.                     :
| **T2-03** | Mandatory Issue Tracker   | High     | Submitting a functional   |
:           : Traceability              :          : logic change without      :
:           :                           :          : linking it to an issue    :
:           :                           :          : ticket.                   :
| **T2-04** | Documentation of          | High     | Stating only the commands |
:           : Engineering Rationale in  :          : that were changed without :
:           : Commits                   :          : explaining the underlying :
:           :                           :          : constraint.               :
| **T2-05** | Synchronized Commit Logs  | High     | Leaving original          |
:           : During Architecture       :          : architectural             :
:           : Changes                   :          : descriptions in the       :
:           :                           :          : commit message despite    :
:           :                           :          : altering the mechanics    :
:           :                           :          : during review.            :
| **T2-06** | Component Scoping and     | Medium   | Writing an unbounded      |
:           : Length Limits in Commit   :          : commit header that lacks  :
:           : Headers                   :          : tool-specific scoping.    :
| **T2-07** | Commit Metadata           | Medium   | Omitting a space after    |
:           : Formatting and Typo       :          : the metadata tag colon.   :
:           : Enforcement               :          :                           :
| **T2-08** | Commit Bug Traceability   | High     | Failing to add a `Bug:`   |
:           :                           :          : trailer when closing or   :
:           :                           :          : referencing a tracked     :
:           :                           :          : issue.                    :
| **T2-09** | Internal Jargon           | Medium   | Describing the            |
:           : Sanitization              :          : architecture using        :
:           :                           :          : internal codenames.       :
| **T2-10** | Commit Header Length      | Medium   | Writing an essay-style    |
:           : Enforcement               :          : introductory sentence for :
:           :                           :          : the commit.               :
| **T2-11** | Change-Id Footer Ordering | Medium   | Appending generic tags or |
:           :                           :          : signatures after the      :
:           :                           :          : Change-Id.                :
| **T2-12** | Sanitization of Internal  | High     | Pasting internal          |
:           : Issue Tracker Links       :          : corporate issue tracker   :
:           :                           :          : URLs directly into the    :
:           :                           :          : commit message body.      :
| **T2-13** | Standardized Public Bug   | High     | Using the internal 'b/'   |
:           : Tracker Notation          :          : prefix for a public issue :
:           :                           :          : tracker ID.               :
| **T2-14** | Commit Message Footer     | High     | Leaving multiple          |
:           : Formatting and Redundancy :          : Change-Id tags or         :
:           : Checks                    :          : redundant subject lines   :
:           :                           :          : at the bottom of the      :
:           :                           :          : commit message.           :
| **T2-15** | Cross-Repository          | High     | Omitting external patch   |
:           : Traceability Links in     :          : URLs when                 :
:           : Commits                   :          : cross-repository          :
:           :                           :          : coordination is required. :
| **T2-16** | Action-Oriented Commit    | Medium   | Writing a commit subject  |
:           : Subjects                  :          : that describes an         :
:           :                           :          : ecosystem observation     :
:           :                           :          : rather than the patch     :
:           :                           :          : action.                   :
| **T2-17** | Strict Spelling Accuracy  | Medium   | Incorrectly identifying   |
:           : for Infrastructure        :          : an internal continuous    :
:           : Services in Commit Logs   :          : integration tool by       :
:           :                           :          : conflating it with a      :
:           :                           :          : commercial product of a   :
:           :                           :          : similar name.             :
| **T2-18** | Descriptive Specificity   | High     | Writing a commit subject  |
:           : in Commit Context         :          : that names the file but   :
:           :                           :          : omits the state or        :
:           :                           :          : condition that failed.    :
| **T2-19** | Commit Message 50/72 Line | High     | Writing continuous        |
:           : Limit Enforcement         :          : paragraphs in a commit    :
:           :                           :          : body without manual line  :
:           :                           :          : wrapping.                 :
| **T2-20** | Commit Message Subject    | Medium   | Writing a commit subject  |
:           : Action Verbs and          :          : that merely lists a       :
:           : Contextual Elaboration    :          : function or component     :
:           :                           :          : name without describing   :
:           :                           :          : the action taken.         :
| **T2-21** | Mandatory Bug Tracker     | High     | Submitting a large        |
:           : Traceability for          :          : feature or refactor       :
:           : Significant Changes       :          : without a linked issue    :
:           :                           :          : tracker reference.        :

--------------------------------------------------------------------------------

### Rules

#### T2-01: Contiguous Git Footer Formatting

> **Rule:** Always place Git metadata footers continuously at the absolute end
> of the commit message without inserting empty lines between tags.
>
> **What:** Git metadata footers (e.g., Bug:, Change-Id:) must be placed
> continuously at the absolute end of the commit message with no intervening
> empty lines.
>
> **Applies To:** Commit message hooks, Gerrit, and version control CI
> pipelines.
>
> **Why:** Trailing blank lines or incorrectly placed footers caused automated
> commit parsers and bug tracking pipelines to fail to link issues with code
> changes. Failing to adhere to this typically results in **Automated Parsing
> Failure**.

**Trap 1: Placing a newline between the Bug tracker ID and the Change-Id.**

**Don't:**

*   Bug: 123456\n\nChange-Id: I987654

**Do:**

*   Bug: 123456\nChange-Id: I987654

**Trap 2: Including redundant custom tags that CI already handles.**

**Don't:**

*   Test: run local CQ\nBug: 123456\nChange-Id: I987654

**Do:**

*   Bug: 123456\nChange-Id: I987654

--------------------------------------------------------------------------------

#### T2-02: Intent-Focused Commit Message Structuring

> **Rule:** Must focus commit message descriptions on overarching system goals
> rather than polluting the history with discarded mechanical implementations.
>
> **What:** Commit message subjects and descriptions must focus on what the
> change achieves at a system level, rather than detailing the mechanical
> implementation ("how") or the considered alternatives.
>
> **Applies To:** Global version control hygiene.
>
> **Why:** Commit histories filled with mechanical descriptions make it
> difficult for maintainers to quickly assess the architectural impact or
> feature intent during git bisect operations. Failing to adhere to this
> typically results in **Historical Obfuscation**.

**Trap 1: Writing commit messages that document the discarded implementations or
granular syntax changes instead of the goal.**

**Don't:**

*   Update regex matching because string splitting was too complex and failed on
    edge cases.

**Do:**

*   Consolidate validation rules to improve parsing reliability of malformed
    inputs.

--------------------------------------------------------------------------------

#### T2-03: Mandatory Issue Tracker Traceability

> **Rule:** Always link functional logic changes to an explicit issue tracker
> ticket via metadata footers.
>
> **What:** Commits must include an explicit reference to the underlying issue
> tracker item (e.g., Bug: <number>) in their metadata footers.
>
> **Applies To:** Commit message footers for all infrastructure code changes.
>
> **Why:** Without bug linkage, tracking the business or operational reason for
> a code change becomes impossible once the original author departs. Failing to
> adhere to this typically results in **Orphaned Commits**.

**Trap 1: Submitting a functional logic change without linking it to an issue
ticket.**

**Don't:**

*   Fix parsing error in license allowlist.<br><br>Change-Id: I123456...

**Do:**

*   Fix parsing error in license allowlist.<br><br>Bug: 504850951<br>Change-Id: I123456...

--------------------------------------------------------------------------------

#### T2-04: Documentation of Engineering Rationale in Commits

> **Rule:** Must explicitly document the underlying engineering rationale and
> performance constraints driving algorithmic or toolset changes.
>
> **What:** Commit messages must document the engineering rationale (the "why")
> behind algorithmic changes or tool substitutions, explicitly noting
> performance bottlenecks or system constraints that triggered the change.
>
> **Applies To:** Commit message descriptions for performance optimizations or
> toolset replacements.
>
> **Why:** When a simple operation (`gc`) was replaced by four complex
> operations (`incremental-repack`, `commit-graph`, etc.), future maintainers
> had no context on why the simpler approach was abandoned, increasing the risk
> of regressions. Failing to adhere to this typically results in **Loss of
> Historical Context**.

**Trap 1: Stating only the commands that were changed without explaining the
underlying constraint.**

**Don't:**

*   Switch from running `git maintenance run --task gc` to running granular
    tasks like repack and commit-graph.

**Do:**

*   Replace `git maintenance run --task gc` with granular tasks
    (incremental-repack, commit-graph) because the monolithic `gc` task was
    taking too long and stalling execution.

--------------------------------------------------------------------------------

#### T2-05: Synchronized Commit Logs During Architecture Changes

> **Rule:** Always retroactively update commit logs to accurately reflect the
> final implementation if mechanics are altered during code review.
>
> **What:** The commit log description must be retroactively updated to maintain
> parity with the final implementation if the execution strategy or API usage
> changes significantly during code review.
>
> **Applies To:** Commit message finalization.
>
> **Why:** An initial patchset utilized `os.execv` but was changed to
> `subprocess.call` during review. Because the commit message was not updated,
> the repository history falsely claimed the tool was altering process images.
> Failing to adhere to this typically results in **Desynchronized
> Documentation**.

**Trap 1: Leaving original architectural descriptions in the commit message
despite altering the mechanics during review.**

**Don't:**

*   Implement wrapper tool. Uses os.execv to replace the current process.

**Do:**

*   Implement wrapper tool. Uses subprocess.call to execute the target command
    and return the exit code.

--------------------------------------------------------------------------------

#### T2-06: Component Scoping and Length Limits in Commit Headers

> **Rule:** Must cap commit message headers at 72 characters and prefix them
> with the specific subsystem or tool name.
>
> **What:** Commit message headers must be strictly capped at 72 characters and
> prefixed with the specific tool or subsystem name (e.g., `siso:`,
> `autoninja:`) to isolate scope and ensure log searchability.
>
> **Applies To:** All commit messages affecting mono-repos or multi-tool suites
> (like depot_tools).
>
> **Why:** Unscoped or overly verbose commit headers caused the git log to
> become unreadable, making it difficult to distinguish which specific CLI tool
> or script a telemetry or flag fix applied to. Failing to adhere to this
> typically results in **Truncated History / Opaque Logs**.

**Trap 1: Writing an unbounded commit header that lacks tool-specific scoping.**

**Don't:**

*   Fix enabling cloud telemetry flags for the build runner tool so it logs
    metrics

**Do:**

*   siso: Fix enabling cloud telemetry flags

**Trap 2: Failing to document the actual rationale (the 'Why') in the commit
message or issue tracker.**

**Don't:**

*   CL Description: Updated the telemetry parameter indices.

**Do:**

*   CL Description: Updated the telemetry parameter indices because the previous
    version caused silent drops in metrics collection during remote builds.

--------------------------------------------------------------------------------

#### T2-07: Commit Metadata Formatting and Typo Enforcement

> **Rule:** Must maintain strict typographic accuracy and exact spacing rules
> for metadata footers.
>
> **What:** Commit messages must be free of spelling errors and adhere to strict
> spacing rules for metadata footers (e.g., ensuring a space follows a tag
> colon).
>
> **Applies To:** Commit message bodies and footer blocks (e.g., Bug:,
> Change-Id:).
>
> **Why:** Automated spellcheckers flagged minor typos, which when ignored,
> reduced the professional quality of the project's history. Improperly
> formatted bug footers disrupted automated issue-tracker linking. Failing to
> adhere to this typically results in **Presubmit Rejection / Broken Issue
> Links**.

**Trap 1: Omitting a space after the metadata tag colon.**

**Don't:**

*   Bug:123456

**Do:**

*   Bug: 123456

**Trap 2: Ignoring automated spellchecker warnings rather than fixing the
typo.**

**Don't:**

*   Fix the preperation logic so it doens't fail.

**Do:**

*   Fix the preparation logic so it doesn't fail.

**Exceptions:** If the spellchecker flags a valid technical term,
`DISABLE_SPELLCHECKER` can be added to the footer.

--------------------------------------------------------------------------------

#### T2-08: Commit Bug Traceability

> **Rule:** Always enforce explicit references to external bug trackers within
> commit metadata trailers.
>
> **What:** Requiring explicit references to external bug trackers in the commit
> message metadata.
>
> **Applies To:** Version control history and commit metadata trailers.
>
> **Why:** Omitting bug links obfuscates the original intention of a patch,
> preventing future maintainers from locating the associated Gerrit or Issue
> Tracker context. Failing to adhere to this typically results in **Orphaned
> Commits**.

**Trap 1: Failing to add a `Bug:` trailer when closing or referencing a tracked
issue.**

**Don't:**

*   Commit summary.<br><br>Description of changes.<br><br>Change-Id: I12345

**Do:**

*   Commit summary.<br><br>Description of changes.<br><br>Bug: 449859271<br>Change-Id: I12345

**Exceptions:** Trivial typo fixes, formatting-only changes, or standalone CLs
with no tracked issue.

--------------------------------------------------------------------------------

#### T2-09: Internal Jargon Sanitization

> **Rule:** Never leak internal codenames or private URLs into open-source
> commit histories.
>
> **What:** Scrubbing internal codenames, architecture titles, and private URLs
> from open-source project commit histories.
>
> **Applies To:** Commit messages and code documentation bridging internal and
> open-source ecosystems.
>
> **Why:** Using internal names like 'Piper' or 'Bling' in open-source histories
> confuses external contributors who lack access to internal glossaries. Failing
> to adhere to this typically results in **Information Leakage**.

**Trap 1: Describing the architecture using internal codenames.**

**Don't:**

*   They have an external upstream, but we use the Google managed fork for Piper
    / Bling codebase.

**Do:**

*   Forked open-source projects stored in internal repos, which then get pulled
    into ios_internal.

--------------------------------------------------------------------------------

#### T2-10: Commit Header Length Enforcement

> **Rule:** Must constrain the summary line of a commit message to a strict
> maximum length for terminal compatibility.
>
> **What:** Constraining the first line of a commit message (the summary) to a
> maximum length for tooling compatibility.
>
> **Applies To:** Git commit messages.
>
> **Why:** Extremely verbose summary lines disrupt default `git log` output and
> overflow CI dashboard UIs. Failing to adhere to this typically results in
> **Log Truncation**.

**Trap 1: Writing an essay-style introductory sentence for the commit.**

**Don't:**

*   This commit refactors the dependency metadata validation engine to introduce
    new heuristics for package managers and git URLs.

**Do:**

*   Refactor dependency metadata validation engine

--------------------------------------------------------------------------------

#### T2-11: Change-Id Footer Ordering

> **Rule:** Always position the Gerrit `Change-Id` tag as the absolute final
> line in the commit message metadata block.
>
> **What:** Positioning the Gerrit `Change-Id` tag as the absolute final line in
> the commit message metadata block.
>
> **Applies To:** Gerrit-based repositories; commit trailers.
>
> **Why:** Placing other footers after the `Change-Id` can sometimes disrupt
> Gerrit hook parsing or cause visual fragmentation of the metadata block.
> Failing to adhere to this typically results in **Tooling Incompatibility**.

**Trap 1: Appending generic tags or signatures after the Change-Id.**

**Don't:**

*   Change-Id: I8912389123<br>Bug: 40861992

**Do:**

*   Bug: 40861992<br>Change-Id: I8912389123

--------------------------------------------------------------------------------

#### T2-12: Sanitization of Internal Issue Tracker Links

> **Rule:** Never include explicit links to internal organizational URLs in
> commit descriptions; use public tracking bug IDs instead.
>
> **What:** Commit descriptions must not contain links to internal
> organizational URLs (e.g., b.corp.google.com). Use public tracking bug IDs or
> reference the internal bug number in a raw format without the proprietary
> domain.
>
> **Applies To:** Git Commit Messages and Pull Request descriptions.
>
> **Why:** Internal-only tracker links were frequently left in public commit
> messages. This frustrated open-source contributors attempting to trace bug
> history and unnecessarily leaked internal infrastructural domain paths.
> Failing to adhere to this typically results in **Broken Public Traceability**.

**Trap 1: Pasting internal corporate issue tracker URLs directly into the commit
message body.**

**Don't:**

*   Fixes bug at https://b.corp.google.com/issues/12345

**Do:**

*   Fixes internal tracking bug: b/12345. Public tracker filed at
    crbug.com/67890.

**Exceptions:** Referencing the bare internal bug number (e.g., 'b/12345') is
permissible if no public Chromium issue exists yet.

--------------------------------------------------------------------------------

#### T2-13: Standardized Public Bug Tracker Notation

> **Rule:** Always omit the internal `b/` prefix when referencing public issue
> tracker bugs in metadata footers.
>
> **What:** Commit message metadata must link to a bug using the standard `Bug:
> <id>` format. For bugs hosted on public issue trackers, the internal `b/`
> prefix must be explicitly omitted.
>
> **Applies To:** Commit messages across the repository.
>
> **Why:** Contributors frequently accidentally included internal-only tracking
> prefixes (`b/`) for bugs hosted on public trackers, leading to broken link
> generation in the code review UI. Failing to adhere to this typically results
> in **Broken Link Generation**.

**Trap 1: Using the internal 'b/' prefix for a public issue tracker ID.**

**Don't:**

*   Bug: b/405286899

**Do:**

*   Bug: 405286899

**Trap 2: Omitting the bug link entirely when the commit resolves an issue.**

**Don't:**

*   Fix caching bug in credentials script.

**Do:**

*   Fix caching bug in credentials script.<br><br>Bug: 408427309

--------------------------------------------------------------------------------

#### T2-14: Commit Message Footer Formatting and Redundancy Checks

> **Rule:** Must cleanly separate metadata footers from the main body with a
> single blank line and deduplicate identical tags.
>
> **What:** Commit message footers must be well-formed, deduplicated (e.g.,
> maintaining a single valid Change-Id), and separated from the main body by a
> blank line.
>
> **Applies To:** Commit messages in Gerrit.
>
> **Why:** Git rebases and automated tooling sometimes injected redundant
> Subject lines or multiple `Change-Id` footers, which broke Gerrit's tracking
> logic and dirtied the version control history. Failing to adhere to this
> typically results in **Gerrit Tracking Failure / Dirty Log**.

**Trap 1: Leaving multiple Change-Id tags or redundant subject lines at the
bottom of the commit message.**

**Don't:**

*   Initial commit logic.<br><br>Initial commit logic.<br>Change-Id: I12345...<br>Change-Id: I8c13742...

**Do:**

*   Initial commit logic.<br><br>Change-Id: I12345...

--------------------------------------------------------------------------------

#### T2-15: Cross-Repository Traceability Links in Commits

> **Rule:** Always explicitly link downstream external code review patches when
> committing cross-repository coordinated changes.
>
> **What:** Commit messages for changes that parallel or depend on an external
> repository patch must explicitly link the downstream external code review.
>
> **Applies To:** Commit message bodies and footers.
>
> **Why:** An infrastructure-level patch modifying internal dependency
> constraints relied on a coupled change in the external `chromium/src`
> repository. The commit omitted reference to the coupled change, breaking
> historical traceability. Failing to adhere to this typically results in
> **Orphaned Dependency**.

**Trap 1: Omitting external patch URLs when cross-repository coordination is
required.**

**Don't:**

*   Fixed dependency resolution logic in presubmit.<br><br>Bug: 12345

**Do:**

*   Fixed dependency resolution logic in presubmit.<br><br>Related chromium/src side change: https://crrev.com/c/6217339<br>Bug: 12345

**Exceptions:** Isolated patches without external codebase side effects.

--------------------------------------------------------------------------------

#### T2-16: Action-Oriented Commit Subjects

> **Rule:** Must use a clear action verb in the commit message subject to
> summarize the explicit behavioral change.
>
> **What:** The commit message subject must clearly summarize the explicit code
> behavior change introduced by the patch, rather than acting as a generic
> trivia statement about system environment variables.
>
> **Applies To:** The first line (subject line) of the COMMIT_MSG file.
>
> **Why:** A commit subject described an inherent trait of Python 3 environment
> parsing on AIX rather than detailing what the patch physically forced the
> codebase to do. Failing to adhere to this typically results in **Misleading
> Log Entry**.

**Trap 1: Writing a commit subject that describes an ecosystem observation
rather than the patch action.**

**Don't:**

*   Python 3 reports 'aix' instead of 'aix6' or 'aix7'.

**Do:**

*   Always return 'aix', instead of 'aix6' or 'aix7'.

--------------------------------------------------------------------------------

#### T2-17: Strict Spelling Accuracy for Infrastructure Services in Commit Logs

> **Rule:** Always accurately spell the names of external tools or
> infrastructure services in commit logs.
>
> **What:** Commit messages must accurately and precisely spell the names of the
> external tools or infrastructure services they affect, to maintain accurate
> version control history.
>
> **Applies To:** Commit message subjects and bodies.
>
> **Why:** A developer accidentally typed 'Bitbucket' instead of 'Buildbucket'
> in a commit message, potentially misleading historical investigations into
> which CI/CD UI the patch was intended for. Failing to adhere to this typically
> results in **Inaccurate Historical Context**.

**Trap 1: Incorrectly identifying an internal continuous integration tool by
conflating it with a commercial product of a similar name.**

**Don't:**

*   Update UI presentation for Bitbucket execution runs.

**Do:**

*   Update UI presentation for Buildbucket execution runs.

--------------------------------------------------------------------------------

#### T2-18: Descriptive Specificity in Commit Context

> **Rule:** Must explicitly detail the operational context or specific failing
> state in the commit subject.
>
> **What:** Commit message subjects must strictly detail the exact operational
> context of the fix, rather than providing generic filenames and unspecific
> error mentions.
>
> **Applies To:** Git commit messages.
>
> **Why:** A generic commit subject ('Fix error in gclient_scm.py') obfuscated
> version history, forcing future reviewers to delve into the diffs to figure
> out which logical subsystem actually broke. Failing to adhere to this
> typically results in **Opaque Version History**.

**Trap 1: Writing a commit subject that names the file but omits the state or
condition that failed.**

**Don't:**

*   Fix error in gclient_scm.py

**Do:**

*   Fix error in gclient_scm.py during processing git configs

--------------------------------------------------------------------------------

#### T2-19: Commit Message 50/72 Line Limit Enforcement

> **Rule:** Always adhere to standard 50/72 formatting constraints by manually
> wrapping commit message bodies.
>
> **What:** Git commit messages must adhere to standard formatting constraints:
> summary lines must be concise, and body text must be manually wrapped at 72
> characters.
>
> **Applies To:** All Git version control history and commit logs.
>
> **Why:** A commit message contained overly long lines in its body, breaking
> standard git log readability in terminal tools and violating Chromium
> contribution rules. Failing to adhere to this typically results in
> **Unreadable Revision History**.

**Trap 1: Writing continuous paragraphs in a commit body without manual line
wrapping.**

**Don't:**

*   Avoid silently overwriting explicitly set user configs. If the user has
    explicitly set it to something else on their chromium checkout, warn rather
    than silently overwriting.

**Do:**

*   Avoid silently overwriting explicitly set user configs.<br><br>If the user has explicitly set it to something else on their<br>chromium checkout, warn rather than silently overwriting.

**Exceptions:** Hyperlinks, deeply nested directory paths, or direct
compiler/log outputs that cannot be safely wrapped.

--------------------------------------------------------------------------------

#### T2-20: Commit Message Subject Action Verbs and Contextual Elaboration

> **Rule:** Must utilize a clear action verb in the subject line and explicitly
> elaborate on the intent in the body.
>
> **What:** Commit message subject lines must utilize a clear action verb to
> describe the patch's behavior, and the body must explicitly elaborate on the
> 'why' and 'what' of the change.
>
> **Applies To:** Version control commit metadata; specifically git commit
> subjects and bodies.
>
> **Why:** When commit messages lacked descriptive verbs or rationale, it became
> difficult for future maintainers to discern the explicit intent of changes
> (e.g., preventing a build tool from running in an invalid output directory).
> Failing to adhere to this typically results in **Historical Ambiguity / Poor
> Traceability**.

**Trap 1: Writing a commit subject that merely lists a function or component
name without describing the action taken.**

**Don't:**

*   siso: checkOutdir

**Do:**

*   siso: call checkOutdir<br><br>Elaborate on why this is called, for example: to ensure Siso is not executed inside a Ninja output directory.

--------------------------------------------------------------------------------

#### T2-21: Mandatory Bug Tracker Traceability for Significant Changes

> **Rule:** Always explicitly link substantive architectural modifications to an
> issue tracking system using a `Bug:` footer.
>
> **What:** Substantive architectural or operational modifications must include
> a correctly formatted `Bug:` footer linking the version control commit to the
> issue tracking system.
>
> **Applies To:** Commit message footers for non-trivial patches.
>
> **Why:** Significant ('meaty') infrastructural changes were landed without an
> accompanying bug identifier, making it difficult during incident response to
> find the initial engineering constraints or context that necessitated the
> change. Failing to adhere to this typically results in **Disconnected Issue
> Tracking**.

**Trap 1: Submitting a large feature or refactor without a linked issue tracker
reference.**

**Don't:**

*   Refactor downstream GCS dep rolling<br><br>Change-Id: I123...

**Do:**

*   Refactor downstream GCS dep rolling<br><br>Bug: 358435510<br>Change-Id: I123...

**Exceptions:** Trivial typo fixes, formatting corrections, or minor
documentation changes.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T8 | Git Tooling & Build System Orchestration - *Commit
    headers must precisely scope build tooling wrappers like Siso and Autoninja
    to aid in telemetry and log parsing.*
*   **Downstream:** T6 | Technical Documentation & Comment Quality - *Typos and
    grammatical corrections identified during commit review directly mirror code
    docstring polish mandates.*

## Chapter: Static Type Hinting & Safety

**Context:** This chapter enforces the precise application of PEP 484 and PEP
604 type annotations to guarantee strict structural safety. It establishes
patterns for explicitly handling nullables, enforcing symmetric constraints on
inputs/outputs, and utilizing robust parameterized collections to eliminate
static analysis blindspots.

### Summary

| Rule ID   | Principle / Constraint    | Priority | Primary Symptom / Trap    |
| :-------- | :------------------------ | :------- | :------------------------ |
| **T3-01** | Strict Type Hinting for   | High     | Initializing a global     |
:           : Nullable Globals          :          : cache variable without    :
:           :                           :          : type hints.               :
| **T3-02** | Concrete Parameterized    | Medium   | Annotating a function     |
:           : Type Hinting              :          : return type with a        :
:           :                           :          : generic collection type   :
:           :                           :          : without specifying the    :
:           :                           :          : content type.             :
| **T3-03** | Precision in Static Type  | High     | Broadly typing constant   |
:           : Hinting Constraints       :          : look-up sets as Lists     :
:           :                           :          : instead of frozensets.    :
| **T3-04** | Idiomatic Type Coercion   | Medium   | Redefining variable type  |
:           : over Complex Union Types  :          : signatures to a complex   :
:           :                           :          : union to satisfy a        :
:           :                           :          : specific method call      :
:           :                           :          : later in execution.       :
| **T3-05** | Accurate Return Typing    | High     | Annotating a return type  |
:           : for Guaranteed Iterables  :          : as `Optional` when the    :
:           :                           :          : function safely yields an :
:           :                           :          : empty dictionary upon     :
:           :                           :          : falling through all       :
:           :                           :          : execution paths.          :
| **T3-06** | Exhaustive Type Hinting   | High     | Omitting parameter and    |
:           : for New Interfaces        :          : return type hints on      :
:           :                           :          : newly introduced parsing  :
:           :                           :          : helpers.                  :
| **T3-07** | Explicit Nullable States  | High     | Annotating a dataclass    |
:           : via Union Types           :          : property with a strict    :
:           :                           :          : concrete type despite     :
:           :                           :          : initialization logic      :
:           :                           :          : allowing it to remain     :
:           :                           :          : empty.                    :
| **T3-08** | Symmetric Type Hinting    | High     | Omitting the `->          |
:           : for Parameters and        :          : ReturnType\:` hint on a   :
:           : Returns                   :          : function that has         :
:           :                           :          : explicitly typed          :
:           :                           :          : parameters.               :
| **T3-09** | Explicit Optional Type    | High     | Assigning a default value |
:           : Hinting (PEP 484)         :          : of `None` to a standard   :
:           :                           :          : typed parameter.          :
| **T3-10** | Comprehensive Function    | Medium   | Omitting parameter and    |
:           : Type Signatures           :          : return type hints for     :
:           :                           :          : internal helper methods.  :
| **T3-11** | Type Hinting for          | High     | Providing type hints for  |
:           : Overloaded Implementation :          : the overload interfaces   :
:           : Signatures                :          : but leaving the actual    :
:           :                           :          : base implementation       :
:           :                           :          : implicitly untyped.       :
| **T3-12** | Structural Consistency in | High     | A variable annotated as a |
:           : Collection Type Hints     :          : List but instantiated as  :
:           :                           :          : a Set via defaultdict     :
:           :                           :          : factory.                  :
| **T3-13** | Forward Compatibility for | Critical | Using the `               |
:           : Modern Type Hinting       :          :                           :

--------------------------------------------------------------------------------

### Rules

#### T3-01: Strict Type Hinting for Nullable Globals

> **Rule:** Global cache variables initialized to `None` must be explicitly
> typed using `Optional[Type]` (or `Type | None`). Never rely on type inference
> for uninitialized globals.
>
> **What:** Global cache variables initialized to `None` must be explicitly
> typed using `Optional[Type]` (or `Type | None`) to ensure static analysis does
> not infer the variable strictly as `NoneType`.
>
> **Applies To:** Python modules utilizing global state or caching mechanics.
>
> **Why:** Global states initialized nakedly as `None` caused static
> type-checkers to raise faults or drop type safety when the variable was later
> hydrated with actual data. Failing to adhere to this typically results in
> **Static Analysis Failure**.

**Trap 1: Initializing a global cache variable without type hints.**

**Don't:**

```python
_cache_is_gce = None
```

**Do:**

```python
_cache_is_gce: Optional[bool] = None
```

--------------------------------------------------------------------------------

#### T3-02: Concrete Parameterized Type Hinting

> **Rule:** Always parameterize collection return types with their explicit
> internal types (e.g., `set[str]`). Never use generic base types.
>
> **What:** Return types for collections must be explicitly parameterized with
> their internal types (e.g., `set[str]`) rather than using generic base types
> (e.g., `set`).
>
> **Applies To:** Python Type Annotations (PEP 585) in shared internal
> libraries.
>
> **Why:** Generic annotations bypass the granular static analysis checks
> provided by tools like mypy, potentially leading to runtime type mismatches
> when retrieving objects from collections. Failing to adhere to this typically
> results in **Static Analysis Blindspots**.

**Trap 1: Annotating a function return type with a generic collection type
without specifying the content type.**

**Don't:**

```python
def load_restrictive_license_approval_textproto(path: str) -> set:
    covered = set()
    # ... logic ...
    return covered
```

**Do:**

```python
def load_restrictive_license_approval_textproto(path: str) -> set[str]:
    covered = set()
    # ... logic ...
    return covered
```

--------------------------------------------------------------------------------

#### T3-03: Precision in Static Type Hinting Constraints

> **Rule:** Type annotations must precisely reflect underlying data structures
> (e.g., `frozenset` instead of `List`), and all functions must declare explicit
> return types.
>
> **What:** Type annotations must precisely reflect the underlying data
> structures, particularly distinguishing between `List`, `Tuple`, and
> `frozenset`. All functions must declare explicit return types.
>
> **Applies To:** All Python method signatures, specifically parameter mapping
> and return types.
>
> **Why:** Incorrect type definitions (e.g., documenting a return as a List of
> Tuples when it returned a List of Strings) misaligned static analysis tools,
> creating integration risks for downstream consumers. Failing to adhere to this
> typically results in **Static Analysis Failure / Mismatched Expectations**.

**Trap 1: Broadly typing constant look-up sets as Lists instead of frozensets.**

**Don't:**

```python
def license_in_list(value: str, allow_list: List[str]) -> bool:
```

**Do:**

```python
def license_in_list(value: str, allow_list: frozenset[str]) -> bool:
```

**Trap 2: Failing to declare boolean return types on validation helper
functions.**

**Don't:**

```python
def _contains_review_enforcement_label(labels: Dict[str, str]):
```

**Do:**

```python
def _contains_review_enforcement_label(labels: Dict[str, str]) -> bool:
```

--------------------------------------------------------------------------------

#### T3-04: Idiomatic Type Coercion over Complex Union Types

> **Rule:** Avoid overloading type signatures with complex unions purely to
> satisfy library requirements; use standard primitive typing and explicitly
> cast at the call site.
>
> **What:** Avoid introducing complex union type hints just to support
> multi-type compatibility in built-in library calls. Maintain standard
> primitive typing (like `list[str]`) and explicitly cast to the required type
> at the call site.
>
> **Applies To:** Python type hinting mapping to standard library interfaces
> (e.g., `str.endswith()`).
>
> **Why:** Type signatures were overloaded to accept both strings and tuples to
> satisfy `str.endswith()`, polluting class definitions and reducing readability
> when a simple cast at runtime achieved the same safety. Failing to adhere to
> this typically results in **Type Hinting Over-complication**.

**Trap 1: Redefining variable type signatures to a complex union to satisfy a
specific method call later in execution.**

**Don't:**

```python
formatters: list[tuple[str | tuple[str, ...], FormatterFunction]] = [
    (('.gn', '.gni'), _RunGnFormat)
]
# later
paths = [p for p in diff_files if p.endswith(file_types)]
```

**Do:**

```python
formatters: list[tuple[list[str], FormatterFunction]] = [
    (['.gn', '.gni'], _RunGnFormat)
]
# later
paths = [p for p in diff_files if p.endswith(tuple(file_types))]
```

--------------------------------------------------------------------------------

#### T3-05: Accurate Return Typing for Guaranteed Iterables

> **Rule:** Never use `Optional` wrappers for iterables that are guaranteed to
> yield empty collections instead of `None`.
>
> **What:** Return type hints must accurately reflect execution guarantees. Do
> not use `Optional` wrappers for endpoints that default to returning empty
> arrays or dictionaries.
>
> **Applies To:** Python static type annotations (PEP 484) on functions,
> methods, and properties.
>
> **Why:** Properties were annotated as returning `Optional[Dict[str, str]]`,
> but the underlying logic was modified to always return a dictionary, causing
> redundant null checks downstream. Failing to adhere to this typically results
> in **TypeChecker Mismatch**.

**Trap 1: Annotating a return type as `Optional` when the function safely yields
an empty dictionary upon falling through all execution paths.**

**Don't:**

```python
@property
def mitigations(self) -> Optional[Dict[str, str]]:
    result = {}
    # ... logic ...
    return result
```

**Do:**

```python
@property
def mitigations(self) -> Dict[str, str]:
    result = {}
    # ... logic ...
    return result
```

**Exceptions:** Endpoints where `None` has distinct semantic meaning separate
from an empty collection (e.g., distinguishing 'uninitialized' from 'cleared').

--------------------------------------------------------------------------------

#### T3-06: Exhaustive Type Hinting for New Interfaces

> **Rule:** All newly introduced functions and methods must be fully annotated
> with standard library type hints prior to merging.
>
> **What:** All newly introduced functions, methods, and complex
> collection-based return types must be fully annotated with Python standard
> library `typing` hints before landing.
>
> **Applies To:** Python functions and methods.
>
> **Why:** Helper methods added to parse and format Git branch changelists
> omitted static type definitions, which violated infrastructure modernization
> protocols. Failing to adhere to this typically results in **Static Analysis
> Omission**.

**Trap 1: Omitting parameter and return type hints on newly introduced parsing
helpers.**

**Don't:**

```python
def SaveSplittingToFile(cl_infos, filename, silent=False):
```

**Do:**

```python
def SaveSplittingToFile(cl_infos: List[CLInfo], filename: str, silent=False):
```

**Exceptions:** Legacy functions pending total system refactoring where type
bounds are impossible to compute strictly.

--------------------------------------------------------------------------------

#### T3-07: Explicit Nullable States via Union Types

> **Rule:** Must explicitly annotate properties and fields initialized to or
> capable of housing `None` using `| None` or `Optional`.
>
> **What:** Dataclass fields and API properties that can be instantiated or set
> to `None` must be explicitly annotated using `| None` or `Optional` to enforce
> static type checking constraints.
>
> **Applies To:** Dataclasses and Recipe API properties handling state tracking,
> specifically Gitiles commit properties.
>
> **Why:** An output commit field was annotated with a strict type but
> conditionally set to None during execution. This divergence circumvented
> static analysis guardrails, increasing the risk of unexpected
> `AttributeError`s down the pipeline. Failing to adhere to this typically
> results in **Type Safety Violation**.

**Trap 1: Annotating a dataclass property with a strict concrete type despite
initialization logic allowing it to remain empty.**

**Don't:**

```python
out_commit: common_pb2.GitilesCommit
```

**Do:**

```python
out_commit: common_pb2.GitilesCommit | None
```

--------------------------------------------------------------------------------

#### T3-08: Symmetric Type Hinting for Parameters and Returns

> **Rule:** Always enforce symmetry; if inputs possess explicit type hints, the
> return signature must similarly be typed.
>
> **What:** If a function declares type hints for its input arguments, it must
> equally provide a strict type hint for its return value.
>
> **Applies To:** Python API surfaces, particularly translation or formatting
> utilities within tracing systems.
>
> **Why:** A translation function annotated its inputs for strict dictionary
> parsing, but failed to annotate the return output, generating blind spots in
> static analysis downstream. Failing to adhere to this typically results in
> **Static Analysis Gaps**.

**Trap 1: Omitting the `-> ReturnType:` hint on a function that has explicitly
typed parameters.**

**Don't:**

```python
def _translate_env(self, data: Dict[str, str]):
    environ = {}
    ...
    return environ
```

**Do:**

```python
def _translate_env(self, data: Dict[str, str]) -> Dict[str, str]:
    environ = {}
    ...
    return environ
```

--------------------------------------------------------------------------------

#### T3-09: Explicit Optional Type Hinting (PEP 484)

> **Rule:** Never utilize implicit optionals; default arguments of `None` must
> strictly manifest in the signature via `Optional[...]` or `| None`.
>
> **What:** Implicit optional types must be avoided. Any parameter that defaults
> to `None` must explicitly use `Optional[...]` or the union operator `| None`
> in its type signature.
>
> **Applies To:** Python function and method signatures utilizing type hints.
>
> **Why:** A sequence argument defaulted to `None` but lacked the `Optional`
> wrapper. A reviewer pointed out that PEP 484 explicitly discourages implicit
> optionals, which can cause static type checker mismatches. Failing to adhere
> to this typically results in **Static Analysis Failure**.

**Trap 1: Assigning a default value of `None` to a standard typed parameter.**

**Don't:**

```python
def __init__(self, allowed_env: Sequence[str] = None) -> None:
```

**Do:**

```python
def __init__(self, allowed_env: Optional[Sequence[str]] = None) -> None:
```

--------------------------------------------------------------------------------

#### T3-10: Comprehensive Function Type Signatures

> **Rule:** Internal helper functions must be fully type-hinted, even if they
> only handle primitive string parameters.
>
> **What:** All module-level functions, even if handling standard or generic
> types (like strings), must include explicit PEP 484 type hints for parameters
> and return types.
>
> **Applies To:** All Python function declarations, including private internal
> helpers.
>
> **Why:** A lack of explicit type hinting on script-level functions reduced IDE
> autocompletion efficacy and disabled static analysis checks, allowing type
> mismatches to propagate into runtime errors. Failing to adhere to this
> typically results in **Static Analysis Blindspot**.

**Trap 1: Omitting parameter and return type hints for internal helper
methods.**

**Don't:**

```python
def _get_deps(deps_ast):
    # ...
```

**Do:**

```python
import ast
from typing import Dict

def _get_deps(deps_ast: ast.Module) -> Dict:
    # ...
```

--------------------------------------------------------------------------------

#### T3-11: Type Hinting for Overloaded Implementation Signatures

> **Rule:** When utilizing `@typing.overload`, the underlying implementation
> function must also declare explicit type hints covering all fallback branches.
>
> **What:** When utilizing @typing.overload to define multiple valid signatures
> for an interface, the actual underlying fallback implementation function must
> also be explicitly type-hinted to enable correct static analysis of its
> internal body.
>
> **Applies To:** Python functions utilizing @typing.overload.
>
> **Why:** While overload signatures correctly validated external callers,
> omitting type hints on the implementation function itself caused static type
> checkers (like Pyright) to treat internal logic as 'Any', masking internal
> type violations. Failing to adhere to this typically results in **Internal
> Type Masking**.

**Trap 1: Providing type hints for the overload interfaces but leaving the
actual base implementation implicitly untyped.**

**Don't:**

```python
@typing.overload
def _parse_args(self, args: None) -> tuple:
    ...

@typing.overload
def _parse_args(self, args: Sequence[AnyStr]) -> tuple:
    ...

def _parse_args(self, args):
    # Type checker cannot validate `args` here
    pass
```

**Do:**

```python
@typing.overload
def _parse_args(self, args: None) -> tuple:
    ...

@typing.overload
def _parse_args(self, args: Sequence[AnyStr]) -> tuple:
    ...

def _parse_args(self, args: Sequence[AnyStr] | None) -> tuple:
    # Internal logic is fully typed and verified
    pass
```

--------------------------------------------------------------------------------

#### T3-12: Structural Consistency in Collection Type Hints

> **Rule:** Runtime instantiation logic must perfectly mirror the static type
> annotation; never annotate a Set as a List.
>
> **What:** Static type annotations for collections must accurately mirror their
> runtime instantiation logic. A variable initialized to hold unique elements
> (via a Set) cannot be type-hinted as a List.
>
> **Applies To:** Python type hinting; specifically defaultdicts and explicitly
> initialized generic collections.
>
> **Why:** Declaring a dictionary value as `List[int]` but instantiating it with
> `defaultdict(lambda: set())` caused static analyzers to assume sequence-like
> operations (like `.append()`) were valid, leading to obscured `AttributeError`
> crashes at runtime when Set methods (`.add()`) were required. Failing to
> adhere to this typically results in **Type Checker Mismatch / Method Error**.

**Trap 1: A variable annotated as a List but instantiated as a Set via
defaultdict factory.**

**Don't:**

```python
self._metadata_line_numbers: Dict[MetadataField, List[int]] = defaultdict(lambda: set())
```

**Do:**

```python
self._metadata_line_numbers: Dict[MetadataField, Set[int]] = defaultdict(lambda: set())
```

--------------------------------------------------------------------------------

#### T3-13: Forward Compatibility for Modern Type Hinting

> **Rule:** Must include `from __future__ import annotations` when utilizing PEP
> 604 type unions (`|`) in files supporting Python 3.8 environments.
>
> **What:** When leveraging modern PEP 604 type unions (the `|` operator) in a
> codebase supporting legacy environments like Python 3.8, the `from __future__
> import annotations` declaration must be included to delay annotation parsing.
>
> **Applies To:** Python files running on versions < 3.10 that use modern typing
> syntax.
>
> **Why:** The introduction of the pipe operator (`|`) for union types natively
> triggered fatal `TypeError` exceptions during module import in Python 3.8 and
> 3.9 environments, breaking infrastructure scripts. Failing to adhere to this
> typically results in **Runtime Interpreter Crash (TypeError)**.

**Trap 1: Using the `|` syntax for type hinting without enabling string-based
annotation evaluation.**

**Don't:**

```python
def run_with_stderr(*cmd, **kwargs) -> Tuple[str, str] | Tuple[bytes, bytes]:
    # Fails in Python 3.8
    pass
```

**Do:**

```python
from __future__ import annotations

def run_with_stderr(*cmd, **kwargs) -> Tuple[str, str] | Tuple[bytes, bytes]:
    # Parsed cleanly in 3.8+
    pass
```

**Exceptions:** Codebases that enforce a minimum runtime of Python 3.10+ do not
require this import.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | Python Language Idioms & Modernization - *Modernizing
    syntax deeply dictates and aligns which structural type hinting paradigms
    (such as PEP 604 unions) are valid versus deprecated.*

## Chapter: Execution Efficiency & Resource Optimization

**Context:** This domain governs the execution efficiency of Python
infrastructure tooling by strictly enforcing native library invocations over
subprocesses, lazy evaluation over eager memory allocation, and the elimination
of redundant data structure conversions.

### Summary

| Rule ID   | Principle / Constraint           | Priority | Primary Symptom /  |
:           :                                  :          : Trap               :
| :-------- | :------------------------------- | :------- | :----------------- |
| **T4-01** | Avoid Redundant Iterable         | Medium   | Passing a `list()` |
:           : Constructors                     :          : constructor output :
:           :                                  :          : directly into      :
:           :                                  :          : `sorted()`.        :
| **T4-02** | Native Python API Preference     | High     | Using              |
:           : Over Subprocess                  :          : `subprocess.run`   :
:           :                                  :          : to invoke a Python :
:           :                                  :          : module instead of  :
:           :                                  :          : importing it.      :
| **T4-03** | Hoisting Sanitization Logic out  | Medium   | Defining a list    |
:           : of Iterative Loops               :          : comprehension      :
:           :                                  :          : sanitization block :
:           :                                  :          : inside a `for`     :
:           :                                  :          : loop.              :
| **T4-04** | Delegating to Sub-Generators via | Medium   | Using a manual     |
:           : `yield from`                     :          : `for` loop to      :
:           :                                  :          : extract and yield  :
:           :                                  :          : elements from a    :
:           :                                  :          : recursive          :
:           :                                  :          : generator call.    :
| **T4-05** | Lazy Evaluation for Intermediate | High     | Using brackets     |
:           : Data Transformations             :          : `[]` to force a    :
:           :                                  :          : list allocation    :
:           :                                  :          : just before        :
:           :                                  :          : dumping the        :
:           :                                  :          : elements into an   :
:           :                                  :          : extension          :
:           :                                  :          : mechanism.         :
| **T4-06** | Direct JSON Stream Parsing       | Medium   | Chaining           |
:           :                                  :          : `.read().decode()` :
:           :                                  :          : with               :
:           :                                  :          : `json.loads()` on  :
:           :                                  :          : file-like objects. :
| **T4-07** | Elimination of Redundant Sorted  | Medium   | Explicitly casting |
:           : List Coercion                    :          : the result of      :
:           :                                  :          : `sorted(...)` to a :
:           :                                  :          : list.              :

--------------------------------------------------------------------------------

### Rules

#### T4-01: Avoid Redundant Iterable Constructors

> **Rule:** Never wrap iterables in a `list()` constructor immediately prior to
> passing them into built-in functions that inherently consume iterables.
>
> **What:** Do not wrap iterables (such as sets or generators) in a `list()`
> constructor immediately prior to passing them into built-in functions like
> `sorted()` which inherently consume iterables.
>
> **Applies To:** Python data processing and sorting logic.
>
> **Why:** Creating temporary lists just to sort them introduced unnecessary
> O(N) memory allocations, degrading script execution efficiency. Failing to
> adhere to this typically results in **Memory Overhead**.

**Trap 1: Passing a `list()` constructor output directly into `sorted()`.**

**Don't:**

```python
additional=sorted(list(validation_errors))
```

**Do:**

```python
additional=sorted(validation_errors)
```

--------------------------------------------------------------------------------

#### T4-02: Native Python API Preference Over Subprocess

> **Rule:** Always invoke the native library API directly rather than spawning
> external `subprocess` executions when a Python equivalent is available.
>
> **What:** Whenever an external command-line tool offers a native Python
> library equivalent (such as `mdformat`), internal tooling must invoke the
> library API directly rather than spawning `subprocess` executions.
>
> **Applies To:** Python infrastructure wrappers and automation scripts.
>
> **Why:** Repeatedly spawning subprocesses to call Python scripts from within
> Python scripts introduced significant execution latency due to Python
> interpreter startup overhead. Failing to adhere to this typically results in
> **Execution Latency / High Overhead**.

**Trap 1: Using `subprocess.run` to invoke a Python module instead of importing
it.**

**Don't:**

```python
cmd = [sys.executable, '-m', 'mdformat', '-']
proc = subprocess.run(cmd, input=text.encode('utf-8'))
```

**Do:**

```python
import mdformat
formatted_text = mdformat.text(text)
```

--------------------------------------------------------------------------------

#### T4-03: Hoisting Sanitization Logic out of Iterative Loops

> **Rule:** Must hoist data sanitization and list processing logic outside of
> nested assertion or evaluation loops.
>
> **What:** Data sanitization or list processing logic must be hoisted outside
> of nested assertion or evaluation loops to prevent redundant O(N*M) execution
> and unnecessary memory allocation.
>
> **Applies To:** Unit testing and dataset validation pipelines.
>
> **Why:** Re-sanitizing output lines inside a checking loop resulted in
> repeating string replacement and array allocation unnecessarily, dragging down
> execution performance. Failing to adhere to this typically results in **O(N*M)
> Time Complexity / Redundant Allocation**.

**Trap 1: Defining a list comprehension sanitization block inside a `for`
loop.**

**Don't:**

```python
for expected in expected_results:
    sanitized_results = [r.replace('\n', ' ') for r in results]
    self.assertTrue(any(expected in r for r in sanitized_results))
```

**Do:**

```python
sanitized_results = [r.replace('\n', ' ') for r in results]
for expected in expected_results:
    self.assertTrue(any(expected in r for r in sanitized_results))
```

**Trap 2: Assigning an intermediate list to a variable that is immediately
redundantly cast to a list.**

**Don't:**

```python
sanitized_results = [r.replace('\n', ' ') for r in results]
unmatched_results = list(sanitized_results)
```

**Do:**

```python
unmatched_results = [r.replace('\n', ' ') for r in results]
```

--------------------------------------------------------------------------------

#### T4-04: Delegating to Sub-Generators via `yield from`

> **Rule:** Always use `yield from` instead of implementing an explicit `for`
> loop when a generator function delegates to another generator.
>
> **What:** When a generator function yields values strictly from another
> generator or iterable, use `yield from` instead of implementing an explicit
> `for` loop.
>
> **Applies To:** Python generator functions and recursive parse routines.
>
> **Why:** Explicit iteration over recursive sub-generators created execution
> inefficiencies and cluttered the code block, missing the optimizations present
> in native PEP 380 `yield from`. Failing to adhere to this typically results in
> **Execution Inefficiency**.

**Trap 1: Using a manual `for` loop to extract and yield elements from a
recursive generator call.**

**Don't:**

```python
for import_line in _gn_lines(output_dir, import_path):
    yield import_line
```

**Do:**

```python
yield from _gn_lines(output_dir, import_path)
```

**Exceptions:** When intermediate transformation of the yielded value is
required before propagating it up the stack.

--------------------------------------------------------------------------------

#### T4-05: Lazy Evaluation for Intermediate Data Transformations

> **Rule:** Must replace eager list comprehensions with lazy generator
> expressions when the resulting dataset is immediately consumed by secondary
> iteration.
>
> **What:** Replace list comprehensions with generator expressions when the
> resulting dataset is immediately consumed by a secondary iteration (e.g.,
> `list.extend()`), avoiding unnecessary intermediate memory allocations.
>
> **Applies To:** Python data transformation pipelines, specifically Telemetry
> span filtering and queuing operations.
>
> **Why:** A list comprehension was used to pre-filter and parse large telemetry
> spans, forcing the entire transformed array into memory before loading it into
> a queue, risking memory inflation. Failing to adhere to this typically results
> in **Excessive Memory Allocation**.

**Trap 1: Using brackets `[]` to force a list allocation just before dumping the
elements into an extension mechanism.**

**Don't:**

```python
spans = [self._prefilter(self._translate_span(s)) for s in spans]
self._queue.extend(spans)
```

**Do:**

```python
spans = (self._prefilter(self._translate_span(s)) for s in spans)
self._queue.extend(spans)
```

**Exceptions:** When the transformed array must be randomly accessed, counted
with `len()`, or mutated prior to its final queue push.

--------------------------------------------------------------------------------

#### T4-06: Direct JSON Stream Parsing

> **Rule:** Always leverage standard library stream parsing methods rather than
> manually decoding bytes into intermediate memory buffers.
>
> **What:** Leverage standard library stream parsing methods (`json.load()`)
> instead of manually buffering and decoding bytes in memory.
>
> **Applies To:** Python scripts processing network requests, standard input, or
> file streams containing JSON payloads.
>
> **Why:** A script read an entire HTTP response into memory, manually decoded
> it to a string, and then parsed it using `json.loads()`, creating unnecessary
> intermediate string allocations. Failing to adhere to this typically results
> in **Inefficient Memory Allocation**.

**Trap 1: Chaining `.read().decode()` with `json.loads()` on file-like
objects.**

**Don't:**

```python
response = urllib.request.urlopen(request)
meta = json.loads(response.read().decode())
```

**Do:**

```python
response = urllib.request.urlopen(request)
meta = json.load(response)
```

**Exceptions:** When the raw payload bytes need to be inspected, hashed, or
archived prior to JSON validation.

--------------------------------------------------------------------------------

#### T4-07: Elimination of Redundant Sorted List Coercion

> **Rule:** Never wrap the output of Python's built-in `sorted()` function
> inside a `list()` constructor.
>
> **What:** Do not wrap the output of Python's built-in sorted() function inside
> a list() constructor, as sorted() intrinsically guarantees a new list as its
> return type.
>
> **Applies To:** Python data structure manipulation and iterables.
>
> **Why:** Wrapping `sorted()` with `list()` forced the interpreter to allocate
> an additional unnecessary list wrapper, wasting minimal memory but violating
> idiomatic Python expectations. Failing to adhere to this typically results in
> **Redundant Allocation Overhead**.

**Trap 1: Explicitly casting the result of `sorted(...)` to a list.**

**Don't:**

```python
return list(sorted(self._metadata_line_numbers[field]))
```

**Do:**

```python
return sorted(self._metadata_line_numbers[field])
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | Python Language Idioms & Modernization - *Embracing
    modern Python idioms, such as generators and truthiness checks,
    fundamentally powers lazy evaluation and limits redundant memory
    allocations.*

## Chapter: Code Formatting & Structural Style

**Context:** This domain governs the structural consistency and aesthetic
hygiene of the codebase, strictly enforcing automated formatter adherence,
precise line length constraints, and import ordering. It ensures uniform
readability across development environments while eliminating subjective
stylistic churn.

### Summary

| Rule ID   | Principle /     | Priority | Primary Symptom / Trap         |
:           : Constraint      :          :                                :
| :-------- | :-------------- | :------- | :----------------------------- |
| **T5-01** | Unused Module   | Medium   | Leaving an import statement    |
:           : Imports Removal :          : intact after removing the last :
:           :                 :          : reference to its methods.      :
| **T5-02** | Manual Line     | Medium   | Leaving a single continuous    |
:           : Wrapping in     :          : string across >100 columns     :
:           : YAML            :          : because the auto-formatter     :
:           : Frontmatter     :          : ignored it.                    :
| **T5-03** | Automated       | High     | Manually aligning dictionary   |
:           : Formatting      :          : keys and values to 'look       :
:           : Adherence       :          : nice', violating the automated :
:           :                 :          : tool's constraints.            :
| **T5-04** | Contextual      | Medium   | Injecting double-quoted        |
:           : Quotation Mark  :          : strings into a file that       :
:           : Consistency     :          : exclusively uses single        :
:           :                 :          : quotes.                        :
| **T5-05** | Prohibition of  | Medium   | Padding spaces to push         |
:           : Vertical        :          : backslashes into a single      :
:           : Padding in      :          : vertical column.               :
:           : Shell Examples  :          :                                :
| **T5-06** | Global Import   | Medium   | Placing an `import json`       |
:           : Placement       :          : statement inside a mock or     :
:           :                 :          : unit test method.              :
| **T5-07** | Preservation of | Medium   | Accepting an auto-formatter's  |
:           : Semantic        :          : output that collapses          :
:           : Vertical        :          : intentional paragraph spacing. :
:           : Whitespace      :          :                                :
| **T5-08** | Uniform String  | Medium   | Injecting single quotes into a |
:           : Quotation       :          : file that predominantly uses   :
:           : Styles          :          : double quotes.                 :
| **T5-09** | Line Length     | Medium   | Failing automated builds due   |
:           : Constraint      :          : to Python lines exceeding 80   :
:           : Suspension      :          : columns.                       :
| **T5-10** | Log Message and | Medium   | Breaking a single logical log  |
:           : Constant String :          : or error message across        :
:           : Line Length     :          : multiple lines to meet column  :
:           : Exemption       :          : limits.                        :
| **T5-11** | 4-Space         | Medium   | Using 2 spaces to indent       |
:           : Docstring       :          : argument descriptions under    :
:           : Parameter       :          : the `Args\:` docstring header. :
:           : Indentation     :          :                                :
| **T5-12** | Prohibition of  | High     | Using '\' to wrap long         |
:           : Explicit Line   :          : conditional expressions.       :
:           : Continuation    :          :                                :
:           : Backslashes     :          :                                :
| **T5-13** | Snake Case for  | Medium   | Defining a helper function     |
:           : Python Function :          : with PascalCase.               :
:           : Names           :          :                                :
| **T5-14** | 80-Column Limit | Medium   | Writing a long message string  |
:           : Enforcement for :          : without line breaks.           :
:           : String Literals :          :                                :
| **T5-15** | Double Blank    | Medium   | Separating top-level functions |
:           : Lines Between   :          : with zero or one blank line.   :
:           : Top-Level       :          :                                :
:           : Definitions     :          :                                :
| **T5-16** | Line Wrapping   | Medium   | Writing an entire paragraph as |
:           : for Markdown    :          : a single unbroken line.        :
:           : Paragraphs      :          :                                :
| **T5-17** | 80-Column Line  | Medium   | Writing multi-line formatting  |
:           : Wrapping        :          : conditionals on a single       :
:           : Enforcement     :          : horizontal axis beyond 80      :
:           :                 :          : columns.                       :
| **T5-18** | Strict Column   | Medium   | Appending multiple arguments   |
:           : Limits for      :          : to a single-line function      :
:           : Function        :          : signature, causing it to       :
:           : Signatures      :          : exceed horizontal bounds.      :
| **T5-19** | Trailing Space  | Medium   | Grouping multiple imported     |
:           : After Import    :          : variables with commas but no   :
:           : Commas          :          : spacing.                       :
| **T5-20** | Alphabetical    | Medium   | Appending a newly required     |
:           : Ordering of     :          : module (e.g.,                  :
:           : Import          :          : `android_build_server_helper`) :
:           : Statements      :          : to the very end of an already  :
:           :                 :          : alphabetized import list.      :
| **T5-21** | Pre-Declaration | Medium   | Defining a helper method like  |
:           : of Helper       :          : `_set_tty_env()` at the end of :
:           : Functions       :          : the file, after it has already :
:           :                 :          : been called in                 :
:           :                 :          : `build_server_context()`.      :
| **T5-22** | Removal of      | Medium   | Leaving a trailing comma after |
:           : Redundant       :          : the last argument when the     :
:           : Trailing Commas :          : function arguments are not     :
:           :                 :          : broken across multiple lines.  :
| **T5-23** | Byte Literal    | Medium   | Introducing a single-quoted    |
:           : Quote           :          : byte literal into a list or    :
:           : Consistency     :          : condition where double-quoted  :
:           :                 :          : byte literals are the          :
:           :                 :          : established norm.              :
| **T5-24** | Editor          | Medium   | Relying purely on a            |
:           : Configuration   :          : developer's local environment  :
:           : Automation via  :          : to format Python files to the  :
:           : Modelines       :          : 4-space indent/80-width        :
:           :                 :          : standard.                      :
| **T5-25** | Strict Unix     | Critical | Committing files processed by  |
:           : Line Endings    :          : a Windows IDE that injected    :
:           : (LF)            :          : carriage returns (\r).         :

--------------------------------------------------------------------------------

### Rules

#### T5-01: Unused Module Imports Removal

> **Rule:** Must permanently remove import statements for modules that are no
> longer executed or referenced in the code path.
>
> **What:** Modules that are no longer referenced in the code execution path
> must have their import statements removed to prevent namespace pollution and
> false dependencies.
>
> **Applies To:** Python dependency management in testing and production files.
>
> **Why:** As test setups refactor from temporary file usage to static data
> loading, unused dependencies like `tempfile` accumulate and confuse static
> analyzers. Failing to adhere to this typically results in **Namespace
> Pollution**.

**Trap 1: Leaving an import statement intact after removing the last reference
to its methods.**

**Don't:**

```python
import sys
from typing import List
import unittest
import tempfile

# Code never calls tempfile.*
```

**Do:**

```python
import sys
from typing import List
import unittest

# Code never calls tempfile.*
```

#### T5-02: Manual Line Wrapping in YAML Frontmatter

> **Rule:** Must manually wrap long strings within Markdown YAML frontmatter to
> adhere to the 80-character limit.
>
> **What:** Long strings within Markdown file YAML frontmatter must be manually
> wrapped to adhere to the 80-character width limit, as automated formatters
> (like git cl format) may bypass YAML blocks.
>
> **Applies To:** Markdown files containing YAML frontmatter (`.md`).
>
> **Why:** Standard documentation formatting tools failed to correctly parse and
> wrap frontmatter descriptions, causing horizontal scroll issues in standard
> text editors. Failing to adhere to this typically results in **Formatting CI
> Failure**.

**Trap 1: Leaving a single continuous string across >100 columns because the
auto-formatter ignored it.**

**Don't:**

```yaml
---
name: buildbucket
description: A safe and convenient wrapper around the 'bb' (buildbucket) tool. Use this to inspect builder builds, check status, list steps, and fetch logs without overwhelming the context window.
---
```

**Do:**

```yaml
---
name: buildbucket
description: >
  A safe and convenient wrapper around the 'bb' (buildbucket) tool. Use this
  to inspect builder builds, check status, list steps, and fetch logs without
  overwhelming the context window.
---
```

#### T5-03: Automated Formatting Adherence

> **Rule:** Always accept the structural output of automated formatting tools,
> regardless of aesthetic preferences.
>
> **What:** Code structure and styling decisions must strictly defer to the
> outputs of the project's automated formatting tools (e.g., `git cl format`),
> even when the resulting style is aesthetically unconventional.
>
> **Applies To:** All source code submitted to the repository.
>
> **Why:** Developer disagreements over stylistic choices like dictionary
> formatting caused unnecessary friction in reviews. Enforcing a strict
> adherence to the formatter eliminated subjective style debates. Failing to
> adhere to this typically results in **Presubmit Rejection**.

**Trap 1: Manually aligning dictionary keys and values to 'look nice', violating
the automated tool's constraints.**

**Don't:**

```python
json_output = {
    "files": {},
    "summary": {
        "total_files": file_count,
        "invalid_files": 0,
    }
}
```

**Do:**

```python
# Accept the formatting imposed by git cl format
json_output = {
    "files": {},
    "summary": {
        "total_files":
        file_count,
        "invalid_files":
        0,
    }
}
```

#### T5-04: Contextual Quotation Mark Consistency

> **Rule:** Must strictly match the existing quotation mark style (single or
> double) established in the surrounding source file.
>
> **What:** String literals must use quotation marks (single vs double) that
> remain consistent with the established style of the specific file being
> edited.
>
> **Applies To:** Python source files.
>
> **Why:** Mixing double and single quotes within the same file randomly caused
> stylistic inconsistencies that tripped up linters and decreased readability.
> Failing to adhere to this typically results in **Style Violation**.

**Trap 1: Injecting double-quoted strings into a file that exclusively uses
single quotes.**

**Don't:**

```python
libc_path = ctypes.util.find_library("c")
```

**Do:**

```python
libc_path = ctypes.util.find_library('c')
```

#### T5-05: Prohibition of Vertical Padding in Shell Examples

> **Rule:** Never use extra whitespace padding to vertically align backslashes
> in shell script documentation snippets.
>
> **What:** Bash command snippets inside documentation must use a single space
> before line continuation characters (`\`), rather than using arbitrary
> whitespace padding to vertically align them.
>
> **Applies To:** Markdown documentation containing multi-line shell command
> snippets.
>
> **Why:** Aligning backslashes vertically forces unnecessary document diffs
> whenever a new parameter length changes the alignment column requirement.
> Failing to adhere to this typically results in **Documentation Churn**.

**Trap 1: Padding spaces to push backslashes into a single vertical column.**

**Don't:**

```bash
scripts/luci_triage.py resolve-build-id \
  --builder "<BUILDER>"                 \
  --build-number <NUMBER>               \
  --project <PROJECT>
```

**Do:**

```bash
scripts/luci_triage.py resolve-build-id \
  --builder "<BUILDER>" \
  --build-number <NUMBER> \
  --project <PROJECT>
```

#### T5-06: Global Import Placement

> **Rule:** Must explicitly declare all module imports at the very top of the
> source file.
>
> **What:** Standard library and external module imports must be declared at the
> top of the file, rather than placed inline within functions or test methods.
>
> **Applies To:** Python module architecture.
>
> **Why:** Inline imports caused unexpected overhead on function calls and made
> dependency auditing difficult by hiding required modules deep inside the
> execution logic. Failing to adhere to this typically results in **Dependency
> Obfuscation**.

**Trap 1: Placing an `import json` statement inside a mock or unit test
method.**

**Don't:**

```python
def test_main_generates_json_summary(self):
    import json
    parsed_data = json.loads(written_data)
```

**Do:**

```python
import json

# ...

def test_main_generates_json_summary(self):
    parsed_data = json.loads(written_data)
```

#### T5-07: Preservation of Semantic Vertical Whitespace

> **Rule:** Must manually revert automated formatting changes that destroy
> intentional, semantic blank lines separating distinct logical blocks.
>
> **What:** Engineers must defend semantic vertical whitespace from overly
> aggressive automated code formatters. Blank lines used to separate distinct
> logical blocks must be manually reverted if stripped.
>
> **Applies To:** Data structures, dictionaries, or long declarative tuples
> heavily annotated with comments.
>
> **Why:** The IDE's auto-formatter (cider) silently stripped intentional
> paragraph spacing that separated a standard list of allowed licenses from a
> complex, heavily commented edge case, destroying the visual hierarchy. Failing
> to adhere to this typically results in **Loss of Visual Hierarchy /
> Readability**.

**Trap 1: Accepting an auto-formatter's output that collapses intentional
paragraph spacing.**

**Don't:**

```python
    # go/keep-sorted start
    "zxing",
    # go/keep-sorted end
    # The Android Software Development Kit License is a special case.
```

**Do:**

```python
    # go/keep-sorted start
    "zxing",
    # go/keep-sorted end

    # The Android Software Development Kit License is a special case.
```

**Exceptions:** Whitespace at the end of files (trailing whitespace) which is
strictly prohibited.

#### T5-08: Uniform String Quotation Styles

> **Rule:** Always maintain uniform string quotation marks throughout a single
> file to prevent visual inconsistency.
>
> **What:** String literals within a single file must utilize a uniform
> quotation style (e.g., exclusively double quotes `"`), mitigating churn and
> avoiding visual inconsistencies.
>
> **Applies To:** All Python source files, especially tests containing assertion
> strings.
>
> **Why:** Test files mixed single and double quotes, triggering linting
> discrepancies and slowing down visual parsing for developers. Failing to
> adhere to this typically results in **Style Guide Violation / Linting
> Errors**.

**Trap 1: Injecting single quotes into a file that predominantly uses double
quotes.**

**Don't:**

```python
expected_warnings = [
    'License has a license not in the allowlist.', "Version is '0'."
]
```

**Do:**

```python
expected_warnings = [
    "License has a license not in the allowlist.", "Version is '0'."
]
```

**Exceptions:** When escaping nested quotes (e.g., `"Version is '0'."`).

#### T5-09: Line Length Constraint Suspension

> **Rule:** Avoid enforcing arbitrary 80-character line lengths for general
> Python logic in environments that explicitly disable them.
>
> **What:** Eliminating arbitrary 80-character line length limits for Python
> code, favoring natural developer flow over strict wrapping.
>
> **Applies To:** Python tooling configuration and linter definitions.
>
> **Why:** Engineers were excessively burdened by line-wrapping constraints for
> long URLs or string formats. Adherence to the Bazel style guide justified
> eliminating the restriction. Failing to adhere to this typically results in
> **Linting Fatigue**.

**Trap 1: Failing automated builds due to Python lines exceeding 80 columns.**

**Don't:**

*   Enforcing max-line-length=80 in the linters, forcing developers to
    artificially fragment their logic.

**Do:**

*   Setting max-line-length to 'uncapped' or disabled in the formatting
    configuration.

**Exceptions:** Repositories strictly adhering to legacy PEP-8 standards where
Bazel inheritance does not apply.

#### T5-10: Log Message and Constant String Line Length Exemption

> **Rule:** Never split long log outputs or error messages across multiple
> lines, even if they exceed line length limits.
>
> **What:** Long constant strings, specifically log and error messages, are
> exempt from the standard 80-character line length limit to preserve
> searchability.
>
> **Applies To:** Python scripts and global source code style enforcement.
>
> **Why:** Developers were splitting string literals across multiple lines to
> appease linters, which broke log analysis tools and standard grep commands
> when developers attempted to search the codebase for specific runtime errors.
> Failing to adhere to this typically results in **Broken Code Search**.

**Trap 1: Breaking a single logical log or error message across multiple lines
to meet column limits.**

**Don't:**

```python
raise IOError(
    "failed to write fully, "
    f"wrote {written} bytes out of {_PLUGIN_HEADER_SIZE} bytes."
)
```

**Do:**

```python
raise IOError(f"failed to write fully, wrote {written} bytes out of {_PLUGIN_HEADER_SIZE} bytes.")
```

**Exceptions:** Only applicable to string literals representing console output,
logs, or error text; other long code statements (like imports or mathematical
equations) must still be wrapped.

#### T5-11: 4-Space Docstring Parameter Indentation

> **Rule:** Must strictly indent all docstring parameter descriptions (`Args:`,
> `Returns:`) by 4 spaces.
>
> **What:** Docstring components, specifically `Args:` and `Returns:` blocks,
> must use a 4-space indentation relative to the surrounding context to align
> with the repository's formatting standards.
>
> **Applies To:** Python docstrings in `depot_tools` (e.g., buildbucket.py) and
> related scripting repositories.
>
> **Why:** New files often used a 2-space indentation default under argument
> headers, creating visual inconsistency across the repository and occasionally
> breaking auto-documentation generators that expect standard offset padding.
> Failing to adhere to this typically results in **Inconsistent Documentation
> Formatting**.

**Trap 1: Using 2 spaces to indent argument descriptions under the `Args:`
docstring header.**

**Don't:**

```python
  """
  Args:
    build_id: The buildbucket id of the build.
  Returns:
    The status of the build as a string
  """
```

**Do:**

```python
  """
  Args:
        build_id: The buildbucket id of the build.
  Returns:
        The status of the build as a string
  """
```

#### T5-12: Prohibition of Explicit Line Continuation Backslashes

> **Rule:** Never use the explicit backslash (`\`) character for line
> continuations; wrap expressions in parentheses instead.
>
> **What:** Do not use the backslash ('\') character for explicit line
> continuation in Python. Implicit line continuation inside parentheses,
> brackets, or braces is required.
>
> **Applies To:** All Python codebase logic.
>
> **Why:** Explicit backslash line continuations are notoriously brittle; a
> single trailing whitespace character after a backslash will throw a
> SyntaxError, creating hard-to-spot regressions during formatting refactors.
> Failing to adhere to this typically results in **SyntaxError / Brittle
> Source**.

**Trap 1: Using '\' to wrap long conditional expressions.**

**Don't:**

```python
if args.update_readme and \
    update_readme_chromium(dependency, roll_to, current_dir):
    print("Success")
```

**Do:**

```python
if (args.update_readme and
    update_readme_chromium(dependency, roll_to, current_dir)):
    print("Success")
```

#### T5-13: Snake Case for Python Function Names

> **Rule:** Always format newly defined Python function names in `snake_case`,
> strictly avoiding `PascalCase`.
>
> **What:** Python function names must strictly adhere to `snake_case` rather
> than `PascalCase` or `camelCase`, conforming to PEP 8 style standards.
>
> **Applies To:** Python script modules and newly introduced utility functions.
>
> **Why:** Inconsistencies arose when developers copy-pasted or mimicked styles
> from older, legacy scripts (e.g., git_cl.py) that used outdated PascalCase
> conventions. Failing to adhere to this typically results in **Style Guideline
> Violation**.

**Trap 1: Defining a helper function with PascalCase.**

**Don't:**

```python
def FormatBranchName(branch):
    return BRIGHT + branch + RESET
```

**Do:**

```python
def format_branch_name(branch):
    return BRIGHT + branch + RESET
```

**Exceptions:** Legacy files where the prevailing style is already PascalCase
and modifying it would break external callers.

#### T5-14: 80-Column Limit Enforcement for String Literals

> **Rule:** Must manually wrap multi-line string constants to ensure no line
> exceeds 80 columns.
>
> **What:** String literals, including multi-line constants and logging
> suggestions, must be manually wrapped to fit within an 80-column line width
> limit.
>
> **Applies To:** Python source files, specifically globally defined string
> constants and stderr output messages.
>
> **Why:** Long diagnostic messages and multi-line strings were occasionally
> allowed to run past the 80-column margin, breaking source code readability in
> terminal-based text editors. Failing to adhere to this typically results in
> **PEP 8 Linter Violation**.

**Trap 1: Writing a long message string without line breaks.**

**Don't:**

```python
_SISO_SUGGESTION = """Please run 'gn clean {output_dir}' when convenient to upgrade this output directory to Siso (Chromium’s Ninja replacement). If you run into any issues, please file a bug via go/siso-bug and switch back temporarily by setting the GN arg 'use_siso = false'"""
```

**Do:**

```python
_SISO_SUGGESTION = """Please run 'gn clean {output_dir}' when convenient to
upgrade this output directory to Siso (Chromium’s Ninja replacement). If you
run into any issues, please file a bug via go/siso-bug and switch back
temporarily by setting the GN arg 'use_siso = false'"""
```

#### T5-15: Double Blank Lines Between Top-Level Definitions

> **Rule:** Always separate top-level functions and classes with exactly two
> blank lines.
>
> **What:** Python source code must separate top-level function and class
> definitions with exactly two blank lines.
>
> **Applies To:** All Python scripts and modules.
>
> **Why:** Developers routinely deleted empty lines or only used single line
> breaks between top-level declarations, resulting in code that was visually
> dense and PEP 8 non-compliant. Failing to adhere to this typically results in
> **Visual Density / Style Violation**.

**Trap 1: Separating top-level functions with zero or one blank line.**

**Don't:**

```python
def _print_cmd():
    pass

def _get_use_reclient_value():
    pass
```

**Do:**

```python
def _print_cmd():
    pass


def _get_use_reclient_value():
    pass
```

#### T5-16: Line Wrapping for Markdown Paragraphs

> **Rule:** Must consistently apply standard line limits to paragraphs within
> Markdown documents.
>
> **What:** Markdown documentation files (e.g., READMEs) should have their
> paragraphs wrapped consistently at line limits (typically 80 characters)
> rather than containing infinitely scrolling single-line paragraphs.
>
> **Applies To:** `.md` files across the repository.
>
> **Why:** IDE auto-formatting or careless typing resulted in massive
> single-line paragraphs, making raw text review in Gerrit and terminal viewing
> highly difficult. Failing to adhere to this typically results in **Review
> Readability Impaired**.

**Trap 1: Writing an entire paragraph as a single unbroken line.**

**Don't:**

*   This doc explains the components that help Chromium developer's and Chromium
    infrastructure interact with Google Cloud Storage.

**Do:**

*   This doc explains the components that help Chromium developer's and Chromium
    infrastructure interact with Google Cloud Storage.

**Exceptions:** Long URLs that cannot be broken.

#### T5-17: 80-Column Line Wrapping Enforcement

> **Rule:** Must aggressively wrap complex logic statements and embedded
> conditionals to remain strictly under the 80-character limit.
>
> **What:** All logic, including complex structural conditionals and embedded
> string literals for error messages, must strictly wrap at or before 80
> characters.
>
> **Applies To:** All Python source code modules and test files.
>
> **Why:** A newly introduced validation check generated excessively long
> exception string configurations that bypassed local formatting guardrails,
> rendering diffs difficult to read on smaller displays. Failing to adhere to
> this typically results in **Structural Style Violation**.

**Trap 1: Writing multi-line formatting conditionals on a single horizontal axis
beyond 80 columns.**

**Don't:**

```python
return vr.ValidationError(
    reason=f"{self._name} contains {'a ' if many_bad else ''}bad delimiter character{'s' if many_bad else ''} {util.quoted(bad_values_in_license)}.",
    additional=[f"Separate licenses by commas. When given a choice of licenses, chose the most permissive one, do not list all options."]
)
```

**Do:**

```python
return vr.ValidationError(
    reason=(f"{self._name} contains {'a ' if many_bad else ''}"
            f"bad delimiter character{'s' if many_bad else ''} "
            f"{util.quoted(bad_values_in_license)}."),
    additional=[
        "Separate licenses by commas. When given a choice of licenses, "
        "chose the most permissive one, do not list all options."
    ]
)
```

**Exceptions:** URLs embedded inside strings or comments.

#### T5-18: Strict Column Limits for Function Signatures

> **Rule:** Must split function signatures across multiple lines if parameter
> additions push them over horizontal line limits.
>
> **What:** Function signatures must be broken into multiple lines if they
> exceed horizontal character limits.
>
> **Applies To:** Python source files; specifically when adding new parameters
> to existing function declarations.
>
> **Why:** When new boolean flags or configuration variables were added to
> existing dependency check functions, the signature expanded beyond the
> designated line limit, degrading readability and violating structural style.
> Failing to adhere to this typically results in **Style Guide Violation**.

**Trap 1: Appending multiple arguments to a single-line function signature,
causing it to exceed horizontal bounds.**

**Don't:**

```python
def CheckChromiumDependencyMetadata(input_api, output_api, file_filter=None, allow_reciprocal_licenses=False):
```

**Do:**

```python
def CheckChromiumDependencyMetadata(
    input_api,
    output_api,
    file_filter=None,
    allow_reciprocal_licenses=False
):
```

#### T5-19: Trailing Space After Import Commas

> **Rule:** Always insert a single space after commas when importing multiple
> modules from the same package.
>
> **What:** Multiple imported objects from a single module must be separated by
> a comma followed by a space.
>
> **Applies To:** Python import statements, specifically `from ... import ...`
> constructs.
>
> **Why:** Imports added without a trailing space created visual clutter and
> technically violated PEP-8 style directives within the infrastructure
> scripting environment. Failing to adhere to this typically results in **Style
> Guide Violation**.

**Trap 1: Grouping multiple imported variables with commas but no spacing.**

**Don't:**

```python
from module import ALLOWED_SPDX_LICENSES,ALLOWED_OPEN_SOURCE_LICENSES
```

**Do:**

```python
from module import ALLOWED_SPDX_LICENSES, ALLOWED_OPEN_SOURCE_LICENSES
```

#### T5-20: Alphabetical Ordering of Import Statements

> **Rule:** Must strictly alphabetize standard and first-party imports within
> their respective definition blocks.
>
> **What:** Standard and first-party Python imports must be strictly
> alphabetized within their respective import blocks.
>
> **Applies To:** Global module imports across all Python infrastructure
> scripts.
>
> **Why:** Adding imports to the bottom of the import block without regarding
> alphabetization caused structural inconsistencies and historically increased
> the likelihood of merge conflicts in heavily edited files. Failing to adhere
> to this typically results in **Structural Inconsistency**.

**Trap 1: Appending a newly required module (e.g.,
`android_build_server_helper`) to the very end of an already alphabetized import
list.**

**Don't:**

```python
import reclient_helper
import siso
import android_build_server_helper
```

**Do:**

```python
import android_build_server_helper
import reclient_helper
import siso
```

#### T5-21: Pre-Declaration of Helper Functions

> **Rule:** Must define internal helper functions physically higher up in the
> source file than the code that invokes them.
>
> **What:** Internal helper functions must be declared earlier in the file than
> the block of code or function that first invokes them.
>
> **Applies To:** Module-level function definitions in Python scripts.
>
> **Why:** Placing helper functions at the very bottom of the file required
> readers to scroll past the usage to understand the behavior, degrading linear
> readability of the code. Failing to adhere to this typically results in
> **Decreased Readability**.

**Trap 1: Defining a helper method like `_set_tty_env()` at the end of the file,
after it has already been called in `build_server_context()`.**

**Don't:**

```python
def do_work():
    _setup_env()

def _setup_env():
    pass
```

**Do:**

```python
def _setup_env():
    pass

def do_work():
    _setup_env()
```

#### T5-22: Removal of Redundant Trailing Commas

> **Rule:** Always strip trailing commas from the final parameter of single-line
> function executions.
>
> **What:** Trailing commas must be removed from the final argument in
> single-line function invocations to minimize visual clutter.
>
> **Applies To:** Python function calls.
>
> **Why:** A trailing comma was left inside a regex search call, introducing
> unnecessary syntax artifacts into the source file. Failing to adhere to this
> typically results in **Formatting Clutter**.

**Trap 1: Leaving a trailing comma after the last argument when the function
arguments are not broken across multiple lines.**

**Don't:**

```python
if re.search(
        r"(^|\s)(use_remoteexec)\s*=\s*true($|\s)",
        line_without_comment,
):
```

**Do:**

```python
if re.search(
        r"(^|\s)(use_remoteexec)\s*=\s*true($|\s)",
        line_without_comment
):
```

**Exceptions:** Multi-line data structure definitions (lists, dicts) or tuples
with a single element.

#### T5-23: Byte Literal Quote Consistency

> **Rule:** Must ensure byte string quotation marks match the prevailing
> quotation style of the surrounding logic.
>
> **What:** Byte string literal definitions (single vs. double quotes) must
> remain consistent with the established style of the surrounding file context.
>
> **Applies To:** Python byte literal declarations across the codebase.
>
> **Why:** Mixing quotation marks for identical data types within the same file
> caused unnecessary visual friction and violated the principle of least
> astonishment for developers reading the logic. Failing to adhere to this
> typically results in **Style Fragmentation**.

**Trap 1: Introducing a single-quoted byte literal into a list or condition
where double-quoted byte literals are the established norm.**

**Don't:**

```python
elif hdr.lower().split(b' ')[0] in (b"get", b"head"):
```

**Do:**

```python
elif hdr.lower().split(b" ")[0] in (b"get", b"head"):
```

**Exceptions:** When escaping nested quotes dictates the use of the alternative
quote type.

#### T5-24: Editor Configuration Automation via Modelines

> **Rule:** Always append editor modelines to the bottom of large files to
> automate global indentation styles.
>
> **What:** To prevent structural style discrepancies (e.g., indentation or tab
> width) across different local developer environments, include an editor
> modeline (like Vim's) at the bottom of the file.
>
> **Applies To:** Large module files or scripts highly susceptible to mixed
> tab/space or indentation drift.
>
> **Why:** Developers using terminal editors like Vim without strict global
> configs occasionally introduced inconsistent tab widths or line-wrapping,
> leading to style-only commit noise. Failing to adhere to this typically
> results in **Indentation Mismatch**.

**Trap 1: Relying purely on a developer's local environment to format Python
files to the 4-space indent/80-width standard.**

**Don't:**

```text
(File ends without editor directives)
```

**Do:**

```python
# vim: sts=4:ts=4:sw=4:tw=80:et:
```

#### T5-25: Strict Unix Line Endings (LF)

> **Rule:** Must explicitly save and commit all text files with Unix-style line
> endings (LF).
>
> **What:** Source files must exclusively utilize Unix-style line endings (LF),
> ensuring cross-platform compatibility and preventing noisy diffs.
>
> **Applies To:** All committed text files, including code, configuration, and
> documentation.
>
> **Why:** Files saved on Windows machines occasionally introduced CRLF line
> endings, which broke shell script shebang evaluations in Unix build
> environments and created massive diff pollution. Failing to adhere to this
> typically results in **Script Execution Failure / Diff Pollution**.

**Trap 1: Committing files processed by a Windows IDE that injected carriage
returns (\r).**

**Don't:**

*   File saved with \r\n (CRLF) line endings.

**Do:**

*   File saved with \n (LF) line endings.

**Exceptions:** Explicitly declared binary files or specific Windows-only
configuration files that strictly mandate CRLF.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | Python Language Idioms & Modernization - *Python
    syntactic structures define the baseline formatting requirements enforced by
    structural style checks.*
*   **Downstream:** T6 | Technical Documentation & Comment Quality - *Docstring
    indentation rules and Markdown frontmatter formatting constraints govern the
    structural delivery of technical documentation.*

## Chapter: Technical Documentation & Comment Quality

**Context:** This domain establishes strict standards for internal code
documentation, enforcing proper formatting, typographical accuracy, and
grammatical correctness. Adherence ensures clear, professional, and easily
parsable technical documentation across all internal scripts, configuration
files, and READMEs.

### Summary

| Rule ID   | Principle / Constraint    | Priority | Primary Symptom / Trap    |
| :-------- | :------------------------ | :------- | :------------------------ |
| **T6-01** | Strict Left-Alignment for | Medium   | Arbitrary indentation for |
:           : Docstring Continuation    :          : the second line of a      :
:           : Lines                     :          : docstring argument        :
:           :                           :          : description.              :
| **T6-02** | Technical Debt            | Medium   | Dropping a generic TODO   |
:           : Traceability              :          : indicating a future task  :
:           :                           :          : without assigning         :
:           :                           :          : accountability or         :
:           :                           :          : tracking.                 :
| **T6-03** | Dynamic Constant          | Medium   | Restating the internal    |
:           : Referencing               :          : contents of an array      :
:           :                           :          : inside the function's     :
:           :                           :          : documentation string.     :
| **T6-04** | Mandatory Terminal        | Medium   | Omitting periods at the   |
:           : Punctuation in Comments   :          : end of inline comments or :
:           :                           :          : docstring arguments.      :
| **T6-05** | Elimination of Redundant  | Medium   | Adding superfluous        |
:           : Docstring Qualifiers      :          : definitions of standard   :
:           :                           :          : Python data behavior to   :
:           :                           :          : function arguments.       :
| **T6-06** | Valid Docstring           | Medium   | Prefixing standard PEP    |
:           : Formatting Without        :          : 257 string blocks with    :
:           : Comment Prefixes          :          : hash signs.               :
| **T6-07** | Strict Typographical      | High     | Misspelling the target    |
:           : Accuracy in OWNERS        :          : filename within a         :
:           : Configuration             :          : `per-file` OWNERS         :
:           :                           :          : declaration.              :
| **T6-08** | Strict Proper Noun        | Medium   | Referencing 'git' with    |
:           : Capitalization in         :          : lowercase spelling in a   :
:           : User-Facing Logs          :          : deprecation warning.      :
| **T6-09** | Synchronized              | Medium   | Pushing a README update   |
:           : Documentation Updates     :          : pointing to a new feature :
:           :                           :          : before the code           :
:           :                           :          : introducing that feature  :
:           :                           :          : is actively deployed.     :
| **T6-10** | Correction of Typos in    | Medium   | Permitting spelling       |
:           : Code Comments             :          : errors within inline      :
:           :                           :          : comments detailing        :
:           :                           :          : execution control flow.   :
| **T6-11** | Grammatical Correctness   | Medium   | Raising an error with     |
:           : in Exception Outputs      :          : uncapitalized sentences   :
:           :                           :          : and mistyped words.       :
| **T6-12** | Correction of Syntactic   | Medium   | Inverting the article and |
:           : Word Order in Docstrings  :          : adjective within a        :
:           :                           :          : descriptive comment.      :
| **T6-13** | Accurate Verb Forms in    | Medium   | Using an incorrect part   |
:           : Docstrings                :          : of speech to describe a   :
:           :                           :          : programmatic action in    :
:           :                           :          : documentation.            :
| **T6-14** | Typographical Accuracy in | Medium   | Merging un-proofread      |
:           : Technical Documentation   :          : placeholder text          :
:           :                           :          : containing typos.         :

--------------------------------------------------------------------------------

### Rules

#### T6-01: Strict Left-Alignment for Docstring Continuation Lines

> **Rule:** Always strictly left-align multi-line descriptions for function
> arguments in docstrings with the starting text of the description.
>
> **What:** When describing function arguments in docstrings (`Args:` section),
> multi-line descriptions must be strictly left-aligned with the starting text
> of the description.
>
> **Applies To:** Python Docstrings across all modules.
>
> **Why:** Inconsistent vertical alignment broke docstring parsers and
> diminished readability in generated technical documentation. Failing to adhere
> to this typically results in **Malformed Documentation Layout**.

**Trap 1: Arbitrary indentation for the second line of a docstring argument
description.**

**Don't:**

```python
Args:
    value: the value to process, which may include both verbose and
           atomic delimiters, e.g. "Apache"
```

**Do:**

```python
Args:
    value: the value to process, which may include both verbose and
        atomic delimiters, e.g. "Apache"
```

--------------------------------------------------------------------------------

#### T6-02: Technical Debt Traceability

> **Rule:** Must link all TODO comments denoting temporary workarounds directly
> to a valid release bug or tracking issue.
>
> **What:** Linking TODO comments denoting temporary workarounds directly to a
> valid release bug or tracking issue.
>
> **Applies To:** Code documentation; specifically `# TODO` blocks.
>
> **Why:** Untracked TODOs frequently become permanent fixtures, masking legacy
> logic that was supposed to be decommissioned post-release. Failing to adhere
> to this typically results in **Stale Logic Accumulation**.

**Trap 1: Dropping a generic TODO indicating a future task without assigning
accountability or tracking.**

**Don't:**

```python
# TODO: Remove .siso_metadata.json after switching the filename for a while
for metadata_file in ['siso_metadata.json', '.siso_metadata.json']:
```

**Do:**

```python
# TODO: Remove .siso_metadata.json after switching the filename for a while
# https://crbug.com/447974622
for metadata_file in ['siso_metadata.json', '.siso_metadata.json']:
```

--------------------------------------------------------------------------------

#### T6-03: Dynamic Constant Referencing

> **Rule:** Always reference global constants or lists by name within docstrings
> rather than hardcoding a partial snapshot of their contents.
>
> **What:** Referencing global constants or lists by name within docstrings,
> rather than hardcoding a partial snapshot of their contents.
>
> **Applies To:** Python docstrings describing validation behavior.
>
> **Why:** When acceptable domain lists expanded (e.g., adding 'bitbucket' to
> 'github' and 'googlesource'), hardcoded docstrings rapidly drifted from truth,
> misleading developers. Failing to adhere to this typically results in
> **Documentation Drift**.

**Trap 1: Restating the internal contents of an array inside the function's
documentation string.**

**Don't:**

```python
"""
subdomain matching 'git', 'github', or 'googlesource'.
"""
```

**Do:**

```python
"""
subdomain matching. See GIT_DOMAIN_INDICATORS for the full list.
"""
```

--------------------------------------------------------------------------------

#### T6-04: Mandatory Terminal Punctuation in Comments

> **Rule:** Must terminate all descriptive sentences in code comments and
> docstrings with a period.
>
> **What:** All descriptive sentences in code comments and docstrings (e.g.,
> parameter descriptions, functional block comments) must end with terminal
> punctuation (a period).
>
> **Applies To:** Python inline comments and Docstrings.
>
> **Why:** Inconsistent casing and missing punctuation degraded the visual
> uniformity of auto-generated documentation and created an unprofessional
> appearance in the codebase. Failing to adhere to this typically results in
> **Poor Documentation Quality**.

**Trap 1: Omitting periods at the end of inline comments or docstring
arguments.**

**Don't:**

```python
# Attempt to update README.chromium
```

**Do:**

```python
# Attempt to update README.chromium.
```

--------------------------------------------------------------------------------

#### T6-05: Elimination of Redundant Docstring Qualifiers

> **Rule:** Avoid restating implicit data structure mechanics within docstrings
> to prevent unnecessary noise.
>
> **What:** Avoid restating implicit data structure mechanics within docstrings.
> Qualifiers that describe standard structural behaviors (like parsed file lines
> not containing newlines) add noise.
>
> **Applies To:** Python docstrings describing parsed text or fundamental data
> types.
>
> **Why:** A reviewer requested clarifying that a parsed 'line' string object
> possessed no internal newlines. The author correctly rebutted that lines
> generated by standard parser sweeps inherently lack internal newlines,
> rendering the addition redundant. Failing to adhere to this typically results
> in **Documentation Bloat**.

**Trap 1: Adding superfluous definitions of standard Python data behavior to
function arguments.**

**Don't:**

*   A list of `<action>, <path>` pairs, each on its own line containing a string
    with no new lines.

**Do:**

*   A list of `<action>, <path>` pairs, each on its own line.

**Exceptions:** Where standard behavior is explicitly broken (e.g., if a parser
*does* retain split line breaks against convention).

--------------------------------------------------------------------------------

#### T6-06: Valid Docstring Formatting Without Comment Prefixes

> **Rule:** Never prefix inline triple-quoted docstrings with standard hash
> (`#`) comment characters.
>
> **What:** Inline triple-quoted docstrings must stand alone and must not be
> prefixed by standard hash `#` comment characters.
>
> **Applies To:** Python class and property docstrings.
>
> **Why:** A docstring inside a property definition was prepended with a `#`
> comment token, confusing documentation parsers. Failing to adhere to this
> typically results in **Malformed Docstrings**.

**Trap 1: Prefixing standard PEP 257 string blocks with hash signs.**

**Don't:**

```python
@property
def mitigated(self) -> Optional[Dict[str, str]]:
    # """Returns mapping of vulnerability IDs to their descriptions."""
```

**Do:**

```python
@property
def mitigated(self) -> Optional[Dict[str, str]]:
    """Returns mapping of vulnerability IDs to their descriptions."""
```

**Exceptions:** When specifically commenting out an old docstring to deprecate
it temporarily.

--------------------------------------------------------------------------------

#### T6-07: Strict Typographical Accuracy in OWNERS Configuration

> **Rule:** Must strictly verify that file paths and file matchers designated in
> `OWNERS` configuration files are free of spelling or typographical errors.
>
> **What:** File paths and file matchers designated in `OWNERS` configuration
> files must be strictly free of spelling or typographical errors.
>
> **Applies To:** OWNERS files defining code review hierarchies and permissions.
>
> **Why:** A spelling error in an `OWNERS` directive meant that intended
> ownership rules for a build server helper script were silently unapplied,
> posing a risk to project governance. Failing to adhere to this typically
> results in **Missing Review Coverage**.

**Trap 1: Misspelling the target filename within a `per-file` OWNERS
declaration.**

**Don't:**

*   per-file android_build_server_heloper.py=user@chromium.org

**Do:**

*   per-file android_build_server_helper.py=user@chromium.org

--------------------------------------------------------------------------------

#### T6-08: Strict Proper Noun Capitalization in User-Facing Logs

> **Rule:** Always enforce proper noun capitalization when referencing external
> systems, platforms, or tools in user-facing logs.
>
> **What:** When referencing external systems, platforms, or tools in
> user-facing logging/console outputs, proper noun capitalization (e.g., "Git"
> instead of "git") must be strictly enforced.
>
> **Applies To:** Console warnings, error logs, and user-facing standard output
> across bootstrapping scripts.
>
> **Why:** Uncapitalized tool names in deprecation warnings created a lax,
> unprofessional tone in infrastructure scripts accessed by thousands of
> developers. Failing to adhere to this typically results in **Unprofessional
> Log Output**.

**Trap 1: Referencing 'git' with lowercase spelling in a deprecation warning.**

**Don't:**

```python
logging.warning('depot_tools will soon stop bundling git for Windows.')
```

**Do:**

```python
logging.warning('depot_tools will soon stop bundling Git for Windows.')
```

**Exceptions:** When referencing the exact binary command or file path (e.g.,
`git.exe`).

--------------------------------------------------------------------------------

#### T6-09: Synchronized Documentation Updates

> **Rule:** Must merge updates to primary technical documentation strictly after
> the relevant upstream system changes have successfully landed.
>
> **What:** Updates to primary technical documentation (e.g., README files) must
> only be merged strictly after the relevant upstream system changes or
> dependent CLs have successfully landed.
>
> **Applies To:** Project documentation schemas, markdown files, and procedural
> guides.
>
> **Why:** Merging documentation changes before the integrated codebase was live
> led to developer confusion, as the documented procedures did not match the
> actual execution state of the infrastructure. Failing to adhere to this
> typically results in **Stale/Inaccurate Documentation**.

**Trap 1: Pushing a README update pointing to a new feature before the code
introducing that feature is actively deployed.**

**Don't:**

*   Merge README changes containing procedures that rely on unsubmitted upstream
    patches.

**Do:**

*   Hold the CL and rebase. Only merge the README update after verifying the
    linked upstream CL (e.g., https://crrev.com/c/6037603) has definitively
    landed.

--------------------------------------------------------------------------------

#### T6-10: Correction of Typos in Code Comments

> **Rule:** Always audit and correct inline code comments and structural
> documentation for spelling mistakes.
>
> **What:** Inline code comments and structural documentation must be regularly
> audited and corrected for spelling mistakes to preserve professionalism and
> readability.
>
> **Applies To:** Python inline comments and script documentations.
>
> **Why:** Spelling errors in technical comments (e.g., "prase" instead of
> "parse") decreased the apparent quality of the codebase and momentarily
> disrupted reader parsing flow. Failing to adhere to this typically results in
> **Degraded Code Readability**.

**Trap 1: Permitting spelling errors within inline comments detailing execution
control flow.**

**Don't:**

```python
# If we don't want to prase commit position for tags, use input
```

**Do:**

```python
# If we don't want to parse commit position for tags, use input
```

--------------------------------------------------------------------------------

#### T6-11: Grammatical Correctness in Exception Outputs

> **Rule:** Must write user-facing exception strings and error messages adhering
> to standard English grammar, proper vocabulary, and capitalization.
>
> **What:** User-facing exception strings and error messages must adhere to
> standard English grammar, including capitalized sentence boundaries and
> accurate vocabulary.
>
> **Applies To:** Error raising syntax, specifically `raise TypeError(...)` or
> `raise RuntimeError(...)`.
>
> **Why:** An exception message was written with a lowercase start and a
> vocabulary typo ('except' instead of 'Expected'). This degraded the
> reliability perception of the tooling for downstream users. Failing to adhere
> to this typically results in **Unprofessional Application Output**.

**Trap 1: Raising an error with uncapitalized sentences and mistyped words.**

**Don't:**

```python
raise TypeError('method "use_siso_default" in "{}" returns invalid result. except bool, got "{}"')
```

**Do:**

```python
raise TypeError('Method "use_siso_default" in "{}" returns invalid result. Expected bool, got "{}"')
```

--------------------------------------------------------------------------------

#### T6-12: Correction of Syntactic Word Order in Docstrings

> **Rule:** Must explicitly proofread module-level docstrings and inline
> comments to ensure logical English word ordering and syntax.
>
> **What:** Module-level docstrings and inline comments must be proofread to
> ensure logical English word ordering and syntax.
>
> **Applies To:** Python file headers and module docstrings.
>
> **Why:** A typo featuring swapped word syntax ('valid a' instead of 'a valid')
> was identified in an allowlist file. Prompt correction ensures maintainability
> and clarity. Failing to adhere to this typically results in **Degraded Code
> Readability**.

**Trap 1: Inverting the article and adjective within a descriptive comment.**

**Don't:**

```python
# Any licenses added should be valid a SPDX Identifier.
```

**Do:**

```python
# Any licenses added should be a valid SPDX Identifier.
```

--------------------------------------------------------------------------------

#### T6-13: Accurate Verb Forms in Docstrings

> **Rule:** Always utilize correct verb forms rather than improper noun phrasing
> when describing function behaviors in documentation.
>
> **What:** Function documentation must utilize correct verb forms (e.g.,
> 'prefers') rather than improper noun phrasing (e.g., 'preferences') when
> describing function behaviors.
>
> **Applies To:** Python function docstrings.
>
> **Why:** A docstring described a function's logic using 'this function
> preferences' instead of 'this function prefers', compromising technical
> clarity. Failing to adhere to this typically results in **Degraded Code
> Readability**.

**Trap 1: Using an incorrect part of speech to describe a programmatic action in
documentation.**

**Don't:**

```python
"""As depot_tools will soon stop bundling Git for Windows, this function preferences installations outside..."""
```

**Do:**

```python
"""As depot_tools will soon stop bundling Git for Windows, this function prefers installations outside..."""
```

--------------------------------------------------------------------------------

#### T6-14: Typographical Accuracy in Technical Documentation

> **Rule:** Must rigorously proofread documentation files such as READMEs for
> spelling, typographical, and grammatical errors prior to submission.
>
> **What:** Documentation files (like READMEs) must be strictly proofread for
> spelling, typographical, and grammatical errors.
>
> **Applies To:** Markdown documentation and README files.
>
> **Why:** Misspellings in foundational documentation (like placeholder text for
> new telemetry libraries) detracted from project professionalism and
> searchability. Failing to adhere to this typically results in **Unprofessional
> Documentation**.

**Trap 1: Merging un-proofread placeholder text containing typos.**

**Don't:**

*   This a placeholder to establish a folder to build the telemtry lib

**Do:**

*   This is a placeholder to establish a folder to build the telemetry lib

## Chapter: Data Validation & Regular Expression Management

**Context:** This chapter dictates the mechanisms for string validation and
regular expression management. It mandates the use of deterministic error
schemas, raw literals for escape sequences, and the consolidation of verbose
string checks into rigorously documented regular expressions.

### Summary

| Rule ID   | Principle / Constraint   | Priority | Primary Symptom / Trap     |
| :-------- | :----------------------- | :------- | :------------------------- |
| **T7-01** | Deterministic Sequences  | High     | Defining an allowlist as a |
:           : in Error Messages        :          : set and directly           :
:           :                          :          : interpolating it into a    :
:           :                          :          : runtime error message.     :
| **T7-02** | Raw String Literals for  | Medium   | Escaping backslashes in a  |
:           : Escape Sequences         :          : standard string literal.   :
| **T7-03** | Consolidation of String  | Medium   | Chaining multiple          |
:           : Validation Logic via     :          : independent if-statements  :
:           : Regular Expressions      :          : to check for invalid       :
:           :                          :          : string conditions.         :
| **T7-04** | Inline Documentation for | Medium   | Defining dense regex       |
:           : Complex Regular          :          : patterns as a single,      :
:           : Expressions              :          : uncommented string         :
:           :                          :          : literal.                   :

--------------------------------------------------------------------------------

### Rules

#### T7-01: Deterministic Sequences in Error Messages

> **Rule:** Always use deterministic data structures (e.g., lists) when
> interpolating constants into log messages or error strings. Never use
> unordered structures like sets for stringified outputs.
>
> **What:** Constants used for lookups that are printed to logs or error
> messages must use deterministic data structures (like `list`) rather than
> unordered structures (like `set`).
>
> **Applies To:** Data validation logic, logging, and exception message
> formatting.
>
> **Why:** When a validation script used a `set` to store supported URI schemes,
> the resulting error strings output random ordering. This broke automated log
> counting pipelines that relied on exact string matching for metrics. Failing
> to adhere to this typically results in **Log Aggregation Failure**.

**Trap 1: Defining an allowlist as a set and directly interpolating it into a
runtime error message.**

**Don't:**

```python
_SUPPORTED = {'http', 'ftp', 'git'}
return f"Supported schemes: {_SUPPORTED}"
```

**Do:**

```python
_SUPPORTED = ['ftp', 'git', 'http']
return f"Supported schemes: {_SUPPORTED}"
```

**Exceptions:** If the collection is strictly used for fast O(1) lookups and
never stringified to standard output or logging pipelines, frozenset/set is
acceptable.

--------------------------------------------------------------------------------

#### T7-02: Raw String Literals for Escape Sequences

> **Rule:** Always use raw string literals (`r""`) to handle heavy backslash
> escape sequences in regular expressions and paths.
>
> **What:** Use raw string literals (`r""`) when passing strings that contain
> heavy backslash escape sequences (such as paths or regular expressions) to
> avoid parser misinterpretations.
>
> **Applies To:** Python scripts handling file paths, shell commands, or regex
> processing.
>
> **Why:** Standard string literals containing double backslashes obfuscated the
> intended path delimiter logic, leading to confusing code and potential
> escaping errors across platforms. Failing to adhere to this typically results
> in **Parsing Ambiguity**.

**Trap 1: Escaping backslashes in a standard string literal.**

**Don't:**

```python
pattern_rel = pattern_clean.lstrip("/\\")
```

**Do:**

```python
pattern_rel = pattern_clean.lstrip(r"\/")
```

--------------------------------------------------------------------------------

#### T7-03: Consolidation of String Validation Logic via Regular Expressions

> **Rule:** Must consolidate fragmented, sequential string validation checks
> into a single compiled regular expression.
>
> **What:** Multiple sequential boolean checks for string format constraints
> (length, characters, substrings) must be consolidated into a single, compiled
> regular expression.
>
> **Applies To:** Input validation routines across all script parsers and
> configuration checkers.
>
> **Why:** Using sequential `if` blocks to check for underscores, uppercase
> characters, and specific boundary conditions resulted in overly verbose and
> brittle code. Failing to adhere to this typically results in **Logic Drift /
> Maintainability Overhead**.

**Trap 1: Chaining multiple independent if-statements to check for invalid
string conditions.**

**Don't:**

```python
if '_' in name:
    errors.append('no underscore')
if name != name.lower():
    errors.append('no uppercase')
if '--' in name:
    errors.append('no consecutive hyphens')
```

**Do:**

```python
_NAME_RE = re.compile(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$')
if not _NAME_RE.match(name):
    errors.append('name must be lowercase alphanumeric and single hyphens only')
```

--------------------------------------------------------------------------------

#### T7-04: Inline Documentation for Complex Regular Expressions

> **Rule:** Always break down and document complex regular expressions
> containing multiple capture groups using `re.VERBOSE` or explicit inline
> comments.
>
> **What:** Complex regular expressions containing multiple capture groups must
> be broken down and clearly commented, either via `re.VERBOSE` multi-line
> strings or adjacent inline documentation detailing the logic behind each
> capturing group.
>
> **Applies To:** Python modules handling text parsing or validation (e.g.,
> metadata fields and string schemas).
>
> **Why:** Monolithic, single-line regular expressions were difficult for
> subsequent engineers to decode and modify, leading to regressions when capture
> groups were updated to support new formatting standards. Failing to adhere to
> this typically results in **Regex Maintenance Burden**.

**Trap 1: Defining dense regex patterns as a single, uncommented string
literal.**

**Don't:**

```python
UPDATE_MECHANISM_REGEX = re.compile(r"^([^.\s(]+)(?:\.([^\s(]+))?(?:\s*\(([^)]+)\))?$")
```

**Do:**

```python
# The regex for validating the structure of the Update-Mechanism field.
# It captures three groups:
# 1. The primary mechanism (e.g., "Autoroll", "Manual", "Static").
# 2. An optional secondary part, preceded by a dot (e.g., ".HardFork").
# 3. An optional comment/bug link in parentheses (e.g., "(crbug.com/12345)").
UPDATE_MECHANISM_REGEX = re.compile(r"^([^.\s(]+)(?:\.([^\s(]+))?(?:\s*\(([^)]+)\))?$")
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Downstream:** T6 | Technical Documentation & Comment Quality - *The
    requirement to exhaustively comment capture groups strictly aligns with the
    broader internal code documentation and grammar guidelines.*

## Chapter: Git Tooling & Build System Orchestration

**Context:** This domain governs the orchestration of version control
configurations, build system artifacts, and CLI environments within Chromium
infrastructure. It enforces correct metadata ordering, documentation
synchronization, and file execution permissions to ensure seamless and
deterministic developer workflows.

### Summary

| Rule ID   | Principle / Constraint    | Priority | Primary Symptom / Trap  |
| :-------- | :------------------------ | :------- | :---------------------- |
| **T8-01** | Accurate Attribution of   | Medium   | Using 'git hooks' to    |
:           : Build Hooks (gclient vs   :          : describe actions        :
:           : git)                      :          : performed by gclient.   :
| **T8-02** | Synchronization of        | High     | Submitting code changes |
:           : Autogenerated             :          : without the updated     :
:           : Documentation Artifacts   :          : autogenerated man/HTML  :
:           :                           :          : files.                  :
| **T8-03** | Chronological Ordering in | Medium   | Prepending new ignore   |
:           : Git Blame Ignore Lists    :          : revisions to the top of :
:           :                           :          : the file or sorting     :
:           :                           :          : newest-first.           :
| **T8-04** | Executable Permissions    | High     | Removing the executable |
:           : for Shebang Scripts       :          : bit from a file that    :
:           :                           :          : contains a shebang.     :

--------------------------------------------------------------------------------

### Rules

#### T8-01: Accurate Attribution of Build Hooks (gclient vs git)

> **Rule:** Always explicitly distinguish between Git's native hook mechanism
> and external hooks executed by the `gclient` tool in documentation.
>
> **What:** Documentation must accurately distinguish between Git's native hook
> mechanism and hooks executed by the `gclient` tool during sync operations.
>
> **Applies To:** Technical documentation, READMEs, and tool descriptions
> relating to Chromium checkout initialization.
>
> **Why:** Documentation incorrectly referred to 'git hooks run by gclient',
> leading to confusion for developers who incorrectly looked in `.git/hooks`
> instead of `.gclient` configurations. Failing to adhere to this typically
> results in **Developer Confusion**.

**Trap 1: Using 'git hooks' to describe actions performed by gclient.**

**Don't:**

*   There may be different git hooks run by `gclient` that pull necessary
    artifacts.

**Do:**

*   There may be different hooks run by `gclient` that pull necessary artifacts.

--------------------------------------------------------------------------------

#### T8-02: Synchronization of Autogenerated Documentation Artifacts

> **Rule:** Must regenerate and commit compiled documentation assets alongside
> any modifications to their underlying source code or CLI usage definitions.
>
> **What:** When modifying code that dictates help texts or CLI usage, the
> developer must locally run the documentation generation script and check in
> the resulting compiled assets (e.g., HTML, man pages).
>
> **Applies To:** CLI tools that auto-generate `man` pages and HTML
> documentation from source files.
>
> **Why:** Contributors updated tool behavior without running the compilation
> script, leaving checked-in manual pages stale and out of sync with the actual
> tool binaries. Failing to adhere to this typically results in **Stale
> Documentation Artifacts**.

**Trap 1: Submitting code changes without the updated autogenerated man/HTML
files.**

**Don't:**

*   Committing only the logic changes to the Python source file, ignoring the
    `man/` directory.

**Do:**

*   Committing changes to the source file alongside the updated outputs from
    `man/src/make_docs.sh`.

--------------------------------------------------------------------------------

#### T8-03: Chronological Ordering in Git Blame Ignore Lists

> **Rule:** Always maintain `.git-blame-ignore-revs` metadata in strict
> oldest-first chronological order.
>
> **What:** The `.git-blame-ignore-revs` file must maintain its entries in
> strict oldest-first chronological order.
>
> **Applies To:** Source control metadata, specifically `.git-blame-ignore-revs`
> files in Chromium/depot_tools repositories.
>
> **Why:** Commits appended to the ignore list were structured newest-first or
> arbitrarily, violating the file's documented standard and making historical
> tracking and merge conflicts more difficult. Failing to adhere to this
> typically results in **Metadata Inconsistency**.

**Trap 1: Prepending new ignore revisions to the top of the file or sorting
newest-first.**

**Don't:**

```text
691128f836966a645a53185c98e8f83a9b1bcf0c
f38dc929a88633e54d1911ba94b2b37a6c164238
677616322a2bc16ed43ac0b3729eed23b50757f4
```

**Do:**

```text
677616322a2bc16ed43ac0b3729eed23b50757f4
f38dc929a88633e54d1911ba94b2b37a6c164238
691128f836966a645a53185c98e8f83a9b1bcf0c
```

--------------------------------------------------------------------------------

#### T8-04: Executable Permissions for Shebang Scripts

> **Rule:** Must enforce and retain the executable file permission bit (`chmod
> +x`, `0755`) in version control for all scripts utilizing a shebang.
>
> **What:** Files intended to be run directly via the command line, designated
> by a shebang (e.g., `#!/usr/bin/env python3`), must retain the executable file
> permission bit in version control.
>
> **Applies To:** Python test scripts and CLI entry points.
>
> **Why:** Scripts with shebang lines were occasionally checked in with standard
> text permissions (0644), preventing local environments from executing them
> seamlessly without prefixing the interpreter. Failing to adhere to this
> typically results in **Execution Denied (EACCES)**.

**Trap 1: Removing the executable bit from a file that contains a shebang.**

**Don't:**

*   File mode 0644 (Read/Write only) for a file starting with `#!/usr/bin/env
    python3`

**Do:**

*   File mode 0755 (Executable) for a file starting with `#!/usr/bin/env
    python3`

**Exceptions:** Library modules that contain a shebang strictly for historical
reasons but are no longer intended to be executed directly.

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T2 | Commit Message Metadata & Hygiene - *Version control
    constraints and commit rules govern how tracking metadata like
    `.git-blame-ignore-revs` are structurally evaluated.*
*   **Downstream:** T6 | Technical Documentation & Comment Quality - *Requires
    documentation pipelines to execute flawlessly so generated documentation
    remains synchronized with underlying logic changes.*
