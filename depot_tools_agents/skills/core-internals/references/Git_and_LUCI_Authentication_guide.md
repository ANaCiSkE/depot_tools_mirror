# Git and LUCI Authentication Engineering Guide

## Executive Summary

Welcome to the Git and LUCI Authentication Engineering Guide. This authoritative
repository is designed to capture critical historical tribal knowledge, prevent
the regression of known failure modes, and standardize architectural boundaries
across our authentication infrastructure. By codifying these strict operational
rules, we empower incoming engineers to safely navigate the complex intersection
of local Git configurations, hardware security tokens, and distributed
continuous integration pipelines without introducing silent regressions.

This guide provides a comprehensive blueprint of our authentication ecosystem.
It spans from the foundational management of local and global Git configuration
hierarchies to the precise orchestration of Gerrit Re-Authentication
(ReAuth/RAPT) contexts. Furthermore, it strictly defines the low-level
integration mechanics for FIDO2 and WebAuthn hardware keys, ensuring robust,
cross-platform reliability that gracefully degrades without breaking headless
bot environments or violating OS-level API sandboxes.

Beyond establishing core authentication states, this document enforces safe
transitional pathways for legacy credential deprecation and polymorphic provider
delegation. It also outlines essential strategies for intercepting raw
subprocess errors and transforming them into semantic, actionable diagnostics
for users. Adherence to these protocols ensures that our infrastructure remains
secure, observable, and resilient across both interactive developer workstations
and automated CI/CD services.

## Summary

| Chapter Theme / Title             | Scope & Objective                        |
| :-------------------------------- | :--------------------------------------- |
| **Git Configuration Hierarchy &   | This chapter governs the management of   |
: Overrides**                       : Git configuration states across local,   :
:                                   : global, and system scopes. It enforces   :
:                                   : strict precedence hierarchies, exact     :
:                                   : path matching for credential helpers,    :
:                                   : and the safe mutation of multi-value     :
:                                   : keys to prevent credential bleed and     :
:                                   : routing failures.                        :
| **Gerrit Re-Authentication        | This chapter defines the architectural   |
: (ReAuth/RAPT) Orchestration**     : standards for Gerrit Re-Authentication   :
:                                   : (ReAuth/RAPT) orchestration. It mandates :
:                                   : secure-by-default execution contexts,    :
:                                   : precise network RPC scoping, and robust  :
:                                   : credential parsing fallbacks for         :
:                                   : elevated privilege requirements.         :
| **FIDO2 / WebAuthn Hardware       | This domain governs the low-level        |
: Integration**                     : integration and fallback logic for FIDO2 :
:                                   : and WebAuthn physical security keys. It  :
:                                   : dictates OS-specific API branching,      :
:                                   : concurrent hardware polling, and         :
:                                   : fail-safe native UI prompts to ensure    :
:                                   : reliable authentication without sandbox  :
:                                   : violations or silent execution hangs.    :
| **Legacy Credential Deprecation & | This chapter governs the safe transition |
: Migration**                       : from legacy authentication files (e.g.,  :
:                                   : `.boto`, `.gitcookies`) to centralized   :
:                                   : systems like `luci-auth`. It enforces    :
:                                   : fail-safe mechanisms for automated bots, :
:                                   : hardcoded kill-switches for core         :
:                                   : infrastructure rollouts, and strict      :
:                                   : visibility constraints for deprecation   :
:                                   : warnings.                                :
| **Bot vs. Interactive Execution   | Accurately distinguishing between        |
: Contexts**                        : headless CI/CD environments and          :
:                                   : interactive developer setups is required :
:                                   : to safely suppress UI prompts, skip      :
:                                   : unnecessary checks, and route            :
:                                   : authentications to ambient contexts.     :
:                                   : This prevents automated pipelines from   :
:                                   : hanging on interactive challenges while  :
:                                   : maintaining strict security for          :
:                                   : developers.                              :
| **Authentication Provider         | This chapter defines the architectural   |
: Polymorphism & Delegation**       : design of the Authenticator interface    :
:                                   : hierarchy, focusing on polymorphic       :
:                                   : delegation, capability checks, and state :
:                                   : caching. It outlines mechanisms for      :
:                                   : chaining authentication attempts,        :
:                                   : memoizing provider applicability, and    :
:                                   : ensuring safe fallbacks for varying      :
:                                   : environments.                            :
| **Subprocess Error Interception & | This chapter governs the interception    |
: User Diagnostics**                : and translation of raw subprocess        :
:                                   : outputs and exit codes from command-line :
:                                   : credential tools. It mandates converting :
:                                   : low-level failures into semantic,        :
:                                   : actionable exceptions to prevent         :
:                                   : exposing raw tracebacks or numerical     :
:                                   : exit codes to users and downstream       :
:                                   : logic.                                   :
| **Service-to-Service Token        | This domain governs the formatting and   |
: Semantics**                       : semantics of OAuth2 tokens exchanged     :
:                                   : across internal infrastructure services. :
:                                   : It strictly enforces the transition from :
:                                   : legacy OIDC ID tokens to standard        :
:                                   : Access/Bearer tokens across LUCI         :
:                                   : configurations and APIs.                 :

--------------------------------------------------------------------------------
--------------------------------------------------------------------------------

## Chapter: Git Configuration Hierarchy & Overrides

**Context:** This chapter governs the management of Git configuration states
across local, global, and system scopes. It enforces strict precedence
hierarchies, exact path matching for credential helpers, and the safe mutation
of multi-value keys to prevent credential bleed and routing failures.

### Summary

| Rule ID   | Principle / Constraint    | Priority | Primary Symptom / Trap    |
| :-------- | :------------------------ | :------- | :------------------------ |
| **T1-01** | Correct Naming of Git     | High     | Pluralizing the           |
:           : Credential Configuration  :          : 'credential' namespace in :
:           : Keys                      :          : user-facing Git commands. :
| **T1-02** | Precedence of Global      | High     | Setting a global Git      |
:           : Authentication Configs    :          : configuration without     :
:           : over Stale Local          :          : cleaning up localized     :
:           : Overrides                 :          : overrides in the active   :
:           :                           :          : repository.               :
| **T1-03** | Appending Multi-Value Git | High     | Overwriting multi-value   |
:           : Configuration Keys        :          : Git config keys inside a  :
:           :                           :          : loop by using global      :
:           :                           :          : replacement flags.        :
| **T1-04** | Explicit Constraint       | Medium   | Implementing partial      |
:           : Documentation for Parsers :          : support for a standard    :
:           :                           :          : protocol without          :
:           :                           :          : documenting the           :
:           :                           :          : unimplemented portions.   :
| **T1-05** | Context-Aware Global Git  | High     | Emitting a generic        |
:           : Credential Guidance       :          : success message after     :
:           :                           :          : global configuration      :
:           :                           :          : without checking for      :
:           :                           :          : multi-host repository     :
:           :                           :          : structures like           :
:           :                           :          : submodules.               :
| **T1-06** | Precedence Override of    | High     | Clearing local SSO        |
:           : Global SSO Git            :          : configs but forgetting    :
:           : Configuration             :          : that Git will inherit the :
:           :                           :          : global SSO rewrite rule.  :
| **T1-07** | Exact Path Matching       | High     | Using a single generated  |
:           : Constraints in Git        :          : root URL (with a trailing :
:           : Credential Configuration  :          : slash) for both Git URL   :
:           :                           :          : rewrites and Git          :
:           :                           :          : credential helper keys.   :
| **T1-08** | Accurate Remote URL       | High     | Passing the generic fetch |
:           : Resolution for Git Cache  :          : URL (which might be a     :
:           : Authentication            :          : local cache directory)    :
:           :                           :          : directly to the global    :
:           :                           :          : authentication            :
:           :                           :          : configurator.             :
| **T1-09** | Cross-Platform Home       | High     | Assuming a bare '~'       |
:           : Directory Expansion       :          : character will be         :
:           :                           :          : correctly parsed by all   :
:           :                           :          : underlying OS system      :
:           :                           :          : calls or subprocess       :
:           :                           :          : commands.                 :

--------------------------------------------------------------------------------

### Rules

#### T1-01: Correct Naming of Git Credential Configuration Keys

> **Rule:** Always use the singular `credential` namespace when generating Git
> configuration commands; never use the plural `credentials`.
>
> **What:** When generating Git configuration troubleshooting commands, the
> namespace for credential properties must be singular (`credential`), not
> plural (`credentials`).
>
> **Applies To:** CLI error output, Git wrapper scripts, and Gerrit
> authentication tooling.
>
> **Why:** An error message instructed users to set `credentials.useHttpPath
> true`. Because the Git configuration schema expects `credential.useHttpPath`,
> users following the instruction created an invalid key, leaving their
> authentication silently broken. Failing to adhere to this typically results in
> **Silent Configuration Ignorance**.

**Trap 1: Pluralizing the 'credential' namespace in user-facing Git commands.**

**Don't:**

```bash
# BAD: Creates an unrecognized git config key
git config credentials.useHttpPath true
```

**Do:**

```bash
# GOOD: Uses the correct Git config schema
git config credential.useHttpPath true
```

--------------------------------------------------------------------------------

#### T1-02: Precedence of Global Authentication Configs over Stale Local Overrides

