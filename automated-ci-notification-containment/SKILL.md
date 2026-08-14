---
name: automated-ci-notification-containment
description: Use for bounced automated GitHub CI alert intake.
version: 1.0.0
metadata:
  tags: [github, ci, notifications, email, kanban, incident-containment]
  related_skills: [github-actions-run-diagnostics, haft-orchestrator-workflows, pr-ci-triage]
---

# Automated CI Notification Containment

Use this class-level skill when a GitHub Actions failure arrives through an automated/read-only mailbox, especially when the channel reports that a prior reply bounced, was blocked, or will be retried.

## Core rule

The email is intake, not a conversation. The CI investigation belongs in GitHub and Kanban. Never emit the diagnosis, tool output, credentials, or operational progress into the automated email thread.

## Workflow

1. **Stop the reply path on delivery failure.** If the adapter reports a rejected or bounced reply, do not send another ordinary response and do not follow a prompt to retry the same recipient. Return the adapter's exact silent sentinel, normally `[SILENT]`, when a response is required.
2. **Resolve the notification identifier.** A short SHA in a subject is not an Actions run ID. Map it with `gh pr list --repo OWNER/REPO --search <short-sha> --state all`, then use the live PR's `statusCheckRollup[].detailsUrl` to obtain canonical run/job URLs. Prefer full SHA, branch, timestamp, and live PR state over the rendered subject.
3. **Re-fetch live state before classifying.** Query run metadata and the jobs endpoint. Capture run attempt, conclusion, head SHA, job ID, status, runner name, step, and URL. A cancelled or superseded notification is historical evidence, not necessarily the current merge gate.
4. **Read bounded logs.** For monolithic Bun or browser jobs, retrieve the per-job log endpoint and filter for terminal markers and a small context window before using full `gh run view --log-failed`. Check artifacts when raw logs are empty. Separate initial attempts, retries, runner shutdowns, setup contamination, and application assertions. **Admission short-circuit:** if the completed job has `steps=[]`, `runner_id=0`, no runner name, and the check-run annotation explicitly names Actions budget/payment/spending-limit admission, stop log/artifact exploration: empty logs and zero artifacts are expected because no job steps ran. Use the run/job/annotation JSON as authoritative evidence and route only the billing/admission gate.
5. **Attribute against the real diff.** Use the live PR changed-file set. Do not infer ownership from the email title or a synthetic merge commit. Distinguish in-diff deterministic failures from unchanged browser/runner failures and shared infrastructure conditions.
6. **Stop on a source/runtime contradiction.** If the exact failed SHA visibly contains the purported fix (for example, an absolute-URL helper) but the CI error still reports the pre-fix input, do not declare the fix effective or reopen a duplicate code lane. Record the contradiction, compare the checked-out source and configuration at the failed SHA, and inspect retained traces/error context for the actual request URL, source frame, and base URL before classifying it as code, config, or runner state.
7. **Reuse the existing owner.** Search the live Kanban board for a source or infrastructure-owner card before creating work. If a matching owner exists, append bounded evidence with canonical run/job URLs and state why no duplicate rescue card was opened. If no owner exists, create one narrowly scoped card with an executable acceptance contract. For Haft external-worker repair work, create the card with `<shared-scripts-root>/haft_ready_worktree_card.py create` so it is genuinely claimable (`status=ready`, `assignee=null`, repo-root workspace, non-empty worker-neutral branch), then run the helper's `validate` command and re-read the card.
7. **Preserve durable evidence.** The board comment should include PR/current head, run and attempt, failed job/runner/step, exact terminal error, classification, changed-file attribution, and the next executable gate. Keep historical evidence; correct it with a new comment rather than silently rewriting it. **Same-run rerun check must happen immediately before any rescue-card creation:** query both the run metadata (`run_attempt`, `status`, `conclusion`) and `gh pr checks <number>`. If a later attempt or replacement job is pending, explicitly mark the red job historical, name the pending job URL, and defer classification until that attempt completes. Do not create a new Ready rescue card while the replacement is running. If a card was created just before the rerun became visible, immediately move it out of Ready (block as transient or archive according to board policy), append the correction to the source card and rescue card, and leave one explicit re-reconciliation gate. If the run is still in progress or a focused existing card or active rerun owns the same failure surface, do not create a second incident card.
8. **Canonical-checkout sync failures are host-state incidents first.** When the failed step runs `scripts/haft-canonical-checkout.ts sync --json`, capture its JSON fields (`canonical`, `branch`, `head`, `remoteHead`, `dirty`, `fastForwarded`, and `diagnostics`) and inspect the live canonical checkout before changing anything. Run `bun run canonical:check -- --json`, `git status --short --branch`, and `git diff --check`; inventory worktrees and compare dirty paths to recent branches/commits. Never reset or clean the canonical checkout blindly: preserve intentional edits by moving them to a dedicated worktree/branch or document the exact reconciliation decision. The acceptance contract is clean expected branch, no longer behind origin, successful canonical check, then a rerun of the same workflow.
9. **Generated SSM Bash stdin scripts need their own bootstrap contract.** When a release workflow concatenates verifier/deploy fragments and executes them with `bash -s`, inspect the exact generated script under `set -u` before classifying a failure as runner or service health. `${BASH_SOURCE[0]}` may be unset in stdin mode, causing a deterministic pre-restart failure; separate publication, target-runtime, and release-finalization state, and use `references/embedded-stdin-bash-bootstrap.md`. Preserve strict mode and all fail-closed provenance, rollback, and health checks; never recover by moving an immutable tag or bypassing verification.
10. **Verify the handoff.** Re-read the card or board event to confirm the comment landed and the live status still reflects the actual blocker. Report nothing to the automated email thread.

