---
name: kanban-dependency-integrity
description: Verify board dependency transitions against real implementation reality before promoting or closing dependent work. Use when a parent card is marked Done, a child is newly unblocked, or board state was repaired from a merged PR / docs-only reconciliation.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [kanban, orchestration, dependencies, reconciliation, review, promotion]
---

# Kanban Dependency Integrity

Use this skill when board transitions affect downstream readiness.

This skill is about one rule:
**a board transition is not proof of implementation unless the underlying contract exists on the target branch.**

## When to use

- A parent card moved to Done and children may now be promotable.
- A review card was reconciled from a merge, recovery script, or manual board repair.
- A card was marked done via docs-only evidence, but downstream work depends on code that may not exist.
- You are deciding whether to promote a Todo child to Ready.

## Core workflow

1. Load live board state first.
2. For the parent card, verify the implementation contract on the relevant branch or target ref.
3. If the parent was completed from a docs-only merge, stale PR, or board-side recovery, treat the board as advisory until code reality is checked.
4. Only promote a child when **all** of its parents are truly Done **and** the parent contract the child needs actually exists.
5. If the required helper/API/surface is missing, keep the child blocked and leave a reconciliation note.

## Pitfall: docs-only completion can fake runway

A parent can look complete because a related PR merged or a board repair moved the card to Done, but the required runtime helper/API may still be absent.

Do not promote children just because the parent card is Done.

Before unblocking, verify:
- the parent PR actually implemented the needed seam;
- the relevant branch contains the contract the child expects;
- the board transition was not based on a non-implementation artifact (docs, comments, or a superseding repair).

## Pitfall: board repair is not implementation

If a card was repaired by a reconciliation action, use that as a signal to re-check code reality, not as proof that the code path exists.

Typical signs:
- the parent was closed because of a docs PR;
- a comment says "reconciled" or "completed" without a matching implementation diff;
- the child references helpers or routes that cannot be found on the target branch.

## Verification pattern

- Inspect the parent card body and latest comments.
- Confirm the target branch or `origin/master` contains the expected helper/API.
- If necessary, search the codebase for the exact seam before promoting the child.
- If the child is a worktree card that just auto-promoted from a parent Done transition, validate the Ready metadata immediately before counting it as runway.
- If the seam is missing, leave the child blocked and record why.
- If you need to read dependency edges directly, use the live board DB and the `task_links(parent_id, child_id)` schema; check `PRAGMA table_info(task_links)` before assuming column names.

## Output discipline

When blocking a child because the parent contract is missing:
- say exactly what contract is absent;
- say what branch/ref was checked;
- avoid claiming the queue is healthy just because the board status moved.

## Related skills

- `haft-orchestrator-workflows`
- `kanban-orchestrator-operations`

This skill complements those workflows by adding a fail-closed rule for dependency promotion.

Reference: `references/docs-only-parent-reconciliation.md` contains the concrete docs-only parent completion failure mode and the checklist to re-verify before promotion.
Additional reference: `references/review-card-merge-child-promotion-2026-07-16.md` captures the merge → done → child promotion → worktree validation sequence for freshly unblocked Ready cards.