> **Rule:** Must explicitly clear conflicting local-scope repository
> configurations when establishing global Git authentication states.
>
> **What:** When establishing global Git authentication configurations via
> automated wizards, any conflicting local-scope repository configurations for
> the same host must be explicitly cleared to prevent stale overrides.
>
> **Applies To:** Git configuration wizards (`git_auth.py`), repository state
> management.
>
> **Why:** Users would run a global authentication setup wizard, but local
> repository settings (e.g., stale email addresses or overrides) would silently
> take precedence over the correct global config, causing unexpected
> authentication failures. Failing to adhere to this typically results in **Auth
> Failure / Stale Credentials**.

**Trap 1: Setting a global Git configuration without cleaning up localized
overrides in the active repository.**

**Don't:**

```python
# BAD: Sets global but ignores local state
self._configure_oauth(parts, scope='global')
return _ConfigInfo(method=_ConfigMethod.OAUTH)
```

**Do:**

```python
# GOOD: Clears conflicting local state when setting global
self._configure_oauth(parts, scope='global')
if scope == 'global':
    self._clear_local_host_config(parts)
return _ConfigInfo(method=_ConfigMethod.OAUTH)
```

**Exceptions:** Operations executed outside a git repository context must safely
skip local configuration modification.

--------------------------------------------------------------------------------

#### T1-03: Appending Multi-Value Git Configuration Keys

> **Rule:** Always sequence and append multi-value Git configurations instead of
> blindly overwriting them with replace-all flags.
>
> **What:** When modifying Git configurations that support multiple values (like
> `url.<base>.insteadOf`), configurations must be appended or set sequentially
> rather than being blanket-overwritten using a replace-all flag.
>
> **Applies To:** Git configuration manipulation (`git config`), specifically
> URL rewrites.
>
> **Why:** Iterating over a list of URLs and setting the `insteadOf` config
> while blindly replacing previous values caused only the last URL in the list
> to be preserved, breaking URL rewriting routing for all previous targets.
> Failing to adhere to this typically results in **Missing URL Rewrites**.

**Trap 1: Overwriting multi-value Git config keys inside a loop by using global
replacement flags.**

**Don't:**

```python
# BAD: Overwrites previous values in the loop
for url in old:
    self._set_config(f'url.{new}.insteadOf', url, modify_all=True)
```

**Do:**

```python
# GOOD: Clears the key once, then appends sequentially
self._set_config(f'url.{new}.insteadOf', None, modify_all=True)
for url in old:
    self._set_config(f'url.{new}.insteadOf', url)
```

--------------------------------------------------------------------------------

#### T1-04: Explicit Constraint Documentation for Parsers

> **Rule:** Must explicitly document absent features (like multi-value arrays)
> when parsing external protocol outputs.
>
> **What:** Custom parsers for external protocols (like Git credential helper
> outputs) must explicitly document unsupported protocol features (such as
> multi-value arrays) to prevent future misinterpretations.
>
> **Applies To:** Parsers interacting with standard tooling outputs (e.g.,
> `_parse_creds_helper_out`).
>
> **Why:** The parser for the Git credential helper was implemented without
> support for multi-value array keys. Reviewers identified that future
> developers might expect this standard Git feature to work, so a documented
> constraint was mandated. Failing to adhere to this typically results in
> **Silent Parsing Failure**.

**Trap 1: Implementing partial support for a standard protocol without
documenting the unimplemented portions.**

**Don't:**

```python
# BAD: No indication that standard features are unsupported
def _parse_creds_helper_out(self, out_bytes: str):
    pass
```

**Do:**

```python
# GOOD: Explicitly outlines parser limitations
def _parse_creds_helper_out(self, out_bytes: str):
    """Parse credential helper's output.
    Note: This does not handle array/multi values (e.g. key[]=value).
    """
    pass
```

--------------------------------------------------------------------------------

#### T1-05: Context-Aware Global Git Credential Guidance

> **Rule:** Always analyze the local repository structure for submodules and
> warn users if global configuration is insufficient.
>
> **What:** When applying global Git credential checks, the tool must
> proactively analyze the local repository structure (such as the presence of
> submodules) and explicitly inform the user that global configuration may be
> insufficient.
>
> **Applies To:** Global Git authentication wizards and repository setup
> scripts.
>
> **Why:** Users applying global Git credentials mistakenly assumed their entire
> checkout (including submodules pointing to different hosts) was authenticated,
> leading to delayed build breakages during deep sync operations. Failing to
> adhere to this typically results in **Incomplete Authentication Coverage**.

**Trap 1: Emitting a generic success message after global configuration without
checking for multi-host repository structures like submodules.**

**Don't:**

```python
print('Global authentication configured successfully.')
return
```

**Do:**

```python
dirs = list(scm.GIT.ListSubmodules(os.getcwd()))
if dirs:
    print('This repository appears to have submodules. These may use different Gerrit hosts and need to be configured separately.')
```

--------------------------------------------------------------------------------

#### T1-06: Precedence Override of Global SSO Git Configuration

> **Rule:** Must insert local URL rewrite rules that shadow global SSO rules
> when local standard authentication is explicitly required.
>
> **What:** When a local repository is explicitly configured for standard
> authentication, the tooling must insert local Git URL rewrite rules that
> shadow (override) any global SSO rewrite rules to prevent unintended global
> configuration bleed.
>
> **Applies To:** Git credential management and URL rewrite configuration
> wizards.
>
> **Why:** Users with global SSO configurations found that they were
> unintentionally forced to use SSO on specific repositories where standard
> authentication was strictly required because removing the local config caused
> Git to fall back to the global rule. Failing to adhere to this typically
> results in **Forced Unwanted Authentication**.

**Trap 1: Clearing local SSO configs but forgetting that Git will inherit the
global SSO rewrite rule.**

**Don't:**

```python
if self.mode == ConfigMode.NEW_AUTH:
    self._set_config(cwd, 'protocol.sso.allow', None)
    self._set_config(cwd, sso_key, None, modify_all=True)
    # Fails to block the global rule from bleeding in
```

**Do:**

```python
if self.mode == ConfigMode.NEW_AUTH:
    self._set_config(cwd, 'protocol.sso.allow', None)
    self._set_config(cwd, sso_key, None, modify_all=True)
    # Shadow a potential global SSO rewrite rule.
    self._set_config(cwd, http_key, self._remote_url, modify_all=True)
```

--------------------------------------------------------------------------------

#### T1-07: Exact Path Matching Constraints in Git Credential Configuration

> **Rule:** Never use root URLs (with trailing slashes) for credential helper
> configurations; use pathless URLs instead.
>
> **What:** Git credential helper configurations (`credential.<url>.helper`)
> require strict exact match semantics and must be configured using pathless
> URLs (host URL without a trailing slash), whereas URL rewrites
> (`url.<url>.insteadOf`) should use the root URL (with a trailing slash).
>
> **Applies To:** Git authentication configuration generators.
>
> **Why:** Applying trailing slashes to credential helper keys caused Git to
> fail credential lookups because the credential path matching rules dictate an
> exact match, unlike `insteadOf` URL prefix matching rules. Failing to adhere
> to this typically results in **Credential Lookup Failure**.

**Trap 1: Using a single generated root URL (with a trailing slash) for both Git
URL rewrites and Git credential helper keys.**

**Don't:**

```python
root_url = 'https://chromium.googlesource.com/'
self._set_config(cwd, f'credential.{root_url}.helper', 'luci')
```

**Do:**

```python
host_url = 'https://chromium.googlesource.com'
root_url = 'https://chromium.googlesource.com/'
self._set_config(cwd, f'credential.{host_url}.helper', 'luci')
self._set_config(cwd, f'url.sso://.../.insteadOf', root_url)
```

--------------------------------------------------------------------------------

#### T1-08: Accurate Remote URL Resolution for Git Cache Authentication

> **Rule:** Always dynamically resolve the actual remote host URL instead of
> passing a local cache directory path to authentication helpers.
>
> **What:** When configuring Git authentication for cloning or fetching, the
> actual remote host URL must be supplied to the authentication helper, rather
> than a local git cache directory path.
>
> **Applies To:** Git checkout, clone, and fetch operations (`gclient_scm.py`);
> environments utilizing local Git caching.
>
> **Why:** When git caching was enabled, the authentication stack was
> inadvertently receiving the local cache directory path instead of the remote
> URL. This caused fresh checkouts to fail because the host could not be
> accurately determined for credential matching. Failing to adhere to this
> typically results in **Authentication Failure / Setup Abort**.

**Trap 1: Passing the generic fetch URL (which might be a local cache directory)
directly to the global authentication configurator.**

**Don't:**

```python
git_auth.ConfigureGlobal('/', url)
```

**Do:**

```python
# We need the actual remote URL to determine auth settings if 'url' is a local cache
git_auth.ConfigureGlobal('/', self.GetActualRemoteURL() or url)
```

--------------------------------------------------------------------------------

#### T1-09: Cross-Platform Home Directory Expansion