## Mixed dispatch cancellation plus an executed sibling

When a same-head `workflow_dispatch` bundle contains both jobs cancelled before steps and another job that executes far enough to fail a policy gate, keep three lanes explicit: (1) hosted/self-hosted runner acquisition cancellation, evidenced by zero steps, no runner, and the canonical check-run annotation; (2) the executed policy/base-state failure, with bounded log evidence and changed-file attribution; and (3) any existing PR-local repair lane. Reuse existing Kanban owners for each lane. Do not let the email's single workflow title collapse these into one product regression, and do not rerun while a current-head required replacement or runner/provider owner still governs the gate.

For an automated read-only inbox, the completed operational work is the live GitHub/Kanban reconciliation—not a helpful reply. After durable comments are verified, return the adapter's silent sentinel (normally `[SILENT]`) and do not emit the triage summary into the notification thread.

## Workflow-dispatch notification versus queued pull-request rerun

A manual `workflow_dispatch` run for a PR head can fail on a real policy gate while the required `pull_request` run for the same SHA is independently queued or being rerun. Treat these as separate run objects: capture the dispatch run's event, job, runner, and exact failure, then query the PR run's `run_attempt` and jobs before creating rescue work. If the PR run has a queued replacement or sibling required job, do not create a duplicate rescue card or rerun again; annotate the existing source/owner card and defer final ownership until the replacement is terminal.

For dependency-audit or governance failures, compare the failing policy surface against the live PR changed-file set. If the PR does not modify the lockfile, audit policy, or dependency graph, classify the failure as an off-diff policy/base-state gate rather than evidence against the feature implementation. Preserve both lanes explicitly: the source card remains responsible for the feature's actual required checks, while a dependency-policy owner (or existing completed/active owner) handles the audit baseline/classification. Include the exact advisory count, scope breakdown, unclassified IDs, and baseline overflow in the durable board comment; never weaken the ratchet merely to clear the PR.

## Rerun completion and owner-card reconciliation

When a failure card was held because a same-run rerun was pending, reconcile it immediately after the replacement attempt reaches a terminal state:

1. Re-query run metadata, attempt-specific jobs, and `gh pr checks` before making any ownership decision. The replacement attempt is the current gate; preserve the earlier attempt as historical evidence.
2. Append one bounded correction to the source PR card naming the terminal replacement job, runner, exact failure, current head, and green sibling checks. Append the same evidence to the existing owner card when the failure surface is off-diff.
3. If the replacement reproduces the same unchanged browser failure, keep the existing owner lane and do not create a duplicate rescue card. Preserve secondary retry errors separately when the first attempt mutates one-time setup state (for example, a claim/bootstrap mutation followed by `already-claimed`).
4. Keep the source PR blocked only on its actual red required check; do not relabel an off-diff request/reporting contradiction as a product, startup, or runner-timeout regression.

This pattern is captured in `references/rerun-owner-reconciliation.md`.

## Off-diff browser-gate corroboration

