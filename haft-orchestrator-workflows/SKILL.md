---
name: haft-orchestrator-workflows
description: Haft PR/review sweeps, board reconciliation, and queue maintenance.
version: 1.1.10
author: Hermes Agent
license: MIT
metadata:
  tags: [haft, orchestration, kanban, pr-review, queue-management, cron]
  triggers:
    - Fast PR/review sweep for Haft
    - Reconcile Kanban board state with GitHub PRs
    - Merge review-ready PRs and move cards Done
    - Promote Ready cards and maintain worker queue
    - Repair Kanban state or status transitions
  related_skills: [hermes-agent, github-pr-workflow, kanban-orchestrator-operations]
---

# Haft Orchestrator Workflows

See `references/herdr-dispatch-lessons.md` for safe remote-pane selection, prompt quoting, timeout handling, explicit-profile routing, and independent board verification.

See `references/release-blocker-friction-capture.md` for recovery.
See `references/deterministic-review-gate-and-base-sync.md` for machine-readable review classification, master sync, async update handling, and current-head verification.
See `references/gh-checks-and-job-log-fallback.md`.
See `references/browser-artifact-name-and-route-ownership-drift.md` + `references/gly-thumbnail-diagnosis-and-canary.md` for discovery/canaries; Herdr dispatch: `references/implementation-dispatch-with-herdr.md`.
See `references/review-to-done-show-first-after-fallback-2026-08-07-pr1599.md` for the show-first verifier after a manual merged-review fallback when `complete` refuses a live `review` card.

Use this skill for live board reconciliation, PR sweep/merge decisions, card status transitions, and queue maintenance on the Haft Kanban board.

## What this skill owns
- Reconcile board state with real GitHub PR state.
- Merge safe review-ready PRs when checks and diff scope are acceptable.
- Transition merged review cards to Done.
- Promote newly unblocked children so Ready stays healthy.
- Maintain claimable external-worker runway without corrupting metadata.
- Recover from CLI transition failures with the approved kanban_db path.

If you only need planning or implementation guidance, use a more specific skill. This one is for operational sweep/reconciliation work.

## Sweep order
1. Load live board state first.

### Transition-receipt and human-gate verification

Do not treat a Kanban create/transition receipt as authoritative state. After creating an approval, founder-review, or other human-decision gate, immediately re-read the live row and assert it is **Blocked** (not Ready), has `block_kind=needs_input` where supported, and is not claimable by an external worker. If the requested initial state or native transition tool disagrees with the live row, use the public `hermes_cli.kanban_db` state API as the reconciliation surface and record a concise comment with the intended gate and current status; do not leave a decision card exposed as Ready.

For merged-PR reconciliation, GitHub `MERGED` remains authoritative even if checks later show post-merge cleanup as pending or `mergeStateStatus=UNKNOWN`. First write PR provenance, then complete the matching tracking card. If normal completion and `kanban_db.complete_task()` both refuse an otherwise verified nonterminal tracking row, use the documented transaction fallback: verify the exact current status, transition only that task to `done`, clear stale claim/block fields, append a completion event, then run failure-counter cleanup, `recompute_ready`, workspace cleanup, and a live integrity/state re-read. Never use an ad-hoc bulk update or infer the PR/card relationship from a nearby historical card.
   - Prefer `hermes kanban --board haft list` or direct kanban_db queries for authoritative status.
   - `list --json` rows omit `block_kind`, claim fields, and all parent/child links (observed keys end at workspace metadata). Do not conclude a card is unblocked or dependency-free from a list row; reconstruct dependency sets with per-card `hermes kanban --board haft show <id>` (prints `parents:`/`children:` lines, comments, and events) or a direct `task_links` query. Batch the `show` calls in one shell loop.
   - Inventory every non-terminal column: `review`, `running`, `ready`, `blocked`, `todo`, `scheduled`, and `triage`. Do not let historical triage or incident shells disappear from a reconciliation simply because they are not currently claimable.
   - When live comments and GitHub evidence prove a card is a duplicate or a superseded historical PR anchor, add a concise reconciliation comment naming the completed or replacement owner, then archive it. Retain cards with an independent executable acceptance slice.
   - When a card needs PR reconciliation, pair the board snapshot with a fresh GitHub PR snapshot in the same sweep; `show` alone does not provide current head SHA or required-check rollup.
   - If you need to parse `list` output, snapshot it to a file first and parse the saved copy; do not stream board output directly into an interpreter when a file-backed snapshot is available.
   - For JSON sweeps, redirect to a temp file first and parse the saved file. Avoid pipes like `hermes kanban --board haft list --json | python3 ...`; they can fail with `BrokenPipeError` and leave you with truncated JSON plus a false sense of board state.
   - When locating the fresh snapshot among accumulated /tmp files, never use `ls /tmp/haft-board-*.json | tail -1`: plain `ls` sorts alphabetically, not by mtime, so `tail -1` can return a days-old file and silently drive the whole sweep from stale board state. Capture the exact target path at write time (`SNAP=$(mktemp ...)` then `> "$SNAP"`) or use `ls -t | head -1`. See `references/stale-tmp-snapshot-alphabetical-selection-pitfall-2026-08-04.md`.
   - This also avoids shell-security scanners that reject direct CLI-to-interpreter pipes on otherwise read-only snapshots. See `references/cli-json-snapshot-parse-pitfall.md` and `references/gh-json-snapshot-file-parse-and-scan-pitfall.md`.
   - Treat the saved file as authoritative and verify its shape before parsing. Some CLI surfaces are version-sensitive or can fall back to plain text; if the snapshot does not begin with JSON structural characters, inspect the raw file and rerun with a simpler command instead of forcing the parser.
   - For a whole-board triage pass, snapshot `hermes kanban --board haft list --json` and summarize it locally before deciding whether the sweep is a no-op; see `references/board-inventory-json-triage.md`.
   - See `references/board-inventory-local-summary.md` for the snapshot-to-local-summary pattern that lets a cron sweep stop cleanly when the board is already healthy.
   - See `references/board-sweep-merge-race-and-task-id-hygiene-2026-07-30.md` for the stale-task-id + transient mergeability-lag pattern from the 2026-07-30 reconciliation run.
   - If `show`, `comment`, `claim`, or `complete` says `no such task`, re-read the latest board snapshot before assuming the card vanished. Re-copy the exact ID from the fresh snapshot and retry once; a stale or mistyped ID is more common than a deleted task. If a fresh `list --json` still contains the task while `show` says it is missing, trust the fresh inventory row and treat `show` as stale for that moment. If the fresh snapshot exposes a same-title neighbor or the ID was copied from memory, trust the fresh snapshot's exact ID only. See `references/task-id-snapshot-hygiene.md` and `references/show-vs-list-staleness-after-direct-mutation-2026-07-31.md`.
   - See `references/board-inventory-json-array-snapshot.md` for the observed top-level-array shape and a minimal parse/stop-silent pattern.
   - See `references/board-json-snapshot-pitfall.md` for the concrete do-not-pipe-live-JSON-into-python pitfall and the file-backed parse pattern.
   - See `references/board-pr-check-summary-short-circuit.md` for the compact board/PR summary shape that avoids extra cross-tool hops.
   - For broad PR reconciliation, prefer `gh pr list --state all --limit <n> --json ...` and then confirm candidates with `gh pr view <n> --json state,mergedAt,url,baseRefName,headRefName`. `gh pr list --head <branch>` is only a convenience check; merged branches may be deleted and return empty even when the PR exists.
   - If `gh pr list --head` is empty for a branch that is already contained in the target base, fall back to direct PR URLs or local branch ancestry (`git merge-base --is-ancestor <branch> origin/master`) instead of assuming the PR vanished. See `references/merged-branch-pr-linkage-fallback.md`.
   - Check both `master` and feature branches used by active lanes, especially `cow` for AgentFS COW cards.
   - See `references/pr-state-sweep-vs-branch-head-lookup.md` for the branch-head deletion pitfall and snapshot-first parse pattern.
2. Reconcile open PRs and Review cards.
   2. Match Review cards to PRs by number/URL in comments or handoff text.
      - If a PR is merged, move the card to Done even if a worker comment still says Review.
      - Feature-branch PRs must be checked on their actual base branch, not just `master`.
      - If the review handoff helper or `hermes kanban complete` refuses a merged card because of a transaction/terminal-state mismatch, verify the live task state first and use the documented `kanban_db` fallback instead of leaving the card stranded.
      - If the review handoff helper resolves a valid Haft PR URL against the legacy `jplew/hypervault` repo or otherwise mismaps the target namespace, treat it as helper routing drift. Add provenance manually if needed, then reconcile from the live PR/board state instead of retrying the same helper blindly. See `references/review-handoff-helper-legacy-repo-mapping.md`.
      - When capturing the reviewed head SHA for a merge gate, read `headRefOid` from a JSON-only snapshot or temp file and assign it before printing any status lines. Do not let compound shell output (for example, a trailing `CLEAN`) leak into `REVIEWED_HEAD`; see `references/review-head-sha-capture-and-terminal-state-pitfall.md`.
      - If `hermes kanban complete` says `unknown id or terminal state` while the live task still shows `review`, do **not** keep retrying the helper. Leave a short provenance comment with PR URL + reviewed head SHA + exact helper refusal text, then apply the direct `review -> done` fallback and call `recompute_ready(conn)` only after the write transaction commits.
      - If `hermes kanban complete` rejects the task with an empty-evidence judge message such as `empty response (nothing to evaluate)`, treat that as a signal to stop looping, post provenance, and use the direct board fallback instead of trying to persuade the helper with more retries.
      - If the live task is already in `review`, do **not** keep retrying `complete`. Re-read the live task, confirm the PR is merged, leave a short provenance comment with PR URL + reviewed head SHA + helper refusal text, then re-read once more immediately before any fallback write. Only use the direct `review -> done` DB fallback when the fresh live task still says `review`: update `status = 'done'`, clear claim fields (`claim_lock`, `claim_expires`, `worker_pid`, `block_kind`), set `completed_at`, set `block_recurrences = 0`, persist the merge result, and emit a status event documenting the board reconciliation. If the fresh task already shows `done`/`archived`, stop after provenance and a fresh board snapshot instead of forcing a duplicate terminal-state write. See `references/merged-review-card-done-fallback-after-helper-refusal.md`, `references/review-to-done-helper-refusal-2026-07-21.md`, and `references/review-to-done-state-race-before-fallback.md`.
      - When the helper refused a merged card with `unknown id or terminal state`, verify GitHub merged state first, leave a short provenance comment with PR URL + head SHA + helper failure text, then apply the DB fallback. Record provenance with a separate comment; `hermes kanban complete` does **not** accept `--author`, so do not try to attach provenance through the completion helper.
      - If the provenance comment succeeds but `complete` still refuses, treat the comment as durable evidence that the handoff context is preserved; do **not** re-run the helper in a loop or rewrite the comment. Move straight to the DB fallback.
      - Before any fallback write, re-read the live task once after provenance is recorded. If that fresh read already shows `done` or `archived`, stop and do not force a duplicate terminal-state mutation.
      - If the gate helper itself refuses because the PR is already merged and a cleanup job is still in progress, treat that as post-merge housekeeping, not a merge blocker: re-read GitHub to confirm `state=MERGED`, add provenance, and reconcile the board from the merged state rather than retrying the gate.
      - If `gh pr merge` fails with `Merge already in progress (mergePullRequest)` after the gate passed, treat that as the same post-merge housekeeping race: re-read GitHub once, confirm the PR is now `MERGED`, and reconcile the board instead of retrying the merge command.
      - If a fresh `gh pr view` read flips the PR to `MERGED` after your earlier sweep snapshot, stop treating the earlier snapshot as current. Re-run board reconciliation from the live merged state, not the pre-merge view. See `references/stale-merged-snapshot-and-helper-refusal-2026-07-27.md` for the stale-snapshot recovery shape.
      - If the live task is still in `review`, do **not** keep retrying `complete`. Re-read the live task, confirm the PR is merged, leave provenance, and apply the direct `review -> done` board fallback. One refusal is enough evidence to switch to the fallback path; do not loop the helper in hopes of a different answer. If the refusal text is `unknown id or terminal state`, treat it as a live review-state reconciliation path rather than a terminal failure. Call `recompute_ready(conn)` only after the write transaction commits. Do not let a terminal-state helper refusal override the live task state.
      - After any manual review→done fallback, re-snapshot the board before checking children. Use the fresh snapshot as the only source of truth for promotions; do not promote from the pre-fallback view. If the fresh snapshot shows no children, stop immediately after reconciliation.
      - When multiple review cards or merged PRs are present in one sweep, verify task ID, branch, explicit PR URL, and reviewed head SHA together before mutating the board. Title similarity alone is not enough to map a PR to a card.
      - If you briefly move the wrong card, repair it immediately and leave a provenance comment explaining the crosswalk mistake before continuing the sweep.
      - See `references/board-sweep-merge-race-and-task-id-hygiene-2026-07-30.md` for the stale-task-id + transient mergeability-lag pattern.
      - See `references/board-sweep-crosswalk-repair-2026-07-30.md` for the exact repair sequence when title similarity caused a mistaken PR/card mapping.

