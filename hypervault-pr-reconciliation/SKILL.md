---
name: hypervault-pr-reconciliation
description: Reconcile Hypervault PRs with Kanban.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, kanban, hypervault, orchestration, pull-requests]
    related_skills: [github-workflows, software-development-lifecycle]
---

# Hypervault PR Reconciliation Skill

Use this when running as the Hypervault orchestrator to sweep open PRs, verify them against the `hypervault` Hermes Kanban board, merge allowed work, and complete the mapped card.

## When to Use

- Scheduled Hypervault orchestrator PR sweep.
- Manual reconciliation of agent-authored PRs on `jplew/hypervault`.
- Post-merge Kanban completion and cleanup for Hypervault cards.

## Prerequisites

- Start from the expected canonical checkout path, but verify the live repo root before acting. If `<hypervault-repo-root>` is missing, inspect the nearby `AGENTS.md` rename note and sibling repo checkout (for example `<haft-repo-root>`) instead of failing the sweep on the historical path.
- Load and follow project `AGENTS.md`. Do not assume a repo-local `ORCHESTRATOR.md` still exists; Hypervault's control-plane policy now lives in the orchestrator profile/skills while repo-specific worker rules stay in `AGENTS.md`.
- Confirm the live GitHub repo slug before PR operations. Hypervault board sweeps may target a repo whose product/repo name has changed (for example `jplew/haft`) while the Kanban board slug remains `hypervault`; use the live repo for git/GitHub commands and keep the board slug unchanged unless the board itself has been renamed.
- Do not trust the cron prompt's historical repo slug by itself. Derive the live slug from the current checkout/remote or repo `AGENTS.md`, then run PR/API queries against that slug. If a sweep starts in `<hypervault-repo-root>` and finds a non-repo or stale checkout, immediately probe the renamed sibling checkout (currently `<haft-repo-root>`) before concluding there are no PRs to reconcile.
- Important silent-run pitfall: querying the stale historical slug (for example `jplew/hypervault`) can return a convincing empty PR list even while the real renamed repo (`jplew/haft`) has open PRs. Before deciding the sweep is silent, verify both the repo root and the remote slug from the live checkout; a clean `[]` on the wrong slug is not evidence of no work.
- Use GitHub as PR/branch transport only; Hermes Kanban board `hypervault` is the task source of truth.

## Pre-PR board reconciliation

Before listing PRs, inspect board state. Worker comments are not state transitions on their own; the orchestrator must reconcile them.

1. List current board lanes:
   ```bash
   hermes kanban --board hypervault stats
   hermes kanban --board hypervault list --status ready
   hermes kanban --board hypervault list --status running
   hermes kanban --board hypervault list --status review
   hermes kanban --board hypervault list --status done
   hermes kanban --board hypervault list --status blocked
   ```
2. **Ready card with stale preassignment?** If a Ready card is intended for external-worker self-claim, has `workspace_kind=worktree`, and already has valid branch metadata, clear any leftover assignee before you count it as healthy runway. Hypervault workers are expected to self-assign on claim; a stale assignee on a Ready card is queue debt, not capacity.
   ```bash
   hermes kanban --board hypervault show <task_id>
   hermes kanban --board hypervault assign <task_id> none
   hermes kanban --board hypervault comment <task_id> --author "Hermes orchestrator" "READY hygiene: cleared stale preassignment so external workers can self-claim this worktree card. Branch metadata verified: <branch>."
   ```
   Do this only after confirming the card is truly still `ready` and already has explicit `branch_name`. If `branch_name` is missing, repair that first or move the card back out of Ready.
3. **Ready card with a fresh external worker claim comment?** If a Ready card has a comment that names the agent, branch, worktree, and start time but is still in Ready, assign the worker id and claim it so it moves to running/In Progress:
   ```bash
   hermes kanban --board hypervault assign <task_id> <worker-id>
   hermes kanban --board hypervault claim <task_id> --ttl 7200
   hermes kanban --board hypervault comment <task_id> --author "Hermes orchestrator" "Reconciled Ready -> running from worker claim comment."
   ```