> **Rule:** Always explicitly resolve user home directories via
> `os.path.expanduser('~')` to maintain cross-platform compatibility.
>
> **What:** When managing global Git configurations across operating systems,
> user home directories must be resolved explicitly using
> `os.path.expanduser('~')` to ensure compatibility with Windows file paths.
>
> **Applies To:** Git Configuration Modifiers (`git_cl.py`); cross-platform
> scripts.
>
> **Why:** Applying global Git authentication credentials directly to paths
> representing 'home' needed to be abstracted to work smoothly for developers
> operating in Windows environments. Failing to adhere to this typically results
> in **Path Resolution Failure / Silent Config Miss**.

**Trap 1: Assuming a bare '~' character will be correctly parsed by all
underlying OS system calls or subprocess commands.**

**Don't:**

```python
# BAD: Fails or behaves unexpectedly on Windows
c.apply_global('~')
```

**Do:**

```python
# GOOD: Explicitly resolve the home directory via the Python OS library
c.apply_global(os.path.expanduser('~'))
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Downstream:** T7 | Subprocess Error Interception & User Diagnostics -
    *Invalid or malformed Git configuration keys handled in T1 directly dictate
    the exit codes and subprocess failures intercepted by T7.*

## Chapter: Gerrit Re-Authentication (ReAuth/RAPT) Orchestration

**Context:** This chapter defines the architectural standards for Gerrit
Re-Authentication (ReAuth/RAPT) orchestration. It mandates secure-by-default
execution contexts, precise network RPC scoping, and robust credential parsing
fallbacks for elevated privilege requirements.

### Summary

| Rule ID   | Principle /       | Priority | Primary Symptom / |
:           : Constraint        :          : Trap              :
| :-------- | :---------------- | :------- | :---------------- |
| **T2-01** | Secure-by-Default | Critical | Defaulting to a   |
:           : Re-Authentication :          : relaxed security  :
:           : Checks            :          : posture where     :
:           :                   :          : ReAuth must be    :
:           :                   :          : explicitly opted  :
:           :                   :          : into.             :
| **T2-02** | Keyword-Only      | Medium   | Defining and      |
:           : Arguments for     :          : calling functions :
:           : Boolean Security  :          : with multiple     :
:           : Flags             :          : positional        :
:           :                   :          : boolean           :
:           :                   :          : arguments.        :
| **T2-03** | Precise Scoping   | High     | Using a blanket   |
:           : of                :          : trigger for       :
:           : Re-Authentication :          : re-authentication :
:           : Triggers          :          : on any label      :
:           :                   :          : mutation.         :
| **T2-04** | Lazy Evaluation   | Medium   | Unconditionally   |
:           : of                :          : pre-fetching      :
:           : Re-Authentication :          : contextual        :
:           : Contexts          :          : metadata via      :
:           :                   :          : network RPC       :
:           :                   :          : before confirming :
:           :                   :          : it is needed.     :
| **T2-05** | Sensible          | Medium   | Requiring         |
:           : Defaulting for    :          : explicit boolean  :
:           : Security Contexts :          : flags to enable a :
:           :                   :          : security          :
:           :                   :          : mechanism when    :
:           :                   :          : the presence of a :
:           :                   :          : security context  :
:           :                   :          : object already    :
:           :                   :          : implies intent.   :
| **T2-06** | Pre-populating    | Medium   | Omitting known    |
:           : Project Context   :          : contextual        :
:           : to Avoid          :          : arguments and     :
:           : Redundant Gerrit  :          : forcing the       :
:           : RPC Calls         :          : underlying        :
:           :                   :          : utility to fetch  :
:           :                   :          : metadata          :
:           :                   :          : dynamically.      :
| **T2-07** | Graceful Fallback | High     | Rejecting a       |
:           : for Standard      :          : credential        :
:           : Access Tokens in  :          : payload entirely  :
:           : ReAuth Flows      :          : because elevated, :
:           :                   :          : ReAuth-specific   :
:           :                   :          : fields are        :
:           :                   :          : missing.          :

--------------------------------------------------------------------------------

### Rules

#### T2-01: Secure-by-Default Re-Authentication Checks

> **Rule:** Must default all authentication verification methods to enforcing
> ReAuth checks, requiring an explicit opt-out parameter to relax the security
> posture.
>
> **What:** Authentication verification methods must default to enforcing
> re-authentication (ReAuth) checks. Opting out of ReAuth should require an
> explicitly named parameter (e.g., `skip_reauth_check=True`).
>
> **Applies To:** Gerrit pre-flight checks, `EnsureAuthenticated` in
> `git_cl.py`.
>
> **Why:** Previously, the authentication check defaulted to NOT requiring
> ReAuth (`requires_reauth=False`), which risked sensitive upload operations
> accidentally bypassing ReAuth requirements if the flag was forgotten at the
> call site. Failing to adhere to this typically results in **Security Bypass**.

**Trap 1: Defaulting to a relaxed security posture where ReAuth must be
explicitly opted into.**

**Don't:**

```python
# BAD: Defaults to an insecure state
def EnsureAuthenticated(self, requires_reauth=False):
    pass
```

**Do:**

```python
# GOOD: Defaults to a secure state, explicitly skip when safe
def EnsureAuthenticated(self, skip_reauth_check=False):
    pass
```

**Exceptions:** Background/read-only commands like `git cl status` explicitly
pass `skip_reauth_check=True`.

--------------------------------------------------------------------------------

#### T2-02: Keyword-Only Arguments for Boolean Security Flags

> **Rule:** Must enforce keyword-only arguments using the `*` marker for methods
> accepting multiple boolean parameters to prevent accidental logic inversion.
>
> **What:** Methods accepting multiple boolean parameters (especially security
> or execution state flags) must enforce keyword-only arguments using the `*`
> marker to prevent accidental parameter swapping.
>
> **Applies To:** Python API design across depot_tools, specifically
> authentication methods.
>
> **Why:** Passing multiple positional booleans made call sites unreadable and
> prone to accidental logic inversions (The Boolean Trap), creating hidden
> security flaws when execution flags were swapped with authentication flags.
> Failing to adhere to this typically results in **Logic Inversion / Boolean
> Trap**.

**Trap 1: Defining and calling functions with multiple positional boolean
arguments.**

**Don't:**

```python
# BAD: Positional booleans are error-prone
def EnsureAuthenticated(self, force: bool, skip_reauth_check: bool = False):
    pass

EnsureAuthenticated(False, True)
```

**Do:**

```python
# GOOD: Keyword-only enforcement
def EnsureAuthenticated(self, *, force: bool, skip_reauth_check: bool = False):
    pass

EnsureAuthenticated(force=False, skip_reauth_check=True)
```

--------------------------------------------------------------------------------

#### T2-03: Precise Scoping of Re-Authentication Triggers

> **Rule:** Limit client-side re-authentication prompts strictly to sensitive
> operations, matching server-side enforcement rules exactly.
>
> **What:** Client-side re-authentication prompts should strictly mirror
> server-side enforcement rules (e.g., triggering only on specific sensitive
> labels like 'Code-Review' rather than any label mutation).
>
> **Applies To:** Gerrit `SetReview` RPCs and label mutation operations.
>
> **Why:** Previously, updating ANY label on a Gerrit CL triggered a ReAuth
> prompt, creating immense developer friction for non-sensitive actions. It was
> determined that only `Code-Review` is subject to server-side review
> enforcement. Failing to adhere to this typically results in **Excessive
> Prompts / Developer Friction**.

**Trap 1: Using a blanket trigger for re-authentication on any label mutation.**

**Don't:**

```python
# BAD: Triggers on non-sensitive labels
if bool(labels):
    reauth_context = auth.ReAuthContext(host=host, project=project)
```

**Do:**

```python
# GOOD: Triggers only on structurally sensitive labels
if labels and _contains_review_enforcement_label(labels):
    reauth_context = auth.ReAuthContext(host=host, project=project)
```

--------------------------------------------------------------------------------

#### T2-04: Lazy Evaluation of Re-Authentication Contexts

> **Rule:** Delay fetching costly contextual data via network RPC until the
> specific operation confirms a ReAuth requirement exists.
>
> **What:** Costly contextual data required for re-authentication (such as
> fetching the Gerrit project ID via network RPC) must only be evaluated lazily
> if the specific operation triggers a ReAuth requirement.
>
> **Applies To:** Gerrit API wrappers, `SetReview` RPC.
>
> **Why:** A network call was added to fetch project information for ReAuth
> context construction. Initially, it was called unconditionally for all
> requests, adding significant latency to non-sensitive actions (like adding a
> comment) that did not require ReAuth. Failing to adhere to this typically
> results in **Unnecessary RPC Overhead**.

**Trap 1: Unconditionally pre-fetching contextual metadata via network RPC
before confirming it is needed.**

**Don't:**

```python
# BAD: Pays network cost unconditionally
project = GetChangeDetail(host, change)["project"]
reauth_context = auth.ReAuthContext(host=host, project=project)
```

**Do:**

```python
# GOOD: Lazy evaluation only if ReAuth is required
if labels and _contains_review_enforcement_label(labels):
    project = GetChangeDetail(host, change)["project"]
    reauth_context = auth.ReAuthContext(host=host, project=project)