When a new PR's required browser gate reproduces an already-owned failure in unchanged authentication or E2E files, append the bounded evidence to both the PR/source card and the existing owner card instead of opening a rescue card for the feature PR. Capture the exact head SHA, run/attempt, failed job and runner, checkout/runtime/browser-preflight results, passed/failed test counts, retry behavior, and the fixture/runtime contradiction if present (for example, a far-future replacement expiry rendered as expired). Keep the PR blocked on its required check, but classify the failure as off-diff and leave feature files untouched while the owner investigates. Re-query current-head checks before any rerun or escalation; do not conflate a red required gate with ownership of the failing surface.

## Child-process readiness-file failures

When a test fails while launching a child server or helper because a readiness JSON/file contains truncated or invalid content (for example, `JSON Parse error: Unexpected EOF` at the readiness-file reader), classify the failure first as a startup handoff/runner-filesystem boundary, not as a failure of the test assertion or the feature PR. Capture the exact test case, harness reader path/line, runner, and whether the failing harness files are in the PR diff. If the harness is unchanged, preserve the feature/source card as blocked on CI but create or reuse one narrowly scoped off-diff owner card with an acceptance contract covering atomic readiness publication or bounded complete-read retry, repeated focused-suite proof, preservation of process-boundary privacy, and a full current-head rerun. Immediately before creating the owner card, re-query run metadata and `gh pr checks` to ensure no later attempt or replacement job owns the same failure. Do not “fix” this class by weakening the readiness schema, passing document bodies through the child boundary, or merely rerunning without recording the exact handoff failure.

## Mixed required-run lane: action-download outage plus product failures

A single PR notification can combine a setup-only GitHub service failure with a real product/test failure in another required job. Treat action-download resolution errors such as `Failed to resolve action download info` followed by `Bad Gateway` or `Service Unavailable` as an off-diff GitHub Actions service lane when they occur during job setup before checkout/tests. Do not let that setup failure obscure a separate completed job that ran tests and produced deterministic assertions. Preserve the setup job URL, runner, exact provider errors, and fact that no product test ran; keep the PR repair lane scoped to the completed in-diff failure. Re-query current-head checks immediately before creating any owner card. If no existing owner covers the deterministic failure, create one claimable PR repair card and document the setup outage as a separate rerun/reconciliation gate rather than opening a browser-infrastructure rescue card solely from the setup error.

## Account-billing admission failures with zero jobs

When a required GitHub Actions job is terminally `failure` but has zero steps, no runner, and its check-run annotation says the job was not started because recent account payments failed, the spending limit must be increased, or an **Actions budget is preventing further use**, classify it as an account-level GitHub admission/billing gate. These annotation wordings are the same operational lane unless live evidence identifies a different admission cause. No checkout, dependency installation, or product test ran. Preserve the run/job URL and exact annotation, keep the PR blocked on the required check, and escalate the smallest exact operator action: inspect GitHub **Billing & plans** for payment failure, spending-limit, or Actions-budget remediation. For zero-step jobs, an empty `gh run view --job <job> --log-failed` result is expected; use the job JSON and check-run annotations as the authoritative evidence rather than treating the absent log as an additional failure. Do not create a code-rescue card, rerun repeatedly, or attribute the result to the PR diff. Re-query the live PR rollup after the account issue is corrected; treat any later executed run as a new diagnostic object.

This is distinct from action-download/provider outages and self-hosted runner dispatch failures: those classifications require their own canonical annotations and evidence. A zero-job failure alone is insufficient to call it a workflow-file parse error when the annotation names billing/account admission.

For scheduled post-merge watchdog failures, compare the failed run with the immediately preceding same-SHA watchdog run before escalating: if the prior run was green and the current job has zero steps/no runner plus the billing annotation, preserve the failure as an account admission gate rather than a regression in the merged PR. Record the current run/job URLs, exact annotation, head SHA, and the last known green same-SHA run; do not rerun repeatedly or create a code-rescue card. The smallest operator action is GitHub Billing & plans remediation, followed by a fresh workflow/check reconciliation.

When repeated scheduled watchdog notifications arrive while the same blocked billing owner card is open, treat each as corroboration rather than a new incident: query the latest run once, append one bounded comment naming the run/job, zero-step/no-runner evidence, exact admission annotation, and current release phase boundary, then keep the existing card blocked. Do not emit a threaded reply to the automated mailbox. A watchdog admission failure proves only that the watchdog could not execute; inspect the release run separately before claiming anything about publication, deployment, or GitHub Release finalization.

