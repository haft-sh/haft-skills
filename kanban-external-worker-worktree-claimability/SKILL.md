---
name: kanban-external-worker-worktree-claimability
description: "Create, validate, and reconcile external-worker worktree Kanban cards so Ready means truly claimable."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [kanban, worktree, external-workers, board-hygiene, review-sweep]
---

# Kanban External-Worker Worktree Claimability

## When to use

Use this when you are creating, backfilling, validating, or reconciling Kanban cards for **external shell workers** that operate in git worktrees.

Typical triggers:
- creating a new Ready worktree card for an external worker
- repairing a Ready card that workers refused to claim
- validating whether a card is actually claimable
- sweeping Review after workers used a fallback handoff path
- hardening board workflow so claimability does not depend on agent memory

## Core rule

A card in **Ready** is only real runway for an external worktree worker if the card is already mechanically claimable.

Do not rely on memory or ad hoc board edits for this. Prefer a helper that fails closed.

## Claimability invariants

For external-worker worktree cards, verify the board policy for the specific repo/board before creation. The recurring invariants are:

1. `assignee = null` until the worker claims the card
2. `status = ready` only when the rest of the metadata is complete
3. `workspace_kind = worktree`
4. `workspace_path` must be the repo-root anchor required by that board's AGENTS instructions
5. `branch_name` must be present before the card enters Ready
6. branch naming must follow the board/repo-specific convention

If any of these are missing, the card is an orchestrator defect, not a worker failure.

## Failure mode: workspace_path names the wrong repo or is outside worker reach

A Ready worktree card can sit unclaimed for weeks even when all six invariants look right, because `workspace_path` points at the **wrong repository** or a directory outside the external workers' filesystem allowlist. The card looks claimable; workers leave comments like "the offending source is outside allowed roots" and move on, and the card ages in Ready while the underlying bug keeps firing.

Detection and repair:

1. Read the card's stale comments for the worker refusal reason (e.g., "not in current origin/main", "outside allowed roots"). Do not treat that stale comment as the current gate — verify live state next.
2. Locate the code that actually needs changing. If it lives in a profile-scoped checkout (e.g., `~/.hermes/profiles/<profile>/plugins/<name>`), find or refresh a Sites checkout of the same repo — profile dirs are typically outside worker roots.
3. Verify the external-worker filesystem allowlist (DevSpace: `~/.devspace/config.json` → `allowedRoots`; this host: `<dev-host-home>/Sites`). The workspace anchor must sit under an allowed root.
4. Confirm the Sites checkout is clean and contains the live runtime head (`git merge-base --is-ancestor <live-head> <checkout-ref>`); fast-forward it if stale so the worker branches from current code.
5. Repoint the card: update `workspace_path` (direct DB edit is acceptable when no CLI affordance exists — board DBs live at `~/.hermes/kanban/boards/<slug>/kanban.db`), bump priority, and post a reconciliation comment naming the old anchor, why it was wrong, the new anchor, and verification evidence.
6. Re-read the card to confirm the full Ready shape, and subscribe the human's home channel (`hermes kanban notify-subscribe <task_id> --platform telegram --chat-id <home>`) so the eventual handoff is visible.

## Haft-specific rule learned here

For **Haft** Ready external-worker worktree cards:

- use the helper script instead of ad hoc creation:
  - `<shared-scripts-root>/haft_ready_worktree_card.py`
- required Ready shape:
  - `assignee = null`
  - `status = ready`
  - `workspace_kind = worktree`
  - `workspace_path = <haft-repo-root>`
  - non-empty `branch_name`
- Haft `branch_name` should be a **bare worker-neutral slug**
  - good: `epic-20-implementation-plan`
  - good: `resend-transactional-email-integration`
  - bad: `jplew/epic-20-implementation-plan`

## Haft helper commands

### Create a claimable Ready card
```bash
python3 <shared-scripts-root>/haft_ready_worktree_card.py create \
  --title "Your title" \
  --body-file /tmp/body.md \
  --priority 95 \
  --branch-name your-short-slug
```

### Dry-run first
```bash
python3 <shared-scripts-root>/haft_ready_worktree_card.py create \
  --title "Your title" \
  --body "Test body" \
  --branch-name your-short-slug \
  --dry-run
```

### Validate an existing card
```bash
python3 <shared-scripts-root>/haft_ready_worktree_card.py validate <task_id>
```

## Cross-repository cards on a shared board

A board may coordinate work whose implementation repository is not the board's primary product repository. Do not force such a card through a repo-specific Ready helper: a Haft-only helper must reject a Hermes Agent workspace rather than silently storing the wrong repo anchor.

