---
name: github-herdr-project-dispatch
description: Use when dispatching GitHub Issues to local Herdr workers.
version: 1.0.0
author: Hermes Agent
license: Proprietary
metadata:
  hermes:
    tags: [github, projects, herdr, dispatch, workspaces, lifecycle]
---

# GitHub Issue Dispatch Through Herdr

## When to Use

Use when a user asks to dispatch a GitHub Issue to a local Herdr worker, especially when the worker must manage GitHub Project state and the human needs a dedicated review workspace.

Use this class-level workflow when a user wants a local Herdr worker to execute a GitHub Issue while managing its GitHub Project lifecycle. This is distinct from Hermes Kanban: the GitHub worker may own GitHub issue/project state when explicitly delegated, while the orchestrator independently verifies the result.

## Required workspace shape

1. Create a **new dedicated Herdr workspace** and a new tab/pane for each dispatched issue. Do not split or reuse an existing active workspace.
2. Launch the worker in that workspace at the repository root or a dedicated worktree.
3. Label both pane and Hermes session with exact `github-issue-<id>` naming where supported.
4. Leave the workspace available for full-screen human review; do not bury the worker in a crowded existing tab.

## Preflight before claim

1. Verify the issue is open and unassigned, or reconcile an existing owner.
2. Verify the worker's actual `gh auth status`, not only the controller shell. Project lifecycle requires `read:project` and `project` access.
3. Never let a noninteractive worker run `gh auth refresh`, device login, or browser authorization. If scope is missing, stop before claiming and report the exact credential boundary.
4. Query the live project item and canonical status field; never guess project or item IDs.

## Worker lifecycle contract

When explicitly delegated, the worker must:

1. Claim the issue for its GitHub identity.
2. Move **Ready → In Progress** before implementation/investigation.
3. Work in a dedicated worktree and keep the main checkout clean.
4. Report concise progress, concrete evidence, blockers, and friction; do not request or expose hidden chain-of-thought.
5. On completion, move **In Progress → Review** and add a sanitized evidence comment.
6. Never move to Done or merge without explicit approval.

## Dispatch and model fallback

Attempt the requested provider/model route once. If provider routing fails before tool execution, record it as dispatch telemetry and use an explicitly authorized fallback only when needed to complete the task. Do not blindly resubmit the same prompt. Record provider/model attempted, fallback, elapsed/round-trip waste, and whether any side effect occurred.

## Verification

The orchestrator independently verifies pane/workspace/session identity, issue assignee, project status, comments, PRs, changed files, worktree cleanliness, checks, and that no cron, credential change, or unauthorized deployment was created.

For browser-dependent acceptance, distinguish backend/test evidence from live authenticated visual evidence. A worker reaching Review with a browser blocker is not Done.

## Friction capture

Capture material friction as concise product-intake evidence: stale or guessed IDs, missing project scopes, interactive auth in noninteractive panes, approval prompts, crowded-pane readability, model/provider fallback waste, and missing authorized browser sessions. Prefer fixes that eliminate extra agent turns and prevent partial claims.

See `references/github-herdr-dispatch-lessons.md` for validated incident patterns and the reusable preflight checklist.