```

**Exceptions:** If the `project` is explicitly passed in by the caller to save
the round-trip, the lazy evaluation check can be bypassed.

--------------------------------------------------------------------------------

#### T2-05: Sensible Defaulting for Security Contexts

> **Rule:** Treat the presence of a sensitive context object as an implicit
> directive to enforce security, requiring explicit opt-out flags to downgrade.
>
> **What:** If an API accepts a sensitive context object (like
> `reauth_context`), it must implicitly default to enforcing the security
> mechanism. Downgrading security must require an explicit opt-out flag (e.g.,
> `reauth_is_optional=True`).
>
> **Applies To:** API architecture handling authentication and secure execution
> requests.
>
> **Why:** The API initially required callers to explicitly pass
> `reauth_required=True` even when a `reauth_context` was provided. This led to
> redundant assertions and the risk of developers passing the context but
> forgetting the enforcement flag. Failing to adhere to this typically results
> in **Accidental Security Downgrade**.

**Trap 1: Requiring explicit boolean flags to enable a security mechanism when
the presence of a security context object already implies intent.**

**Don't:**

```python
# BAD: Fails openly unless required flag is set
def CreateHttpConn(reauth_context=None, reauth_required=False):
    assert (not reauth_required or reauth_context)
```

**Do:**

```python
# GOOD: Enforces by default, allows explicit opt-out
def CreateHttpConn(reauth_context=None, reauth_is_optional=False):
    # ReAuth is strictly enforced if context is present, unless optional.
```

--------------------------------------------------------------------------------

#### T2-06: Pre-populating Project Context to Avoid Redundant Gerrit RPC Calls

> **Rule:** Pass known project contexts from the caller when orchestrating
> sensitive actions to bypass dynamic lookup and reduce network latency.
>
> **What:** When orchestrating ReAuth for sensitive actions (like modifying code
> review labels), the required project context should be passed by the caller if
> known, bypassing dynamic lookup.
>
> **Applies To:** Gerrit API utilities, specifically request orchestrators like
> `SetReview` and `CreateHttpConn`.
>
> **Why:** The authentication orchestrator was defaulting to an RPC call
> (`GetChangeDetail`) on every review update just to extract the project name
> for the ReAuth token payload, adding unnecessary network latency and server
> load. Failing to adhere to this typically results in **Unnecessary Latency**.

**Trap 1: Omitting known contextual arguments and forcing the underlying utility
to fetch metadata dynamically.**

**Don't:**

```python
# BAD: Forcing the orchestrator to fetch ChangeDetail internally
conn = CreateHttpConn(host, path, reqtype='POST', body=body)
```

**Do:**

```python
# GOOD: Passing the project to save a server round-trip
reauth_context = auth.ReAuthContext(host=host, project=project_from_caller)
conn = CreateHttpConn(host, path, reqtype='POST', body=body, reauth_context=reauth_context)
```

--------------------------------------------------------------------------------

#### T2-07: Graceful Fallback for Standard Access Tokens in ReAuth Flows

> **Rule:** Fall back to standard access tokens (Bearer) when a credential
> helper succeeds but lacks ReAuth-specific fields, unless ReAuth is strictly
> mandated.
>
> **What:** The credential parser must fall back to extracting and returning a
> standard access token (Bearer) if a credential helper call succeeds but does
> not provide ReAuth-specific credentials.
>
> **Applies To:** Credential parsing logic intercepting outputs from
> `git-credential-luci` or similar authentication helpers.
>
> **Why:** The authentication flow was incorrectly failing early when a
> requested ReAuth payload was absent, even when the helper provided a standard
> access token that was completely sufficient for the immediate operation
> context. Failing to adhere to this typically results in **Broken
> Authentication Chain**.

**Trap 1: Rejecting a credential payload entirely because elevated,
ReAuth-specific fields are missing.**

**Don't:**

```python
if authtype and credential:
    return f"{authtype} {credential}"
# BAD: Ignores valid standard password/token
return None
```

**Do:**

```python
if authtype and credential:
    return f"{authtype} {credential}"
# GOOD: Fallback to standard access token
if password := out.get("password", None):
    return f"Bearer {password}"
return None
```

**Exceptions:** Contexts where ReAuth is strictly mandated (hard failure must be
evaluated upstream by the caller checking if a ReAuth-specific token was
successfully attached).

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T4 | Legacy Credential Deprecation & Migration - *Standard
    access token fallback behaviors in ReAuth flows rely on modern centralized
    auth configurations.*
*   **Upstream:** T8 | Service-to-Service Token Semantics - *Token extraction
    must understand standard Bearer token semantics when falling back from
    ReAuth payloads.*
*   **Downstream:** T6 | Authentication Provider Polymorphism & Delegation -
    *ReAuth contextual enforcement directs polymorphic checks within the broader
    Authenticator chain.*

## Chapter: FIDO2 / WebAuthn Hardware Integration

**Context:** This domain governs the low-level integration and fallback logic
for FIDO2 and WebAuthn physical security keys. It dictates OS-specific API
branching, concurrent hardware polling, and fail-safe native UI prompts to
ensure reliable authentication without sandbox violations or silent execution
hangs.

### Summary

| Rule ID   | Principle /          | Priority | Primary Symptom  |
:           : Constraint           :          : / Trap           :
| :-------- | :------------------- | :------- | :--------------- |
| **T3-01** | Native UI Fallbacks  | High     | Relying on       |
:           : for Hardware         :          : non-standard     :
:           : Authentication       :          : external         :
:           : Prompts              :          : binaries to      :
:           :                      :          : prompt for       :
:           :                      :          : hardware         :
:           :                      :          : security PINs on :
:           :                      :          : macOS.           :
| **T3-02** | Just-In-Time         | Medium   | Failing or       |
:           : Evaluation of        :          : warning at       :
:           : Optional Hardware    :          : application      :
:           : Dependencies         :          : startup when an  :
:           :                      :          : optional         :
:           :                      :          : hardware         :
:           :                      :          : dependency is    :
:           :                      :          : missing.         :
| **T3-03** | Bypassing Windows    | High     | Unconditionally  |
:           : Native WebAuthn API  :          : defaulting to    :
:           : in Elevated Contexts :          : the Windows      :
:           :                      :          : native WebAuthn  :
:           :                      :          : API based solely :
:           :                      :          : on OS            :
:           :                      :          : availability.    :
| **T3-04** | Competitive          | Medium   | Awaiting all     |
:           : Concurrency for      :          : hardware token   :
:           : Multiple FIDO2       :          : request futures  :
:           : Devices              :          : to complete      :
:           :                      :          : sequentially or  :
:           :                      :          : unconditionally. :
| **T3-05** | Bypassing Logging    | Critical | Utilizing        |
:           : Subsystems for       :          : standard logging :
:           : Blocking Hardware    :          : frameworks to    :
:           : Prompts              :          : emit critical    :
:           :                      :          : hardware touch   :
:           :                      :          : instructions.    :
| **T3-06** | Explicit             | High     | Silently         |
:           : Environment-Specific :          : bypassing a      :
:           : Authentication Path  :          : preferred        :
:           : Logging              :          : OS-native        :
:           :                      :          : authentication   :
:           :                      :          : API without      :
:           :                      :          : leaving a trace  :
:           :                      :          : in the logs.     :
| **T3-07** | Lazy Initialization  | Medium   | Allocating       |
:           : of Hardware          :          : generic hardware :
:           : Interaction Handlers :          : interaction      :
:           :                      :          : handlers before  :
:           :                      :          : checking if the  :
:           :                      :          : environment      :
:           :                      :          : provides a       :
:           :                      :          : native           :
:           :                      :          : alternative.     :

--------------------------------------------------------------------------------

### Rules

#### T3-01: Native UI Fallbacks for Hardware Authentication Prompts

> **Rule:** Always utilize OS-native UI dialogs for hardware authentication
> prompts rather than introducing external binary dependencies.
>
> **What:** Hardware authentication tools must prefer OS-native UI dialogs
> (e.g., macOS `osascript`, Windows WebAuthn) over external dependencies (like
> `pinentry`) to avoid deployment failures in restricted corporate environments.
>
> **Applies To:** FIDO2/WebAuthn plugins, user interaction handlers
> (`PinEntryInteraction`).
>
> **Why:** The authentication plugin relied on `pinentry` (installed via package
> managers), which was blocked on corporate-managed macOS devices. This caused
> FIDO2 PIN authentication to fail entirely. Failing to adhere to this typically
> results in **Missing Dependency Crash**.

**Trap 1: Relying on non-standard external binaries to prompt for hardware
security PINs on macOS.**

**Don't:**

*   Forcing macOS users to install `pinentry` via Homebrew to authenticate with
    FIDO2 keys.

**Do:**

*   Using native macOS tools like `osascript` to trigger a system dialog for PIN
    entry, removing the external dependency.

**Exceptions:** Linux environments where native fallbacks are less standardized
and `pinentry` remains the expected tool.

--------------------------------------------------------------------------------

#### T3-02: Just-In-Time Evaluation of Optional Hardware Dependencies

> **Rule:** Must defer validation checks for optional hardware dependencies
> until the exact moment they are required by the authentication handshake.
>
> **What:** Validation checks for optional authentication dependencies (like
> `pinentry` for FIDO2 PINs) must be deferred until the dependency is strictly
> required during the handshake, preventing startup noise for unaffected users.
>
> **Applies To:** Hardware authentication plugins and dependency initialization
> phases.
>
> **Why:** The auth plugin checked for `pinentry` at startup and warned users if
> it was missing, even though users with U2F keys (which don't support PINs)
> never needed it, leading to confusion and log spam. Failing to adhere to this
> typically results in **False Positive Warnings / Log Spam**.

**Trap 1: Failing or warning at application startup when an optional hardware
dependency is missing.**

**Don't:**

```python
# BAD: Evaluated at startup for all users
if not get_pinentry_path():
    logging.warning('pinentry command not found!')
