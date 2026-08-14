---
name: ci-supersession-reconciliation
description: Reconcile failed CI/deploy incident cards when later green runs or merged fixes supersede older failures. Deduplicate stale notification-driven work, keep the board truthful, and avoid spawning duplicate incident cards.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  tags: [ci, github-actions, incident-management, dedupe, reconciliation, sweeps]
  triggers:
    - "failed GitHub workflow email arrived but a later run is already green"
    - "same failure class appears on an older run and a newer commit already fixed it"
    - "stale incident card should be retired after a superseding release lands"
---

# CI Supersession Reconciliation

Use this workflow when a GitHub Actions failure, deploy incident, or release refusal has already been superseded by newer evidence.

Reference: `references/ci-failure-supersession-dedup.md` contains a concise example pattern and dedupe rules. See also `references/runner-disconnect-dedup.md` for the runner-disconnect / duplicate-intake classification pattern, `references/merged-source-card-noop-reconciliation.md` for the merged-PR / archived-source-card silent-sweep pattern, `references/inbox-noise-silent-sweep.md` for the notification-noise / `[SILENT]` case from a live cron sweep, and `references/pre-run-admission-failure-triage.md` for the runner-allocation and check-run annotation probe.

## Core rule
Do **not** create a duplicate follow-up card just because an older failure email arrived late.

An email by itself is not a queue signal. First map it to a live card, open PR, or still-active incident. If there is no live owner and the board is already otherwise healthy, keep the board untouched and let the sweep stay silent instead of spawning noise.

If a newer run, rerun, or merged fix clearly supersedes the older incident:
1. verify the newest relevant run/commit;
2. compare the failing surface to the newer green evidence;
3. comment the original incident card with the superseding evidence;
4. retire the stale card to `done` when the fix is canonical;
5. leave unrelated claimable work in `ready` alone.

## Pre-run admission failures

A failed workflow can be an account/platform admission failure rather than an execution failure. Before treating it as a product or workflow defect, inspect the run and job metadata:

1. Fetch the run JSON and identify the failed job.
2. Inspect the job for `runner_id`, `runner_name`, `steps`, and labels. A zero runner ID, empty runner name, and empty steps indicate the job never started.
3. Fetch check-run annotations with `GET /repos/{owner}/{repo}/check-runs/{check_run_id}/annotations` (the run's job ID is commonly the check-run ID). Classify from the exact annotation, not from the email subject or an empty `--log-failed` result.
4. For messages such as Actions budget, billing, spending-limit, or payment admission blocks: map to an existing operator-owned billing/runner-admission card, append the fresh run URL, SHA, job ID, runner metadata, and annotation, and do not edit workflow code or repeatedly rerun.
5. Keep the card blocked until the account gate is repaired; acceptance requires a fresh run that both acquires a runner and executes steps.

This branch is distinct from runner-listener outages: those usually have a meaningful job attempt but fail to acquire a matching self-hosted runner, whereas account admission failures prevent allocation entirely.

## When to use
- A workflow failure email arrives after the board has already moved on.
- A rerun on the same branch advances past the old blocker.
- A later release commit fixes the issue that the incident card was tracking.
- Multiple notifications refer to the same underlying failure, but only one card should own it.
- A workflow fails with no runner, no steps, and an authoritative platform/billing annotation.

## When not to use
- The newer run fails in a different phase or exposes a different blocker.
- The later evidence is only a partial rerun, not a true fix.
- The card still owns a live, unaddressed failure.

## Procedure
1. Find the authoritative workflow/run URL, not just the email subject.
2. Check the latest visible state for the branch/commit.
3. Ask: does the new evidence truly supersede the original failure?
4. If yes, document the supersession on the board and move the stale card to done.
5. If no, keep the original card active and file a narrowly scoped follow-up only when needed.

## Pitfalls
- Do not dedupe purely by branch, workflow name, or broad failure class.
- Do not spawn a new card if the original card already has the exact run evidence and the fix is now merged.
- Do not treat a later run that fails in a new phase as the same incident.
- Do not close a card on a vague hunch; require explicit superseding evidence.
- Do not treat an empty or unhelpful `--log-failed` result as evidence that the failure is a product bug; inspect run/job JSON and runner annotations before classifying the incident.
- Do not create a second intake card when another live card already owns the same run/failure phase; comment the live owner and archive the duplicate instead.

## Verification
Before closing a stale incident card, confirm:
- the later run is green or the merged fix is present;
- the newer evidence covers the same failure surface;
- the board comment includes the original run and the superseding run/commit.