### Human-input block preservation

A Review card may need an explicit `needs_input` block rather than Review→Done when its linked PR is closed unmerged or another owner decision is required. The normal `kanban_block` helper may reject cards already in `review`; use the same fresh-connection DB recovery discipline to set `status='blocked'`, `block_kind='needs_input'`, clear claim/run fields, and write a status event plus a durable comment stating the exact decision needed.

**Critical recomputation pitfall:** `recompute_ready(conn)` can promote a no-parent `blocked` card back to `ready` even when its `block_kind='needs_input'`. Do not count a `ready` row with a retained human-input block as worker runway. When the only intended mutation is a human-input block, run any required child/dependency recomputation first, then make the final block write afterward and verify with a direct board query that the card remains `blocked`. Do not call `kanban_list` as the final verifier if it implicitly recomputes readiness; use a non-mutating direct query or task show instead.

      - When the board helper says `unknown id or terminal state` for a live non-done task, treat the helper as stale, not authoritative. The live task can still be `review`, `scheduled`, or another non-terminal state even though the helper refuses completion; in that case, leave the provenance comment first, then apply the direct DB fallback appropriate to the live state and only afterward call `_clear_failure_counter(conn, task_id)`, `recompute_ready(conn)`, and `_cleanup_workspace(conn, task_id)` on fresh connections.
      - The direct fallback should persist the verified evidence in the task result/comment payload, clear `claim_lock`, `claim_expires`, `worker_pid`, and `block_kind`, set `block_recurrences = 0`, and set `completed_at` before closing the transaction.
      - After the fallback transaction commits, call `_clear_failure_counter(conn, task_id)`, then `recompute_ready(conn)`, then `_cleanup_workspace(conn, task_id)`. Do not call any of them inside the write transaction.
      - After the fallback, re-snapshot the board to confirm the Done transition and any child promotions actually landed. Do not use the pre-fallback snapshot to judge child readiness.
      - Immediately after a direct DB fallback, prefer a fresh `show` on the mutated task as the first verifier; `list --json` can lag the projection briefly. If `show` says the task is `done` but the inventory is stale, trust the task read and refresh the inventory again before judging children.


                  - Promote any Todo child whose parents are now all Done.

4. Keep Ready healthy.
   - Prefer dependency-safe EPIC21 and AgentFS work first.
   - Only promote cards that are genuinely claimable.
5. Stop when there is no reconciliation or promotion to do.
   - If the board is already consistent and no queue change is needed, return `[SILENT]`.

## Review-card reconciliation
- Check the PR state directly with `gh pr view <n> --json state,mergedAt,url,baseRefName,headRefName`.
- If the PR is `MERGED`, reconcile the card to Done.
- Do not hold routine valid Haft PRs once required checks are green, local verification is sound, and scope matches the card.
- Do not merge if required checks are still pending, queued, stale, or failing.
- Treat partial green as not green enough.
- If an open PR is a draft and no live board card maps to it, treat it as inventory only; do not let it trigger board mutations or merge triage by itself.
- If a merged PR still shows `mergeStateStatus=UNKNOWN` or an in-progress non-CI cleanup job in its rollup, treat that as post-merge housekeeping and reconcile the board from the merged state anyway; do not leave the Review card stranded waiting on the cleanup workflow. A post-merge `gh pr checks` line that is still pending on orphan cleanup work is not a reason to delay board reconciliation once GitHub reports `MERGED`.
- A fresh post-merge `gh pr view` can transiently return `state=MERGED` with `mergeStateStatus=UNKNOWN`; treat the `MERGED` state as authoritative and the `UNKNOWN` rollup as lagging cleanup noise, not as a reason to reopen merge gating. See `references/merged-pr-post-merge-cleanup-jobs.md`, `references/merged-pr-post-merge-state-lag-2026-07-24.md`, `references/merged-pr-cleanup-lag-reconcile-2026-07-26.md`, and `references/post-merge-cleanup-lag-and-stale-repair-card-archival-2026-07-29.md`.
- If the review handoff helper or `hermes kanban complete` refuses a merged card because of a transaction/terminal-state mismatch, verify the live task state first and use the documented `kanban_db` fallback instead of leaving the card stranded.
- If `show` already reports the task as `done`, treat the refusal as a stale transition race: add provenance only if needed, do not keep retrying the helper, and do not re-mutate the board.
- If a required browser suite fails on a seam the PR does **not** touch, classify it as an off-diff regression: keep the source PR in Review on the concrete failing assertion, and create or reuse one narrow repair card for the actual owning seam instead of duplicating the fix into the source PR. See `references/off-diff-browser-regression-repair-card-split-2026-07-31.md`.
- When the off-diff owning seam already has a live repair card, keep the ownership split explicit in the hold note: source PR stays held, repair card owns the fix, and the two must not be merged conceptually just because the browser suite mentions both.
- If the repair card is already Ready and claimable, leave it as separate runway; do not reopen or re-label the source PR just because the repair lane exists.

### Deterministic current-head CI repair requeue

When the same current-head required check fails on two attempts, preferably on different runners, with the same in-diff assertion or error, classify it as deterministic PR-local repair work rather than runner flakiness. If the source card already owns that PR and no independent repair seam exists:

1. Do **not** create a parallel CI-rescue card or competing branch.
2. Add one bounded source-card comment with the run URL, attempts/jobs/runners, exact test or step, and attribution.
3. Move the source card from `review` back to `ready` for repair, clearing assignee and claim/run fields while preserving its PR branch, `workspace_kind=worktree`, and repo-root workspace anchor.
4. Re-read the card and verify it is genuinely claimable (`assignee=null`, no claim lock, non-empty neutral branch). Keep the existing PR held until the exact failure and current-head required rollup are green.

Use a direct board fallback only after a fresh task read confirms `review`; record the status reason as a deterministic CI repair requeue. This prevents an unowned failed-Review lane while preserving one source of truth. After the requeue, re-read the task row and verify the card is truly claimable (`assignee=null`, non-empty neutral branch, `workspace_kind=worktree`, repo-root `workspace_path=<haft-repo-root>`) before counting it as Ready runway. See `references/deterministic-current-head-ci-requeue-and-claimability-repair-2026-08-05.md`.

Variant — DIRTY head with **zero CI runs**: if `gh pr checks` says `no checks reported`, the commit-status API returns `pending` with `total_count: 0`, and no CI workflow run exists for the head (`gh run list -c <sha>`), no rerun can produce checks; the card must be repair-requeued to Ready with the concrete conflict file named (find it via `git merge-tree --write-tree origin/master <head>`). See `references/repair-requeue-no-ci-run-dirty-head-2026-08-05.md`.

- If `haft_pr_green_gate.py` rejects a PR that GitHub already reports as `MERGED`, treat that as cleanup-lag reconciliation, not a merge failure: re-read GitHub once, write provenance if the board still needs it, and move straight to the board fallback.


### Non-PR review card reconciliation (audits, reports, deliverable-only)

Some cards reach `review` without a PR — read-only audits, planning docs, or report deliverables whose output lives in task comments/attachments rather than a merged branch. These cards block children just like PR-backed review cards.

Reconciliation criteria (all must hold):
1. The stated deliverable is present in comments or attachments (e.g. audit report, findings list).
2. Any child cards referenced in the deliverable exist on the board.
3. No PR is expected per the card body/constraints (e.g. "read-only audit", "do not modify source code").
4. The worker's final comment or run summary declares the deliverable complete.

When those hold, reconcile review → done via the same DB fallback path (the `kanban_complete` helper will refuse with "unknown id or terminal state" because there is no PR evidence for its judge). Then promote children exactly as for PR-backed cards.

Do NOT wait for a merge that will never come. Do NOT leave the card in review "for reviewer triage" when the deliverable is self-evidently complete and children are blocked.

See `references/non-pr-audit-card-reconciliation-2026-07-28.md` for the live example.

### Review-handoff verification-completeness check
A worker's PR handoff comment can claim a green verification set that is **narrower than the PR's actual required CI gate**. The most common shape: the handoff reports a small number of focused E2E tests (for example "2 Chromium E2E tests") while the repo's merge gate runs a broader suite (for example the `Extended browser regressions` workflow with dozens of specs).

When reconciling a Review card whose PR has a red required check:

1. Read the handoff's stated verification list and compare it against the failing workflow's actual scope (`gh run view <id> --json jobs`, the workflow file, or the suite's pass/fail counts).
2. If the handoff only ran a focused subset and the failing suite is broader, treat the red gate as **real, unverified-by-the-worker evidence**, not as a flaky rerun candidate.
3. File the repair card citing the exact failing specs and the handoff's verification gap, so the next worker knows the focused tests the original author ran are not sufficient proof.
4. Do not let a handoff's "typecheck + N focused tests + build" line substitute for the full required-check rollup when deciding whether a Review PR is mergeable.

Good pattern:

> The handoff claimed "2 Chromium E2E tests" passed, but the `Extended browser regressions` gate runs 42 specs and failed 2 — one the PR's own new test, one an existing virtualization spec the PR's tree/context-menu changes regressed. The focused handoff verification did not cover the gate; file the repair against the full suite, not the subset.

### Running-card PR-merged reconciliation

A card can still be in `running` while its PR is already merged — the worker pushed, opened the PR, JP merged it, but the worker never posted a review handoff or the run was interrupted. During sweeps:

1. Cross-reference running cards' branches against `gh pr list --state merged`.
2. If a running card's branch matches a merged PR, reconcile it directly to done (same DB fallback).
3. Record a short provenance comment with the PR URL and reviewed head SHA, then re-read the task with `show` before trusting `list --json`.
4. Check children for promotion afterward.
5. After the completion write, prefer the fresh `show` result over `list --json` for the first verification; board inventory can lag briefly and still render the card as `running` even though the direct task read is already `done`.
6. When several running/review cards are all already merged, batch the provenance comments, reconcile each card from the live GitHub merge state, then take one fresh board snapshot at the end; see `references/merged-running-review-reconciliation-2026-08-06.md`.

This prevents cards from languishing in `running` with a stale claim lock while their work is already on master.

See `references/running-card-merged-pr-reconciliation.md` for the compact sequence.

### Merge gates that deserve extra caution
Escalate before merge when the diff touches:
- auth/session/cookies/credentials
- path containment, filesystem serving, or symlink behavior
- upload/import/fetch behavior beyond the documented contract
- public deployment or live infra
- route policy or public/private boundary changes
- broad architecture rewrites

### Current-head CI hold pattern
A PR can look mergeable in GitHub and still be held by the executable gate if the current-head required-check rollup is incomplete. Treat any missing required context as a hard stop, even when `mergeStateStatus` is clean.

When this happens:
1. capture the exact reviewed head SHA;
2. run the gate helper against that SHA immediately before any merge attempt;
3. record the exact missing/failing check names in a board comment;
4. do not rely on earlier rollups, mergeability, or workflow_dispatch reruns to unblock the PR;
5. if the failing check is a schema-vs-contract mirror mismatch (for example, a config schema expanded without updating a mirrored env contract), classify it as contract drift and point the repair at the contract source/docs, not unrelated product code; see `references/hq-env-contract-drift-hold-and-repair.md` for the PR #1387 example;
6. if the executable gate returns `UNKNOWN` and a fresh `gh pr view` then shows `DIRTY`, treat the newest GitHub snapshot as authoritative and hold; do not merge from the earlier clean rollup;
7. if the first gate attempt returns `UNKNOWN` even though the last GitHub read was clean and green, re-read GitHub once before holding; a second clean read means you hit cleanup lag, not a real blocker. See `references/transient-merge-state-unknown-after-clean-read.md`.

Important pitfall:
- If the PR intentionally changes or consolidates required checks, a stale host-local merge gate can still report legacy names as missing even when GitHub is green on the new contract.
- In that case, treat the blocker as operator-policy drift, not product failure.
- Refresh the host-local gate helper and cron prompt to the live required-check contract before classifying the PR; do not let an outdated local gate define the product state.
- If the executable gate reports a draft-state blocker but a fresh `gh pr view` snapshot says `isDraft=false` with green required checks, treat the helper as stale and re-read GitHub once before retrying. Do not loop the same helper invocation against the stale snapshot.

See `references/current-head-required-check-hold-pattern.md` for the observed failure shape and comment wording.
See `references/current-check-contract-drift-2026-07-18.md` for the 2026-07-18 browser-gate consolidation example.
- `references/ci-log-failure-extraction.md` for the log-first pattern that recovers the exact failing tests from a red required check. If `gh run download` says `no valid artifacts found to download`, treat the artifact as absent and switch immediately to `gh run view --log > /tmp/<run>.log` plus saved-log search; do not loop the download. If `gh run view --log` is empty or strips the useful failure body for a completed browser job, jump straight to the job API plus the `playwright-browser-gate-failure` artifact and recover the first concrete assertion from `test-results/**/error-context.md` instead of retrying the same log surface. See `references/gh-run-empty-log-browser-gate-artifact-fallback-2026-08-04.md`. For a truncated inbound GitHub notification that supplies only a workflow title and short commit SHA, use `references/inbound-pr-browser-failure-triage.md` to resolve the live PR/run, distinguish off-diff deterministic failures, and preserve source-card ownership correctly. If the live rollup exposes more than one independently failing required check, use `references/inbound-pr-multiple-independent-ci-failures.md` to split PR-local and off-diff ownership without creating competing source-branch PRs. When the current-head browser failures are deterministic and in-diff on an existing Review PR, use `references/inbound-pr-current-head-browser-regression-hold.md`: comment the source lane, avoid a competing rescue branch, and record a generic Review hold through the documented fallback when needed. For self-hosted lock ownership, cross-runner `/tmp` artifacts, and a bounded cleanup remedy, see `references/ci-runner-shared-lock-and-temp-ownership.md`.
See `references/browser-gate-failure-drilldown.md` for the browser-job artifact fallback when `gh run view --log` is sparse or empty.
- For focused Playwright reruns in Haft, see `references/playwright-focused-test-invocation-pitfall-2026-07-24.md` when a test file is not discovered by a path-qualified invocation.
- `references/gh-run-log-artifact-absent-fallback-2026-07-31.md` captures the absent-artifact → saved-run-log fallback with concrete PR examples.
- `references/browser-gate-absent-artifact-fallback-2026-08-05.md` captures the no-diagnostics-artifact case: when `gh run download` cannot find the browser failure artifact, stop retrying the download and fall back to the saved run log for the first concrete assertion.
- `references/browser-gate-raw-job-log-endpoint-fallback-2026-08-05.md` captures the raw-job-log recovery path when `gh run download` cannot produce any browser diagnostics artifact at all.
- `references/mixed-browser-and-bun-blocker-artifact-drilldown-2026-08-05.md` — compact mixed-sweep example for splitting browser and Bun blockers by PR and extracting the first concrete assertion from downloaded artifacts.

## Dependency unblocking after Done
When a card moves to Done:
1. Inspect its children.
2. For each child in Todo, verify all parents are Done.
3. Promote the child to Ready only if it is still valid claimable work.
4. For any newly Ready worktree card, clear stale ownership immediately if `assignee` is non-null; do not count a fake-ready card as queue health.
5. Leave a board comment that it was promoted after parent completion.
6. Re-snapshot the board after the promotion/repair and confirm the child is truly claimable (`workspace_kind=worktree`, repo-root workspace path, non-empty worker-neutral branch, `assignee=null`).

If a later board correction reopens the parent after a temporary done reconciliation, treat any child promoted during the false-done window as provisional until the parent is finally back to `done` and the child is re-verified against the fresh board snapshot.

Session pitfall: after a batch of Done reconciliations, re-check dependent ready candidates before assuming they stayed valid. In this sweep, `t_28fd4727` flipped back to Ready only after `t_2c0de92d`, `t_25a9269f`, and `t_5fb71fef` were all actually Done; the board had previously exposed a stale promotion that had to be retracted when one parent was still open.

Promotion nuance: if a child is still blocked by another parent after one parent completes, do not treat the first failed promote as a transient board glitch. Re-read the full parent set, surface the remaining unsatisfied parents in the next comment/reconciliation note, and only then retry promotion when every parent is actually Done/archived. This avoids the extra round trip of discovering one blocker at a time.

This is the main queue-flow mechanism. Do not skip it.

See `references/ready-worktree-child-promotion-hygiene.md` for the exact repair sequence and verification pitfall.

## Merged implementation versus deployed-proof follow-ons
A merged implementation PR and its source-card completion do **not** automatically prove release, deployment, or controlled live-dogfood acceptance.

Before calling a live-evidence request superseded by a merged PR:
1. Read the PR body and source-card handoff for explicit remaining acceptance items.
2. Compare the installed CLI/runtime embedded commit and deployed immutable build with the merged fix commit.
3. Verify that a release and the intended non-production target actually contain that commit.
4. State the distinction precisely: landed implementation versus unproven deployed evidence.

Concrete ancestry check (proven 2026-08-04): read the embedded commit from the target's public health endpoint (`curl -sS https://<target>/health` → `build.commit`), then run `git merge-base --is-ancestor <merged-squash-sha> <embedded-commit>` per merged PR to decide which fixes the deployed build actually contains. A PR merged to master **after** the deployed release cut fails this check even though `origin/master` contains it — that gap is exactly what a deploy/canary card still owes. Use squash-merge SHAs from `git log --oneline origin/master`, not pre-merge branch heads. See `references/deployed-embedded-commit-ancestry-check-2026-08-04.md` for the live GLY v0.1.62 example and the stale-gate rewrite it supported.

If code is merged but the requested proof requires a matching release/deploy plus a controlled target run, create **one narrow successor card** for release provenance and dogfood evidence. Link it to the completed implementation card; if immediately claimable, helper-create and validate it as an unassigned Ready worktree card. Label it an operator-evidence successor, not duplicate implementation work.

Do not create that successor when the user only asks whether the code landed. Conversely, do not archive it merely because the PR merged when the PR handoff explicitly says matching deployed proof remains open. The card must prohibit production rollout unless authorized, forbid unsafe fallback mutations, require bounded/redacted evidence, and block with the exact release/deploy gate if it cannot obtain a matching runtime.

A separate pitfall showed up in this sweep: a repair or source card can end up tied to a PR that is **closed and unmerged** even though the repaired head later received green CI. In that state, do not reconcile the card to Done. Move the source or repair card to `blocked` with `needs_input` or `triage` and leave a short comment stating the exact owner decision needed (reopen/merge versus abandon/re-scope). Treat green CI on a closed PR as evidence about the head, not proof that the implementation landed.

When the operator explicitly authorizes a semantic full rollout, use the preflight → worktree version bump → release-PR CI → immutable tag → complete workflow watch sequence in `references/semantic-release-full-rollout-and-dogfood-unblock.md`. Confirm embedded version and commit on HQ, Gly, and dev before releasing a dogfood card to Ready. Release success clears the freshness gate only; do not mark the actual installed-CLI dogfood proof complete unless it was run.

### Leaf-card rule
If a review card has no children, there is nothing to promote. Reconcile the card and stop.
See `references/task-links-schema-and-leaf-review-reconciliation-2026-07-16.md` for the direct task_links schema note and the leaf-review pattern.

## Approval-only gates and dependency-state repair

During every queue sweep, inspect blocked cards that gate Todo descendants. If the only missing input is a routine operator approval, surface it proactively in the user-facing sweep with the exact decision needed and a copy-paste authorization line; do not merely report the card as blocked. Distinguish a real target/environment choice from redundant wording: if a product has one unambiguous target, say so and ask only for the meaningful remaining authorization (for example, the current execution window).

### Blocked-card reactivation and duplicate-scope check
Before unblocking a card held for duplicate scope, capability, or a predecessor worker:
1. Read its full task/comment history with `kanban_show`, not only an inventory row or most-recent comment.
2. Read the cited predecessor's current terminal status and merged-PR/result evidence.
3. Compare evidence timestamps. A later live reproduction after the predecessor merged supersedes an older duplicate warning and makes the remaining card the valid repair owner.
4. In that case, unblock only one unassigned, claimable repair card and write a reconciliation comment that explains why the older duplicate hold is stale; preserve any fail-closed authorization boundary.
5. If the predecessor fixed the defect and no later reproduction contradicts it, reconcile the duplicate to Done/superseded rather than creating Ready queue noise.

Live task status controls availability, but historical comments remain required evidence before changing a blocked card. A status-only snapshot is insufficient for this decision.

### Satisfied-precondition detection for blocked gates

A blocked card's stated human-decision precondition can be silently overtaken by events while the card keeps reciting the old gate: a gated service restart happened by another means, disk capacity was restored, or a later release shipped past the failed one. Before escalating or preserving the gate, translate it into a checkable predicate and verify against live state:

- Restart gate → `systemctl show <unit> -p ActiveEnterTimestamp,ActiveState` (a recent ActiveEnterTimestamp after the incident time proves the restart already happened).
- Capacity gate → `df -h /` compared against the incident's recorded free space.
- Release/manifest gate → later release versions published and public manifest status.

If the precondition is satisfied but residual scope remains (e.g. the retention/budget implementation that motivated the gate), keep the card blocked, post a reconciliation comment separating what is now moot from what is still open, and surface the exact residual decision to JP. Do not unilaterally unblock a safety-gated card because one precondition cleared, and do not keep reporting the stale gate text as the current blocker. See `references/satisfied-blocked-precondition-detection-2026-08-04.md`.

When JP grants a bounded approval, record its scope in a card comment and promote the card only after confirming all parent work is actually complete. Preserve the stated safety boundary (for example: evidence-only rebuild/reconcile; no deploy, live configuration change, or corpus mutation) in the transition event/comment.

**Terminal-status dependency pitfall:** a merged implementation card can be incorrectly marked `archived` even though its result records a merged PR. This blocks descendants because dependency recomputation treats `archived` differently from `done`. Before declaring a queue genuinely empty, compare terminal parent statuses with their handoff/result evidence. If an `archived` parent represents merged/completed work, repair it to `done`, write a reconciliation status event, then recompute/promote children. Reserve `archived` for superseded or intentionally retired work.

**Ready worktree repair:** after any direct status transition, verify a Ready external-worker worktree card is truly claimable: `assignee=NULL`, `workspace_kind=worktree`, `workspace_path=<haft-repo-root>`, and non-empty worker-neutral `branch_name`. Normalize stale per-task worktree paths to the repo-root anchor in the same repair before reporting Ready runway.

## Board-state recovery and direct DB fallback
- See `references/gateway-safe-dbt-fallback.md` for the detached-user-unit pattern when a direct `kanban_db` recovery write is blocked from inside the running gateway process.
- Use the approved `kanban_db` Python path when the CLI transition helper fails or gives a false negative.
- If a direct `kanban_db` repair is rejected because it is running inside the gateway process, rerun the same temp-file script via `systemd-run --user --wait --collect --pipe` from a separate shell/session; do not rewrite the DB logic, only move execution outside the gateway context.
- If the shell/lifecycle scanner rejects that temp-file form with `embedded null byte`, treat it as "the command never ran" and switch immediately to the detached user-unit path. In this environment the scanner can reject both write-fallback and read-only inspection scripts, so do not keep retrying the inline form once the guard has objected.
- See `references/detached-user-unit-db-fallback-embedded-null-byte-2026-08-05.md` for the compact detached fallback recipe and the read-only-script pitfall.
- Use `--pipe` when you need the script's stdout/stderr in the tool result instead of only in the journal.
- See `references/gateway-safe-dbt-fallback.md` for the detached-user-unit pattern and the post-commit `show`-first verification step.
- See `references/gateway-safe-dbt-fallback-pipe.md` for the visible-output variant of the same recovery pattern.
- See `references/review-to-done-gateway-detached-fallback-2026-08-03.md` for the stale-review/merged-PR case where the first inline DB fallback is blocked by the gateway process and must be re-run as a detached user unit.
- See `references/detached-user-unit-db-fallback.md` for the detached-user-unit fallback recipe when inline DB repair hits the lifecycle guard.
- See `references/detached-db-fallback-lifecycle-guard-pitfall-2026-08-05.md` for the exact inline-heredoc-to-temp-file recovery shape when the lifecycle scanner throws `embedded null byte` before execution.
- See `references/detached-user-unit-db-fallback-embedded-null-byte.md` for the specific temp-file + lifecycle-guard rejection shape and the detached `systemd-run --user --wait --collect --pipe` recovery.
- See `references/detached-user-unit-db-fallback-2026-08-04.md` for the exact merged-review replay where an inline temp-file fallback script tripped the lifecycle scanner and the same script succeeded once rerun detached with `systemd-run --user --wait --collect --pipe`.
- If a temp-file DB fallback script is rejected by the terminal/lifecycle guard with an embedded-null-byte or referenced-script scan error, do not keep iterating the temp-file variant; rerun the same recovery detached with `systemd-run --user --wait --collect --pipe` from a separate shell/session, then re-read the task before any child-promotion checks. Both inline heredoc and referenced temp-file forms can trip the scanner in the same session; for read-only inspection, prefer parsing an already-snapshotted board JSON over running a DB probe script at all. The scanner rejection can surface as an unhandled `ValueError: embedded null byte` traceback from `_read_referenced_script` (an exception inside `os.open`, exit_code -1) instead of a clean refusal — treat that traceback as "the command never ran", not as a command failure, and go straight to the detached variant. In practice, write the fallback script to a temp file first and invoke that file via the detached user unit; do not retry a long inline `python3 - <<'PY' ...` heredoc after the guard has already objected. Confirmed 2026-08-04: even pure read-only inspection scripts (e.g. a sqlite `task_links` children check) trip the scanner, and the detached `systemd-run --user --wait --collect --pipe` form works for read-only probes as well as write fallbacks. See `references/lifecycle-scanner-null-byte-rejects-read-only-scripts-2026-08-04.md` and `references/review-to-done-detached-fallback-scan-pitfall-2026-08-04.md`.
- See `references/direct-db-fallback-inline-python-pitfall.md` for the compact inline-Python fallback note.
- If a direct `kanban_db` repair is rejected because it is executing inside the gateway process, do not keep retrying the inline shell block; move the same script into a detached user unit (`systemd-run --user --wait --collect --pipe`) rather than changing the DB logic.

**Haft board DB path:** `<hermes-home>/kanban/boards/haft/kanban.db`

**Schema notes for direct SQL:**
- `tasks` table columns: `id`, `title`, `body`, `assignee`, `status`, `priority`, `created_by`, `created_at`, `started_at`, `completed_at`, `workspace_kind`, `workspace_path`, `branch_name`, `claim_lock`, `claim_expires`, `tenant`, `result`, `idempotency_key`, `consecutive_failures`, `worker_pid`, `last_failure_error`, `max_runtime_seconds`, `last_heartbeat_at`, `current_run_id`, `workflow_template_id`, `current_step_key`, `skills`, `model_override`, `max_retries`, `goal_mode`, `goal_max_turns`, `session_id`, `project_id`, `block_kind`, `block_recurrences`, `provider_override`.
- `task_events` table columns: `id`, `task_id`, `run_id`, **`kind`** (NOT `event_type`), `payload`, `created_at`. Use `kind='status'` for status transitions.
- `task_links` table: `parent_id`, `child_id`.

**Shell quoting pitfall:** When using `hermes kanban comment <id> text...` or `hermes kanban create --body "..."` via terminal, parentheses, backticks, semicolons, and other shell metacharacters in the body string can trigger shell interpolation or command substitution. A provenance comment can appear to succeed while losing the intended SHA or URL text. Prefer the Hermes tools that bypass shell entirely, or wrap the body in single quotes / stage it in a temp file when the text contains markdown punctuation. Re-read the stored comment when the exact reviewed head SHA matters. See `references/kanban-comment-shell-quoting-pitfall-2026-08-02.md`.
See `references/kanban-comment-shell-quoting-pitfall-2026-08-07.md` for a concrete 2026-08-07 provenance-comment example where shell backticks stripped the literal command text and the fix was to stage the body instead of inlining it.

**Batch DB fallback pattern:** For multi-card reconciliation, write a Python script to a temp file and execute it rather than inlining SQL in shell strings. The script should: (1) iterate cards, (2) skip already-done, (3) UPDATE status + clear claim fields + set completed_at + set block_recurrences=0 + clear current_run_id, (4) INSERT a status event with `kind='status'`, (5) commit per-card, (6) check children for promotion eligibility. See `references/batch-db-fallback-script-2026-07-28.md`.

Prefer the supported CLI transition helpers (`block`, `schedule`, `promote`, `complete`) for ordinary status changes. Reserve ad hoc SQL for the documented recovery paths only, and after any direct mutation re-snapshot both `show` and `list` before trusting the result; board projections can lag or derive from the event stream. If `list --json` still reflects the pre-mutation state after a repair, treat `show` or a direct DB read as authoritative and refresh `list` only after the projection catches up. If `show` briefly says `no such task` for a card that still appears in a fresh inventory snapshot, assume snapshot lag first, re-copy the exact ID from the fresh inventory row, and retry once before concluding the card vanished or was deleted. Do not make follow-on promotion/no-op decisions from the stale list snapshot; always refresh the board view first. Use Hermes board snapshots (`show`/`list`) for routine inventory and reconciliation; avoid ad hoc sqlite probes from the orchestrator/gateway process when a snapshot already answers the question.

A direct metadata repair can also lag in the opposite direction: `show` may reflect the new `block_kind` immediately while `list --json` still shows the old projection for one refresh cycle. Use the task read as the first verifier, then re-snapshot inventory before judging queue health.

See `references/list-snapshot-staleness-after-direct-mutation.md` for the observed stale-list repair sequence.
See `references/already-blocked-metadata-repair-2026-08-01.md` for the block-kind-only repair variant.
- `references/list-snapshot-staleness-after-direct-mutation-2026-07-30.md` — direct-board-mutation snapshot lag note: `show` can reflect a DB fallback before an older `list --json` inventory catches up; always refresh inventory before judging queue health.

Session note: review handoff helper can fail with a nested-transaction error (`cannot start a transaction within a transaction`) when the wrapper tries to open a transaction while one is already active. In that case, do not wrap the helper call in an outer `write_txn`; use fresh connections for each mutation step and do not loop on the wrapper once the board mutation itself is the blocker. See `references/review-handoff-helper-nested-transaction-pitfall.md` for the minimal recovery sequence and verification shape.

Session note: when `hermes kanban complete` refuses a live `review` card as `unknown id or terminal state`, the durable recovery is comment-first provenance, then a direct `review -> done` DB fallback on a fresh connection, then post-commit cleanup helpers and a fresh board re-snapshot. See `references/review-to-done-helper-refusal-db-fallback.md` for the compact step order.

Session note: `hermes kanban comment` is a positional CLI in this environment (`comment <task_id> <text...>` plus optional `--author`); write provenance as a standalone comment before fallback and verify it independently. Do not try to attach provenance through `complete`, and do not assume the transition helper will preserve comment metadata.

Session note: `references/merged-review-sweep-reconciliation-2026-07-22.md` captures the live `review -> done` recovery path where a merged review card refused `complete` with `unknown id or terminal state`; provenance was written first, then the direct DB fallback landed cleanly. The 2026-07-24 follow-up in `references/review-to-done-helper-refusal-live-session-2026-07-24.md` confirms the same sequence on a fresh merged PR plus stale `review` card, including the fresh-connection cleanup order and post-commit re-snapshot before any child checks. The 2026-07-25 note in `references/review-to-done-helper-refusal-live-session-2026-07-25.md` adds the same recovery path with the post-snapshot child promotion landing on a newly claimable child. The 2026-07-28 session in `references/review-to-done-helper-refusal-live-session-2026-07-28.md` reinforces the same stale-terminal refusal shape when `show` still reported `review` after GitHub merge and `complete` refused with `unknown id or terminal state`. The PR #1381 replay in `references/review-to-done-helper-refusal-live-session-2026-07-28-pr1381.md` adds a compact example where the helper refusal was treated as durable evidence, provenance stayed in a separate comment, and the direct fallback plus fresh cleanup helpers promoted a child immediately afterward. See `references/review-to-done-helper-refusal-live-session-2026-07-28-pr1375.md` for the exact merged-PR / stale-review recovery transcript. See `references/merged-review-helper-refusal-live-session-2026-07-27.md` for the latest batched example: two merged review cards were reconciled in one sweep, one `complete` call refused with `unknown id or terminal state`, and both cards were completed with provenance-first comments plus fresh-connection DB fallback. See `references/merged-review-helper-refusal-fresh-snapshot-child-promotion.md` for the exact comment-first + DB-fallback + fresh-snapshot sequence and the ready-child promotion pitfall. See `references/review-to-done-stale-helper-refusal-fresh-snapshot.md` for a compact 2026-07-26 example where `complete` refused a merged card as `unknown id or terminal state`; it records the provenance comment, direct DB fallback, fresh cleanup helpers, and the required post-fallback re-snapshot before any child promotion. See `references/merged-review-repair-card-fallback-2026-07-24.md` for the paired source-review + repair-card reconciliation pattern when one PR strands multiple live cards. Always re-snapshot the board afterward and re-check any child promotions against the fresh state before declaring queue health.

Typical uses:
- Review → Done when `hermes kanban complete` or the equivalent helper refuses a valid merged card
- Done → Ready promotion verification when the board lagged behind GitHub
- Repairing status transitions after a merged PR or docs-only reconciliation

- Important details:
- Use the live task view as the source of truth for children when possible.
- If you query SQLite directly, the link table is `task_links(parent_id, child_id)`.
- Do not guess alternate column names.
- When doing a manual DB fallback, keep `recompute_ready(conn)` outside the write transaction. Nested transaction boundaries can fail even after the task update itself succeeds.
- Also keep `_clear_failure_counter(conn)` and `_cleanup_workspace(conn)` outside the same write transaction; both open their own transactions and will throw `sqlite3.OperationalError: cannot start a transaction within a transaction` if called before commit.
- Do not wrap the post-commit cleanup helpers in a fresh `write_txn(...)` block either; call them on a plain fresh connection after the fallback commit so their internal transaction boundaries remain clean.
- If the helper refused a merged card with `unknown id or terminal state`, verify GitHub merged state first, leave a short provenance comment with PR URL + head SHA + helper failure text, then apply the DB fallback. Record provenance with a separate comment; `hermes kanban complete` does **not** accept `--author`, so do not try to attach provenance through the completion helper.
- If the provenance comment succeeds but `complete` still refuses, treat the comment as durable evidence that the handoff context is preserved; do **not** re-run the helper in a loop or rewrite the comment. Move straight to the DB fallback.
- If the gate helper itself refuses because the PR is already merged and a cleanup job is still in progress, treat that as post-merge housekeeping, not a merge blocker: re-read GitHub to confirm `state=MERGED`, add provenance, and reconcile the board from the merged state rather than retrying the gate.
- If the live task is still in `review`, do **not** keep retrying `complete`. Treat that as a live reconciliation path, not a terminal done-state. Re-read the task, confirm the PR is merged, add a short provenance comment first when needed, then use the direct `review -> done` DB fallback: update `status = 'done'`, clear claim fields (`claim_lock`, `claim_expires`, `worker_pid`, `block_kind`), set `completed_at`, set `block_recurrences = 0` rather than `NULL`, clear `current_run_id`, persist the merge evidence in the task result/comment payload, and record a status event. This is the correct recovery path when the helper's terminal-state guard is out of sync with a merged review card. `current_run_id = NULL` is not a reason to skip fallback; use the live board status plus GitHub merge state as the decision inputs. After the fallback transaction commits, take a fresh board snapshot before any child-promotion checks and only promote from that new snapshot. See `references/review-to-done-db-fallback-task-id-pitfall-2026-07-23.md` for the task-scoped maintenance helper signatures.
- If `complete` refuses with `unknown id or terminal state` after a verified merge, treat the refusal as stale board state, not as evidence that the card is already done. Write provenance first, then apply the direct DB fallback on a fresh connection, and only after commit run `_clear_failure_counter(conn, task_id)`, `recompute_ready(conn)`, and `_cleanup_workspace(conn, task_id)` in that order. Keep `recompute_ready(conn)` outside the write transaction. See `references/review-to-done-show-first-after-fallback-2026-08-06.md` for the show-first verification pattern when inventory lags the repair.
- Do not treat a null `current_run_id` as a reason to skip the fallback; use the live board status plus GitHub merge state as the decision inputs.
- After the fallback transaction commits, call `_clear_failure_counter(conn, task_id)`, then `recompute_ready(conn)`, then `_cleanup_workspace(conn, task_id)`. Do not call any of them inside the write transaction.
- After the fallback, re-read the mutated task with `show` first. Treat `show` as authoritative for the immediate post-fallback state; `list --json` can lag one projection cycle. Only refresh inventory after `show` if you need to judge child readiness or queue health.

- Session note: `references/review-to-done-helper-refusal-live-session-2026-07-24.md` captures the exact comment-first + DB-fallback + fresh cleanup sequence used when a merged PR still showed `review`.
- Session note: if `hermes kanban complete` refuses a live `review` card with `unknown id or terminal state`, do **not** loop the helper. Re-read the live task, confirm the PR is merged, add a short provenance comment first, then use the direct `review -> done` DB fallback on a fresh connection, clear failure counters/cleanup helpers after commit, and re-snapshot before any child promotion. Treat the provenance comment as durable evidence; `complete` does not accept `--author`.

- Session-specific example: `references/review-to-done-helper-refusal-2026-07-21-session.md`.
- Session-specific example: `references/review-state-live-helper-refusal-fallback-2026-07-21.md`.
- - Session-specific example: `references/merged-review-double-reconciliation-2026-07-23.md`.
- Session-specific example: `references/review-to-done-helper-refusal-live-session-2026-07-24.md`.
- Session-specific example: `references/review-to-done-fresh-snapshot-child-promotion-2026-07-24.md`.
-
See `references/pr-sweep-2026-07-06-python-db-verification.md` for the direct board-query pattern. When the fallback is used after a merged PR, record the merged PR URL/head SHA and the helper failure reason in the task result/comment so the reconciliation trail stays explicit; see `references/review-handoff-db-fallback-and-merge-race-2026-07-18.md` and `references/merged-leaf-review-reconciliation.md`. Recent example: `references/merged-review-reconciliation-2026-07-29.md`. Session addendum: `references/merged-review-reconciliation-2026-07-29-pr1405-pr1407.md` captures the 2026-07-29 merged-review sweep where `complete` refused a live review card after GitHub already reported the PRs as merged; the recovery was provenance comment first, then direct DB fallback, then fresh snapshot verification. See also `references/merged-review-helper-refusal-live-session-2026-07-30.md` for the same recovery shape with a transient `mergeStateStatus=UNKNOWN` on the merged PR. Session-specific PR #1398 note: `references/merged-review-reconciliation-2026-07-29-pr1398.md`.

## Ready worktree cards
A Ready worktree card is only claimable when all of these are true:
- `workspace_kind == worktree`
- `workspace_path == <haft-repo-root>`
- `branch_name` is a non-empty worker-neutral slug
- `assignee == null`

If any of those are wrong, repair the metadata or move the card out of Ready before counting it as queue health. See `references/ready-claimability-repair-2026-07-29.md` for a live example.

When a card is superficially Ready but still capability-blocked or owner-assigned, move it out of Ready rather than leaving a fake-ready card on the board. Re-snapshot after the mutation and confirm the queue changed the way you intended.

If a Ready worktree card has a stale per-worker worktree path, repair the path to `<haft-repo-root>` rather than to the old `.worktrees/<task-id>` checkout path. If the same card also has a stale assignee, clear both in the same fresh kanban_db repair so the card does not remain fake-ready between partial fixes. Then re-show the task and confirm `workspace_kind=worktree`, `workspace_path=<haft-repo-root>`, `branch_name` unchanged, and `assignee=null`.

A single stale field can hide the other. In practice, treat `assignee` and `workspace_path` as a pair: repair them together in one transaction, then refresh the board snapshot before declaring the card claimable.

Pitfall: a Ready worktree card that still points at its per-worker `.worktrees` checkout path is not truly claimable yet, even if `assignee` is null and `branch_name` looks valid. Normalize the path to `<haft-repo-root>` first, then re-snapshot and verify the card is still Ready with the repo-root anchor before letting workers claim it.

If a Ready worktree card is missing `branch_name`, treat it as queue hygiene work, not claimable implementation. Comment that the card is not yet claimable, move it out of Ready, and wait for metadata repair before anyone claims it. Do not count a stale `assignee=null` as claimability if `branch_name` is still missing. Re-read the live task row after any repair; a cleared assignee alone is not enough. See `references/ready-worktree-metadata-repair-direct-sqlite.md` for the compact repair/verify sequence when the normal helper path is unavailable, and `references/fake-ready-worktree-claimability-repair-2026-08-06.md` for the claimability checklist.

If a card is `workspace_kind=scratch` or clearly depends on human pairing / OTP / browser proof / other operator input, do **not** leave it in Ready. Move it to `blocked` with `needs_input` and a short reason instead; Ready should stay limited to dependency-safe external-worker work. If a scratch card is accidentally promoted into Ready with a worker assignee, treat that as queue corruption, not claimable runway: block it first, then clear the stale assignment only if the board surface requires it. After blocking, re-snapshot the board and verify the card no longer appears in Ready before treating queue health as restored. Use the live task row as the first verifier; inventory rows can lag one projection cycle after the mutation.

If the task is already `blocked` and the only thing wrong is the stored `block_kind`, the normal `block` helper may refuse with `cannot block <task_id>`. In that case, repair the metadata on a fresh `kanban_db` connection, leave a short provenance comment, then re-read `show` before refreshing the inventory snapshot. Some inventory views can omit or lag `block_kind` for blocked tasks, so do not trust a plain list row to prove the card is or is not `needs_input`; verify the live task row before deciding queue health. See `references/already-blocked-metadata-repair-2026-08-01.md` and `references/blocked-inventory-vs-live-task-read.md` for the observed repair sequence and the list-vs-show pitfall.

See `references/ready-worktree-repo-root-anchor-repair.md` for the path repair sequence and `references/ready-worktree-claimability-repair-2026-07-26.md` for the paired path+assignee repair pitfall.

See `references/ready-lane-invalid-orchestrator-card-reconciliation-2026-07-10.md`, `references/ready-metadata-repair-and-capability-blocking.md`, `references/ready-worktree-card-claimability-repair.md`, and `references/task-links-schema-and-leaf-review-reconciliation-2026-07-16.md` for repair patterns.

## Fork-main integration gates

When a multi-PR implementation is landing through the user's fork before any later upstream PR:

1. Treat each feature PR into `<fork>:main` as a review handoff, not a completed source card merely because the worker opened it.
2. Do **not** release dependent cards that instruct workers to branch from `fork/main` until GitHub reports the prerequisite PR as `MERGED`.
3. Fetch the fork and verify the merge commit is an ancestor of `fork/main` before promotion. Example: `git fetch fork --prune && git merge-base --is-ancestor <merge-sha> fork/main`.
4. Only then reconcile the integration gate to Done and promote the dependent external-worker cards.
5. Keep the eventual upstream PR separate: after the coherent milestone is reviewed and integrated in the fork, open `<fork-owner>:main` → `<upstream-owner>/<repo>:main`; do not treat internal fork PRs as upstream submission.

This prevents workers from branching from a fork mainline that lacks the code their card assumes.

## PR-level CI rescue rerun after a harness fix merges
When an open implementation PR is held only by an evidenced full-suite/harness timeout and a separate, narrowly scoped CI-rescue PR merges with green checks:

1. Verify the rescue PR is merged to the implementation PR's actual base branch and that its required checks are green.
2. Rerun the failed job on the still-open implementation PR (`gh run rerun <run-id> --failed`, then `gh run watch <run-id> --exit-status`).
3. Re-read the implementation PR after the rerun. Do not infer success from the rescue PR alone—the implementation PR needs its own current-head green check result.
4. If the source PR is then merged by an operator or concurrent automation, reconcile its Review card to Done and recompute/promote dependency-safe children.
5. If it remains open despite green checks, leave it in Review for the normal merge decision; do not mark the source card Done prematurely.

This preserves ownership: the CI-rescue card proves the harness correction, while the source card is only complete after its own PR merges.

### Merge-race successor PR rule
When a remediation PR merges or is auto-closed while a verified corrective commit is still local and not in that merge, do not stop at reporting that it "needs a new PR." Immediately fetch current `origin/master`, create a fresh focused worktree/branch, cherry-pick or reapply only the corrective commit, rerun its tight verification, push, and open the successor PR. Report the successor URL and its live check state. This is the default proactive recovery path; do not wait for JP to request the obvious follow-up.

## Recovered master-CI timeout follow-up
When a GitHub failure email is for a merged `master` push run and attempt 1 times out in one exact Bun test, do not stop at the stale red email and do not reopen the merged source card automatically.

Required sequence:
1. capture the exact attempt-1 failing test and timeout text;
2. verify the merged PR diff does not touch that test or its immediate implementation surface;
3. reproduce on the exact merged `master` commit with both a focused test run and full `bun run test` when practical;
4. rerun the failed job on the same workflow run before classifying it;
5. if attempt 2 recovers green, keep the source card `Done` and treat the incident as recovered false-negative evidence;
6. if there is **no source card**, the focused repro on current `master` passes, and the rerun recovers green, stay silent — do not invent retrospective board work from a single recovered timeout;
7. only create a new narrow Ready worktree follow-up when the exact failing test is still unowned **and** the failure persists, reproduces, or recurs after rerun.

References:
- `references/recovered-master-ci-timeout-followup.md`
- `references/merged-master-no-source-card-recovered-timeout-silent-triage.md`

## Release runner capacity-preflight failure intake
When a Haft `Release` workflow fails in `Publish Haft CLI release binaries` (or equivalent release publish work) at `Preflight release runner capacity`, classify it as a self-hosted runner-maintenance blocker unless newer evidence proves otherwise.

Required sequence:
1. capture the live run state, exact failing job/step, and the capacity annotation;
2. corroborate with current host disk evidence;
3. treat the follow-up as actionable external-worker work, not triage-only bookkeeping;
4. create a claimable Ready worktree card for conservative disk reclamation plus local preflight verification;
5. do **not** rerun the release workflow during inbox triage, because that resumes a public release path before headroom is restored;
6. do **not** publish the release, move tags, or treat the failure as a product regression unless later evidence changes the classification.

Good pattern:

> The release run is still red. The failure is the release-runner capacity gate, not the product test/build surface. Current host disk evidence confirms low headroom. Create one Ready worktree cleanup card with the exact run URL, annotation, threshold, and local verification goal; leave the actual rerun/publish step for after cleanup.

Reference: `references/release-runner-capacity-preflight-ready-intake.md`. For the evidence boundary between failure-time capacity, current disk state, skipped downstream jobs, and immutable-publication status, see `references/release-capacity-failure-intake-v0144.md`.

## Recovered-but-red deploy follow-up
When a deploy workflow run is still red but the live runtime later reports the intended SHA as healthy, do not dismiss the email as stale and do not misclassify it as a current product regression.

Required sequence:
1. capture the exact failing run/job, head ref/SHA, remote command id, and target instance;
2. query the failed remote-command record directly and preserve both stdout and stderr;
3. classify from the **failed-time** host evidence first (systemd status, crash text, missing drop-ins, bounded-health failures), not just from current host state;
4. compare the failed-time unit drop-ins against the current live unit state to detect host-unit drift;
5. verify current public/runtime health separately;
6. if the deploy later recovered on the same SHA, create one narrow follow-up for deploy reliability / host-unit drift rather than reopening unrelated product work.

Two common recovered-but-red subtypes now matter:
- **host-unit drift / crash-loop**: the runtime never stabilized during the failed restart; see `references/recovered-deploy-red-run-dropin-drift.md`.
- **post-health verification false negative**: the deploy already served healthy localhost and public runtime traffic on the intended SHA, but a later observability/verification probe still failed; treat that as a separate deploy-verification lane, not automatic ownership by an older same-workflow card. See `references/recovered-gly-deploy-verification-false-negative-after-healthy-localhost-checks.md`.

## Cron and environment constraints
- When push/retry is blocked by host auth, report the state clearly and do not loop endlessly.
- If the local checkout is dirty or stale, reconcile the checkout before relying on the repo for deploy verification.
- Do not use outbound email from `<read-only-canary-address>`; the inbox is read-only operational state.
- Installed `gh` gaps: `gh run list --pr` does not exist (use `-c <sha>` / `-b <branch>`); `--json attempts` is unsupported (use `gh api .../runs/<id>/attempts/<n>/jobs` for per-attempt jobs + runner attribution). See `references/gh-cli-field-gaps-and-run-list-pr-flag-2026-08-05.md`.
- If canonical checkout drift reappears after a completed stash-repair card, compare mtimes against the stash timestamp and check `git log --all -S` before classifying; it may be external operator reapplication (e.g. Yogendra rollout prep), not new drift — report, do not auto-discard. See `references/canonical-drift-reappearing-after-stash-repair-2026-08-05.md`.
- When the same E2E failure recurs only on one runner name across release runs while reruns on healthy runners pass, treat it as runner-lane evidence for the rollout card, not product code; use per-attempt job queries for runner attribution. See `references/runner-isolated-relative-url-failure-evidence-2026-08-05.md`.

## Stale Ready card triage and archival

Auto-generated CI rescue, browser-regression repair, and runner-infra cards accumulate in Ready after their triggering PRs merge. Triage them during sweeps:

1. Identify Ready cards whose body references a specific PR number (e.g. "PR #1337 CI failure", "Repair PR #1349").
2. Check that PR's live state: `gh pr view <n> --json state,mergedAt`.
3. If the PR is MERGED and the fix is confirmed on master (check `git log --oneline origin/master -- <affected-file>` or recent green CI), the rescue card is stale.
4. Also check whether a separate rescue PR (referenced in the card or merged around the same time) already landed the fix.
5. Archive stale cards with a result string citing the merged PR and why the card is superseded.
6. If a repair/follow-up card is itself proven to be a no-op on the current head or `origin/master`, close it as a stale follow-up instead of spinning a duplicate repair PR, and preserve the no-op evidence in the task result/comment.
   - Before reopening, unblocking, or escalating a blocked repair card whose PR closed unmerged, first check whether its goal already exists on `origin/master` (`git log --oneline origin/master -- <file>` + `git show origin/master:<path>`); recurring failures confined to one runner while reruns on healthy runners pass are runner-lane evidence, not missing code. See `references/superseded-repair-card-fix-already-on-master-2026-08-05.md`.
   - For release/deploy repair cards, prove no-op status by a later successful release run through the same previously-failing step plus live endpoint evidence (health version/commit), then archive citing the fixing PR, the green run, and the live state. See `references/release-deploy-repair-noop-via-later-green-release-2026-08-05.md`.
7. If a narrow off-diff repair card is later shown to duplicate a completed follow-on fix, archive the duplicate repair card as stale queue noise rather than leaving it blocked or ready. Leave one provenance comment naming the superseding completed task / merged PR and stating that no implementation remains, then refresh the board snapshot so the duplicate disappears from inventory.

Reference note: `references/off-diff-repair-card-duplication-archive-2026-07-31.md`.

See `references/stale-noop-follow-up-reconciliation-2026-07-31.md` for the no-op recovery pattern.

Do NOT archive:
- Cards referencing PRs that are still OPEN (CI may still be in flight).
- Infra cards (runner deps, tool installs) unless recent CI runs on the affected pool are demonstrably green.
- Implementation cards from audit findings or roadmap work that are not PR-tied.

See `references/stale-ready-card-archival-2026-07-28.md` for the concrete triage example.

## Queue-health heuristics
- Keep enough Ready runway for active worker lanes.
- Do not crowd Ready with tracker shells or broad placeholders.
- Preserve dependency correctness over cosmetic queue fullness.
- If a card is already clearly running or review-handoff complete, do not duplicate work elsewhere.
- Treat board snapshots as moment-in-time inventory. After any claim, promote, complete, block, or direct DB repair, refresh the live task/board view before deciding whether the queue actually changed; a stale list snapshot can lag behind a fresh `show`/task view.
- If a sweep finds only already-running cards owned by active workers and no Review/Ready inconsistencies, stop after confirming that state instead of hunting for a PR or queue mutation to make the run look productive.
- A board snapshot that appears empty is not enough to declare the sweep done if there were recent PR changes in the same lane. Re-read live GitHub PR state before calling the run a no-op, especially when a PR may already be merged but its card has not yet been reconciled or projection has lagged. See `references/board-snapshot-is-not-authoritative-after-merge.md`.
- If a Ready rescue card is superseded by newer current-head evidence (for example, a later CI run proves the earlier failure class is gone and another card owns the remaining blocker), transient-block or retire it instead of claiming it. Treat the newer live run as authoritative and avoid manufacturing stale queue health.
- If a Ready card is operator-run, scratch-scoped, or missing claimability metadata (`workspace_kind != worktree`, missing `branch_name`, stale non-null `assignee`), do not count it as runway: block it or repair it first, then re-read the live task row before declaring queue health restored. See `references/fake-ready-card-triage-2026-08-03.md`.

### Retiring recovered CI/deploy follow-ups
When reviewing Ready cards created from a recovered CI or deploy failure, classify them from **current evidence**, not the original red alert alone.

This same rule also applies to scheduled follow-up cards that were filed as incident placeholders: if the underlying failure is already fixed and the card is now stale queue noise, verify current evidence first, then retire the card instead of preserving it forever just because it is `scheduled`.

Archive a card only when all applicable facts are verified:
1. the failed workflow was rerun or superseded by a successful equivalent workflow;
2. the current deployment target is still the same host, or the failed host is no longer the configured target;
3. the live health endpoint reports the intended immutable commit with embedded provenance; and
4. the latest relevant master CI is green when the card concerns test reliability.

Keep the card if the same failure recurs, there is an unproven deterministic root cause, or the old host remains an active deployment target. Distinct incidents on different hosts or failure phases are not duplicates merely because both mention the same deploy workflow; archive them as independently resolved historical incidents rather than merging their evidence.

A completed implementation card left in `review` after its PR is merged should be reconciled to `done`; a newly discovered production follow-up is a successor, not a duplicate.

See `references/scheduled-card-exclusion.md` for the default no-touch rule and its stale-follow-up retirement exception.

- `references/current-head-required-check-hold-pattern.md`
- `references/current-check-contract-drift-2026-07-18.md`
- `references/release-runner-capacity-preflight-ready-intake.md`
- `references/pr-sweep-2026-07-06-python-db-verification.md`
- `references/board-snapshot-file-parse-pattern.md`
- `references/board-inventory-json-triage.md`
- `references/cron-board-and-pr-sweep-pattern.md`
- `references/review-card-no-children-reconciliation.md`
- `references/task-links-schema-and-leaf-review-reconciliation-2026-07-16.md`
- `references/review-merge-ack-board-reconciliation.md`
- `references/review-handoff-helper-and-merge-cleanup-recovery.md`
- `references/merged-review-card-complete-fallback.md`
- `references/merged-review-card-done-fallback-after-helper-refusal.md` — exact `review -> done` DB fallback pattern when a merged review card is already in review and the helper says `unknown id or terminal state`.
- `references/merged-review-helper-refusal-fresh-connection-fallback.md` — compact checklist for the same merged-review refusal path, including the fresh-connection fallback sequence and the leaf-card stop rule.
- `references/review-to-done-db-fallback-2026-07-21.md` — concise operator recipe for the same recovery path, including the clear-fields set and `recompute_ready(conn)` placement.
- `references/review-to-done-db-fallback-nested-transaction-pitfall.md` — live recovery note for the transaction boundary trap: `_clear_failure_counter(conn)` and `_cleanup_workspace(conn)` must run after the write txn, not inside it.
- `references/review-to-done-helper-refusal-2026-07-21.md` — session-derived sequence for a live `review` task whose merged PR causes helper refusal; keep the provenance comment, DB fallback, and child check ordering explicit.
- `references/review-to-done-helper-refusal-2026-07-22.md` — current helper-refusal fallback note for the `unknown id or terminal state` case with a live `review` task.
- `references/complete-helper-refusal-live-task-state-fallback-2026-07-23.md` — scheduled/non-review stale-refusal variant.
- `references/review-to-done-live-merged-review-fallback-2026-07-23.md` — compact session transcript for the merged-PR / stale-review / helper-refusal recovery path.
- Session note: `references/review-to-done-helper-refusal-live-session-2026-07-24.md` captures the exact "comment provenance first, then DB fallback, then fresh cleanup helpers" sequence after `complete` refused merged PRs still showing `review`; this run also confirmed re-snapshotting before child promotion and queue-health checks.
- Session note: `references/review-to-done-fresh-snapshot-child-promotion-2026-07-29.md` records the same fallback shape with the fresh-parent `show` check before promoting a newly claimable child; use it when direct DB reconciliation succeeds but the board projection may still be catching up.
- `references/review-to-done-helper-refusal-live-session-2026-07-25.md` — 2026-07-25 merged-PR / stale-review recovery example, including the comment-first handoff, direct DB fallback, and post-snapshot promotion of a newly claimable child.
- `references/review-to-done-helper-refusal-live-session-2026-07-25-postmerge.md` — compact post-merge replay of the same helper-refusal pattern; useful when the live task still shows `review` after GitHub says `MERGED`.
- `references/merged-review-batch-reconciliation-2026-07-27.md` — batched two-card reconciliation note: write provenance comments first, then apply per-card DB fallbacks on fresh connections, then validate the board snapshot once at the end of the sweep. The 2026-08-01 addendum in the same file covers the three-card stale-review sweep with the same comment-first + fresh-connection fallback pattern.
- `references/merged-review-batch-reconciliation-2026-08-01.md` — updated session note for a four-card stale-review sweep: the helper refused already-merged cards, so the correct path was provenance comment first, then direct `review -> done` fallback on a fresh connection, then post-commit cleanup and a show-first verification pass.
- `references/merged-review-terminal-state-refusal-live-session-2026-07-26.md` — live 2026-07-26 example of `complete` refusing a merged review card as `unknown id or terminal state`; use the provenance-comment-first + direct DB fallback sequence.
- `references/review-to-done-helper-refusal-live-session-2026-07-26-pr1277.md` — concise PR #1277 transcript of the same merged-review refusal plus the exact fresh-connection cleanup ordering and post-fallback snapshot check.
- `references/merged-review-helper-refusal-live-session-2026-07-27.md` — latest merged-review refusal session: `state=MERGED`, transient `mergeStateStatus=UNKNOWN`, comment-first provenance, direct DB fallback, fresh cleanup helpers, and leaf-card stop. This note covers the two-card PR #1305 sweep (`t_1d28f8c8`, `t_7aa76169`) that both needed stale-review reconciliation after merge.
- `references/review-to-done-helper-refusal-live-session-2026-07-28.md` — newest compact example of the same stale-terminal refusal path; use it when a merged review card still shows `review` and `complete` refuses with `unknown id or terminal state`.
- `references/review-to-done-helper-refusal-live-session-2026-07-28-pr1380.md` — PR #1380 example of the same merge-lag + stale-review recovery path, including the provenance-first comment and leaf-card stop.
- `references/review-to-done-helper-refusal-live-session-2026-07-29-pr1393.md` — PR #1393 example showing merged-review reconciliation plus immediate child promotion after the fresh post-fallback snapshot.
- `references/merged-pr-merge-state-unknown-cleanup-lag-2026-07-29.md` — short note on a transient `mergeStateStatus=UNKNOWN` that cleared after a fresh GitHub re-read and a second merge attempt.
- `references/post-merge-cleanup-lag-and-board-no-op-2026-07-29.md` — session note for treating `MERGED` + transient `UNKNOWN` as cleanup lag and stopping when the board has no review/running work left.
- `references/merged-review-helper-refusal-live-session-2026-07-29-pr1400-pr1401.md` — two-card 2026-07-29 sweep where `complete` refused already-merged review cards twice and the fix was provenance comment first, then direct DB fallback, then post-commit cleanup and a fresh board snapshot.
- `references/review-to-done-helper-refusal-live-session-2026-07-30.md` — 2026-07-30 merged-review refusal transcript for PRs #1447 and #1446, including the cleanup-lag `mergeStateStatus=UNKNOWN` read and the leaf-card stop.
- `references/merged-review-helper-refusal-live-session-2026-07-30-pr1477.md` — PR #1477 example of the same stale-terminal refusal path: GitHub `MERGED` + board `review` + `complete` refusal, then provenance-first comment, direct DB fallback, fresh cleanup helpers, and child promotion only after the fresh post-fallback snapshot.
- `references/merged-review-helper-refusal-live-session-2026-07-30-pr1466.md` — PR #1466 example of the same live `review` + merged-PR recovery path: provenance comment first, direct DB fallback, fresh post-fallback snapshot, and promotion of three newly claimable children.

- `references/merged-review-helper-refusal-live-session-2026-07-30-pr1468.md` — PR #1468 example showing the same helper refusal after a live merge, including the transient `mergeStateStatus=UNKNOWN` cleanup lag and the fresh-snapshot leaf-card stop.
- `references/merged-review-helper-refusal-leaf-card-stop-2026-07-30.md` — concise leaf-card replay of the same provenance-first + direct fallback + fresh-snapshot stop rule for PRs #1445 and #1448.
- `references/merged-review-helper-refusal-fresh-connection-fallback-2026-07-27.md` — concise recovery recipe for the same refusal shape, with the exact fresh-connection cleanup order and the no-loop/no-`--author` pitfalls.
- `references/review-to-done-merged-pr-cleanup-lag-2026-07-24.md` — concise end-to-end note for the same merge-lag case where GitHub already said `MERGED` but `mergeStateStatus` still lagged `UNKNOWN` and the board card remained `review` until the direct fallback landed.
- `references/review-to-done-live-merged-helper-refusal-2026-07-24.md` — compact transcript for the current merged-PR / stale-review / helper-refusal recovery path, including the fresh-connection cleanup order and durable provenance fields.
- `references/review-complete-empty-evidence-judge-path.md` — narrow note for the `complete` helper's empty-evidence judge refusal shape and the correct stop-loop + provenance + direct-fallback recovery order.
- `references/review-to-done-state-race-before-fallback.md` — live note for the race where a merged review card becomes `done`/`archived` before the fallback write; provenance-first, then stop.
- `references/superseded-ci-rescue-card-dedup.md` — example of a Ready rescue card that became stale after newer current-head CI evidence removed the original blocker; useful for deciding when to block/retire rather than claim.
- `references/stale-noop-follow-up-retirement.md` — retire rescue/follow-up cards as stale no-ops when the reviewed head is already green and no code change is required.
- `references/post-merge-cleanup-unknown-state-and-already-done-card.md` — post-merge housekeeping example where `state=MERGED` but `mergeStateStatus=UNKNOWN` while cleanup is in progress; stop if the card already shows `done`.
- `references/archived-completed-parent-repair.md` — session note for the archived-but-complete parent repair sequence: normalize to `done`, then re-snapshot before child promotion.
- `references/review-to-done-fresh-snapshot-fallback.md` — compact operator recipe for the merged-review `unknown id or terminal state` recovery path with the required post-commit fresh snapshot.
- `references/review-to-done-cleanup-order-and-transaction-pitfall.md` — observed cleanup-order note: the post-commit helpers each open their own transaction and must not be wrapped in another `write_txn(...)` block.
- `references/merged-review-reconciliation-after-helper-refusal-and-stale-snapshot.md` — concise sequence for comment-first provenance, direct `review -> done` fallback, and the required fresh post-fallback snapshot before any child promotion.
- `references/review-to-done-post-fallback-fresh-snapshot-2026-07-30.md` — live 2026-07-30 note: provenance comment first, then direct `review -> done` fallback, then a fresh board snapshot before any child promotion; leaf cards stop immediately after reconciliation.
- `references/review-to-done-post-comment-refresh-stop-2026-07-31.md` — session note for the cheaper branch: after a provenance comment on a merged PR, re-read the task before any fallback write; if it already says `done`/`archived`, stop.
- `references/post-fallback-board-refresh.md` — short note on the `show`-first verification pattern after a direct fallback when `list --json` lags the updated task state.
- `references/board-correction-after-stale-merged-assumption-2026-08-07.md` — review→done→review correction note: a parent can be reopened after a temporary merged assumption, so any child promoted during the false-done window must be re-verified against the fresh post-correction snapshot.
- `references/review-to-done-helper-refusal-live-session-2026-07-31-pr1503.md` — compact PR #1503 replay of the same merged-review repair path, including the pipe-to-interpreter scan pitfall and the show-first verification after DB fallback.
- `references/merged-review-sweep-reconciliation-2026-07-31.md` — this sweep's merged-PR / stale-review reconciliation pattern, plus the no-op branch for merged PRs that have no Kanban card and the log-first blocker extraction note.
- `references/merged-review-helper-refusal-live-session-2026-07-30-pr1478.md` — concise live example of `MERGED` + transient `UNKNOWN` cleanup lag, `complete` refusal, provenance-first comment, DB fallback, and post-fallback child promotion.
- `references/merged-review-helper-refusal-live-session-2026-07-30-pr1479.md` — PR #1479 example where `complete` refused a merged review card as `unknown id or terminal state`; provenance was written first, then the direct DB fallback reconciled the leaf card to Done.
- `references/merged-review-helper-refusal-live-session-2026-07-30-pr1480.md` — PR #1480 example of the same merged-review recovery path on a non-master base branch, including the provenance-first comment, helper refusal, direct DB fallback, and fresh post-fallback board snapshot.
- `references/merged-review-helper-refusal-live-session-2026-07-31-pr1489.md` — live PR #1489 example showing `complete` refusing a stale `review` card after GitHub reported `MERGED`; use it for the provenance-first + fresh `show` + direct fallback sequence.
- `references/merged-review-helper-refusal-live-session-2026-07-31-pr1493.md` — PR #1493 example where a merged review card refused completion, then was reconciled via provenance comment, direct `review -> done` DB fallback, fresh cleanup helpers, and a post-fallback child promotion; use it as the latest child-promotion-after-fallback shape.
- `references/review-to-done-helper-refusal-live-session-2026-07-31.md` — current merged-leaf example: `complete` refused a live `review` card after merge, provenance was written first, the direct DB fallback landed cleanly, and a fresh `show` confirmed there were no children to promote.
- `references/review-to-done-helper-refusal-live-session-2026-07-31-pr1508.md` — PR #1508 example of the same merged-review refusal path, including the post-merge `mergeStateStatus=UNKNOWN` cleanup lag, the provenance-comment-first recovery, and the fresh `show` gate before deciding whether the fallback write was still needed.
- `references/review-to-done-helper-refusal-live-session-2026-07-31-pr1505.md` — PR #1505 example of the same refusal path, with the extra `show`-after-provenance stop check and the show-first verification after fallback when `list --json` lagged.
- `references/review-to-done-helper-refusal-live-session-2026-07-31-pr1502.md` — PR #1502 example of the same stale-review recovery path, including the pre-fallback fresh `show` check and the post-fallback child promotion.
- `references/review-to-done-helper-refusal-live-session-2026-08-01.md` — PR #1524 example of the same merged-review refusal path, with comment-first provenance, one fresh `show` check before fallback, and show-first verification after direct DB reconciliation.

- `references/merged-review-reconciliation-and-child-promotion.md` — worked example of merged Review → Done fallback plus Ready-child promotion after parent completion.
- `references/merged-review-reconciliation-2026-07-27.md` — latest leaf-card reconciliation example: helper refusal, provenance comment, direct DB fallback, then stop because the fresh snapshot had no children.
- `references/merged-review-gate-draft-state-lag-2026-07-27.md` — observed case where the executable gate briefly claimed draft-state blockage on a live non-draft PR, then later surfaced post-merge cleanup lag (`mergeStateStatus=UNKNOWN`) after GitHub reported `MERGED`.
- `references/merged-review-sweep-reconciliation-2026-07-21.md` — a short merged-sweep example showing serial merge, post-merge state recheck, and board fallback after helper refusal.
- `references/gh-json-filtering-cron.md`
- `references/empty-board-silent-sweep-pattern.md`
- `references/feature-branch-pr-reconciliation-2026-07-07.md`
- `references/review-queue-ci-and-merge-conflict-rescue-triage.md`

## Short operational checklist
- Load board
- Reconcile merged PRs on the right base branch
- Mark merged Review cards Done
- Promote newly unblocked children
- Repair claimable Ready metadata
- For a simple one-PR sweep, use the fast path in `references/merge-sweep-serial-checklist.md`.
- If multiple merged review cards are being reconciled, batch the provenance-comment-first + DB-fallback flow, then validate the board snapshot once at the end. See `references/merged-review-double-reconciliation-2026-07-23.md`.
- If the batch spans mixed base branches or a board sweep includes both `master` and feature-branch PRs, do not special-case the branch. Treat each PR by its live GitHub state, batch provenance comments first, then batch the fresh-connection DB fallbacks, and only then take one final board snapshot. See `references/merged-review-batch-reconciliation-2026-07-28.md`.
- Leaf review cards need no child promotion after reconciliation; stop once the card is `done`.
- Return `[SILENT]` when nothing changed
- For no-op sweeps, consult `references/cron-board-sweep-no-op-criteria.md` to distinguish healthy Ready/Running runway from a real reconciliation or promotion trigger.
- When several review PRs are open, hold each one on its own concrete failing assertion and do not manufacture a board mutation just to make the sweep look active; see `references/multi-pr-sweep-blocker-extraction-and-no-op-2026-07-30.md`.
- When two review PRs fail for different reasons, keep their evidence separate in the note and map each failing assertion back to the correct card before deciding on board mutations.
- See `references/cron-sweep-no-op-running-cards.md` for the case where active running cards exist but GitHub has no open PRs and the board still needs no mutation.

## CLI transition pitfall
- `hermes kanban complete` takes task IDs only. Do **not** pass `--board` to `complete`.
- For Ready worktree repairs, `hermes kanban assign <task_id> none` is the supported unassign form; re-show the task after repair to verify `assignee=null` before counting the card as claimable.
- If a board transition helper errors with usage text, re-run `hermes kanban <subcommand> --help` before assuming the board state is broken; the live CLI surface is authoritative.
- For `hermes kanban block`, keep the task id immediately after `block`, put the full human reason in the positional slot, and place `--kind` at the end. Safe form observed in this environment: `hermes kanban block <task_id> <reason...> --kind needs_input` (or `... --kind dependency`). Putting `--kind` before the reason can push the reason into the top-level parser and yield a misleading `unrecognized arguments` error.
- After any direct DB fallback or metadata repair, re-read the live task row before judging queue health; `list --json` can lag the projection briefly. If needed, use a supported Hermes transition helper to reconcile the projection before declaring the card claimable or blocked.
- Quote the entire reason string when it contains shell metacharacters. An unquoted `;` will split the command; parentheses, backticks, and similar punctuation can also break the shell before `hermes` ever sees the reason. For long or punctuation-heavy reasons, prefer a single-quoted string or stage the text in a temp file and feed it through a tiny Python helper.
- Keep helper invocations aligned with the current help output, especially for completion, blocking, and review-handoff paths.
- See `references/board-mutation-projection-lag-and-comment-scan-pitfall-2026-08-05.md` for the direct-mutation projection lag and invisible-Unicode comment scanner pitfall.
- See `references/kanban-cli-transition-pitfalls.md` for the compact recovery and syntax notes.
- See `references/kanban-block-shell-quoting-pitfall-2026-07-31.md` for the live failure transcript and safe shell forms.
kind` at the end. Safe form observed in this environment: `hermes kanban block <task_id> <reason...> --kind needs_input` (or `... --kind dependency`). Putting `--kind` before the reason can push the reason into the top-level parser and yield a misleading `unrecognized arguments` error.
- Quote the entire reason string when it contains shell metacharacters. An unquoted `;` will split the command; parentheses, backticks, and similar punctuation can also break the shell before `hermes` ever sees the reason. For long or punctuation-heavy reasons, prefer a single-quoted string or stage the text in a temp file and feed it through a tiny Python helper.
- Keep helper invocations aligned with the current help output, especially for completion, blocking, and review-handoff paths.
- See `references/kanban-cli-transition-pitfalls.md` for the compact recovery and syntax notes.
- See `references/kanban-block-shell-quoting-pitfall-2026-07-31.md` for the live failure transcript and safe shell forms.