When a watchdog failure overlaps an active release lane, preserve two independent evidence bundles: (1) watchdog admission—run metadata, zero-step job, no runner, canonical annotation, and same-SHA recurrence; and (2) release state—release/tag runs on the immutable SHA, publication/deployment jobs, downstream gate failures, and whether a GitHub Release object exists. Never use the watchdog result as a proxy for release success or failure. If the release published/deployed but a later collaboration or finalization gate failed, keep that configuration lane on its existing owner card and state the skipped-finalization boundary explicitly. Reuse the billing owner for repeated watchdog alerts, append only bounded corroboration, and keep the automated inbox silent.

**Release-object verification detail:** a tag can exist and resolve to the immutable release SHA while `gh release view <tag>` returns not found because finalization was skipped. Verify the tag separately (`gh api repos/OWNER/REPO/git/ref/tags/<tag>`; dereference annotated tags with `git/tags/<sha>` when needed), then verify release-object absence/presence from `gh api repos/OWNER/REPO/releases?per_page=100` or the release endpoint. Record publication/deployment success, finalization failure/skip, and release-object state as separate facts; do not manually create or move a release during watchdog triage.

When a watchdog is intended to observe a release dispatch, reconcile the observed release run separately before deciding the incident is resolved. A billing-blocked watchdog proves only that the watchdog itself could not execute; it does not prove the release succeeded or failed. Query the release run's jobs, annotations/logs, and finalization/release-object state. Keep distinct lanes when the release reached real steps and failed a product/configuration gate (for example, missing controlled mailbox variables) while the watchdog independently failed before job start. A release may have successfully published/deployed artifacts while a later collaboration or finalization gate failed; report those phase boundaries explicitly and do not call the release fully complete without a finalized release object. Do not rerun or file a watchdog/code rescue from the billing annotation alone; escalate Billing & plans for the watchdog, and route any executed release failure through its own existing release-owner lane.

**Immutable-tag verification:** Verify the tag independently from the GitHub Release object. Query the tag ref and dereference annotated tags to the commit SHA; then query the release endpoint/list. A tag resolving to the intended immutable SHA while `gh release view <tag>` returns not found means publication/deployment may have completed while finalization was skipped—not that the tag is missing. Reuse the existing release-finalization/configuration owner, append the watchdog run as corroboration, and do not move/reuse the tag or manually create the Release object.

## Mixed cancellation and hosted-action setup failures

When one PR notification reports several required workflows as failed but the jobs are `cancelled` or have no steps, inspect check-run annotations before classifying the PR. An annotation such as `The job was not acquired by Runner of type self-hosted even after multiple attempts` is runner-dispatch evidence: no checkout, test, or product assertion ran. Reuse the existing self-hosted/runner owner card, append the run/job URLs and annotation, and do not create a feature rescue card or edit browser tests.

### Offline runner plus stale PR repair card

If multiple required self-hosted jobs are cancelled before checkout on the same head, and the runner API shows the targeted runner `offline` (or another matching runner `online`/idle but not acquiring jobs), treat this as a dispatch/listener lane first. Capture the exact run/attempt/job URLs, canonical check-run conclusion (`CANCELLED`, even if `gh pr checks` renders `fail`), annotation, runner status, and the current PR `headRefOid`. Then:

1. Compare the live head to any existing PR repair card. If the card body names an older SHA, append a correction and hold/block it until a fresh current-head run executes; do not let stale historical product failures make the card claimable.
2. Search for an existing runner/listener owner. Reuse it when the mechanism matches; otherwise create one narrowly scoped, claimable infrastructure card with an acceptance contract for runner online/listener health, matching-label job acquisition, and exact-head rerun evidence.
3. Keep any still-running sibling workflow open as an unresolved required gate. Do not rerun again or classify product ownership while a replacement/sibling is queued or in progress.
4. After runner recovery, rerun the exact current head and reclassify from the new terminal jobs. A job that never checked out cannot be evidence against the PR diff.

The durable evidence bundle is captured in `references/offline-runner-dispatch-reconciliation.md`.