4. **Running card with a fresh worker handoff/PR?** If a running card has a comment with an open PR URL plus provenance/verification details, reconcile it into Review before deeper PR handling:
   ```bash
   hermes kanban --board hypervault comment <task_id> --author "Hermes orchestrator" "Reconciled running -> Review: <PR URL>"
   ```
   The board may not enforce a `running -> review` transition; orchestrator comments document the reconciliation.
4. **Done-column hygiene.** Archive Done cards older than 48 hours. Report the archive pass only when cards were actually archived or an archive attempt failed. If the Done lane is large, do not rely on a giant `hermes kanban list --status done` scrollback to decide age. Query the live board DB for `status='done'` rows whose `completed_at` is older than the 48-hour cutoff, write the task ids to a temp file, then batch `hermes kanban --board hypervault archive` over those ids. Re-query afterward to confirm `remaining_old_done = 0`.

## Ready-buffer stewardship

After PR handling, check board stats and the ready/running/blocked/review lanes. Maintain a small Ready buffer sized to active worker lanes — for Hypervault, target **2 implementation cards plus 1 low-risk planning/spec card**.

- If Ready falls below target, split or promote safe dependency-satisfied cards immediately.
- If the roadmap/todo/scheduled pipeline is exhausted or blocked by a real decision/risk, alert JP with the exact blocker and decision needed.
- Do not invent speculative cards. Prefer deriving the next narrow slice from repo planning docs, follow-up sections, or accepted contracts.
- Do not count tracker/umbrella cards or debug-intake cards as healthy refill material just because they already exist in Scheduled. If a Scheduled card is explicitly a lane marker, broad intake, or otherwise not yet a bounded executable slice, leave it parked and report that it is reserve context rather than real runway.
- If the only obvious Scheduled follow-on is in the same sensitive auth/production lane as an already-open Review card or policy-held PR, it is acceptable to leave Ready below target rather than promoting overlapping same-lane work just to hit the numeric buffer.
- Prefer diversification when a green-but-sensitive PR is on policy hold. If Ready would otherwise collapse to one auth/session follow-on card while an auth/access-control PR remains in Review, promote an already-existing low-collision card from another lane (for example boundary/docs drift-guard or smoke/audit coverage) before promoting more same-lane auth follow-ons. Record the reason in the unblock note so workers understand the refill was intentional queue shaping, not a silent priority change.
- A queue can also be truthfully exhausted because the remaining root cause is **operator work, not agent code**. Example shape: a bug-intake card whose code splits all merged, leaving only a live credential/bucket-policy denial (for example Cloudflare R2 `AccessDenied` on the configured remote-publish target). Do not manufacture an agent card for credential rotation or live provider-policy debugging. Leave the intake in Scheduled as tracking context, note on the card which splits landed, and report the exhausted queue as a decision for JP: (a) operator resolves the credential/policy issue, (b) unblocks a human-gated lane (for example design signoff), or (c) the sprint planner cuts new slices. Framing it as an explicit decision menu is better than either silent emptiness or fake runway.\n- When deciding whether to refill from Scheduled, audit each candidate against the **current open review set**, not just its title/epic. Leave Ready empty when the concrete next cards are blocked for different reasons such as: (a) direct dependency on an auth/session PR still in Review, (b) same-surface file collision with a conflicted review PR (for example shared `admin-dashboard` / `app.ts` / route-test files), or (c) unresolved predecessor contract work in the same production evidence lane. In the report, name the blocked candidate cards and give the per-card rationale instead of vaguely saying the queue is "not safe to refill."

## Procedure

1. Inspect repository and policy context:
   ```bash
   git status --short --branch
   gh pr list --repo jplew/haft --state open --json number,title,url,headRefName,baseRefName,isDraft,mergeable,mergeStateStatus,body
   ```
