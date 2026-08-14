---
name: pr-handoff-reconciliation
description: Reconcile merged or closed-unmerged GitHub PRs with Kanban review cards and local worktree cleanup when branch deletion, shell quoting, or board transitions get in the way.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, kanban, pr-review, worktree, cleanup, orchestration]
    related_skills: [github-pr-workflow, kanban-orchestrator-operations, haft-orchestrator-workflows]
---

# PR Handoff Reconciliation

Use this skill when a PR has merged but the final handoff is blocked by local cleanup, board transition friction, or shell quoting issues while posting the handoff evidence. Also use when a PR is **closed unmerged** and its Kanban review card must be reconciled to a terminal state — see the closed-unmerged section below.

## Trigger conditions
- `gh pr merge --delete-branch` merged the PR but failed to delete the head branch because the branch is still checked out in a worktree.
- A Kanban handoff comment needs to be posted from a shell command that includes backticks or other shell-sensitive punctuation.
- A Review card is still in `review` after the PR is already merged.
- A GitHub notification says "Closed #N" (no merge) and the corresponding review card needs a terminal disposition.
- `hermes kanban complete` returns `unknown id or terminal state` on a merged review card while the live board still shows `review`.
- Local cleanup and board reconciliation need to be separated so merge success is not mistaken for branch deletion success.

## Standard sequence
1. Verify the PR merge state directly:
   ```bash
   gh pr view <n> --json state,mergedAt,url,mergeCommit,baseRefName,headRefName
   ```
2. If the PR is merged, treat the merge as authoritative even if `--delete-branch` failed.
3. Post the board handoff comment with shell-safe quoting.
4. Move the Kanban card to `done`/`review` as appropriate.
5. Remove or relocate the worktree that still has the branch checked out.
6. Delete the local branch only after the worktree is gone.
7. Re-run canonical sync/check if the canonical checkout must be verified clean.

## Shell quoting rules
- Do **not** put raw backticks inside a double-quoted shell string.
- Prefer a single-quoted shell string for the whole comment body, or escape backticks explicitly.
- If the comment text needs code spans, consider a here-doc passed through a temp file instead of inlining it in the shell command.

## Pitfalls
- `gh pr merge --delete-branch` can fail for local worktree reasons while the PR is already merged on GitHub.
- A failed branch delete is a cleanup problem, not a merge failure.
- If a merge command races with another actor and reports the PR was already merged, verify with `gh pr view` and continue reconciliation instead of retrying the merge.
- `hermes-kanban-review-handoff` can fail during cron reconciliation with `sqlite3.OperationalError: cannot start a transaction within a transaction`. Treat that as a helper transaction issue, not proof that the PR or board state is wrong. Verify merge state directly, then use the documented `kanban_db` recovery path to persist the review→done transition and immediately re-read the card.
- If `hermes kanban complete` refuses a merged review card with `unknown id or terminal state`, write provenance as a separate comment, apply the fresh-connection `review -> done` DB fallback, then run cleanup helpers outside the write transaction and re-snapshot the board before child checks.
- After a direct fallback, trust the fresh `show` read before the inventory projection: `list --json` can lag one refresh cycle even when `show` already says `done`. Promote children only from the fresh post-fallback snapshot, and re-verify any Ready child is truly claimable (`workspace_kind=worktree`, repo-root workspace path, worker-neutral branch, `assignee=null`) before counting the queue as healthy.
- If a child is already `ready`, do not call `promote` again; `hermes kanban promote` only applies to `todo` or `blocked` tasks. Re-read the live row and treat the ready state as success.

## Closed-unmerged PR reconciliation

A GitHub "Closed #N" notification means the PR was closed **without merging**. Do not run the merged-PR sequence — the card disposition is different:

1. Verify state and close actor:
   ```bash
   gh pr view <n> --json number,state,mergedAt,closedAt,headRefName,url
   ```
   `state=CLOSED` + `mergedAt=null` = closed unmerged. There is **no `merged` field** on `gh pr view` — use `mergedAt`/`mergedBy`.
   If you need the close actor (product owner vs bot vs author):
   ```bash
   gh api graphql -f query='{ repository(owner:"<o>", name:"<r>") { pullRequest(number:<n>) { state closed timelineItems(last:10, itemTypes:[CLOSED_EVENT, MERGED_EVENT]) { nodes { __typename ... on ClosedEvent { actor { login } createdAt } ... on MergedEvent { actor { login } } } } } } }'
   ```
   The REST timeline endpoint (`/repos/<o>/<r>/issues/<n>/timeline` or `.../pulls/<n>/timeline`) can 404 after a repo rename; GraphQL is the reliable fallback.
2. Read the card's comment thread for context (why it was in review, what was blocking it).
3. Post a reconciliation comment recording: close actor, `ClosedEvent` timestamp, `mergedAt=null`, head SHA that never merged, and the blocker context (e.g. runner capacity, reviewer abstention).
4. Move the card to `done` with disposition metadata (`pr_state: CLOSED_UNMERGED`, `disposition: closed-by-product-owner`). Treat a product-owner close as a scope decision, not a CI outcome — do **not** refile automatically; note that re-filing requires explicit owner direction.
5. Preserve the branch and worktree pending explicit direction; do not delete them as part of routine cleanup.
6. If the close came from an automated sender (e.g. GitHub notifications email), do not reply to the email thread — reconcile on the board only.

See `references/closed-unmerged-pr-reconciliation.md` for the full worked sequence.

## Verification
- `gh pr view <n> --json state,mergedAt,url,mergeCommit`
- `git worktree list`
- `git status --short --branch`
- `bun run canonical:check` when the canonical checkout is involved

## Support files
- `references/pr-handoff-shell-quoting-and-worktree-branch-cleanup.md` — concise reproduction and cleanup notes for the shell-quoting and worktree-checked-out branch deletion pitfall.
- `references/closed-unmerged-pr-reconciliation.md` — closed-unmerged PR disposition: verify close actor via GraphQL, reconcile card to done with `CLOSED_UNMERGED` metadata, preserve branch/worktree, never refile automatically.
- `references/review-handoff-transaction-recovery.md` — helper transaction failure recovery when review handoff needs a direct DB transition.
- `references/review-handoff-direct-db-recovery.md` — exact merged-review `unknown id or terminal state` recovery sequence, including provenance-first comment, fresh-connection fallback, and post-commit cleanup order.
- `references/merged-review-helper-refusal-show-first-postmerge.md` — compact session note for the same helper-refusal shape, including the show-first post-fallback verifier and the live GitHub re-read correction pitfall.