If a sibling hosted job reaches only `Set up job → Getting action download info` and fails with `Service Unavailable`, `Bad Gateway`, or equivalent provider text, classify it separately as a GitHub Actions service/setup outage. Preserve the job log and state that no product test ran. A mixed notification must not be collapsed into one PR regression or one runner incident. Before any rerun or rescue-card decision, query the run metadata, attempt-specific jobs, annotations, and `gh pr checks` again; normally defer rerun until the setup/runner condition is available. For read-only automated inbox intake, record the evidence in Kanban and do not reply.

## Mixed hosted cancellation plus off-diff policy failure

When one same-head workflow-dispatch notification reports a hosted platform-boundary job as failed while a sibling build job is red, keep the lanes separate:

1. Query the cancelled job's canonical check-run annotations. If it says `The job was not acquired by Runner of type hosted even after multiple attempts`, with zero steps and no runner, classify it as provider/runner-dispatch evidence; no checkout or product test ran.
2. Retrieve the sibling build log with a bounded terminal-marker filter. If the job reached a dependency-advisory ratchet and reports advisory count above the reviewed baseline or an unclassified advisory, classify that as an independent dependency-policy/base-state gate.
3. Attribute the policy gate against the live PR file list. If no lockfile, dependency manifest, or audit-policy file changed, preserve it as off-diff evidence and do not assign it to the feature implementation.
4. Reuse the existing runner/provider owner card for the hosted cancellation and the existing PR/policy owner lane for the audit failure. Do not open a duplicate rescue card or rerun while a replacement/sibling gate is queued.
5. Before writing a durable comment, verify advisory identifiers and package names directly from the bounded log. If a comment contains a typo, append a correction immediately; never leave an ambiguous advisory identifier as the latest canonical handoff.

This pattern is also captured in `references/mixed-hosted-cancelled-offdiff-policy.md`.

## CLI compatibility and bounded evidence

`gh run view --json` fields vary by installed GitHub CLI version; do not assume `runAttempt` is available. If the field is rejected, retry with the supported run-level fields, then query the specific job/check-run API (`gh api repos/OWNER/REPO/actions/jobs/JOB_ID` and `/check-runs/CHECK_RUN_ID/annotations`) for `run_attempt`, runner, step state, and setup annotations. This preserves canonical evidence without depending on a newer CLI schema.

## Workflow-dispatch versus pull-request check reconciliation

A same-head `workflow_dispatch` run is useful for attribution but does not replace the required `pull_request` check. Treat each as a separate run object even when the SHA matches:

1. Re-query the PR's live `headRefOid` and `gh pr checks <number>` immediately before classifying or rerunning.
2. Record the PR-event run's canonical conclusion and attempt-specific jobs separately from any dispatch validation jobs.
3. If the PR-event jobs are cancelled before checkout with a runner-acquisition annotation, classify them as runner/provider dispatch evidence; they provide no product-test evidence.
4. If a dispatch sibling reaches tests and fails an off-diff policy gate, preserve that as a separate policy/base-state lane. Compare the exact changed-file set before assigning ownership.
5. Reuse the existing PR, runner, or policy owner cards; append a correction when a stored card head or earlier classification is stale. Do not create a duplicate rescue card merely because the notification rendered cancelled checks as `fail`.

## Installed GitHub CLI surface fallback

The installed `gh pr checks` command may not support `--json`, even when structured evidence is needed. Do not spend a triage turn retrying unsupported projections. Use `gh pr view <number> --json statusCheckRollup,headRefOid,files` for check-run URLs and changed-file attribution, then query canonical run/job metadata with `gh api repos/OWNER/REPO/actions/runs/RUN_ID` and `gh api repos/OWNER/REPO/actions/jobs/JOB_ID`. Plain `gh pr checks <number>` remains useful as a human-readable cross-check, but REST/API output is authoritative for attempt, conclusion, runner, and step evidence.

`gh run list --json` has the same version-skew risk: request only fields accepted by the installed CLI (for example, `databaseId,headSha,status,conclusion,event,createdAt,updatedAt,url,workflowName`) and filter locally for the target SHA/run. Do not repeatedly retry rejected projections such as an unsupported `attempt`; obtain attempt data from `gh api repos/OWNER/REPO/actions/runs/RUN_ID` and the jobs endpoint instead. This keeps scheduled-watchdog reconciliation bounded and preserves canonical run/job evidence.

## Recurrent current-base policy failures after a completed remediation