```

**Do:**

```python
# GOOD: Evaluated just-in-time only if the key requests a PIN
def request_pin(self, permissions, rp_id):
    proc = subprocess.Popen([get_pinentry_path()], ...)
```

--------------------------------------------------------------------------------

#### T3-03: Bypassing Windows Native WebAuthn API in Elevated Contexts

> **Rule:** Never invoke the native Windows WebAuthn API when the application is
> executing with Administrator privileges; fallback to direct CTAP HID
> execution.
>
> **What:** The client selection logic for FIDO2 devices must dynamically
> disable the usage of the Windows native WebAuthn API if the application is
> executing with Administrator privileges.
>
> **Applies To:** FIDO2 / WebAuthn plugin initialization running in Windows
> environments.
>
> **Why:** Invoking the native Windows WebAuthn APIs from elevated prompts
> results in unpredictable behavior, potential API sandbox restrictions, or
> missing UI, necessitating a direct CTAP HID fallback. Failing to adhere to
> this typically results in **API Sandbox Violation / Missing UI**.

**Trap 1: Unconditionally defaulting to the Windows native WebAuthn API based
solely on OS availability.**

**Don't:**

```python
# BAD: Will fail or hang if the user terminal is running as Admin
use_winclient = WindowsClient.is_available()
```

**Do:**

```python
# GOOD: Explicitly check and block Admin privilege contexts
use_winclient = (WindowsClient.is_available()
                 and not ctypes.windll.shell32.IsUserAnAdmin())
```

--------------------------------------------------------------------------------

#### T3-04: Competitive Concurrency for Multiple FIDO2 Devices

> **Rule:** Must dispatch hardware assertion requests concurrently across all
> detected devices and immediately cancel pending requests upon the first
> successful authentication.
>
> **What:** When multiple FIDO2 hardware devices are detected, assertion
> requests must be dispatched concurrently, but a successful authentication on
> any single device must immediately cancel all pending requests.
>
> **Applies To:** Hardware token polling logic utilizing ThreadPoolExecutors and
> multiple CTAP HID devices.
>
> **Why:** Failure to cancel sibling threads resulted in redundant I/O waits and
> thread leaks, as the application would unnecessarily wait for unused security
> keys to time out even after the user had already successfully interacted with
> one. Failing to adhere to this typically results in **Thread Leak / Blocked
> Execution**.

**Trap 1: Awaiting all hardware token request futures to complete sequentially
or unconditionally.**

**Don't:**

*   Sequentially iterating through FIDO2 clients, or waiting for all concurrent
    futures to return via `as_completed` without signaling an early cancellation
    mechanism.

**Do:**

*   Dispatch FIDO2 requests via ThreadPoolExecutor alongside a shared
    `threading.Event`. The first successful thread sets the event, which
    immediately terminates and cleans up pending futures for the remaining keys.

--------------------------------------------------------------------------------

#### T3-05: Bypassing Logging Subsystems for Blocking Hardware Prompts

> **Rule:** Always write interactive CLI prompts for blocking hardware actions
> directly to `sys.stderr` to bypass configurable logging layers.
>
> **What:** Interactive CLI prompts associated with blocking hardware actions
> (e.g., 'Touch security key') must be written directly to `sys.stderr`,
> bypassing standard logging modules.
>
> **Applies To:** FIDO2 `UserInteraction` implementations or any module
> requesting physical hardware interaction from a user.
>
> **Why:** Because logging levels can be reconfigured or disabled entirely,
> routing physical interaction prompts through `logging.info()` caused the
> application to appear permanently hung (frozen) to users, as the prompt was
> silenced. Failing to adhere to this typically results in **Silent Hang / UX
> Deadlock**.

**Trap 1: Utilizing standard logging frameworks to emit critical hardware touch
instructions.**

**Don't:**

```python
# BAD: Can be silently swallowed if logging is disabled
def prompt_up(self):
    logging.info("Touch your blinking security key to continue.")
```

**Do:**

```python
# GOOD: Guaranteed to reach the terminal UI directly
def prompt_up(self):
    sys.stderr.write("\nTouch your blinking security key to continue.\n\n")
```

--------------------------------------------------------------------------------

#### T3-06: Explicit Environment-Specific Authentication Path Logging

> **Rule:** Must explicitly log the decision branch whenever environmental
> factors force a fallback from native OS APIs to direct hardware access.
>
> **What:** When environmental factors (such as administrator privileges) force
> a fallback or branch in hardware authentication paths (e.g., bypassing a
> native OS WebAuthn API for direct HID access), the decision branch must be
> explicitly logged.
>
> **Applies To:** FIDO2/WebAuthn plugins; environment-based client selection
> logic.
>
> **Why:** Historically, it was difficult to troubleshoot why specific
> authentication clients (like direct CTAP HID vs. native Windows API) were
> chosen at runtime, making environment-specific authentication failures
> extremely hard to diagnose. Failing to adhere to this typically results in
> **Silent Authentication Fallback**.

**Trap 1: Silently bypassing a preferred OS-native authentication API without
leaving a trace in the logs.**

**Don't:**

```python
if WindowsClient.is_available() and not ctypes.windll.shell32.IsUserAnAdmin():
    return [(WindowsClient(client_data_collector), 'WindowsWebAuthn')]
```

**Do:**

```python
if WindowsClient.is_available():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        return [(WindowsClient(client_data_collector), 'WindowsWebAuthn')]
    else:
        logging.info('the user is admin; use Fido2Client instead of WindowsClient')
```

--------------------------------------------------------------------------------

#### T3-07: Lazy Initialization of Hardware Interaction Handlers

> **Rule:** Defer instantiation of hardware UI interaction handlers until after
> confirming the absence of native OS API fallbacks.
>
> **What:** Objects handling hardware interactions or UI prompts must only be
> instantiated immediately prior to their use, avoiding allocation in code paths
> that utilize native OS APIs which manage their own interactions.
>
> **Applies To:** FIDO2 client selection logic and hardware interaction objects.
>
> **Why:** Objects handling UI interactions were previously allocated at the top
> of client selection functions, resulting in redundant memory allocations and
> initialization cycles when native OS APIs short-circuited the function.
> Failing to adhere to this typically results in **Redundant Object
> Allocation**.

**Trap 1: Allocating generic hardware interaction handlers before checking if
the environment provides a native alternative.**

**Don't:**

```python
user_interaction = DiscardInteraction()
if use_winclient:
    return [(WindowsClient(...), 'WindowsWebAuthn')]
# ... code using user_interaction ...
```

**Do:**

```python
if use_winclient:
    return [(WindowsClient(...), 'WindowsWebAuthn')]

user_interaction = DiscardInteraction()
# ... code using user_interaction ...
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T5 | Bot vs. Interactive Execution Contexts - *Determines if
    interactive UI prompts and physical hardware interactions should be
    suppressed or permitted based on environment constraints.*
*   **Downstream:** T7 | Subprocess Error Interception & User Diagnostics -
    *Governs how raw stderr output from low-level hardware components is
    translated and surfaced to the end user.*

## Chapter: Legacy Credential Deprecation & Migration

**Context:** This chapter governs the safe transition from legacy authentication
files (e.g., `.boto`, `.gitcookies`) to centralized systems like `luci-auth`. It
enforces fail-safe mechanisms for automated bots, hardcoded kill-switches for
core infrastructure rollouts, and strict visibility constraints for deprecation
warnings.

### Summary

| Rule ID   | Principle / Constraint       | Priority | Primary Symptom /     |
:           :                              :          : Trap                  :
| :-------- | :--------------------------- | :------- | :-------------------- |
| **T4-01** | Preservation of Legacy       | High     | Enforcing strict      |
:           : Authentication Backdoors for :          : client-side ReAuth    :
:           : Automated Systems            :          : checks that reject    :
:           :                              :          : legacy authenticators :
:           :                              :          : used by bots.         :
| **T4-02** | Hardcoded Kill-Switches for  | Critical | Completely replacing  |
:           : Core Authentication          :          : legacy authentication :
:           : Migrations                   :          : code paths with new   :
:           :                              :          : mechanisms without    :
:           :                              :          : leaving a bypass      :
:           :                              :          : variable.             :
| **T4-03** | Intentional Visibility of    | Medium   | Adding a `--quiet` or |
:           : Deprecation Warnings         :          : `--suppress-warnings` :
:           :                              :          : flag specifically to  :
:           :                              :          : hide deprecation      :
:           :                              :          : notices from users    :
:           :                              :          : operating on broken   :
:           :                              :          : or outdated           :
:           :                              :          : workflows.            :

--------------------------------------------------------------------------------

### Rules

#### T4-01: Preservation of Legacy Authentication Backdoors for Automated Systems