2. If no open PRs exist, do not stop at the PR list alone. Also check for board inconsistencies that still make the sweep non-silent: stranded `review` cards, malformed `ready` worktree cards, and executable `done` cards missing completion metadata such as `result` or `completed_at`. If none of those exist and no reconciliation, archive, or buffer action happened, return exactly `[SILENT]`. Otherwise produce a concise action report.
   - **Externally merged review cards.** An empty open-PR list with live `review` cards often means JP merged the PRs directly (for example, resolving an earlier policy hold via human review). Check `gh pr list --state all --limit 8` plus `gh pr view <n> --json state,mergedAt,mergeCommit,mergedBy` for each review card's PR URL. If merged: run ONE aggregated post-merge verification bundle on a detached worktree from updated `origin/master` (it already contains all the merges — the focused tests from all merged cards can run together), then complete each card with its own PR URL + merge commit, citing the shared bundle. A human merge on a previously policy-held PR is the hold resolving as designed, not an anomaly; say plainly in the report that the merge was performed by the human reviewer, not this sweep. Cleanup still applies: worker task worktrees under `.worktrees/<task-id>` and local branches remain after external merges and must be removed by the sweep; expect `git push origin --delete` to fail with `remote ref does not exist` because GitHub auto-deleted the head branch — that is success, not a blocker.
3. For each non-draft PR, map it to exactly one Kanban card from the title/body/provenance. Prefer the internal task id from the PR body (for example `t_...`):
   ```bash
   hermes kanban --board hypervault show <task-id>
   ```
4. Fetch and inspect the actual diff before trusting the PR summary:
   ```bash
   git fetch origin master <headRefName>
   git diff --stat origin/master...origin/<headRefName>
   git diff --name-status origin/master...origin/<headRefName>
   git diff origin/master...origin/<headRefName> -- <changed-paths>
   ```
5. Apply `ORCHESTRATOR.md`/policy autonomous-merge and mandatory-human-review gates. Docs-only deployment/security plans that explicitly perform no deployment, publishing, credential, auth, or runtime-exposure changes may be auto-merged if all other gates pass.
   - Before merging, re-query `gh pr view --json statusCheckRollup,mergeable,mergeStateStatus` and wait for any still-`IN_PROGRESS` checks to reach a terminal state. Do not merge on a partially-green rollup just because the main `bun test · typecheck · build` lane already passed; Hypervault/Haft PRs can still have a trailing browser/axe check finishing after the main lane.
6. Verify on the PR worktree/branch:
   ```bash
   git diff --check origin/master...HEAD
   bun run test
   bun run typecheck
   bun run build
   ```
   If tests fail only because dependencies are missing in a fresh worktree (`Cannot find package 'elysia'`, `zod`, React, `@types/bun`, etc.), run `bun install` in that worktree and rerun the required verification.
7. Merge from the canonical `main` checkout, not the feature worktree:
   ```bash
   gh pr merge <number> --repo jplew/hypervault --squash --delete-branch --subject "HV-XXX: <title>" --body "Implements HV-XXX."
   gh pr view <number> --repo jplew/hypervault --json state,mergedAt,mergeCommit,url,headRefName
   ```
   If `merge` exits non-zero, still query `gh pr view`; the server-side merge may have succeeded while local branch cleanup failed.