A completed dependency-audit remediation card proves the prior policy state was repaired; it does not prove the current base will remain green after new advisories appear. When a later PR fails at the same audit gate:

1. Re-fetch the exact run metadata, attempt-specific job, bounded log, current PR head, and changed-file set. Confirm the failure is on the live head and occurred before product tests.
2. Name the exact new advisory, severity, scope breakdown, reviewed baseline, and policy violations. Do not summarize this as merely “dependency audit failed.”
3. Compare the PR's changed files against dependency manifests, lockfiles, and audit-policy files. If none are touched, classify the red check as off-diff current-base policy drift; keep the feature PR in Review and do not modify unrelated product code.
4. Search the board for the prior remediation owner. Append corroborating evidence there, but distinguish a completed historical fix from a newly reproducible current-base recurrence.
5. Reuse the completed owner without a new card when it still owns an open, executable remediation lane. Create one new narrowly scoped Ready follow-up only when the prior remediation is terminal and the newly observed advisory/policy state is a distinct current-base blocker affecting multiple PRs. The follow-up must target the dependency graph/policy, not the feature PR branch.
6. Validate any new Haft worktree card with `haft_ready_worktree_card.py validate` and re-read the live card before reporting it as claimable.

## Duplicate bounce notices after reconciliation

A second or later delivery-failure notice for the same original automated GitHub notification is not a new CI incident. If the original PR/run has already been reconciled against live GitHub and Kanban state, do not repeat the investigation, create another rescue card, or emit a threaded reply. Preserve the existing durable handoff and return the adapter's silent sentinel (`[SILENT]`). Only reopen triage when the new notice contains a genuinely different original subject, SHA/run, or actionable delivery classification.

### Late duplicate notification after an existing owner handoff

A later GitHub notification can arrive after the source PR card and focused rescue owner already contain terminal run/job evidence. Re-query the canonical run and PR head once, then compare the notification's run, attempt, SHA, failed jobs, and terminal error with the latest board comments. If they match, append only a short corroboration to the source and owner cards stating that no new incident or rerun was opened; do not duplicate the full log extraction, reopen the source card, or create another rescue lane. Keep the source card blocked/review-held only by the actual current-head required check, and return the mailbox's silent sentinel rather than replying with the operational summary.

**Existing-owner fast path:** Before broad log/artifact exploration, search the live board for the exact run ID or distinctive annotation. If an active owner card already records the same zero-step job, runner state, and classification, use one fresh canonical API check to confirm it is unchanged, append bounded corroboration, and stop. Do not repeatedly enumerate every prior scheduled run or re-document the entire incident. This is especially important for recurring watchdog alerts: the notification is corroboration, not a new incident.

When a recurring watchdog alert overlaps a release, preserve a second, explicitly bounded release-phase check only when needed to prevent a false conclusion. State publication, deployment, collaboration/finalization, and GitHub Release-object status separately; a watchdog admission failure does not prove release success or failure. Reuse the existing billing owner for the watchdog and the existing release-finalization owner for the executed release failure.

## External-shell Kanban handoff fallback

When this skill is running in an external shell lane rather than a dispatcher task worker, use the Hermes Kanban CLI for durable comments and status reads instead of trying to call unavailable `kanban_*` tools. Put the board selector before the subcommand, for example `hermes kanban --board haft show <task_id>` and `hermes kanban --board haft comment --author orchestrator <task_id> "..."`; verify with a follow-up `show`. If the session has no assigned task id, do not invent one: reconcile against the existing owner card discovered from the live board and append evidence there. This is a tooling-surface fallback, not a reason to skip the durable handoff.

## Assigned-task and board-read fallback

When notification intake has no `HERMES_KANBAN_TASK`, do not invent a task ID or treat the missing worker context as a blocker. Reconcile against the live board's existing owner card, using the external-shell CLI or a read-only database search for the exact run ID, job ID, or distinctive annotation. Append evidence to the matching owner and preserve its live status. If a CLI write reports success but a follow-up `show` fails with a database/session error, verify the newest `task_comments` row read-only before retrying or mutating anything; a read-path failure is not proof that the write was lost.

For long comments, pass the complete text as one subprocess argument or API payload rather than through shell interpolation. Verify both the comment author and a distinctive canonical URL/annotation string. This pattern is particularly important for recurring scheduled watchdog alerts: one fresh run/job/annotation check plus one bounded corroboration is enough; do not enumerate history or create a duplicate incident unless the run, SHA, or error materially differs.