> **Rule:** Never preemptively reject legacy authentication mechanisms (like
> `.gitcookies`) on the client side during ReAuth checks.
>
> **What:** Client-side re-authentication validation must not aggressively fail
> when legacy `.gitcookies` authenticators are present. CI/CD bots rely on these
> cookies and are server-side exempt from ReAuth policies.
>
> **Applies To:** Cookie authenticators (`CookiesAuthenticator`), automated
> service accounts.
>
> **Why:** A strict client-side check was added that immediately threw an error
> if `.gitcookies` was used during a ReAuth-required operation. This broke
> automated CI/CD bots which still rely on cookies but are designated as
> 'trusted robots' by Gerrit. Failing to adhere to this typically results in
> **CI Pipeline Breakage**.

**Trap 1: Enforcing strict client-side ReAuth checks that reject legacy
authenticators used by bots.**

**Don't:**

```python
# BAD: Client-side fail-fast breaks bots
if reauth_context:
    return False, ".gitcookies can't be used when ReAuth is required."
```

**Do:**

```python
# GOOD: Allow execution to proceed; server handles rejections
try:
    self._authenticator.get_authorization_header(reauth_context)
    return (True, '')
```

**Exceptions:** Interactive human users using gitcookies will still eventually
fail, but the rejection must happen via server response, not preemptive client
rejection.

--------------------------------------------------------------------------------

#### T4-02: Hardcoded Kill-Switches for Core Authentication Migrations

> **Rule:** Always implement a hardcoded boolean kill-switch when migrating core
> authentication infrastructure to ensure immediate rollback capability.
>
> **What:** When transitioning between core infrastructure authentication
> mechanisms (e.g., from `.boto` to centralized auth), the logic must include a
> hardcoded boolean kill-switch in the codebase to enable rapid rollback without
> complex git reverts.
>
> **Applies To:** Authentication routing and fallback logic scripts.
>
> **Why:** Rolling out new authentication flows across diverse developer setups
> carries extreme risk. A rapid, single-line configuration rollback mechanism
> was required to mitigate unforeseen, system-wide production emergencies.
> Failing to adhere to this typically results in **Irreversible Auth Breakage**.

**Trap 1: Completely replacing legacy authentication code paths with new
mechanisms without leaving a bypass variable.**

**Don't:**

```python
# Removed boto support entirely
return luci_context(cmd)
```

**Do:**

```python
PREFER_LUCI_AUTH = True
if PREFER_LUCI_AUTH and boto_path:
    return luci_context(cmd)
# Fallback logic to boto if PREFER_LUCI_AUTH is set to False in an emergency
```

**Exceptions:** Once the migration is strictly proven and the legacy system is
formally decommissioned network-wide, the kill-switch can be removed.

--------------------------------------------------------------------------------

#### T4-03: Intentional Visibility of Deprecation Warnings

> **Rule:** Must never provide suppression flags or quiet modes to hide legacy
> authentication deprecation warnings.
>
> **What:** When deprecating legacy authentication files, tools must not provide
> configuration switches to suppress the resulting warnings, forcing downstream
> consumers to address the root technical debt.
>
> **Applies To:** Authentication configuration checks and migration notices.
>
> **Why:** Providing suppression flags for deprecated workflows allowed
> technical debt to persist indefinitely within complex external project builds,
> significantly delaying ecosystem-wide security migrations. Failing to adhere
> to this typically results in **Permanent Technical Debt**.

**Trap 1: Adding a `--quiet` or `--suppress-warnings` flag specifically to hide
deprecation notices from users operating on broken or outdated workflows.**

**Don't:**

```python
if has_gitcookies and not options.suppress_gitcookie_warning:
    print_warning()
```

**Do:**

```python
if has_gitcookies:
    _PrintGitcookiesWarning() # Unsuppressible warning to force workflow migration
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T2 | Gerrit Re-Authentication (ReAuth/RAPT) Orchestration -
    *Dictates the ReAuth context and elevated privilege requirements that
    client-side legacy authenticators must safely pass through.*
*   **Downstream:** T5 | Bot vs. Interactive Execution Contexts - *Relies on
    legacy fallback handlers to successfully authenticate headless CI/CD
    environments without dropping into interactive UI prompts.*

## Chapter: Bot vs. Interactive Execution Contexts

**Context:** Accurately distinguishing between headless CI/CD environments and
interactive developer setups is required to safely suppress UI prompts, skip
unnecessary checks, and route authentications to ambient contexts. This prevents
automated pipelines from hanging on interactive challenges while maintaining
strict security for developers.

### Summary

| Rule ID   | Principle /       | Priority | Primary Symptom / Trap  |
:           : Constraint        :          :                         :
| :-------- | :---------------- | :------- | :---------------------- |
| **T5-01** | Implicit          | High     | Hardcoding interactive  |
:           : Re-Authentication :          : ReAuth failure logic in :
:           : Satisfaction for  :          : a generic orchestrator  :
:           : Ambient Contexts  :          : instead of delegating   :
:           :                   :          : to the context.         :
| **T5-02** | Suppressing       | High     | Only setting            |
:           : IDE-Injected Git  :          : `GIT_TERMINAL_PROMPT=0` :
:           : Credential        :          : and leaving             :
:           : Prompts in        :          : `GIT_ASKPASS`           :
:           : Headless          :          : vulnerable to           :
:           : Scenarios         :          : environmental           :
:           :                   :          : overrides.              :
| **T5-03** | Isolation of      | Critical | Toggling a global       |
:           : Automated         :          : default authentication  :
:           : Contexts from     :          : flag to True without    :
:           : Authentication    :          : verifying the execution :
:           : Migrations        :          : context.                :

--------------------------------------------------------------------------------

### Rules

#### T5-01: Implicit Re-Authentication Satisfaction for Ambient Contexts

> **Rule:** Always delegate ReAuth validation to the execution context, allowing
> ambient authenticators to self-certify and bypass headless challenges.
>
> **What:** Ambient authentication contexts (such as GCE metadata or LUCI
> contexts) must map directly to ReAuth requirements, returning `True` in
> headless environments to natively bypass ReAuth challenges.
>
> **Applies To:** GCE / LUCI Authenticators, bot execution contexts.
>
> **Why:** Automated systems lacked an interactive mechanism to pass ReAuth
> challenges. By abstracting the ReAuth check, ambient contexts could return
> `True` to bypass ReAuth where they are inherently trusted, preventing headless
> hangs. Failing to adhere to this typically results in **Headless Environment
> Hang**.

**Trap 1: Hardcoding interactive ReAuth failure logic in a generic orchestrator
instead of delegating to the context.**

**Don't:**

```python
# BAD: Forces interactive challenges on bots
if reauth_required and not has_reauth_token():
    raise GitReAuthRequiredError()
```

**Do:**

```python
# GOOD: Context self-certifies its trust level
def attempt_authenticate_with_reauth(self, conn, context):
    # GCE/LUCI credential natively satisfies ReAuth.
    self.authenticate(conn)
    return True
```

**Exceptions:** Interactive local development environments must still undergo
actual ReAuth challenges.

--------------------------------------------------------------------------------

#### T5-02: Suppressing IDE-Injected Git Credential Prompts in Headless Scenarios

> **Rule:** Must explicitly neutralize both `GIT_TERMINAL_PROMPT` and
> `GIT_ASKPASS` to guarantee non-interactive Git executions in background
> environments.
>
> **What:** To guarantee non-interactive Git executions, scripts must explicitly
> override both `GIT_TERMINAL_PROMPT` and `GIT_ASKPASS` to negate graphical
> prompt handlers injected by external developer environments.
>
> **Applies To:** Background/automated tooling initiating `git fetch` or `git
> push` subcommands.
>
> **Why:** Disabling `GIT_TERMINAL_PROMPT` was insufficient because IDEs (such
> as VSCode) automatically injected graphical `GIT_ASKPASS` handlers into their
> integrated terminals. This caused automated Git operations with expired tokens
> to hang on a tiny, easily missed UI prompt. Failing to adhere to this
> typically results in **Process Hang / Blocked Execution**.

**Trap 1: Only setting `GIT_TERMINAL_PROMPT=0` and leaving `GIT_ASKPASS`
vulnerable to environmental overrides.**

**Don't:**

```python
# BAD: Susceptible to IDE-injected askpass handlers
env['GIT_TERMINAL_PROMPT'] = '0'
```

**Do:**

```python
# GOOD: Neutralize both terminal prompts and graphical askpass handlers
env['GIT_TERMINAL_PROMPT'] = '0'
env['GIT_ASKPASS'] = ''
```

--------------------------------------------------------------------------------

#### T5-03: Isolation of Automated Contexts from Authentication Migrations

> **Rule:** Never roll out interactive authentication flows globally without
> explicitly exempting automated execution environments via environment
> variables.
>
> **What:** When rolling out new interactive or developer-focused authentication
> stacks as the default behavior, automated execution environments must be
> explicitly exempted via environment variables to prevent CI hangs.
>
> **Applies To:** Feature flags, enablement toggles, and environment boot
> scripts.
>
> **Why:** Rolling out new interactive authentication flows globally
> inadvertently applied them to headless CI bots. Since the bots could not
> handle interactive login prompts, automated builds hung indefinitely. Failing
> to adhere to this typically results in **CI Pipeline Hang**.

**Trap 1: Toggling a global default authentication flag to True without
verifying the execution context.**

**Don't:**

```python
def Enabled() -> bool:
    # Enabled by default for all environments
    return True
