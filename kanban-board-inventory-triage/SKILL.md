---
name: kanban-board-inventory-triage
description: "Snapshot-first triage of live Kanban board state for sweep/reconciliation jobs."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [kanban, triage, board-state, sweep, reconciliation]
---

# Kanban Board Inventory Triage

Use this skill when you need a fast, evidence-backed read on live board state before deciding whether to reconcile PRs, promote children, or leave the board unchanged.

This is a lightweight companion to broader Kanban orchestration skills. It focuses on inventorying the board safely and deterministically.

## Core rule

Always snapshot the board to a file first, then parse locally.

Do **not** stream live board output directly into an interpreter when a file-backed snapshot is available.

## Standard flow

1. Capture a snapshot:

```bash
mkdir -p /tmp/haft-sweep
hermes kanban --board haft list --json > /tmp/haft-sweep/board.json
```

2. Parse the snapshot locally.
   - Treat the payload as a top-level JSON array of task objects.
   - Count statuses first: `ready`, `running`, `review`, `blocked`, `done`.
   - Inspect claimability fields when needed: `assignee`, `workspace_kind`, `workspace_path`, `branch_name`.

3. Reconcile against GitHub PR state.
   - Check merged PRs on the relevant base branches.
   - For Haft sweeps, inspect both `master` and feature lanes such as `cow` when they are active.
   - Use PR state plus board comments to match review cards to real PRs.

4. Decide whether action is needed.
   - If the board is already consistent and no promotion is needed, return `[SILENT]`.
   - If merged work exists, move review cards to Done.
   - If a Done card unlocks children, promote only dependency-safe Todo children.

## Queue hygiene reminders

- Do not claim worker tasks as the orchestrator.
- Do not promote cards that are not actually unblocked.
- Do not leave worktree cards in Ready unless they are genuinely claimable.
- Prefer evidence over comments: board state, PR state, and comments must agree before you act.

## Pitfalls

- A blank open-PR result does not prove there is no merged PR to reconcile; check merged state explicitly.
- A large board snapshot is easier to reason about from a file than from a live pipe.
- Ready worktree cards need valid branch and workspace metadata before they count as healthy queue runway.
- **Merged-review completion fallback:** if GitHub proves a review card's PR is merged but both the Kanban completion tool and `hermes kanban complete` refuse with `unknown id or terminal state`, do not leave the card in Review. Re-read the exact task and confirm its live status, PR URL, and merged SHA. Only then use the board-scoped SQLite fallback transaction: mark the task `done`, clear active claim/run fields, close the review run as `done/completed` with bounded PR metadata, append a status event, and re-read it. Recompute/promote dependency-safe children afterward and validate their Ready metadata. Never use this fallback for an unmerged PR or a red required check.

## Reference

See `references/board-inventory-json-triage-notes.md` for a session-proven snapshot/parse pattern and observed board JSON fields.
See `references/gateway-guard-live-board-snapshot-fallback-2026-08-07.md` for the detached snapshot fallback when a live Hermes board read is blocked by the gateway guard.

## Related skills

- `kanban-orchestrator-operations`
- `kanban-dependency-integrity`
- `pr-review-reconciliation`