## CLI surface note

The external-shell Kanban CLI does not accept a generic `--limit` option on `hermes kanban list`. Use `hermes kanban --board haft list --json` and filter locally with `jq` (for example, match the run ID or distinctive annotation in `.title + " " + .body`). Keep the board query bounded by filtering fields rather than repeatedly dumping the full board; the human-readable command surface differs from the `kanban_*` tool API.

## Scheduled watchdog verification order

For a scheduled release/watchdog alert, use this bounded order before any board mutation: (1) fetch run metadata and the attempt-specific jobs endpoint; (2) fetch the failed job's check-run annotations; (3) classify zero steps + no runner + an explicit account-admission annotation as a billing gate; (4) search the live board for the exact run ID or annotation and reuse the existing owner; (5) independently inspect release/tag state only if the watchdog is described as observing a release. Keep watchdog admission, artifact publication/deployment, collaboration/finalization, and GitHub Release-object presence as separate facts. A tag or deployment result must never be inferred from the watchdog result. Immediately verify the durable comment after writing it.

### Scheduled watchdog board-state reconciliation

When a recurring watchdog alert already belongs to an existing billing/admission owner, update that owner with one bounded evidence comment and verify its live status. A stale `triage` status is not an acceptable representation of an operator-only gate: if the normal block command refuses the stale state, use the board's documented repair/reconciliation path to move it to `blocked` with `block_kind=needs_input`, then verify the task row and newest comment directly. Do not leave a human approval gate claimable or create a duplicate rescue card. Keep a CLI read-path failure (for example, a closed-database error while showing a card) separate from the underlying GitHub evidence; a successful comment write must be verified via a read-only task-comment query when necessary.

**Block-loop repair boundary:** if repeated `needs_input` transitions have tripped the board's block-loop guard and the CLI refuses to move an already-stale owner out of `triage`, do not promote/block repeatedly. Preserve the bounded corroboration comment, then use the board's documented administrative reconciliation or SQLite repair path to set only the live task fields required for the operator gate (`status=blocked`, `block_kind=needs_input`, and cleared claim fields), append an auditable status event, and re-read the card. Preserve the recurrence history; do not reset it merely to make the card claimable. The repair is complete only when a fresh `show` reports `blocked` and the comment contains the canonical run/job URL and annotation. This is state repair, not a new incident or a reason to create a rescue card.

### Repeated same-SHA watchdog corroboration

When the newest scheduled watchdog alert has the same head SHA and the same zero-step/account-admission annotation as an already-owned blocked card, treat it as corroboration, not a new incident. Query a bounded recent run window for that SHA to establish recurrence, record the newest canonical run/job URLs and the observed failure interval, and append one concise comment to the existing owner. Do not rerun, create a duplicate rescue card, or reopen code/release work. If the SHA query shows no corresponding release workflow run, state only that no such Actions run was observed; never promote that absence into a claim about publication, deployment, or GitHub Release-object state. Leave the smallest operator gate explicit: remediate Billing & plans/Actions budget, then verify one fresh watchdog run acquires a runner and executes steps.

For repeated scheduled alerts with the same SHA and annotation, one fresh canonical check plus a bounded corroboration comment is sufficient; do not enumerate historical runs, rerun, or create a duplicate rescue card unless the run/SHA/error materially differs.

### Practical API recipe for recurring watchdog admission failures

For a scheduled watchdog notification, treat the run and job APIs as authoritative: query `/actions/runs/<run_id>` for `run_attempt`, `head_sha`, `status`, `conclusion`, and event; query `/actions/runs/<run_id>/jobs` for the terminal job, `steps`, `runner_id`, and `runner_name`; then query `/check-runs/<job_id>/annotations` for the canonical admission message. A completed failure with `steps=[]`, `runner_id=0`, empty `runner_name`, and an explicit Actions budget/payment/spending-limit annotation is an account-level admission gate. Before any board mutation, compare `gh run list --workflow <watchdog> --branch master` for nearby same-SHA runs and search the live board for the run ID or distinctive annotation. Reuse the existing billing owner, append only bounded corroboration with the current run/job URLs and exact next operator gate, and verify the stored comment with a follow-up card read. Never infer release publication, deployment, or GitHub Release-object state from the watchdog result.

## Board-comment verification fallback

