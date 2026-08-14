---
name: workflow-alert-board-reconciliation
description: Reconcile GitHub workflow failure alerts against live PR state and board ownership so recovered, merged, or already-tracked failures do not spawn duplicate rescue work.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, github-actions, kanban, triage, alerts, reconciliation]
    triggers:
      - "A GitHub email says a PR workflow failed"
      - "A failed workflow alert arrives after the PR already merged"
      - "Need to decide whether a failing run needs a new board card or just evidence on an existing one"
---

# Workflow Alert Board Reconciliation

## When to use

Use this when the input is a workflow failure alert tied to a PR or branch and you must decide whether it represents:

- an active new failure needing new ownership,
- a failure already covered by an existing rescue card,
- a recovered/transient attempt, or
- a failure attached to a PR that already merged.

This skill is for keeping the board truthful and non-duplicative.

## Core rule

A workflow alert is evidence that a run failed. It is **not** automatically evidence that you need a new fix card.

### Read-only notification-inbox rule

When an alert arrived through a read-only operational inbox—especially automated `notifications@github.com` mail—use it only as triage input. Record the evidence in the live PR and Kanban surfaces; **never reply to the notification address**, even if the chat adapter presents the thread as reply-capable.

**Auto-threaded adapter safeguard:** Some email adapters treat any natural-language assistant output in the inbound thread—including progress acknowledgements, steering notices, or a normal final summary—as a threaded outbound reply. For read-only automated alert senders, perform tool work without user-facing prose and finish with exactly `[SILENT]`; do not call an outbound email tool. If the adapter reports a rejected outbound attempt, do not retry that address or explain the failure in-thread; preserve the operational result in the relevant Kanban record instead.

Always prove three things before creating work:

1. the live PR/run state,
2. the exact failing job/spec/assertion, and
3. whether that failure is already owned somewhere on the board.

## Required sequence

1. Query the PR live state.
   - Capture PR URL, state (`OPEN`/`MERGED`/`CLOSED`), merge time if merged, merge commit, head branch, and head SHA.
2. Query the failing run live state.
   - Capture run URL, workflow name, conclusion, head SHA, and job list.
3. Identify the narrow failing surface.
   - Prefer the exact job name, test file, assertion, or failing step over a generic "E2E failed" summary.
   - For a pre-test policy gate (dependency/security audit, architecture ratchet, generated-file check), capture the exact threshold, observed result, and every downstream phase skipped because of it. Do not call skipped tests, typecheck, or build failures, and do not retry a deterministic policy violation as if it were a flaky test.
4. Check board ownership.
   - Search for the source card mapped to the PR.
   - Search for an existing rescue/regression card that already names the same failing surface.
   - Search **running and blocked cards, not just Ready**: a concurrent sweep may have created and claimed the owning card minutes earlier, and a Ready-only search misses a just-claimed owner. If an owner already exists, verify it is still claimable/healthy (e.g. `haft_ready_worktree_card.py validate <task_id>` for Haft worktree cards) and add attribution evidence instead of creating work.
5. Decide the action:
   - **Already tracked failure** → add evidence comments only; do not create duplicate work.
   - **Recovered/transient** → annotate the source card and stop unless a narrower reliability follow-up is warranted.
   - **New unmapped failure** → create a focused rescue card with exact failure evidence.

## Merged-PR rule

If the PR is already merged when you investigate, do **not** assume the merged feature introduced a new distinct bug.

Instead:

1. verify the exact failing spec/job;
2. compare it to existing board rescue work;
3. if it matches an existing rescue card, treat the new run as additional evidence for that card;
4. annotate the merged source card so later sweeps do not generate duplicate fix tickets.

Good pattern:

> PR #N is already merged. The alerting run failed in spec X. Spec X is already owned by rescue card T. Add the new run URL / SHA / assertion to T and note on the source card that the alert maps to T.

### When the merged PR has no source board card

Sometimes the merged PR was direct work and the PR body or provenance explicitly says there is **no source card**.

In that case:

1. still verify live run state, attempt count, and exact failing surface first;
2. if the failure is already owned elsewhere, add evidence to that owning card and stop;
3. if the failure is **not** already owned and the run is still red, create **one narrow new rescue/reliability card** for the actual failure class instead of inventing a retrospective source card;
4. in the new card body, record explicitly that the source card is `none` and cite the PR URL, run URL, merge SHA, and why the failure was classified as CI/reliability vs. product regression.

Good pattern:

> PR #N is merged and had no board card. The latest master run is still red, all jobs share the same runner-disconnect annotation, and no existing rescue card owns that failure class. Create one narrow CI-reliability card, record `source card: none`, and keep the merged PR out of scope.

### When the open PR has no source board card

Sometimes the alerting PR is still **open**, but it is direct operator/release work and the PR body or provenance explicitly says there is **no source card**.

In that case:

1. verify the live PR state, run state, attempt count, and exact failing surface first;
2. do **not** invent a retrospective implementation/review source card just to satisfy the board model;
3. if an existing rescue/reliability card already owns the same failing surface, add evidence there and stop;
4. if the latest run is still red and the failure is not already owned, create **one narrow rescue/reliability card** for the actual blocker;
5. in that new card body, record explicitly that the source card is `none`, cite the PR URL, run URL, head SHA, and whether the evidence currently points to CI/reliability or a concrete product regression;
6. if the evidence is only a runner-disconnect annotation or similarly incomplete CI signal, keep the card scoped to truthful re-verification/recovery rather than claiming a product bug up front.

Good pattern:

> PR #N is still open, but it was direct operator release work with no board card. The alerting E2E run is red, the failed job only shows a self-hosted runner disconnect annotation, and no existing rescue card owns that live blocker. Create one narrow rescue card, record `source card: none`, preserve the run URL/head SHA/annotation, and scope the work to re-verifying the live blocker before any product-regression claim.

### Open release/version-bump PR with an off-diff timeout that recovers on rerun

Sometimes the alerting PR is an open release/operator PR with **no source board card**, the diff is only a version bump or similarly trivial release metadata, and attempt 1 fails in an off-diff CI test timeout.

In that case:

1. verify the PR diff is truly release-scoped/off-diff for the failing test surface;
2. capture the exact failing job, test name, and timeout/assertion from attempt 1;
3. rerun the failed job(s) on the **same run** before creating board work. For one job, use `gh run rerun --repo <owner>/<repo> --job <job-id>`; this command accepts either a positional run id or `--job`, not both;
4. capture the new run attempt and job conclusions before classifying the incident;
5. if the rerun recovers green and no other workflow remains red, classify the alert as recovered/transient evidence and **do not** create a rescue card;
6. **Rerun-refused fallback:** GitHub can reject a failed-job rerun (for example, `run <id> cannot be rerun; its workflow file may be broken`). Record the exact refusal; it is not a product diagnosis. Re-query the current PR head and run the exact failing spec at least twice on that head in the PR worktree. If the failure is off-diff and those repetitions pass but no fresh GitHub verification can be triggered, leave the source card in Review and create at most one narrow CI/reliability investigation card. Require it to cite the run/job URL, assertion, head SHA, local repetitions, and rerun refusal—and explicitly forbid blind timeout increases, skips, or unrelated feature edits.
7. if local reproduction is attempted from the operator host and fails for host-state reasons (for example disk pressure), treat that local failure as non-authoritative context unless it matches the GitHub runner failure class.

Good pattern:

> PR #N is an open release/version-bump PR with no source card. Attempt 1 timed out in an auth/session test that the PR did not touch. The failed CI job was rerun on the same run and recovered green, paired workflows are green, and no live blocker remains. Record the recovery and stop without creating a board card.

## Comment pattern