8. After a confirmed merge, run a post-merge smoke check on updated `master`. If the canonical checkout has intentional local-only drift or uncommitted operator changes, verify in a temporary detached worktree from `origin/master` instead of forcing the canonical checkout to fast-forward:
   ```bash
   git fetch origin master
   git worktree add --detach /tmp/hypervault-postmerge-<pr> origin/master
   cd /tmp/hypervault-postmerge-<pr>
   bun test ./tests/server-route-composition.test.ts ./tests/embed-editor-routes.test.ts ./tests/public-admin-route-boundary.test.ts
   bun run typecheck
   bun run build
   git diff --check HEAD~1..HEAD
   cd <hypervault-repo-root>
   git worktree remove /tmp/hypervault-postmerge-<pr> --force
   ```
   If the fresh temporary worktree fails only because dependencies are missing, run `bun install` there and rerun the intended verification suite before treating it as a code failure. If the first verification attempt aborts before cleanup, remove the temp worktree explicitly in a separate guarded step before recreating it.
 If `git worktree add` says the temp path is "missing but already registered", treat that as leftover worktree metadata rather than a merge blocker: run `git worktree remove <path> --force` (or `git worktree prune` if needed), then recreate the detached verification worktree and rerun the post-merge bundle.
 When using Hermes `terminal()` for this step, keep `workdir` on an existing repo path (for example the canonical checkout) and `cd` into the temp worktree **after** `git worktree add` succeeds. Do not set the tool workdir to `/tmp/<repo>-postmerge-<pr>` before it exists, or the command fails before the worktree is created.
 9. Complete the Kanban card with PR URL, merge commit SHA, and exact verification commands. `hermes kanban complete` does not accept `--comment`; use `--result`/`--metadata`, then add a separate comment:
   ```bash
   hermes kanban --board hypervault complete <task-id> \
     --result "Merged PR #N. Merge commit <sha>. Verification: ..." \
     --metadata '{"pr_url":"...","merge_commit":"...","verification":["git diff --check pass","bun run test pass","bun run typecheck pass","bun run build pass"]}'
   hermes kanban --board hypervault comment <task-id> --author "Hermes orchestrator" "Reconciled and merged ..."
   ```
   If `complete` reports `cannot complete <task-id> (unknown id or terminal state)` but `hermes kanban show <task-id>` still shows a live `review` card, treat that as the known stranded-review bug rather than as a true missing task. Re-check the card first, then use the DB recovery path to set `status='done'`, populate `completed_at` and `result`, clear claim fields, and insert a `task_events` status record carrying the merge metadata.
10. Clean up only after the PR is confirmed merged. Branch cleanup may fail because the branch is checked out in a worktree; remove the worktree first, then delete the local branch, and delete the remote branch if `gh` did not remove it:
    ```bash
    # Prefer the actual registered worktree path from `git worktree list --porcelain`.
    # Current Hypervault cards default to <hypervault-repo-root>/.worktrees/<task-id>.
    # Older cards may still point at legacy sibling worktrees from earlier hosts/layouts.
    git worktree remove <actual-worktree-path>
    git branch -D <headRefName>
    git push origin --delete <headRefName>
    git fetch --prune origin
    ```
    If you verify remote-branch absence with `gh api repos/<owner>/<repo>/git/refs/heads/<headRefName>` and receive HTTP 404, treat that as successful cleanup rather than a blocker. Keep that ref check separate or guarded in shell command chains so the expected 404 does not make an otherwise-successful cleanup step look failed.
11. Query open PRs again before final reporting.

## Pitfalls

