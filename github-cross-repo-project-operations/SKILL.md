---
name: github-cross-repo-project-operations
description: Use when bootstrapping cross-repository GitHub Projects.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, projects, issues, cross-repository, kanban-migration]
---

# Cross-repository GitHub Project Operations

## When to Use

Use when replacing a machine-local task board with GitHub Issues and an organization-wide Project V2, or when bootstrapping a cross-repository project for remote agents.

## Purpose

Use this class-level workflow when a project is moving from a machine-local task board to GitHub Issues plus an organization-wide GitHub Project V2. The goal is to make task state accessible to remote agents while preserving an explicit workflow contract, provenance, and safe issue content.

## Operating sequence

1. **Discover scope and authority.** Verify `gh auth status`, organization ownership, and the active repository list. Do not assume the current checkout represents the whole organization. Decide explicitly whether GitHub Issues/Project is becoming the forward source of truth; retain old board IDs only as provenance.
2. **Create the organization project.** Create one organization-owned Project V2, record its URL/number, add a concise description, and write a README containing the workflow, issue contract, repository scope, and migration rule.
3. **Link repositories.** Link every active repository in scope. A project may accept cross-repository items without links, but explicit links document intended scope and improve discoverability.
4. **Define canonical workflow fields.** GitHub creates a built-in `Status` field with its own `Todo/In Progress/Done` options. Do not assume the default field can be renamed or replaced through the CLI. Create a custom single-select field named `Stage` with exactly the product states, and omit deprecated lanes such as Triage when the user says they are not used. Add `Priority` only if required by the operating contract.
5. **Configure the view honestly.** Set the initial view to board layout. Query the view afterward. If the available CLI/GraphQL surface cannot set the group-by field reliably, report the remaining one-time UI action to group by the canonical `Stage` field; do not claim the visible columns are correct just because the field exists.
6. **Create the first issue as a durable handoff.** Use a structured body with goal, bounded current evidence, checklist, acceptance criteria, safety boundaries, and historical provenance. Never include credentials, OTPs, invitation tokens, cookies, signed URLs, private document bodies, or raw private source paths.
7. **Add and initialize the project item.** Add the issue URL to the project, set the canonical `Stage` and `Priority`, and re-read the project item. Verify issue number, repository, project item ID, stage, priority, and project URL before reporting completion.
8. **Keep issue and project state distinct.** An open issue can be To-do, Scheduled, Ready, or Review. Closing an issue is not a substitute for setting the final project stage; reconciliation automation must define how issue/PR state maps to Stage.

## Remote-agent contract

Issue bodies and the project README must be sufficient for a worker without access to the originating machine. Include exact acceptance and safety boundaries, not only a title or a pointer to local board history. Historical local-board identifiers are useful provenance but must never be required for execution.

## Migration and reconciliation

- New work goes to GitHub Issues and the organization project.
- Existing local-board cards should be migrated selectively with provenance links rather than copied blindly.
- Preserve the distinction between implementation state, review state, and done/accepted state.
- Prefer idempotent project-item updates and verify after each mutation.
- If two workflow fields coexist, declare one canonical in the project README and automation; otherwise state drift is likely.

## Verification checklist

- [ ] Authenticated organization and repository scope verified.
- [ ] Organization project URL/number captured.
- [ ] Project README explains workflow, repository scope, issue contract, and migration.
- [ ] All intended repositories linked.
- [ ] Canonical `Stage` options match the user request exactly.
- [ ] Board layout verified; group-by limitation reported if applicable.
- [ ] First issue has bounded evidence and acceptance criteria.
- [ ] Issue is added to the project with verified Stage/Priority.
- [ ] No secrets or private document content entered into project metadata.

See `references/cross-repo-project-bootstrap.md` for the reusable command sequence, API caveats, and verification evidence shape.