See also `references/open-pr-multi-failure-separate-rescue-ownership.md` for the pattern where one open PR run contains multiple distinct blocker classes that should stay split across rescue cards.
See also `references/open-pr-multi-workflow-single-blocker.md` for the inverse pattern where multiple workflows on the same open PR all collapse to one exact blocker class and should map to one rescue owner.
See also `references/open-pr-off-diff-browser-failure-rerun-recovery.md` for the pattern where a concrete-looking browser assertion is off-diff, passes focused local repro in both the PR worktree and canonical checkout, and recovers green on rerun — so the source Review card stays the only owner.
See also `references/open-release-pr-off-diff-ci-timeout-rerun-recovery.md` for the pattern where an open release/version-bump PR with no source board card hits an off-diff CI timeout, the failed jobs are rerun on the same run, and the rerun recovers green — so no rescue card is created.
See also `references/merged-docs-only-off-diff-ci-timeout-rerun-recovery.md` for the post-merge variant where a docs-only or metadata-only PR triggers an off-diff master CI timeout, focused local repro on synced `master` passes, and the same-run rerun recovers green — so the source card gets evidence only and no new rescue card is created.
See also `references/single-runner-deterministic-failure-cross-runner-attribution.md` for the pattern where a deterministic single-test failure reproduces only on one runner and the owning card gets cross-runner attribution evidence (green-runner comparison plus a reproduction requirement) instead of duplicate work.
See also `references/root-runner-test-portability-divergence.md` for the pattern where a single-runner deterministic failure is actually root-execution test divergence: the runner runs as root, a permission-denial test flips behavior, and `sudo -E` repro proves it.
See `references/runner-reregistration-race-approval-label-gate.md` for the self-hosted runner quarantine race: supervisor re-registration silently restores removed labels and pre-assigned jobs still land on a quarantined runner, so label removal is not durable — the durable fix is a fail-closed approval-label selector.
See `references/repeated-watchdog-budget-admission.md` for the evidence pattern when a scheduled watchdog repeatedly fails before runner admission because GitHub Actions budget enforcement is active.

### On the source card / PR-mapped card
Record:

- the alerting run URL,
- whether the PR is open or merged,
- the exact failing job/spec,
- the owning rescue card if one already exists,
- a one-line statement that no duplicate card was created.

### On the owning rescue card
Record:

- the new run URL,
- head SHA or merge ref if relevant,
- the exact failing assertion or step,
- a one-line statement that this is additional evidence, not a new failure class.

## Create a new card only when

Create a fresh rescue card only if at least one is true:

- the failing surface is genuinely new,
- the existing card covers a different failure class,
- ownership should move to a different lane,
- or the new failure occurs on a different post-merge/base-branch surface than the existing rescue work.

### Multiple distinct failures on the same open PR

Sometimes one alerting PR run exposes **more than one real failure class at once**.

Example shape:

- the source implementation card is already in `review` with an open PR,
- one browser/E2E failure class is already owned by an existing rescue card,
- the same latest run also shows a separate policy/build failure on the same head SHA.

In that case:

1. keep the source review card as the PR anchor;
2. keep the existing rescue card as the owner for the already-tracked failure class;
3. create **one additional narrow rescue card** only for the distinct new blocker;
4. do **not** create a broad replacement card that re-owns the already-tracked browser failures;
5. add reconciliation comments to the source card and both rescue cards naming:
   - PR URL,
   - run URL,
   - head SHA,
   - exact job/step/spec for each failure class,
   - which card owns which blocker.

Good pattern:

> PR #N is still open and still red. Browser failures A/B are already owned by rescue card T1. The same run also fails architecture/policy gate C on the same head SHA. Keep the source card in Review, keep T1 for A/B, and create a second narrow rescue card T2 only for C.

### Same PR, different workflows, one exact blocker class

Sometimes two different workflows on the same open PR head both fail, but they are really reporting the **same exact blocker class** rather than separate ownership slices.

Common shape:

- the source PR card is already in `review`;
- a broad CI workflow (for example an always-on browser smoke job) fails in one exact spec;
- a second workflow (for example E2E smoke) fails in that same spec or the same narrow UI/action path;
- the failing surfaces all point back to one concrete regression on the PR-owned branch.

In that case:

1. keep the source review card as the PR anchor;
2. treat the matching failures as **one blocker class**, not one rescue card per workflow;
3. create at most **one** narrow rescue card for that blocker when separate implementation ownership is still useful;
4. in the rescue card body, cite **all** live run URLs / job URLs that demonstrate the same blocker class;
5. if the source review card already owns the PR branch metadata, give the rescue card its **own** claimable branch slug and instruct the worker how to push the narrow fix back onto the source PR branch;
6. comment both cards so future sweeps can see that multiple failing workflows map to one live owner.

