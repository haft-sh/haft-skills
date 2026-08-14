---
name: pr-review-reconciliation
description: Reconcile review-ready PRs with board cards, rescue follow-ups, and latest-head CI truth.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, kanban, pr-review, reconciliation, ci, merge]
---

# PR Review Reconciliation

Use this skill when a PR review sweep needs to reconcile GitHub state with Kanban state, especially when:

- a review PR has a temporary failure that later becomes green on a newer head SHA
- a rescue/fix card was created to isolate the blocker
- the source PR merges and the rescue card should be retired as superseded
- a merged review card may unblock children that must be promoted

## Steps

1. Read the live board card and the PR metadata together.
2. Check the **current** PR head SHA and current check state; do not rely on the first failing run if a new commit landed.
3. If the latest head is green and the PR merges cleanly, comment the source card with the merge evidence and move it to Done.
4. If a rescue card exists for the same blocker, comment it as superseded by the source PR fix and move it to Done as well.
5. If the review-handoff helper throws the known nested-transaction SQLite error after a successful dry-run, preserve the PR URL and verification evidence and use the documented board-state fallback to `Review` rather than retrying the helper blindly.
6. After any Done transition, inspect children and promote Todo children whose parents are all Done.
7. If a promoted child is a Haft worktree card, immediately validate claimability (`assignee=null`, repo-root `workspace_path`, `workspace_kind=worktree`, non-empty worker-neutral `branch_name`) before counting it as runway.
8. Keep the board truthful: a superseded rescue card should not stay Ready, Running, or Review.
9. When the board DB schema is unclear, use the direct `task_links` parent/child lookup (`parent_id`, `child_id`) rather than assuming a richer edge table.
10. When `gh pr checks` shows a mixed pass/pending summary, treat it as a cue to inspect the underlying workflow run with `gh run view <run_id> --json status,conclusion,jobs` before reporting the blocker. See `references/gh-pr-checks-pending-aggregate-vs-run-view.md`.
11. When a review PR is blocked by stale branch drift rather than a defect in its changed files, file a separate, explicitly scoped rescue card only after checking for an existing PR-linked card. The rescue body should name the source review card, current head SHA, merged prerequisite commit/PR, exact required repair, verification commands, and a no-merge/no-deploy boundary. For Haft external-worker work, create it with `haft_ready_worktree_card.py` (unassigned, repo-root worktree, worker-neutral branch) and immediately validate the resulting card; link the rescue ticket back to the source review card.
12. Treat a historical red check as unresolved until the source branch has a fresh head and a fresh required CI rollup. A successful disposable rebase or test run is evidence for scoping the rescue, not evidence that the GitHub PR is merge-ready.
13. When reviewing workflow-driven PRs, validate implementation against exact GitHub REST response envelopes and event semantics, not only fixture-shaped payloads. Workflow-run responses expose `jobs_url`; job counts and records come from a separate envelope `{total_count, jobs:[...]}`. Parsers should tolerate missing enrichment fields, default safely, then let enrichment fill them. Include cancelled runs whenever cancelled jobs are actionable.
14. Verify workflow trigger filters against the `name:` values declared in referenced workflow files. Filenames and slugs such as `e2e` or `visual-evidence` are not equivalent to workflow names and can silently suppress notifications.
15. If a remote worker reports PR-ready after a transport timeout, independently verify pane state, branch/commit, changed files, PR metadata, inline feedback, and fresh checks before moving the card to Review. A prompt timeout is transport evidence only—not failure or completion.
16. If the Herdr server or pane disappears during a wait, do not redispatch or abandon the task immediately. Verify the remote worktree directly over bounded SSH (`git status`, diff, branch, and recent log), run targeted tests/typecheck/build there, then commit and push only after those checks pass. Treat the worktree as the durable handoff and the Herdr control plane as recoverable transport.
17. When a GitHub notification email (rebase report, CI alert, review comment) triggers reconciliation, map the PR number to its board card via `task_comments` in the board DB — title search alone usually misses it. Then, if the only remaining gate is pending required checks, arm a bounded background settle-watch instead of polling turn by turn. See `references/pr-to-card-mapping-and-ci-settle-watch.md`.

See `references/github-workflow-payload-normalization.md` for the reusable response-shape and trigger-filter checklist.

## Pitfalls

- A prior failed CI run is historical once a newer head SHA passes.
- Do not keep both the source review card and the rescue card active after the source PR has been fixed and merged.
- If the rescue card is only a temporary implementation slice, retire it explicitly instead of leaving it stranded.
- `gh pr list --state open` is not a queue-health signal by itself; it can be empty while the board still has Running, Ready, or Todo work that must be reconciled from live board state.
- A mixed `gh pr checks` summary with one check passing and one pending is not enough to diagnose the hold. Drill into the workflow run/job view for the pending check before deciding whether the PR is truly blocked.
- If a browser diagnostics artifact is absent, do not loop `gh run download`. Fetch the raw job log endpoint, save it to a file, check the file type first, and quote the first concrete failing assertion from the raw log. Mention runner shutdown/cancellation separately if that is the terminal state.
- A GitHub notification email is a trigger, never evidence: verify head SHA, review decision, mergeability, and check state live before acting or reporting. `mergeStateStatus: BLOCKED` with `mergeable: MERGEABLE` and `reviewDecision: APPROVED` usually just means required checks are still pending — confirm before escalating.

See `references/review-rescue-pr-reconciliation-2026-07-15.md` for a concrete example.
See `references/review-handoff-helper-nested-transaction-fallback.md` for the nested-transaction fallback shape when the review handoff helper dry-run succeeds but the write transition fails.
See `references/review-card-child-promotion-task-links.md` for the child-promotion/task_links lookup pattern and the board-vs-GitHub reconciliation note.
See `references/browser-gate-absent-artifact-raw-log-fallback-2026-08-06.md` for the browser-gate absent-artifact raw-log fallback pattern.
See `references/pr-to-card-mapping-and-ci-settle-watch.md` for the PR→card comment-table mapping query and the bounded background CI settle-watch loop.