```

**Do:**

```python
def Enabled() -> bool:
    if os.getenv('SWARMING_BOT_ID'):
        return False # Exempt headless bots
    return True
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T2 | Gerrit Re-Authentication (ReAuth/RAPT) Orchestration -
    *Provides the orchestrator checks that ambient contexts must implicitly
    satisfy.*
*   **Upstream:** T4 | Legacy Credential Deprecation & Migration - *Defines the
    rollout and fallback logic that must explicitly isolate bot contexts.*
*   **Downstream:** T1 | Git Configuration Hierarchy & Overrides - *Relies on
    isolated bot environments to ensure injected IDE configurations (like
    `GIT_ASKPASS`) do not hijack background operations.*

## Chapter: Authentication Provider Polymorphism & Delegation

**Context:** This chapter defines the architectural design of the Authenticator
interface hierarchy, focusing on polymorphic delegation, capability checks, and
state caching. It outlines mechanisms for chaining authentication attempts,
memoizing provider applicability, and ensuring safe fallbacks for varying
environments.

### Summary

| Rule ID   | Principle / Constraint        | Priority | Primary Symptom /  |
:           :                               :          : Trap               :
| :-------- | :---------------------------- | :------- | :----------------- |
| **T6-01** | Centralized Authenticator     | Medium   | Inlining the       |
:           : Delegation via Generators     :          : applicability loop :
:           :                               :          : and conditional    :
:           :                               :          : check in every     :
:           :                               :          : delegated method.  :
| **T6-02** | Memoization of Authentication | Medium   | Executing          |
:           : State Applicability           :          : expensive state    :
:           :                               :          : checks multiple    :
:           :                               :          : times for a single :
:           :                               :          : host context.      :
| **T6-03** | Consolidated Authentication   | High     | Separating base    |
:           : Pre-flight Strategies         :          : authentication and :
:           :                               :          : re-authentication  :
:           :                               :          : into distinct      :
:           :                               :          : pipeline steps     :
:           :                               :          : that evaluate the  :
:           :                               :          : same underlying    :
:           :                               :          : credential source  :
:           :                               :          : independently.     :
| **T6-04** | Polymorphic Feature Detection | Medium   | Checking if a      |
:           : for Authentication Providers  :          : subclass has       :
:           :                               :          : overridden a       :
:           :                               :          : capability method  :
:           :                               :          : by comparing       :
:           :                               :          : memory             :
:           :                               :          : addresses/pointers :
:           :                               :          : of the functions.  :
| **T6-05** | Graceful Fallback for Missing | Critical | Assuming an HTTP   |
:           : Gerrit Accounts               :          : error during an    :
:           :                               :          : account details    :
:           :                               :          : retrieval          :
:           :                               :          : signifies a        :
:           :                               :          : generic network or :
:           :                               :          : transient failure, :
:           :                               :          : allowing the       :
:           :                               :          : exception to crash :
:           :                               :          : the application.   :

--------------------------------------------------------------------------------

### Rules

#### T6-01: Centralized Authenticator Delegation via Generators

> **Rule:** Always use centralized generators to filter applicable
> authenticators instead of duplicating conditional loops across delegation
> methods.
>
> **What:** Polymorphic chained authenticators should use centralized
> generators/iterators to filter applicable authenticators rather than
> duplicating `is_applicable` conditional checks across multiple delegation
> methods.
>
> **Applies To:** `ChainedAuthenticator` implementations and delegation methods.
>
> **Why:** The logic to iterate over all authenticators and check
> `is_applicable` was duplicated across multiple wrapper methods, leading to
> boilerplate and potential inconsistencies when modifying the chain logic.
> Failing to adhere to this typically results in **Code Duplication**.

**Trap 1: Inlining the applicability loop and conditional check in every
delegated method.**

**Don't:**

```python
# BAD: Duplicating the applicability check
for a in self.authenticators:
    if a.is_applicable(gerrit_host=gerrit_host):
        return a.ensure_authenticated(...)
```

**Do:**

```python
# GOOD: Using a centralized generator
for a in self.applicable_authenticators(gerrit_host=gerrit_host):
    return a.ensure_authenticated(...)
```

#### T6-02: Memoization of Authentication State Applicability

> **Rule:** Must memoize applicability checks for authentication providers
> during command execution to prevent repetitive I/O.
>
> **What:** Applicability checks for authentication providers must be memoized
> (`@functools.cache`) during command execution to avoid redundant network RPCs
> or disk I/O.
>
> **Applies To:** Applicability heuristics (`is_applicable`,
> `gerrit_account_exists`) within short-lived CLI tools.
>
> **Why:** Applicability checks were called multiple times per command
> execution, causing unnecessary repeated Git config reads or network requests
> for an environment state that does not change mid-execution. Failing to adhere
> to this typically results in **Performance Degradation / Redundant I/O**.

**Trap 1: Executing expensive state checks multiple times for a single host
context.**

**Don't:**

```python
# BAD: Reads disk/network on every invocation
def is_applicable(self, *, gerrit_host: str):
    return self.gerrit_account_exists(gerrit_host)
```

**Do:**

```python
# GOOD: Caches the result per command lifecycle
@functools.cache
def is_applicable(self, *, gerrit_host: str):
    return self.gerrit_account_exists(gerrit_host)
```

**Exceptions:** Long-running daemon processes where external authentication
states might realistically change between calls.

#### T6-03: Consolidated Authentication Pre-flight Strategies

> **Rule:** Consolidate ReAuth and standard authentication into a single
> pipeline method to prevent redundant credential helper invocations.
>
> **What:** Polymorphic authenticators must consolidate ReAuth and standard
> authentication into a single pipeline method to prevent redundant invocations
> of expensive credential helpers.
>
> **Applies To:** `_Authenticator` interface hierarchies, network connection
> layers.
>
> **Why:** The HTTP connection flow initially called the standard `authenticate`
> method, and then subsequently called an `attempt_reauth` method. This caused
> the underlying `git-credential-luci` helper to be executed twice per request,
> adding significant latency. Failing to adhere to this typically results in
> **High Latency / Redundant Execution**.

**Trap 1: Separating base authentication and re-authentication into distinct
pipeline steps that evaluate the same underlying credential source
independently.**

**Don't:**

```python
# BAD: Runs credential helper twice
authenticator.authenticate(conn)
if reauth_context:
    authenticator.attempt_reauth(conn, reauth_context)
```

**Do:**

```python
# GOOD: Checks ReAuth first, falls back to standard auth if unavailable
reauth_succeed = authenticator.attempt_authenticate_with_reauth(conn, reauth_context)
if not reauth_succeed:
    authenticator.authenticate(conn)
```

#### T6-04: Polymorphic Feature Detection for Authentication Providers

> **Rule:** Never use method identity checks to determine authenticator
> capabilities; handle feature detection polymorphically via boolean method
> returns.
>
> **What:** Determining whether a specific authenticator subclass supports a
> feature (like ReAuth) must be handled polymorphically via boolean method
> returns, rather than by evaluating method identity.
>
> **Applies To:** Chained authenticators or authentication delegators evaluating
> capabilities of subclass providers.
>
> **Why:** The system relied on runtime identity checks (`method is not
> Base.method`) to determine if an authenticator supported ReAuth. This was
> fragile, non-idiomatic, and susceptible to breakages during class refactoring.
> Failing to adhere to this typically results in **Brittle Interface
> Delegation**.

**Trap 1: Checking if a subclass has overridden a capability method by comparing
memory addresses/pointers of the functions.**

**Don't:**

```python
if a.authenticate_with_reauth is not _Authenticator.authenticate_with_reauth:
    # Authenticator applies and concrete instance supports ReAuth
    a.authenticate_with_reauth(conn, context)
```

**Do:**

```python
# Base class defines a default `attempt_reauth(...) -> bool: return False`
if a.attempt_reauth(conn, context):
    return True
```

#### T6-05: Graceful Fallback for Missing Gerrit Accounts

> **Rule:** Must explicitly catch HTTP 400 errors and missing-account exceptions
> during Gerrit API lookups to trigger safe fallbacks instead of crashing.
>
> **What:** The authentication flow must explicitly catch HTTP 400 errors (Bad
> Request) and `LoginRequiredError` during Gerrit API account lookups,
> interpreting them as a "missing account" state and falling back gracefully
> rather than crashing.
>
> **Applies To:** Gerrit Authentication Providers (`gerrit_util.py`,
> `git_auth.py`); specifically polymorphic capability checks like
> `gerrit_account_exists`.
>
> **Why:** If a user was successfully authenticated via SSO but lacked an
> explicit account on a specific internal/private Gerrit host, Gerrit returned
> an HTTP 400 Bad Request. Unhandled, this bubbled up as a fatal traceback and
> crashed the entire sync process. Failing to adhere to this typically results
> in **Application Crash / Traceback**.

**Trap 1: Assuming an HTTP error during an account details retrieval signifies a
generic network or transient failure, allowing the exception to crash the
application.**

