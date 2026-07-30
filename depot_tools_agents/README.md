# depot_tools AI Review Agents (WIP)

**Note:** This project is a work in progress and is subject to change.

This directory contains configurations and skills for AI review agents that
automatically analyze changes in the `depot_tools` codebase.

These agents help maintain code quality, enforce style guidelines, and catch
common pitfalls before code is merged.

## Directory Structure

*   [`agent_configs.txtpb`](agent_configs.txtpb): Defines the active AI
    agents, their configurations, and which skills they are equipped with.
*   [`skills/`](skills/): Contains the "skills" (rules, guidelines, and traps)
    used by the agents.
    *   [`code-review-workflow/`](skills/code-review-workflow/SKILL.md):
        Guidelines for Gerrit review coordination, OWNERS/code-ownership and
        approvals, Python code style, commit metadata, documentation, and
        developer collaboration.
    *   [`core-internals/`](skills/core-internals/SKILL.md): Technical
        guidelines for `depot_tools` core logic (SCM/git wrappers, gclient,
        vpython, presubmit, git_cl tooling, build-system IPC, filesystem
        management, and Git/LUCI authentication).

## How It Works

The agents defined in `agent_configs.txtpb` are configured to run
automatically on new changes. They analyze the diffs against the rules defined
in their respective skills and provide feedback in the code review interface
(e.g., Gerrit).

## Contributing

To improve the agent's review quality or add new rules:

1.  **Update existing skills**: Modify the `SKILL.md` files under `skills/` to
    add new rules, "What" explanations, "Why" rationales, and "Traps"
    (Don't/Do code examples).
2.  **Add new skills**:
    *   Create a new directory under `skills/`.
    *   Add a `SKILL.md` following the established format (see existing skills
        for reference).
    *   Register the new skill in `agent_configs.txtpb` by adding it to the
        `skills` field of an agent configuration.