Good pattern:

> PR #N is in Review. `Always-on browser smoke` and `Playwright import render smoke` both fail on the same import-flow regression in the same test file on the same head SHA. Keep the source card in Review, create one narrow rescue card for the import-flow blocker, cite both runs in that card, and avoid creating separate rescue cards per workflow.

## Prior-head drift reconciliation

Open PRs can advance between alerts. A rescue card that was correct for head SHA A can become stale when the same PR moves to head SHA B and the failing surface changes.

### Alert head superseded by a newer green PR head

A common inbox-triage shape is:

- the email alert points at failed run/head **A**,
- the PR is still open,
- the author pushes a follow-up commit producing head **B** before triage finishes,
- and the latest run on **B** goes green.

In that case:

1. capture the alerting run URL and its failing head SHA;
2. query the PR live state and compare the current `headRefOid` to the alert head;
3. if the PR head advanced, inspect the latest run on the **current** head instead of treating the email's failed run as the authoritative live blocker;
4. if the newer head is green, classify the alert as recovered on the source PR lane;
5. add evidence to the source card naming both SHAs and the exact earlier failure surface;
6. do **not** create a rescue card just because the earlier head failed.

Good pattern:

> Alert run on head A failed in one exact source assertion. The PR advanced to head B with a follow-up fix, the latest CI on B is green, and the PR merge state is clean. Record the recovered earlier failure on the source card and create no separate rescue work.

When a source PR is still open and already has one or more rescue cards:

1. query the latest PR head SHA first;
2. compare the latest failing run's head SHA and exact failing surfaces against the existing rescue-card evidence;
3. if an older rescue card names failures from a prior head that no longer match the latest live blocker, do **not** keep treating it as the active owner;
4. create a new narrow rescue card for the latest head only when the current blocker is genuinely different;
5. if board policy and permissions allow, mark the stale prior-head rescue card as superseded before claim; otherwise leave an explicit reconciliation comment saying it is **historical evidence / recovered on the current head** and point it at the new card so workers do not mistake it for the live owner;
6. add a reconciliation comment on the source PR card naming:
   - latest head SHA
   - latest run URL(s)
   - new active rescue card id(s)
   - superseded or historical older rescue card id(s)

Good pattern:

> PR #N stayed open but advanced from head A to head B. The older rescue cards captured failures on A. The latest live blockers on B are different, so retire the stale Ready cards as superseded and seed new narrow cards for B instead of leaving multiple contradictory rescue cards in Ready.

### Same failure class on a newer head

Sometimes the PR advances to a newer head, but the live blocker is still the **same narrow failure class** rather than a genuinely different one — for example the same E2E spec remains red, but the exact assertion or line number shifts on the new head.

### Different failure class on a newer head

Sometimes an older rescue card for an open PR was correct for head A, but head B fails at a **different workflow phase entirely** — for example an earlier card covered a spec/assertion failure, while the newest head now dies in browser installation or another setup step before the test body starts.

In that case:

1. treat the newest-head failure class as authoritative for current ownership;
2. do **not** revive or relabel the older card just because it shares the same PR number or workflow name;
3. keep the older card archived/superseded as historical evidence if it already represents resolved prior-head work;
4. create one new narrow rescue card for the current blocker, naming the exact step/command/error;
5. on the new card, explicitly cite the older card as historical-only when helpful so workers do not mistake it for the live owner.

Good pattern:

> PR #N previously had a guides-row E2E assertion card on head A. Head B is now red earlier in `Install Playwright browser` with a `sudo` requirement before any spec runs. Keep the older card archived as prior-head history and create a new current-head rescue card for the browser-install blocker.

In that case:

1. treat the newest-head run as authoritative;
2. if an existing rescue card was written against an older head and a newer, more precise card is created for the same failure class, keep **only one Ready owner** for that blocker;
3. supersede the older-head card before claim when you can; otherwise leave an explicit reconciliation comment that it is historical evidence only and point workers at the newer card;
4. anchor the surviving rescue card to the latest head SHA, latest run URL, and latest exact assertion/log excerpt;
5. update the source PR card so it names the single current rescue card.