For an upstream Hermes Agent task filed on the Haft board:

1. Keep the implementation boundary explicit in the body: the target is `NousResearch/hermes-agent`, not Haft, private skills repositories, or Athabasca.
2. Identify the live installation and the real development checkout from install/source metadata. Never edit the live runtime checkout.
3. Store the actual Hermes development checkout as the workspace path (under the worker filesystem allowlist), and require a fresh worktree from the upstream default branch before implementation.
4. If the board/helper cannot represent an unassigned Ready card with that foreign workspace and branch metadata, use a non-claiming `blocked` or dependency-gated coordination card rather than assigning/claiming work or mislabeling it as Haft work.
5. Record why the repo-specific helper refused, the exact workspace path, upstream remote, live version/commit, and the worker's required base-refresh procedure.

A cross-repository coordination card is not Ready capacity until its worker identity, branch metadata, workspace shape, and repository boundary are all mechanically valid.

## Dependency-gated future queue planning

When a user wants a roadmap represented now without turning blocked work into misleading Ready capacity, create the later slices in **Todo** immediately.

For every future external-worker worktree card:

1. Give it a complete worker-ready body: objective, scope, acceptance criteria, boundaries, verification, and PR handoff requirements.
2. Seed `workspace_kind=worktree`, the board-required repo-root workspace anchor, a unique worker-neutral `branch_name`, and `assignee=null` even while it is Todo.
3. Add real parent→child dependency edges for every prerequisite; dependency prose alone is insufficient.
4. Keep it in `todo` until all parent cards are Done. Only then promote it after a live recheck confirms the Ready invariants.
5. Re-read every new card and its links after mutation. Report actual Ready capacity separately from dependency-gated Todo inventory.

### Helper-limited intake: preserve truthful live status

Some repo-specific claimability helpers intentionally create **Ready** cards only. That helper is appropriate for immediately claimable work, but it must not cause a dependency-gated roadmap card to remain or be reported as Ready.

When pre-seeding a future card through a helper-limited path:

1. Create only genuinely independent cards as Ready.
2. Put later cards into `todo` with actual parent→child links before reporting the intake complete; preserve `assignee=null`, worktree anchor, and branch metadata.
3. Add an explicit reconciliation comment when the creation audit record mentions Ready but the live task status is Todo. The live `status` is authoritative.
4. Re-read every card and dependency link after mutation; run the repo claimability validator only for cards whose live status is Ready.
5. At promotion time, validate the newly Ready card again rather than assuming its pre-seeded metadata survived unchanged.

This keeps future work discoverable and mechanically prepared without asking workers to claim branches that cannot yet be safely based or merged. Never pad Ready with dependency-gated cards merely to make the roadmap look stocked.

## Review sweep procedure

When a worker says a PR is ready or merged, do not clear Review from self-report alone.

1. Read the card comments/events for PR number and handoff evidence.
2. Verify the PR's live state on GitHub or the canonical git remote.
3. Only move Review -> Done after confirmed merge.
4. Leave an explicit reconciliation comment or event with the PR URL and merge timestamp.

## Fallback when normal board completion fails

If the usual board-completion path fails during a review sweep but the live board row still shows `review`, use the repo's documented recovery path instead of looping blindly.

Safe fallback pattern:
1. Re-read the live card and confirm it is still in `review`.
2. Verify the corresponding PR is truly merged.
3. Apply the repo-approved DB fallback carefully:
   - set `status = done`
   - set `completed_at`
   - record a concise result summary
   - clear stale claim fields if appropriate for the board's schema
   - add a comment naming PR, URL, merge time, and why fallback was used
   - add a status event indicating the reconciliation source
4. Re-read the board and confirm Review is actually clean.

## Pitfalls

- **Do not blame workers** for refusing a Ready worktree card missing `branch_name`.
- **Do not count broken Ready cards** toward Ready-buffer health.
- **Do not assume a claimed card should still satisfy Ready invariants.** Once claimed, the worker's worktree path and assignment should change.
- **Do not move review cards to done from comment text alone.** Verify merge state first.
- **Do not keep retrying the same board-completion tool call** after repeated terminal/id errors. Diagnose, then switch to the documented fallback.

## Outcome standard

A good orchestration result here means:
- workers only see truly claimable Ready cards
- branch metadata and null-assignment policy are enforced mechanically
- review sweeps are evidence-based
- fallback reconciliation leaves clear durable provenance for the next operator
