---
name: haft-pr-reconciliation
description: Use when reconciling Haft PRs against the live Haft Kanban board, merged review handoffs, claimable Ready worktree cards, and current `master`-based operational policy.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, kanban, haft, orchestration, pull-requests]
    related_skills: [github-workflows, software-development-lifecycle]
---

# Haft PR Reconciliation

## Overview

Use this when sweeping Haft PRs and the Haft Kanban board together.

This skill is for the **current Haft operating model** on this host:
- repo: `<github-org>/haft`
- canonical checkout: `<repo-root>`
- branch of record: `master`
- board of record: `haft`
- external-worker runway depends on **claimable Ready worktree cards**, not just raw status labels

The goal is not to produce a pretty report. The goal is to leave GitHub and the board in a state that a worker can trust.

## When to Use

Use for:
- PR sweeps on `<github-org>/haft`
- review→done reconciliation after merged PRs
- queue stewardship for Haft external-worker worktree cards
- claimability repair after auto-promotion or stale metadata

Do not use for:
- implementing product changes yourself
- speculative roadmap planning unrelated to the live board
- editing canonical checkout files directly

## Current Ground Truth

Before acting, assume these are the defaults unless the live repo proves otherwise:

- Use Kanban board slug **`haft`**, not anything historical.
- Use canonical repo `<repo-root>` only as an operational anchor.
- Do development in worktrees under `<repo-root>/.worktrees/`.
- Merge target is **`master`**.
- Ready external-worker cards are only real if they validate under the Haft helper.

## Reconciliation Loop

1. **Read live board state first.**
   - Inspect `review`, `running`, `ready`, `todo`, and when relevant `blocked`.
   - Do not infer board state from comments or prior reports.

2. **Clear stale Review cards before anything else.**
   For each `review` card:
   - map it to its PR
   - verify merge state on GitHub
   - if merged, move the card to `done` immediately
   - then re-read the board because children may auto-promote

3. **Treat every newly promoted Ready worktree card as suspect.**
   Auto-promotion is not proof of claimability.

4. **Validate every Haft Ready worktree card before reporting runway.**
   Required shape:
   - `assignee = null`
   - `workspace_kind = worktree`
   - `workspace_path = <repo-root>`
   - non-empty worker-neutral `branch_name`
   - `python3 <scripts-dir>/haft_ready_worktree_card.py validate <task_id>` returns `ok: true`

5. **Repair fake-ready cards immediately.**
   Common broken shape after parent completion:
   - `status=ready`
   - `assignee='worker'`
   - `branch_name=null`

   Fix the task row, add a reconciliation comment, and re-run helper validation.

6. **Do not leave tracker shells in Ready.**
   If a broad Epic tracker auto-promotes while a real acceptance slice is still blocked/running, add the missing dependency edge and move the tracker back out of Ready.

7. **If Ready is empty after honest reconciliation, seed only genuine independent work.**
   Do not promote blocked children just to pad the queue.

## GitHub / Merge Discipline

### Merge only when all are true
- PR maps cleanly to one real Haft card
- diff matches the card scope
- required checks are green or you have an explicit verified reason a failing check is unrelated
- no unresolved conflict state
- no elevated-risk runtime/auth/credential surprise in the diff

### Elevated-risk surfaces for Haft
Do not merge casually when the diff touches:
- auth/session/credential handling
- public route exposure or route-policy classification
- import path containment or upload trust rules
- deploy/runtime selection
- filesystem serving / artifact preview resolution
- central remote-target discovery / grant exchange seams

## Canonical Checkout Rule

`<repo-root>` must stay:
- clean
- on `master`
- fast-forwarded to `origin/master`

If it is dirty:
- do not develop there
- do not normalize the dirt as acceptable
- preserve any accidental edits in a worktree/PR first
- then run canonical sync/check

## Practical Commands

### PR state
```bash
gh pr list --repo <github-org>/haft --state open
gh pr view <n> --repo <github-org>/haft --json state,mergedAt,url,headRefName,headRefOid
```

### Canonical safety
```bash
git -C <repo-root> status --short --branch
cd <repo-root> && bun run canonical:check
cd <repo-root> && bun run canonical:sync
```

### Ready-card validation
```bash
python3 <scripts-dir>/haft_ready_worktree_card.py validate <task_id>
```

## Common Pitfalls

1. **Treating merged PRs as reconciled board state**
   - A merged PR with a stale `review` card is unfinished orchestration.

2. **Counting fake-ready cards as runway**
   - Status alone is insufficient; validate the worktree card shape.

3. **Leaving Epic trackers in Ready**
   - Trackers are not worker runway.

4. **Working in canonical**
   - If repo changes are needed, use a worktree and PR.

5. **Forgetting `master`**
   - Haft uses `master` as the merge target on this host.

## Verification Checklist

- [ ] Board slug used was `haft`
- [ ] Review column checked against GitHub merge state
- [ ] Merged review cards moved to `done`
- [ ] Newly promoted Ready cards validated with the Haft helper
- [ ] Any fake-ready cards repaired before reporting runway
- [ ] No tracker shell left in Ready by accident
- [ ] Canonical checkout left clean on `master`
- [ ] Final report grounded in a fresh post-reconciliation board read