- In mixed sweeps, you may have both a freshly mergeable PR and an older `review` card whose PR already landed earlier. It is acceptable to run one truthful aggregated post-merge verification bundle on the final updated `origin/master` detached worktree and cite that same bundle across both the newly merged card and the stale merged-review completion, while keeping each card's own PR URL and merge commit distinct.
- If that detached post-merge verification worktree fails only because dependencies are missing, run `bun install --frozen-lockfile` there and rerun the intended focused bundle before treating it as a code problem. Capture the install step as setup recovery in the completion note rather than reporting a false regression.
- When the worker opens a docs-only or provenance-only PR for an artifact-delivery card whose real deliverable lives outside git (for example a mockup image placed in the local Haft vault), verify the actual artifact directly: confirm the final path exists, compare hash and byte count against the reported generation artifact, check the file signature/dimensions when applicable, complete the Kanban card from that evidence, and close the PR unmerged instead of merging handoff notes just to satisfy process.
- Common Haft variant of that pattern: the PR adds only a repo-side diagnosis/provenance markdown file while the real deliverable is a local-vault artifact under `~/.haft/vaults/default/...`. In that case, treat the vault artifact as the product deliverable and the PR branch as transport-only. Verify the vault file directly (`test -f`, `sha256sum`, `file`, and byte count; include dimensions for images when available), post a short PR comment explaining that the artifact was verified outside git, close the PR unmerged, mark the board card Done from the artifact evidence, then remove the now-unneeded worktree/branch if safe.
- When the remaining unresolved review card is a production/auth/public-boundary policy slice, do not refill Ready just to keep the queue non-empty with later same-lane follow-ons. It is correct to leave Ready empty and report that refill was intentionally skipped to avoid overlap until the sensitive review item resolves.
- Follow-on queue nuance: even if Ready has dropped below the nominal buffer target, do not promote a scheduled card that shares the same concrete file/surface collision as an already-open conflicted review PR. Example shape: a scheduled admin-dashboard follow-on while another review PR is already DIRTY in `apps/server/src/routes/admin-dashboard-providers.ts`, `apps/server/src/routes/app.ts`, and `tests/admin-dashboard-route.test.ts`. In that case, keep the smaller truthful Ready set and report the collision rationale instead of manufacturing parallel runway in the same surface.
- Stronger same-lane hygiene: if a card is **already in Ready** and a newly reviewed/conflicted PR proves that the Ready card overlaps the same concrete lane (for example the same UI/test files in a remote-publish flow), do not leave the Ready card in place just because it was previously promoted. Move it back to `scheduled`, preserve worker-neutral branch metadata, and add a short comment explaining that Ready was intentionally reduced to avoid colliding worktree runway while the review PR is refreshed or resolved.
- Policy-hold communication nuance: when a PR is green and mergeable but held solely because it touches auth/session/access-control policy surfaces, leave an explicit note on both the PR and the mapped Kanban card that this is a **policy hold**, not a request for more worker refresh. Say plainly that no additional implementation work is being requested unless scope changes or human review finds an issue.
- Remote-publish/upload policy-hold nuance: a PR that only improves sanitized remote-publish error classification or provider-denial UI can be technically clean and fully green, but it still changes upload/provider-denial handling. Treat that as inside the repo's upload/risk-gate surface for unattended sweeps. Verify it normally, reconcile the card to Review if needed, and leave a PR + Kanban policy-hold note instead of auto-merging. Phrase it as “policy hold, not a worker fix request.”
- CLI pitfall: `hermes kanban schedule` takes the reason as a positional argument (`hermes kanban --board <board> schedule <task-id> "<reason>"`), not `--reason`. If you try the flag form during queue hygiene, the command fails and the Ready card remains misleadingly live. Use the positional reason form, then optionally add a second explicit comment when you want a shorter operator-facing explanation alongside the schedule event.