**Don't:**

```python
# BAD: Fails fatally on HTTP 400
info = GetAccountDetails(host, authenticator=cls())
return 'email' in info
```

**Do:**

```python
# GOOD: Catch known HTTP states representing valid missing-account scenarios
try:
    info = GetAccountDetails(host, authenticator=cls())
except GerritError as e:
    if e.http_status == 400:
        return False
    raise
return 'email' in info
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T2 | Gerrit Re-Authentication (ReAuth/RAPT) Orchestration -
    *Provides the generated ReAuth context and fallback logic utilized by the
    authenticator hierarchy.*
*   **Downstream:** T7 | Subprocess Error Interception & User Diagnostics -
    *Translates the HTTP errors and raw exceptions caught by authenticators into
    human-readable instructions.*

## Chapter: Subprocess Error Interception & User Diagnostics

**Context:** This chapter governs the interception and translation of raw
subprocess outputs and exit codes from command-line credential tools. It
mandates converting low-level failures into semantic, actionable exceptions to
prevent exposing raw tracebacks or numerical exit codes to users and downstream
logic.

### Summary

| Rule ID   | Principle / Constraint         | Priority | Primary Symptom /    |
:           :                                :          : Trap                 :
| :-------- | :----------------------------- | :------- | :------------------- |
| **T7-01** | Diagnostic Translation of      | High     | Allowing raw         |
:           : Subprocess Authentication      :          : `CalledProcessError` :
:           : Errors                         :          : exceptions to        :
:           :                                :          : propagate directly   :
:           :                                :          : to the user when a   :
:           :                                :          : known auth tool      :
:           :                                :          : fails.               :
| **T7-02** | Explicit Exception Raising for | High     | Silently returning   |
:           : Missing Subprocess Credentials :          : `None` when a        :
:           :                                :          : required standard    :
:           :                                :          : token payload is not :
:           :                                :          : found in subprocess  :
:           :                                :          : output.              :
| **T7-03** | Encapsulation of Subprocess    | Medium   | Defining public      |
:           : Exit Codes Behind Exceptions   :          : numerical exit code  :
:           :                                :          : constants and        :
:           :                                :          : expecting downstream :
:           :                                :          : clients to utilize   :
:           :                                :          : them in conditional  :
:           :                                :          : logic.               :

--------------------------------------------------------------------------------

### Rules

#### T7-01: Diagnostic Translation of Subprocess Authentication Errors

> **Rule:** Always intercept raw subprocess errors from authentication tools and
> translate them into actionable, high-level exceptions.
>
> **What:** Raw subprocess errors containing specific authentication failure
> signatures must be intercepted and translated into high-level, actionable
> error classes rather than exposing raw tracebacks.
>
> **Applies To:** CLI command wrappers and `subprocess` invocation sites
> handling Git or credential helpers.
>
> **Why:** When ReAuth tokens expired during a `git push`, the underlying
> credential helper emitted an error that resulted in a raw `CalledProcessError`
> stack trace. This obscured the root cause and left users confused on how to
> recover. Failing to adhere to this typically results in **Obscured Root
> Cause**.

**Trap 1: Allowing raw `CalledProcessError` exceptions to propagate directly to
the user when a known auth tool fails.**

**Don't:**

```python
# BAD: Raw tracebacks leak to user
except subprocess2.CalledProcessError as e:
    raise GitPushError('Failed to upload change')
```

**Do:**

```python
# GOOD: Translates recognized stdout patterns into actionable instructions
except subprocess2.CalledProcessError as e:
    if 'git credential-luci reauth' in str(e.stdout):
        raise GitPushError('ReAuth is required.\nPlease run: git credential-luci reauth') from None
```

**Exceptions:** Unrecognized subprocess outputs should still raise generic
errors or preserve the original stack trace for debugging.

--------------------------------------------------------------------------------

#### T7-02: Explicit Exception Raising for Missing Subprocess Credentials

> **Rule:** Never return `None` when a credential payload is missing from
> subprocess output; strictly raise a domain-specific exception.
>
> **What:** Parsers executing command-line credential helpers must raise
> domain-specific exceptions (e.g., `GitUnknownError`) when a valid token is
> missing, rather than silently returning `None`.
>
> **Applies To:** Credential extraction wrappers managing subprocess calls
> (e.g., `subprocess2.check_call_out`).
>
> **Why:** Returning `None` for absent credentials caused type-hint mismatches
> (failing pyright static analysis) and shifted null-pointer handling
> downstream, leading to obscure runtime bugs. Failing to adhere to this
> typically results in **Downstream Type Error**.

**Trap 1: Silently returning `None` when a required standard token payload is
not found in subprocess output.**

**Don't:**

```python
if password := out.get("password", None):
    return password
logging.error('git-credential-luci did not return a token')
return None  # BAD: Leads to unhandled NoneType errors downstream
```

**Do:**

```python
if password := out.get("password", None):
    return password
logging.error('git-credential-luci did not return a token')
raise GitUnknownError()  # GOOD: Fails fast and preserves type safety
```

--------------------------------------------------------------------------------

#### T7-03: Encapsulation of Subprocess Exit Codes Behind Exceptions

> **Rule:** Must map internal subprocess exit codes to private constants and
> translate them into semantic exceptions before propagating to callers.
>
> **What:** Underlying command-line exit codes from external tools must be
> stored as private constants and mapped to semantic domain exceptions rather
> than exposing raw numerical codes to callers.
>
> **Applies To:** Modules wrapping CLI binaries (e.g., `auth.py` wrapping
> `git-credential-luci`).
>
> **Why:** Exposing public numerical exit code constants tightly coupled caller
> logic to the internal implementation details of an external binary. This
> brittle design made future updates to the external tool highly disruptive.
> Failing to adhere to this typically results in **Brittle API Coupling**.

**Trap 1: Defining public numerical exit code constants and expecting downstream
clients to utilize them in conditional logic.**

**Don't:**

```python
# BAD: Exposing raw subprocess codes
GCL_EXITCODE_REAUTH_REQUIRED = 3
# ... external caller ...
if e.returncode == GCL_EXITCODE_REAUTH_REQUIRED:
```

**Do:**

```python
# GOOD: Private constants mapped to semantic exceptions
_GCL_EXITCODE_REAUTH_REQUIRED = 3
# ... internal handler ...
if exitcode == self._GCL_EXITCODE_REAUTH_REQUIRED:
    raise GitReAuthRequiredError()
```

--------------------------------------------------------------------------------

### Cross-Domain Dependencies

*   **Upstream:** T1 | Git Configuration Hierarchy & Overrides - *Git
    configurations invoke the credential helpers that generate the subprocess
    errors intercepted here.*
*   **Upstream:** T2 | Gerrit Re-Authentication (ReAuth/RAPT) Orchestration -
    *Subprocess wrappers detect missing ReAuth contexts and translate them to
    trigger orchestrator fallback flows or user instructions.*

## Chapter: Service-to-Service Token Semantics

**Context:** This domain governs the formatting and semantics of OAuth2 tokens
exchanged across internal infrastructure services. It strictly enforces the
transition from legacy OIDC ID tokens to standard Access/Bearer tokens across
LUCI configurations and APIs.

### Summary

| Rule ID   | Principle / Constraint  | Priority | Primary Symptom / Trap     |
| :-------- | :---------------------- | :------- | :------------------------- |
| **T8-01** | Enforce Standard OAuth2 | Medium   | Continuing to request and  |
:           : Access Tokens for LUCI  :          : pass OIDC ID tokens for    :
:           : Config Communication    :          : LUCI Config communication  :
:           :                         :          : due to outdated            :
:           :                         :          : architectural constraints. :

--------------------------------------------------------------------------------

### Rules

#### T8-01: Enforce Standard OAuth2 Access Tokens for LUCI Config Communication

> **Rule:** Always use standard OAuth2 Bearer (Access) tokens for
> service-to-service communication with LUCI Config. Never pass legacy OIDC ID
> tokens unless the target service is explicitly shielded by Identity-Aware
> Proxy (IAP).
>
> **What:** Service-to-service communication with LUCI Config must use standard
> OAuth2 Bearer (Access) tokens instead of OIDC ID tokens, reflecting the
> removal of legacy IAP proxy constraints.
>
> **Applies To:** LUCI Config clients, dependent Go CLIs (`lucicfg`), and
> authentication token generation services.
>
> **Why:** Historically, ID tokens were required because the LUCI Config service
> was placed behind Identity-Aware Proxy (IAP) during development. After these
> restrictions were lifted, clients continuing to send ID tokens caused
> confusion and non-standard authentication flows. Failing to adhere to this
> typically results in **Non-Standard Auth / Validation Failure**.

**Trap 1: Continuing to request and pass OIDC ID tokens for LUCI Config
communication due to outdated architectural constraints.**

**Don't:**

```go
// BAD: Requesting an OIDC ID token for LUCI Config
token := get_oidc_id_token(audience="luci-config")
```

**Do:**

```go
// GOOD: Requesting standard OAuth2 Bearer token
token := get_oauth2_access_token(scopes)
```

**Exceptions:** Services that are still explicitly shielded by IAP where OIDC ID
tokens remain mandatory.
