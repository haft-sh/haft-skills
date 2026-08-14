---
name: haft-sprint-planner-orchestration
description: "Haft Sprint Planner queue promotion and triage from live Kanban state."
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [kanban, sprint-planning, cron-jobs, haft, queue-management]
---

# Haft Sprint Planner Orchestration

## Purpose

Use this skill only to move existing Haft Kanban work toward execution from live board state.

The planner may:

- inspect `triage`, `scheduled`, and `todo` cards;
- promote existing cards when their timing, dependencies, scope, and metadata make them executable;
- classify actionable triage cards into the appropriate existing workflow state;
- leave concise comments when a state transition needs an audit trail.

The planner must not create new cards, derive work from planning documents, select work from historical priority context, merge pull requests, or perform implementation.

## Procedure

1. Read the repo `AGENTS.md` only for current board mechanics, worker-lane rules, workspace requirements, and claimability policy.
2. Inspect live `triage`, `scheduled`, `todo`, `ready`, `running`, `review`, and `blocked` state.
3. Evaluate existing cards using only their live body, dependencies, comments, events, and current status.
4. Process triage conservatively:
   - move a card forward only when its objective, acceptance criteria, ownership lane, and required metadata are concrete;
   - choose `todo` when dependencies remain;
   - choose `scheduled` only when the card itself contains an explicit future timing condition;
   - choose `ready` only when it is immediately executable and fully claimable;
   - leave ambiguous or product-decision-dependent cards in triage.
5. Promote `scheduled` cards only when their explicit timing condition has arrived and all dependencies are satisfied.
6. Promote `todo` cards only when every parent dependency is done and the card is immediately executable.
7. Before any Ready transition, verify:
   - acceptance criteria are concrete;
   - no unmet dependency or unresolved decision remains;
   - worktree cards use repo-root workspace `<haft-repo-root>`;
   - `branch_name` is non-empty and worker-neutral;
   - `assignee` is null for external-worker Ready cards.
8. Re-read the affected cards after mutation and verify their final state and metadata.

## Output policy

- If no card is eligible for triage or promotion and no anomaly requires attention, output exactly `[SILENT]`.
- If cards changed, report only the card IDs, old and new states, and the live reason for each transition.
- If an item cannot move because of missing information or a genuine blocker, report the exact blocker without inventing work.

## Safety boundaries

- Never create replacement, follow-up, recovery, or queue-filler cards.
- Never promote a tracker, placeholder, or broad idea into Ready.
- Never infer priority from a document, card age, naming convention, or completed work.
- Never change Done, Review, Running, or Blocked cards except to read them as dependency context.
- Never assign an external-worker Ready card.
- Never claim success without verifying the post-transition live board state.
