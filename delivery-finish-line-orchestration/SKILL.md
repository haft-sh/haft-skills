---
name: delivery-finish-line-orchestration
description: Reconcile roadmap/epic tracker cards against actual child-card delivery, identify the true finish-line work, and decide when prod/infra follow-ons should stay with the orchestrator instead of being handed to generic workers.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Delivery Finish-Line Orchestration

Use when:
- a board looks stalled because epic/phase tracker shells stay Scheduled while real execution happened in child cards
- the user asks for a bird's-eye roadmap/epic status and the visible tracker state may be misleading
- you need to promote the final executable cards that actually close an initiative
- the remaining work is prod/infra/deploy execution and may be a poor fit for generic implementation-worker handoff

## Core workflow

1. **Read live board state, not memory.** Inspect the epic/tracker card, then compare it to live child cards across `done`, `review`, `running`, `ready`, and `scheduled`.
2. **Separate tracker shells from execution cards.** A Scheduled epic/phase shell does not mean the initiative is idle if child implementation cards are already Done.
3. **Report truth at two layers.**
   - *Board-presentation truth*: tracker cards may still be Scheduled.
   - *Delivery truth*: the substantive implementation may already be largely complete.
4. **Identify the real finish-line cards.** Promote only the executable cards that still matter; do not promote tracker shells just to make the queue look active.
   - Trace the actual user journey, not feature labels. Similar-looking local and managed flows may have different side effects.
   - Read acceptance criteria for permitted deferrals such as disabled mutation wiring; a projection-only UI card does not implicitly deliver the action button.
   - Add a dedicated integration card for any missing mutation seam, then add one final end-to-end proof card covering delivery, acceptance, destination authorization, revocation, and exact-commit deployment.
5. **Reconcile stale gating.** If a finish-line card still points at old tracker-parent dependencies that no longer reflect delivered reality, document that explicitly before changing status.
6. **Treat prod/infra follow-ons differently.** When the remaining work is dedicated production infrastructure, deploy automation, DNS/TLS, or similar operator-facing finish-line work, prefer direct orchestrator execution over generic worker runway unless the user wants delegation.

## User-preference lesson

For JP-style orchestration, prod/infra finish-line work should default to **direct orchestrator execution** when feasible, even if ordinary implementation slices usually go through worker cards. Do not assume every Ready card belongs in generic worker runway.

## Promotion rules

Promote a card to Ready only if all are true:
- it is executable now
- its dependencies are satisfied in substance, not just cosmetically
- it represents real remaining work, not roadmap signage
- it will not create avoidable collision with already-running review/merge work

Keep a card parked when any of these are true:
- it is still a tracker/program shell
- it depends on future operator access or credentials you do not have yet
- it is better executed directly by the orchestrator because of infra/prod risk

## Bird's-eye reporting format

When summarizing initiative status, explicitly provide:
1. **Executive summary** — one sentence on actual delivery state
2. **What is done** — phases/slices materially delivered
3. **What remains** — the actual finish-line cards
4. **What needs operator input** — credentials, IAM, DNS, host choice, deploy path
5. **Judgment** — whether the board presentation is misleading relative to real delivery

For staged epic ladders driven by a planning doc, reconcile against the current source-of-truth doc explicitly (for example, the newest dated plan on `master`), not just tracker-card status. When the final implementation slice merges, separate **implementation complete / code complete** from **operationally validated**: if the last slice adds runbooks, dogfood smokes, or operator surfaces, report the code ladder as complete but keep a live operator run through the documented flow as the remaining gap until a human actually exercises it on a real self-hosted or EC2-like instance.

## Pitfalls

- Do not conclude an epic is mostly inactive just because tracker shells remain Scheduled.
- Do not hand prod/deploy follow-on work to generic workers by reflex.
- Do not promote stale dependency wiring without leaving a reconciliation comment.
- Do not ask the user broad planning questions when concrete operator decisions are the only blocker; give a short checklist instead.
- When the finish-line card is a merged review handoff, verify merge state first and treat `gh pr merge --delete-branch` failures caused by a checked-out worktree as local cleanup only. Reconcile the card to Done once the PR is merged, then promote any newly unblocked children.
- See `references/merged-review-handoff-local-cleanup.md` for a concrete merge + local-cleanup recovery pattern.

## Tracker-shell closure cleanup

When a user explicitly says to close an epic and handle any remaining gaps as follow-up tickets:

1. Close the delivered epic tracker, even if the remaining gap is only operational validation or polish.
2. Close sibling phase/lane tracker shells that now exist only as historical signage.
3. Leave concrete executable follow-on cards open when they still represent real work.
4. In your summary/comment, separate **tracker cleanup** from **remaining executable work** so the board does not imply the whole area is finished when only the shell cards were retired.
5. If a board tool refuses to complete a Scheduled tracker shell directly, first move it back to a completable state (for example via unblock), then complete it with a cleanup summary.

## Design-lock refill pattern

When JP says the board is empty/thin after a design-lock or planning card completed, mine the accepted doc for explicit implementation slices rather than inventing generic placeholders. Put independent base-contract/skeleton slices in Ready, but park dependent UI/projection slices in Todo with dependency comments or parent edges so workers do not collide.

For example, after a media-grid/color-label visual lock, good immediate Ready cards are the color-label metadata contract and media-grid viewer skeleton; inspector/tree label rendering should wait behind the metadata contract. Capture the source doc path, worker-neutral branch, repo-root worktree anchor, and assignee=null on every new Ready card.

## Plan-revision pauses

When JP pauses a feature lane because the design/implementation plan is being revised, treat the pause as authoritative over Ready/PR momentum:

1. Block active/running implementation cards with a product-plan pause reason, not a code-failure reason.
2. Move unstarted stale implementation cards out of Ready into Scheduled/Todo until amended.
3. Comment on any open related PR that the plan is paused and should not merge until revised or explicitly approved.
4. After the revised addendum lands, amend existing cards in place where possible, review pre-existing PRs against the new addendum, and leave only dependency-safe non-overlapping cards in Ready.
5. Keep dependent UI/projection cards parked until the revised metadata/API contract they consume is merged.

Detailed reference for Kanban board operations: `kanban-orchestrator-operations/references/feature-plan-revision-board-coordination.md`.

## References

- `references/merged-review-handoff-local-cleanup.md` — merge/review closure when local worktree cleanup fails after GitHub merge.
- `references/managed-feature-finish-line-reconciliation.md` — trace a managed feature across UI mutation, provider delivery, recipient acceptance, destination projection, revocation, and deployment; build a claimable dependency ladder and repair stale parent gating.

## Outputs to leave behind

- a tracker/finish-line reconciliation comment on the relevant card
- only the truly executable finish-line cards in Ready
- dependency-gated reserve in Todo when follow-on slices need an upstream contract first
- a short operator checklist covering missing IAM, DNS, secrets, host choice, and deploy path