Good pattern:

> PR #N advanced from head A to head B. The same E2E spec is still the blocker, but the live failure detail changed on B. Close the older-head rescue card as superseded and keep only the newer-head card in Ready, so workers do not see two claimable cards for one live blocker.

### Open PR exact in-diff UI/accessibility contract failure

Sometimes the alerting run is still on an **open** PR and the failing assertion is directly explained by the PR's own UI, copy, or accessibility-contract change.

In that case:

1. verify the source PR is still open and capture the latest head SHA;
2. identify the exact failing assertion, locator, or accessible-name expectation from the live run/job logs;
3. compare that failing surface against the PR diff, not just the workflow title;
4. when practical, reproduce the narrow failing spec locally in the PR worktree;
5. if the local repro matches the live failure and the changed component/contract is in-diff, keep the **source review card** as the active owner;
6. add a reconciliation comment with the PR URL, run URL, job URL, head SHA, local repro command, and the exact in-diff contract change;
7. do **not** create a separate rescue card unless another distinct out-of-diff blocker exists.

Good pattern:

> PR #N changes a reader/article accessible name from `artifact view` to `document view`. Live E2E fails on the old accessible-name assertion, and the same narrow spec fails locally in the PR worktree. Keep the Review card as the blocker owner and treat the workflow alert as review-blocking evidence, not a new rescue lane.

See also `references/open-pr-in-diff-ui-contract-failure.md`.

### Open PR in-diff route-registry documentation drift

A route-classification registry addition or reclassification can make a route-count/documentation verification fail even when the product path is otherwise healthy. Capture the exact expected-versus-derived count, inspect the registry diff, and run the narrow verification on the exact PR SHA. When the delta matches the PR's route change, keep the source Review card as the owner and update the documentation/plan in that PR; do not create a generic CI rescue card. Evaluate any other failed jobs independently, because a passing isolated repro for an unrelated timeout or browser assertion is transient evidence rather than proof of a shared regression.

See `references/open-pr-route-registry-doc-drift.md`.

### Same run, different failure surfaces across rerun attempts on an open PR

A single workflow run can fail at one exact surface on attempt 1, then fail at a **different** exact surface on attempt 2 after rerun.

When the source PR is still open and already anchored by a source implementation/review card:

1. treat the **latest attempt** as the authoritative live blocker for ownership decisions;
2. preserve earlier-attempt failure evidence in comments, but do **not** seed separate rescue cards for superseded attempt-1 blockers unless they still reproduce on the latest attempt or are already independently owned;
3. if the latest surviving signal is still only a runner-disconnect or similar infra annotation, keep it in the CI rescue / reliability lane until a concrete blocker is proven;
4. if the latest surviving blocker is a concrete test/product failure **inside the PR diff** and the source card already owns that implementation branch/PR, keep the source card as the active owner and do **not** create a duplicate rescue card just because attempt 1 looked like infra noise;
5. if the source PR diff does not touch the latest failing surface, classify it as a narrow CI rescue / reliability lane rather than automatically broadening the source implementation scope;
6. keep the source card as the PR anchor unless a distinct outside-the-diff blocker truly needs separate ownership;
7. create at most **one** new rescue card for the latest exact blocker when no existing card already owns it and the source implementation card is not already the truthful owner;
8. in comments, explicitly distinguish:
   - attempt-1 failure surface,
   - latest-attempt failure surface,
   - which one is historical context,
   - and which one is the current live blocker.

Good pattern:

> Attempt 1 in CI and E2E both died from self-hosted runner disconnects. After rerun, CI recovered green while E2E exposed one concrete Playwright assertion inside the PR's own diff. Treat the disconnects as historical context only, keep the source PR card as the active owner, and do not seed a duplicate rescue card for the rerun-discovered in-diff failure.

## Repeated off-diff full-suite timeouts that shift across attempts

An open PR can remain red after a failed-job rerun even when each exact failed test passes in focused repro on both the PR head and clean base. If the failing test **changes between attempts**, treat that as evidence of a shared CI/full-suite reliability problem rather than a product regression in the source PR.

Required sequence:

1. Capture the attempt-specific test names, timeout thresholds, durations, run/job URLs, and unchanged PR head SHA.
2. Confirm the failing test files are outside the PR diff.
3. Run each focused file on the PR worktree and clean current base; preserve exact pass counts/results.
4. Review recent runner-capacity/serialization changes and earlier reliability cards. A merged mitigation may be insufficient for the current workload.
5. If the latest attempt remains red, keep the source Review card as the PR anchor, explicitly state that no product-fix scope is assigned from the alert, and create **one** narrow CI-reliability card for the shared full-suite/runner failure class.
6. Scope that card to contention/host-lock/capacity/shared-state diagnosis, CI-like reproduction where practical, and a clean full suite. Forbid blanket timeout increases, skipped tests, or product-semantic changes without causal evidence.
7. Do not create one rescue card per shifting timeout case. They are historical symptoms of one active reliability lane unless evidence proves distinct root causes.

Good pattern:

> Attempt 1 timed out in two Daily Notes cases; after rerunning the failed job, attempt 2 timed out in an unrelated remote-publish case. Both focused files pass on the PR worktree and clean base, and neither is in the PR diff. Keep the feature PR in Review and create one claimable CI full-suite reliability card, not a feature repair or separate card per test.

## Deterministic single-test failure that reproduces on only one runner

A required job can fail on exactly one test across every attempt of a run (e.g. 566 pass / 1 fail) while the same job runs green on other runners in the pool on master-equivalent heads. When the PR diff does not touch the failing test's surface:

1. capture the failing test, the expected-vs-received assertion diff, and every attempt/job URL that reproduces it;
2. query recent green runs of the same job and record which runner names they used (`gh api repos/<owner>/<repo>/actions/runs/<id>/jobs`);
3. if all red attempts ran on one runner and green runs used a different runner, record the failure as **single-runner-correlated so far** — evidence against a pure product regression, but not proof of a runner defect, since the test may be timing/env-sensitive;
4. add a cross-runner attribution comment to the owning rescue card requiring the worker to reproduce the exact test on a known-good runner or current master head before concluding the causal fix is product code;
5. do not fold this into a runner-image/contract card unless a preflight or setup step also failed — a suite that passed every preflight and reached governed tests has already satisfied the runner contract.

Good pattern:

> Both PR #1550 attempts failed exactly one AgentSession mirror assertion on `yogendra-build`, while the same job was green on `haft-ci-build-ca-west-1` for master-equivalent heads. All preflights passed on `yogendra-build`, so the runner contract itself is not the suspected cause. Add attribution evidence to the owning repair card and require reproduction on a known-good runner before concluding the fix is product code.

See `references/single-runner-deterministic-failure-cross-runner-attribution.md`.

### Root-execution test divergence on self-hosted runners

A deterministic single-test failure on one runner can be caused by the runner process executing as **root**, not by product code. Permission-denial tests — a test pointing a write at a deliberately missing directory and expecting an exception — pass under a normal user (write fails, exception path exercised) but fail under root, because `mkdirSync(recursive)` succeeds anywhere and no exception is raised.

Detection and repro sequence:

1. Check the job log for root-execution tells: `Copying '/root/.gitconfig'`, bun under `/root/.bun/bin`, root-owned HOME.
2. Run the exact failing test as the normal user on the canonical checkout at the same head: `bun test <file>` — record result.
3. Re-run as root: `sudo -E bun test <file>`.
4. If the root run reproduces the exact CI assertion while the normal-user run passes, the failure class is root-execution / test-portability, not a product regression. Attribute to the runner-contract lane. Durable fixes: non-root runner process (GitHub self-hosted guidance), and/or make the test uid-independent by injecting the write failure.

See `references/root-runner-test-portability-divergence.md`.

## Pre-fix PR alert: a separate repair merged while the alerting PR run was underway

A PR can fail an off-diff test on an older base while a different, focused PR for that exact failure merges during or immediately after the alerting run. Do not classify the alert as a regression in the feature PR merely because the red run is still attached to it.

Required sequence:

1. Capture the alerting run's creation/start time, PR head SHA, exact failing assertion, and run attempt.
2. Search recent merged PRs for a focused repair of that same failure surface; verify its merge time and merged head.
3. Sync the canonical checkout to current `origin/master` before using a local result as base evidence. A stale canonical checkout is not a valid comparison point.
4. Run the exact focused test on current master.
5. If current master passes and the repair merged after the alerting run began, classify the alert as **pre-fix base evidence**. Add evidence to the source Review card, create no duplicate rescue card, and require the feature PR to rebase/update onto current master for fresh CI.
6. Keep the source card in Review until that refreshed PR run is green; do not merge merely because master now passes.

Good pattern:

> PR #N's extended-browser run started before a separate nav-search repair merged. The alert failed only in the repaired off-diff spec; after canonical sync, the exact spec passes on current master. Record the alert as pre-fix evidence, keep the feature PR in Review, and require a rebase plus fresh workflow run.

## Pitfalls

### Pitfall: truncated or non-actionable notification links
Inbox adapters and GitHub notification templates can expose only a run-ID prefix or a truncated URL. Treat that as a discovery hint, not a runnable locator.

1. Extract the repository, PR/branch title, and commit prefix from the alert.
2. Resolve the full run list by branch first; if the alert commit prefix is accepted, also query by commit.
3. Match workflow name, head SHA, creation time, and conclusion before inspecting logs.
4. Capture the canonical run URL and failed job URL in the board evidence comment and, when material, log the notification-contract gap as product friction.

Do not guess the missing run ID or classify the failure from the email subject alone.

### Pitfall: zero-step admission failures need check-run annotations
A failed GitHub Actions job with `runner_id=0`, an empty runner name, and `steps=[]` did not execute checkout, dependencies, tests, or release code. Treat it as an admission/configuration failure until the check-run annotation proves otherwise. Query the annotation from the check-run endpoint, not the Actions job-annotations endpoint:

```bash
gh api repos/<owner>/<repo>/actions/runs/<run-id>/jobs
# capture the job id, then:
gh api repos/<owner>/<repo>/check-runs/<job-id>/annotations
```

The annotation can distinguish account billing/spending-limit admission (`Actions budget is preventing further use`, or payment/spending-limit wording) from a runner disconnect or workflow execution failure. Record the exact annotation, canonical run/job URLs, head SHA, zero-step evidence, and the existing board owner. Do not rerun repeatedly, edit workflow code, or create a product rescue card when the same account-level admission lane is already tracked. See `references/zero-step-actions-admission-failures.md`.

### Pitfall: duplicate Ready cards for one live blocker
If you seed a rescue card for head A, then later seed another for head B covering the same failure class, the board becomes misleading unless you explicitly retire the older one. Do not leave both claimable in `Ready` just because both were truthful at creation time. The queue should present one active owner per live blocker, with the older one preserved only as historical evidence after supersession.

## Pitfalls

### Pitfall: alert text is broader than the real failure
Emails often summarize at workflow level (for example "E2E smoke failed") while only one exact test is actually red. Do not create broad rescue work until you identify the specific failing spec/assertion.

### Pitfall: one run can expose independent runner contracts
A single PR run can fail in more than one job before application assertions execute—for example, a build job rejects a non-executable tmpfs while a browser job lacks a Playwright shared library. Capture the first concrete pre-test error from **each** failed job and classify each as its own failure class. Before filing or reusing a runner-repair owner, compare GitHub's live labels with the failing workflow's actual `runs-on` selector: removing a narrow label does not quarantine a runner when a broader selector still matches. Reuse an existing live owner for each exact contract; otherwise create one narrowly scoped card per independent contract, cross-reference them, and keep unrelated PR diffs out of both scopes.

### Pitfall: merged source PR plus existing rescue card
When the source PR is merged and the same failing test is already tracked elsewhere, a second rescue card makes the board lie about the number of distinct regressions. Prefer evidence comments over new work.

### Pitfall: current-state drift
The source PR, run list, and board can all move while you triage. Re-query before commenting or creating work if there was a delay.

## Verification checklist

- [ ] PR live state captured
- [ ] Run live state captured
- [ ] Exact failing job/spec/assertion identified
- [ ] Existing board ownership checked
- [ ] Evidence comments added to the right card(s)
- [ ] New card created only if the failure is genuinely new