- A local branch may fail to delete because it is still checked out in a worktree. Remove the worktree first, delete the local branch, then explicitly `git push origin --delete <headRefName>` if the remote branch remains. After a local `git branch -D` on a squashed branch, git may warn that the branch is not fully merged; that warning is safe once `gh pr view` confirms the PR is merged.
- `hermes kanban complete <task-id>` does **not** accept `--comment`. If you pass one, the CLI rejects it with `unrecognized arguments`. Use `--result` and `--metadata` for the completion record, then call `hermes kanban comment` separately.
- When doing DB-backed board hygiene or reconciliation queries, use the live per-board database path under `~/.hermes/kanban/boards/<board>/kanban.db` after confirming the schema, not the generic top-level `~/.hermes/kanban/kanban.db`. The top-level file may exist but be empty or not contain the board tables you expect, which can produce false `no such table` / empty-result diagnostics.
- A **claim comment alone is not a claim**. If a Ready card has a fresh external worker claim comment (agent/branch/worktree/start time) but is still in Ready, the orchestrator must assign + claim it before treating it as In Progress.
- A **running card with a PR handoff body/comment is not in Review** until the orchestrator reconciles it. Move it to Review before running full PR verification.
- Review-handoff race nuance: if the review-handoff helper or reconciliation command returns an error like `task <id> is review, expected running`, immediately re-query `hermes kanban show <id>`. A worker may have completed the fallback transition between your earlier read and your helper call. If the card is already `review`, do not retry state mutation or report failure; continue with PR review/hold/merge and add only the necessary policy/result comment.
- `gh pr diff --stat` may not support all flags. Fetch the PR branch and use plain `git diff` for stats/name-status/patch inspection.
- Fresh worktrees may lack Bun dependencies even when the canonical checkout has them. Install and rerun before treating missing packages as code failures.
- When a failing CI log reports only a Bun test suite name / test title (for example `dynamic Bun API app`) rather than the source file path, do not guess the filename from memory. Search the repo for the failing test title text first, then rerun the actual file you found. This prevents false no-match reruns like `bun test ./tests/<guessed-name>.test.ts` when the real file uses a different stem.
- Treat worker-reported verification in the PR body as unverified provenance, not merge evidence. If CI is red or a fresh head SHA appears after the worker handoff, rerun the smallest relevant focused bundle on the current PR head in an isolated review worktree. If that rerun fails on a brittle source-string assertion after a harmless refactor (for example the implementation now uses an intermediate variable and the test still expects the old inline expression), classify it as a real code/test refresh blocker: leave the PR in Review, post the exact failing test name and command on both the PR and the Kanban card, and do not wave it through as "probably fine" just because the surrounding diff looks low-risk.
- Follow-on verification pitfall: if a focused rerun passes only in the worker task worktree, check `git status --short` before trusting it. Uncommitted local edits in the same failing test files can make a red PR head look green locally. In that shape, treat the pass as non-authoritative, report the dirty-worktree evidence explicitly, and ask for a clean branch refresh / new pushed head SHA before merge consideration.
- Shell parsing pitfall: when inspecting PR JSON from `gh pr view --json ...`, do not pipe it into `python3 - <<'PY' ...` or another heredoc-fed parser. The heredoc consumes stdin, so the JSON pipe arrives empty and you get misleading `JSONDecodeError` / blank-input failures. Safe pattern: capture the CLI JSON into a shell variable or temp file first, then pass that content to `python3 -c`, `jq`, or a file-based parser.
- Do not merge PRs that change auth, credentials, public deployment, route exposure, filesystem serving, uploads/imports, workflow policy, or broad architecture without human review.
- Hypervault/Haft checkouts can carry unrelated tracked local repo-operational edits under `.hermes/skills/...` from orchestrator maintenance. If those edits do not overlap the PR paths, leave them untouched and run review/post-merge verification in the task worktree or a detached review worktree instead of force-cleaning the canonical checkout.
- Follow-on checkout-drift nuance: the canonical checkout can also be both **behind `origin/master`** and intentionally dirty with unrelated tracked changes. In that shape, do not force a `git pull --ff-only` just to make post-merge verification look local-current. Server-side merge the PRs, fetch the updated remote branch, and run one truthful aggregated post-merge verification bundle in a detached worktree from `origin/master`. Report that the canonical checkout was left untouched instead of implying it was synchronized locally.
- Ready-buffer rename-drift nuance: if the board still holds dependency-safe scheduled/ready worktree cards with a historical repo-root anchor (for example `<hypervault-repo-root>`) after the live checkout has moved to `<haft-repo-root>`, repair `workspace_path` to the live repo root before counting or promoting the card. Re-read the card afterward and only leave it in `ready` when `assignee=null`, `branch_name` is explicit, and the updated repo-root anchor is stored.
- Important Hypervault/Haft worktree-anchor nuance: a `workspace_kind=worktree` card may intentionally show the repo-root anchor (for example `<haft-repo-root>`) before a worker claims it; Hermes materializes the actual task worktree later under `.worktrees/<task-id>`. Do **not** treat the repo-root anchor alone as a Ready claimability defect. The defect is a stale historical anchor, missing `branch_name`, or non-null preassignment — not the fact that the stored path is the repo root.
- Do not mark a card Done from an agent self-report. Complete it only after real verification and a confirmed merge commit.
- The silence token `[SILENT]` is only for runs where **nothing changed**: no open PRs, no board reconciliations, no archive events, no buffer moves. If any PR or board state changed, report actions.

## References

- `references/hypervault-orchestrator-sweep-checklist.md` — printable checklist for each scheduled sweep.

## Verification

A successful reconciliation report should include:

- PR number/URL and mapped Kanban card.
- Merge commit SHA.
- Diff scope summary.
- Exact verification commands and pass/fail results.
- Any setup recovery, such as `bun install` after missing dependencies.
- Cleanup performed and remaining blockers, if any.
