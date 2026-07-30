---
name: core-internals
description: Provides guidance and best practices on depot_tools core internals; SCM/git wrappers, gclient dependency resolution, vpython environments, presubmit infrastructure, git_cl tooling, build-system daemons and IPC, filesystem management, and Git/LUCI authentication.
---

# Depot Tools Core Internals

## Executive Summary

This skill consolidates the technical internals of the depot_tools codebase. It
captures the failure modes and architectural constraints governing the SCM/git
wrappers, gclient, hermetic vpython environments, presubmit infrastructure,
git_cl tooling, build-system daemon/IPC orchestration, filesystem atomicity, and
Git/LUCI authentication layers.

## How to use this skill

Use this page as the overview, then open the relevant reference guide below for
the detailed rules, rationale, traps, and worked examples on a given topic. Each
guide is self-contained — read only the one(s) relevant to the code under review.

## Reference guides

| Topic | When to consult | Guide |
|-------|-----------------|-------|
| Core infrastructure | SCM/git wrappers & configuration, gclient dependency resolution, hermetic vpython, presubmit infrastructure, formatter/linter orchestration, and Gerrit REST/CLI internals. | [Depot_Tools_Infrastructure_guide.md](references/Depot_Tools_Infrastructure_guide.md) |
| Build system infrastructure | Daemon orchestration & health polling, IPC socket safety/constraints, declarative build-state extraction, and platform-specific (Windows) build toolchains. | [Build_System_Infrastructure_guide.md](references/Build_System_Infrastructure_guide.md) |
| git_cl & CLI tooling | Flag propagation/order resolution, batch-operation checkpointing & conflict recovery, rebase/reference resolution, stale-branch GC, host-URL parsing, and actionable diagnostics. | [Git_CL_Tooling_guide.md](references/Git_CL_Tooling_guide.md) |
| Filesystem management | Destructive-path validation, cross-platform path constraints, OS-native syscalls/performance, configuration transactionality, and subprocess lifecycle/resource management. | [Filesystem_Management_guide.md](references/Filesystem_Management_guide.md) |
| Git & LUCI authentication | Gerrit re-authentication (ReAuth/RAPT), FIDO2/WebAuthn hardware integration, legacy credential migration, bot vs. interactive contexts, and service-to-service tokens. | [Git_and_LUCI_Authentication_guide.md](references/Git_and_LUCI_Authentication_guide.md) |