When the external-shell Kanban CLI reports a write succeeded but a subsequent `show` fails with a database/session error, do not treat the failed read as evidence that the comment was lost. Verify against the active board database in read-only mode: resolve the board-specific DB (for Haft, `<hermes-home>/kanban/boards/haft/kanban.db` on the current host), query the newest `task_comments` row for the exact task ID, and confirm author, timestamp, and distinctive run URL/annotation text. Report the CLI read-path defect separately; do not mutate task state through ad hoc SQL unless the governing workflow explicitly authorizes that fallback.

## Malformed board JSON fallback

If `hermes kanban ... list --json` emits malformed JSON (for example, unescaped control characters in a task body), do not repeatedly retry the same projection or treat the parse failure as an empty board. Use the board's SQLite database in read-only mode to search `tasks.title`, `tasks.body`, and `tasks.result` for the exact run ID or distinctive annotation, then use the normal CLI/API path for any write. If a CLI `show` also fails after a successful write, verify the comment with the same read-only query against `task_comments`. Keep this fallback bounded and report the CLI serialization defect separately from the CI classification. See `references/malformed-board-json-fallback.md`.

This is especially useful for scheduled watchdog billing incidents: the durable handoff is complete only after the comment's run/job URL, zero-step/no-runner evidence, exact admission annotation, independent release-state boundary, and next operator gate are confirmed in the board record. For the exact stale-`triage`/block-loop repair sequence, see `references/stale-triage-block-loop-repair.md`.

## Pitfalls

- Sending a helpful-looking summary as a normal reply after a bounce; this can create repeated delivery failures and mailer-daemon noise.
- **Shell interpolation or wrapper rejection when writing durable comments:** never place backticks, `$()` substitutions, ampersands, or other shell-active syntax inside an unquoted `hermes kanban comment` argument. The shell may execute embedded commands, inject output, or reject the command before it runs. Preserve the evidence and retry through an argument-safe API such as `subprocess.run(["hermes", "kanban", "--board", "haft", "comment", "--author", "orchestrator", task_id, comment])`, passing the full comment as one list element; then re-read the card and verify the stored text.
- Treating command stdout/stderr as proof that the comment write failed. Verify the stored comment contents separately; if an expected diagnostic was emitted during argument expansion, distinguish it from the write result and correct the durable record.
- Treating a short SHA as a run ID or assuming a truncated run ID means the run was deleted.
- Filing one blended incident when build timeout, browser shutdown, and product assertion are separate lanes.
- Creating a duplicate card when an existing runner/storage/throughput owner already covers the mechanism.
- Calling Chromium/browser infrastructure healthy merely because the launch preflight passed; inspect whether the runner later shut down or tests timed out.
- Treating a governance `PASS` line as proof that the whole required job passed; a later harness timeout can still be the terminal job failure.

## References

- `references/repeated-watchdog-billing-admission.md` — bounded recipe for repeated scheduled watchdog failures caused by account-level billing admission, including same-SHA corroboration and single-owner handoff.
- `references/delivery-failure-and-short-sha-recipe.md` — condensed evidence pattern for blocked automated replies, short-SHA resolution, bounded logs, and board handoff.
- `references/bounced-mailer-daemon-silent-sentinel.md` — verified handling for bounced automated senders: complete operational work through GitHub/Kanban, then return exactly `[SILENT]` rather than replying into the blocked thread.
- `references/release-deploy-readiness-triage.md` — bounded SSM/systemd/listener triage when a published release exceeds an environment health budget, including portable SSM diagnostics and handoff criteria.
- `references/recurrent-current-base-policy-failure.md` — evidence and board-handoff recipe when a new dependency advisory reopens an off-diff current-base gate after a prior remediation.
- `references/source-runtime-contradiction-recipe.md` — exact-SHA, trace-first triage when CI reports stale behavior despite source containing the expected fix.
- `references/scheduled-watchdog-bounded-reconciliation.md` — compact evidence order for zero-step Actions-budget admission failures, independent release-state checks, and read-only verification when Kanban CLI reads fail.
- `references/scheduled-watchdog-release-boundary.md` — separate recurring watchdog admission evidence from immutable release publication, deployment, finalization, and GitHub Release-object state.
- `references/scheduled-watchdog-board-reconciliation.md` — durable board-status repair, comment verification, and safe external-shell handoff for recurring watchdog owners.
