---
name: github-actions-run-diagnostics
description: Diagnose GitHub Actions workflow failures from run-level and attempt-level evidence, especially rerun/retry cases where different attempts fail for different reasons.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  tags: [github, github-actions, ci, deploy, retries, diagnostics]
  related_skills: [github-workflows, pr-ci-triage]
---

# GitHub Actions Run Diagnostics

## When to use

Use this skill when a GitHub notification, PR, deploy, or post-merge workflow reports a failed Actions run and you need to determine the real blocker from live evidence.

Especially use it when:
- the run was rerun or retried
- a deploy/release workflow has multiple jobs with different failure surfaces
- a later attempt appears to fail for a different reason than an earlier attempt
- you are reconciling GitHub failures into Kanban follow-up cards
- a workflow step that used to fire on an event (merge/push) has silently stopped
  firing — there is no failed run, only the *absence* of an expected run. Diagnose
  the trigger history before touching the step logic; see
  `references/workflow-trigger-regression-diagnosis.md`. (For the canonical-checkout
  instance of this, see the `canonical-checkout-drift-repair` skill.)

## Core rule

Treat a GitHub Actions **run** and a GitHub Actions **attempt** as different diagnostic objects.

A single run id can contain multiple attempts. Default `gh run view <run-id>` output often emphasizes the latest attempt, which can hide earlier blockers. Do not compress a multi-attempt incident into one root cause until you inspect the attempts explicitly.

## Workflow

1. **Establish the run identity.**
   - Capture repo, workflow name, run id, branch/tag, head SHA, event, and run URL.
   - For deploy/release failures, also capture the PR or merge commit that produced the tag/commit.

2. **Inspect the run summary first.**
   - Use `gh api repos/<owner>/<repo>/actions/runs/<run-id>` or equivalent.
   - Record `run_attempt`, `head_sha`, `event`, and final `conclusion`.
   - **Notification-ID fallback:** rendered notification links can contain only a shortened run-id prefix—or be truncated before a usable link/ID (for example, ending at `View resul`). If direct run lookup is impossible, do not infer the run is gone. Resolve the PR/head branch from the notification; if the subject includes a short commit SHA, use it as the primary discriminator. **Query the PR's `statusCheckRollup[].detailsUrl` first**: it often contains the canonical full run and job IDs even when `gh run list --commit <short-sha>` returns no rows. Do not treat an empty short-SHA `--commit` query as absence: GitHub may require the full 40-character SHA. If the full SHA is unavailable, query recent workflow runs and match the notification’s branch, short-SHA prefix, and finished timestamp:

       gh api repos/<owner>/<repo>/actions/runs --jq '.workflow_runs[:10] | .[] | "\(.id) \(.name) \(.status) \(.conclusion) \(.created_at) \(.head_branch)"'

     A common failure mode: notification emails truncate the numeric run ID (for example `303115566` when the real ID is `30311556695`). The truncated ID returns HTTP 404 from both `gh run view` and the runs API. Do not conclude the run was deleted — list recent runs as above and match by workflow name, branch/tag, and timestamp. Select the exact SHA/time match before continuing, then record the canonical run URL in the handoff.

3. **Reconcile notification timing before filing or escalating.**
   - **Exact-head manual validation:** when a PR owner supplies a corrected immutable head and asks for CI verification, first query the live PR `headRefOid` and the branch ref; both must equal the requested 40-character SHA. If no matching Actions runs exist, explicitly dispatch each requested `workflow_dispatch` workflow with `gh workflow run <workflow> --repo <owner/repo> --ref <head-branch>`. Then accept only runs whose `event=workflow_dispatch` (or the requested PR event) **and** `head_sha` equal that SHA; do not inherit an earlier SHA's green result. Wait for every job in each selected run to reach `completed`, including secondary browser jobs. Report run URL, job URL, runner ID/name, and terminal conclusion. A red browser job whose checkout, browser installation, and runner-runtime verification steps passed is not by itself runner-infrastructure evidence; extract bounded test logs before proposing any runner change. **Retry-contaminated one-time setup:** if a browser test first fails after issuing a one-time claim/token/bootstrap mutation, its retry can fail with an already-used/already-claimed error rather than the primary assertion. Report first-attempt and retry errors separately; classify the retry as setup-state contamination unless it independently reproduces the same failure. Repair tests with per-attempt isolated state or an idempotent setup helper—never runner changes or a timeout increase that hides the state leak.
   - A failure notification can describe an attempt that is already being rerun when it is read. Re-fetch run metadata immediately before treating the failure as terminal. If `run_attempt` has advanced or `gh pr checks` shows replacement jobs, treat the original red result as historical immediately: append a correction to the owner/source card naming the replacement run/job URLs and defer final attribution until the replacement attempt is terminal. Do not leave a comment that still tells operators to rerun when the rerun is already active.
   - If `status=in_progress` and `run_attempt` has increased, preserve the completed attempt as evidence but wait for the current attempt's terminal job result. Do not create a second incident card while a focused existing card or active rerun owns the same failure surface.
   - **Partially completed workflow:** a workflow can remain queued/in-progress while one job already has `conclusion=failure`. Record the failed job ID, runner, step, and completed timestamp from the jobs endpoint, but do not treat a failed-job log as unavailable merely because `gh run view --log-failed` says the run is still in progress. Try `gh api repos/<owner>/<repo>/actions/jobs/<job-id>/logs` once. If GitHub withholds that blob too, query the job's check-run record (`GET /repos/<owner>/<repo>/check-runs/<job-id>`) and annotations (`GET /repos/<owner>/<repo>/check-runs/<job-id>/annotations`). A self-hosted runner can be terminally marked `failure` while its final workflow step remains `in_progress` and the log endpoint 404s; a `runner lost communication` annotation is infrastructure evidence, not a product-test regression. State the job failure is real but its root cause is pending only when neither logs nor annotations explain it; do not infer a cause from the check badge.
   - **Zero-job workflow-file failure:** if a completed run has a near-zero duration, no jobs from the attempts/jobs endpoint, `gh run view` says it likely failed because of a workflow-file issue, and logs return 404, classify it as workflow evaluation/configuration—not a runner or test failure. Inspect the exact workflow at the failed SHA and its commit diff. Check expression-context availability at the field where it appears: a context can be valid in step-level `env` but invalid in `jobs.<job_id>.env` (for example, use of `runner.temp` at job scope). Preserve the intended runtime/security behavior by moving the expression to an allowed step-level environment or command; do not replace an ownership-safe per-runner lock with a broadly writable shared path merely to make parsing succeed. Record the run URL, SHA, zero-job fact, and the existing owner card; reuse that card rather than filing a duplicate.
   - Once a rerun completes, compare the failed job, assertion, and runner identity. The same assertion failing on separate runners and its in-job test retry is evidence of a reproducible defect lane, not merely transient runner pressure.
   - **Queued rerun discipline:** `gh run rerun --failed` can leave a self-hosted job queued for a long time while other jobs in the same run have already passed. Do not block the orchestration turn on `gh run watch`'s noisy three-second refresh loop. Query the run plus `/jobs` endpoint once and record `run_attempt`, job ID, status, `runner_name`, and timestamps. If the failed job is still queued/unassigned, report it as pending with no verdict; do not promise monitoring. Re-query only during a later sweep or on an explicit request.
   - **Cancellation supersession:** `gh run watch --exit-status` can render a cancelled job as a red `X`. Before calling it a failure, query `gh api repos/<owner>/<repo>/actions/runs/<run-id>` and use the run's terminal `conclusion` as authoritative. If it is `cancelled`, inspect the next same-workflow run on that branch: a newer push commonly supersedes it. Preserve completed job evidence, but never open a regression card from a cancelled run alone.
   - **Notification-versus-current-head reconciliation:** a notification subject may call a workflow “failed” even when its resolved run is terminal `cancelled` after a later commit advanced the PR. Query the PR’s live `headRefOid` and `statusCheckRollup` after resolving the old run. Treat the newest-head checks—not the email’s SHA—as the merge gate. Add one concise source-card comment with the old run URL/conclusion, current head, replacement run URLs/statuses, and the explicit decision (for example, “no rescue card; await current-head gates”) so later sweeps do not repeat the correlation work.
   - **Rerun with cancelled setup job and still-queued sibling workflows:** a same-head rerun can finish its primary workflow as `failure` even though the only failed job is a setup-phase job ending `cancelled`, while separate required workflows from that rerun remain `queued`. Treat this as an open CI gate, not a product failure: inspect the prior attempt’s terminal setup error, preserve the rerun’s cancelled job URL, and do not create a rescue card or rerun again while sibling jobs are queued. Re-query the primary run, all sibling run IDs from the PR status rollup, and `gh pr checks <number>` only after those jobs reach terminal states. If the setup error is `Failed to resolve action download info` with provider `Internal Server Error`, `Service Unavailable`, or `Bad Gateway`, classify it as a GitHub Actions service/setup lane; no checkout or product test ran in that job. A raw `/logs` request for the cancelled replacement may return 404, so use the completed prior attempt’s job log as authoritative failure evidence and record the 404 as an unavailable-log boundary, not a new diagnosis.
   - **Notification subject/PR mismatch:** do not trust the PR number or title rendered in an automated email as the run’s ownership. Resolve the run metadata first, then correlate its `head_branch`, full `head_sha`, and `pull_requests[]` to the live PR. A subject referring to PR #1549 can resolve to a follow-up PR #1563 on the same branch; record the canonical run/PR pair and keep any source-card repair scoped to the actual head. If the email arrives through a read-only automated inbox, preserve the correction in Kanban and use the channel’s exact silent sentinel rather than replying with the triage summary.

4. **Inspect attempts explicitly.**
   - **Cancelled-attempt empty-jobs trap:** `gh run view <run-id> --json jobs` and plain `gh run view <run-id>` return **zero jobs** when the latest attempt's conclusion is `cancelled`. Do not interpret empty job output as "no jobs ran" or a workflow-file issue. Query the run metadata first (`gh api repos/<owner>/<repo>/actions/runs/<run-id>`) to get `run_attempt` and `conclusion`; if `conclusion=cancelled`, inspect the prior attempt explicitly via `gh api repos/<owner>/<repo>/actions/runs/<run-id>/attempts/1/jobs?per_page=30`.
   - Enumerate per-attempt jobs with:
     - `gh api repos/<owner>/<repo>/actions/runs/<run-id>/attempts/<n>/jobs`
   - Pull failed logs per attempt with:
     - `gh run view <run-id> --attempt <n> --log-failed`
     - If `gh run view --job <job-id> --log-failed` returns no output despite a failed job, or the job-log blob 404s, fall back to the run summary and job metadata before retrying log retrieval. If needed, retrieve the raw per-job log endpoint and reduce it to bounded failure context:

     gh api repos/<owner>/<repo>/actions/jobs/<job-id>/logs \
       | python3 -c 'import sys,re; lines=sys.stdin.read().splitlines(); pats=re.compile(r"FAILED|ERROR|AssertionError|short test summary", re.I); hits=[i for i,x in enumerate(lines) if pats.search(x)]; shown=set(); [shown.update(range(max(0,i-8), min(len(lines), i+12))) for i in hits]; print("\\n".join(f"{i+1}: {lines[i]}" for i in sorted(shown)))'
     ```
     The API follows the raw-log redirect; the filter retains the useful error and nearby test context without flooding the session.
     - For very verbose Bun/Jest-style suite logs, do not use a broad `ERROR` matcher: expected negative-path test output can flood the result. Filter specifically for terminal summary markers such as `\\(fail\\)|tests failed:|timed out after|test timing:|error: script` and retain a small context window around only those hits.
    - **Raw-log format check:** the job-logs endpoint may return plain UTF-8 text (including ANSI/control sequences), not a ZIP archive. Before using an archive extractor, identify the response with a bounded format probe. For text, decode it directly and print only a small context window around the terminal error. An archive-extractor error is not evidence that GitHub log retrieval failed.
    - **Bounded-first rule:** do not begin with `gh run view <run-id> --log-failed` when the failed step is a monolithic full-suite command. That output can exceed the tool/session limit before its terminal summary arrives. Retrieve the job-log endpoint and apply the bounded terminal-marker/context filter first; fetch broader logs only if the reduced evidence is insufficient.
    - **Browser-artifact fallback when raw job logs are empty:** GitHub can return no useful bytes from the per-job `/logs` endpoint and only a generic `Process completed with exit code 1` annotation, even when a Playwright diagnostics artifact was uploaded. List run artifacts, download the named browser-failure artifact to a disposable directory, then inspect `test-results/**/error-context.md` first. Record the terminal failed-test list plus retry outcome; screenshots/video are corroboration, not the primary triage source. If the artifact identifies multiple deterministic failures, do not collapse them into an infrastructure/timeout diagnosis merely because one neighboring test passed on retry. `gh run view <run-id> --log-failed` remains a secondary fallback, but filter or page its output rather than pasting the whole suite log.
    - **No-valid-artifacts fallback:** if `gh run download` returns `no valid artifacts found to download` for both the governance and browser diagnostics artifacts, stop retrying the download surface. Switch to `gh api repos/<owner>/<repo>/actions/jobs/<job_id>/logs`, inspect the saved payload with `file` first, and treat plain UTF-8/BOM output as authoritative log evidence. If the job log shows runner shutdown or cancellation and no diagnostics artifact exists, report diagnostics as unavailable rather than looping the artifact path.
    - For timeout incidents, retain the exact test/case duration, configured threshold, suite wall time, and runner pressure telemetry printed by the job. Then run the exact focused file/case at least three times on the current base before classifying it as an off-diff shared-suite reliability lane.
   - Do not rely only on the default latest-attempt log.

4. **Check for a wall-clock boundary before calling a repeatable failure "flaky."**
   - Compare the timestamps of the last passing run and first failing run on the same or equivalent SHA.
   - Inspect fixtures and code for fixed `expiresAt`, `issuedAt`, refresh-window, retention, or grace-period values that the real clock may have crossed.
   - If tests expose an injected `now`/clock, trace it through every nested helper. One refresh or validation call that falls back to `new Date()` can make a previously green SHA turn red at a predictable hour.
   - Reproduce the smallest failing test, capture the actual response/error body rather than only the status assertion, and fix the missing clock propagation instead of extending fixture dates. Extending dates only postpones the same failure.

5. **Separate blockers by lane.**
   - If attempts fail for different reasons, classify them separately.
   - Typical split:
     - runner / host-state / capacity / setup pressure
     - workflow/config/auth issue
     - code/path/script regression
     - deterministic wall-clock boundary / incomplete injected-clock propagation
   - **Dedicated-pool bootstrap drift:** when unrelated PRs fail before their test commands across two or more runners in one pool, compare the exact failed step, missing executable/shared library, runner names, and timestamps. Identical dependency-lifecycle exits (for example a postinstall requiring `node`) or Playwright launch exits caused by a missing system library are shared runner-image prerequisites, not PR regressions. Check recent workflow runs to prove cross-PR scope, then append bounded evidence to the existing runner/image-owner card rather than opening per-PR rescue cards. Preserve any earlier real PR-local assertion failures separately; runner remediation does not make those regressions green.
   - **Host-wide `flock` permission drift:** if `flock` exits before the guarded command with `Permission denied`, capture the runner name and inspect the lock's owner/mode plus every runner service account on that *physical host*. A `0644` lock created by one runner account cannot be opened by a second runner account. Do not “fix” intended host-wide serialization by moving the lock to `$RUNNER_TEMP`; that can create independent locks per runner service. Drain the pool, provision a root-managed `/var/lock/<product>` directory with a shared runner group and `2770` directory / `0660` lock modes, restart the affected services for group membership, and verify `flock --nonblock` under each account. See `references/self-hosted-runner-shared-locks.md`.
   - **Post-remediation separation:** a merged repair for one runner failure can reveal different failures in the next validation run. Classify each by **runner and phase**: checkout failures from stale Git refs, test failures from shared temporary-path ownership/state, and cleanup syscall failures are host/workspace lanes unless the PR diff touches them. Keep the original repair as resolved evidence, append the new bounded facts to the existing runner-remediation owner card, and do not call follow-on failures regressions in the lock/workflow change.
   - **Persistent checkout corruption:** when `actions/checkout` fails before dependency installation or tests with `fatal: bad object refs/tags/<name>`, repeated `cannot lock ref 'refs/tags/<name>': ... reference broken`, or a broken `refs/remotes/origin/*` ref, classify it as the affected self-hosted runner's persistent workspace, not a PR regression. A subsequent checkout retry may emit `fatal: --unshallow on a complete repository does not make sense`; that is a retry artifact, not the root cause. `actions/checkout` cleanup may not remove malformed refs. Drain that specific runner/process, inspect `git -C <workdir> fsck --no-reflogs --connectivity-only`, then prefer deleting the repository checkout under `<runner>/_work/<repo>/<repo>` so the next job performs a fresh clone—especially when multiple tag or remote refs are corrupt. A targeted `git update-ref -d <bad-ref>` is acceptable only after inspection when the workspace is otherwise healthy. Do not weaken checkout fetch coverage, delete refs while another job may use the clone, or treat a queued/rerun job as repair evidence until the runner workspace has actually been repaired. See `references/self-hosted-checkout-broken-tag-refs.md`.
   - Preserve those as distinct facts instead of rewriting history around the latest attempt only.

6. **Attribute failures to the PR diff before assigning ownership.**
   - For a PR run, use `gh pr diff <n> --name-only` (or the PR files API) as the authoritative changed-file set. Do **not** infer PR scope from `git diff <merge-commit>^1 <merge-commit>`: a branch merge can carry base-branch changes that were not authored by the PR.
   - Compare every failed test, workflow file, and asserted document/fixture path to that PR file set. A required suite can fail because the branch absorbed pre-existing base drift; report that distinction explicitly rather than calling it a feature regression.
   - Preserve the base SHA and head SHA from the PR API so a later rebase can be evaluated cleanly.
   - **PR merge-ref correlation:** a `pull_request` run may expose a synthetic merge ref and merge SHA (for example, `refs/pull/<n>/merge`) while the notification or PR API exposes the contributor head SHA. Resolve the PR by matching the run's head branch/SHA, then use the PR's changed-file set for attribution. Do not treat the synthetic merge SHA as the authored commit or open a duplicate rescue for base-branch failures.
   - **Stale synthetic merge-ref drift:** a PR run can be created against an older base even after `master` advances, especially when a dependency or governance repair lands between PR creation and job execution. Prove the run's checked-out merge commit parents from the checkout log or fetched `refs/pull/<n>/merge`, and compare that base parent with live `origin/master`. If the failed policy/dependency result is present on the stale merge ref but absent on current master, and the PR changed no dependency/policy files, classify it as stale merge-ref/base drift rather than a feature regression. Record the exact old base, current base, corrective commit, and a fresh-rebase acceptance gate. Do not weaken the policy or edit unrelated dependency files on the feature branch.
   - **Mixed-failure handoff:** when one run has an in-diff deterministic gate failure (such as governance metadata) and a separate off-diff browser/runner shutdown, keep them as separate lanes. Reuse the existing shared runner/browser owner card for the latter and create one scoped PR repair lane for the former; never ask a worker to modify browser tests to compensate for an infrastructure shutdown.

### Partial required CI run with mixed off-diff failures

When a PR's required CI workflow is still `in_progress` but one job has already failed, preserve the run as a live mixed-lane incident rather than waiting for the workflow summary or treating every red job as one regression:

1. Query the run and jobs endpoints and record the immutable head SHA, failed job/runner/step, and any still-running required jobs.
2. Read the failed job's bounded logs before classifying it. A test timeout after a long shared-lock wait, elevated runner pressure, or a governance report that explicitly says `PASS` is runner/workload evidence, not a governance failure.
3. Attribute browser failures against the PR changed-file set. If an unchanged E2E spec fails identically on the initial attempt and retry, file or reuse one narrowly scoped off-diff repair lane; do not modify the feature PR merely because its required check is red.
4. Keep the source PR repair card scoped to in-diff failures. Add the off-diff run/job evidence to the existing shared runner/browser owner or create one new owner card only when no matching lane exists.
5. Do not report the PR's required checks as fully resolved while another required job remains `in_progress`; re-check current status in a later sweep.

This pattern is captured with a concrete mixed-run evidence recipe in `references/partial-required-run-mixed-lanes.md`.

7. **Map evidence to the right follow-up card.**
   - If one lane is already tracked, add evidence there instead of opening a duplicate card.
   - If a later attempt reveals a genuinely separate bug after an earlier host-state blocker was cleared, track that as a separate card with a bounded acceptance contract.
   - Keep board comments explicit about which attempt each blocker came from, the PR/run URL, and whether the failure was in-diff or base drift.
   - **Correct conflicting annotations promptly:** board comments and notification summaries are derived evidence, not authority. If the canonical run/job log disproves an earlier board annotation, append a concise correction to both the source PR card and any shared-owner card that absorbed the bad evidence. State the exact run, attempt, job ID, terminal failure, and corrected lane; preserve the old comment as history rather than editing or silently superseding it. Do not route a host fixture setup error (for example, an `EACCES` writing a shared `/tmp` pathname before the assertion runs) into a timeout/reliability card merely because an earlier summary claimed it was a timeout.

8. **Re-check live production/runtime state before escalating stale deploy failures.**
   - For deploy workflows, verify whether a later rerun already succeeded and moved production forward.
   - If the runtime is now current, keep the follow-up scoped to prevention or the specific remaining bug rather than reporting prod as still stale.

9. **Preserve a single PR repair lane when multiple required checks fail.**
   - **Style/governance correction already pushed:** if the failure belongs to an older PR head and a later corrective commit is already present, inspect that narrow correction and its replacement run before creating work. For deterministic policy failures (for example, raw design values or duplicate selectors), record the original run/job/violations and the correction SHA, then hold the existing Review card for current-head required checks. Do not open a duplicate rescue card or treat the old run as the merge gate.
   - Search the live board for an existing PR-linked repair card before filing another rescue card.
   - If a claimable repair card already owns the PR, append bounded evidence for each distinct additional failure: run/job URL, retry behavior, test or step, runner, and attribution status.
   - Do not send concurrent workers to push the same PR branch merely because their likely file edits differ. Create a second card only when ownership can be safely separated; otherwise make the additional failure an explicit merge gate on the existing lane.
   - If local reproduction cannot run because the current environment lacks a required test runtime, record that narrowly as an attribution gap. Do not misclassify the CI failure as transient or PR-local without live evidence.

### Job stuck queued despite idle matching runners (deaf listener)

When a job stays `queued` for >15 minutes, every runner carrying its required label reports `online` and `busy: false`, and re-triggering the workflow queues identically:

1. Classify this as a runner-dispatch failure, not a workflow/config problem. First rule out the two lookalikes: a non-terminal prior run holding the workflow's `concurrency` group, and a label mismatch (the job's `runs-on` must be a subset of an online runner's labels).
2. The GitHub runner API signals only process liveness, not dispatch liveness — a wedged listener keeps heartbeating but accepts no jobs. Confirm via the runner's `_diag/Runner_*.log`: only RSA-key-reload lines and no `JobDispatcher` entries for hours means a deaf listener. A preceding cancellation / `renewjob ... NotFound` / lost-communication entry is the usual trigger.
3. Fix by restarting the runner's systemd service (`sudo systemctl restart actions.runner.<org>-<repo>.<runner-name>.service`); the queued job is picked up within seconds. Do not move tags, cut a new version, or re-trigger as the primary fix. Full recipe in the `self-hosted-ci-operations` skill, `references/deaf-runner-listener.md`.
4. Treat the incident as runner-infrastructure, not a release/test regression. The tag/SHA is unaffected; once the listener recovers, the original immutable run proceeds.

### SIGTERM / exit-143 full-suite classification

When a required PR or push job ends with `SIGTERM`, `Terminated`, or exit `143` while a monolithic test suite is still running:

1. Capture the job and failed step, runner, final visible test file, signal, and whether a terminal assertion or Bun timeout summary appears.
2. Do **not** attribute the failure to the visible test file merely because it was in progress when the process stopped. Treat it as a runner/workload interruption until focused reproduction or runner evidence proves otherwise.
3. Compare the PR changed-file set to the visible test surface. If it is off-diff, preserve that fact and keep the feature PR blocked only on the required check; do not open a feature rescue card.
4. Query sibling required workflows before reporting: independently passed browser gates strengthen the separation from a product regression, but do not make the failed required check optional.
5. Reuse an active shared-suite/runner reliability card if one owns the mechanism; append the canonical run URL, SHA, runner, step, signal, and no-assertion fact. Create a separate card only when evidence demonstrates a distinct causal lane.

### Post-merge full-suite timeout classification

When a push-to-`master`/`main` run fails only because unrelated test cases cross Bun's per-test timeout:

1. Preserve per-attempt evidence: failed test names, elapsed durations, runner names, and the exact commit/run URL. Different unrelated files timing out on different self-hosted runners are a shared-suite reliability signal, not immediate evidence against the merged diff.
2. Compare the merge diff to the failed test surfaces. Do not reopen or create a rescue implementation card for a merged PR when the files are outside its change set.
3. At the failed SHA on current base, run the exact failing files at least three times. Record results and durations; focused passes alone do not prove the full suite is fixed.
4. Rerun only the failed GitHub job. If the rerun passes and all focused repeats pass, classify the incident as transient/shared-suite runner-load flakiness, comment that evidence on the merged source card, and do not create a duplicate rescue card.
5. Create or revive a dedicated reliability card only when the rerun fails again, the focused reproduction fails, or recurrence demonstrates a persistent shared cause. Keep it separate from the merged feature card.

### Immutable release retry boundary

For a semantic-release workflow that fails **before** immutable artifact publication or deployment:

1. Confirm the exact failed step and prove the failure occurred before any release media upload, runtime swap, or downstream deployment.
2. Repair only the bounded runner/host condition (for example, reclaim verified stale test workspaces or tool caches), then re-check capacity.
3. Rerun the **same** workflow/tag only when the immutable payload was never created or changed. Do not move the tag or cut a second version merely for a pre-publication capacity gate.
4. If the workflow later succeeds but the release-cutter process did not create a GitHub Release object, verify the tag SHA and terminal workflow outcome, then create one non-draft release targeted at that exact immutable SHA. Re-query its draft/prerelease/target fields.
5. For a capacity failure, inspect the same runner filesystem *after* its built-in cleanup before deleting anything: record `df -h <runner-workspace>`, then size the runner work directory, package/tool caches, and inactive worktrees independently. Reclaim only plainly regenerable caches or completed inactive workspaces; preserve active task worktrees, source checkouts, tags, and published artifacts. Re-check free space against the workflow threshold before rerunning the exact immutable run/tag.
6. If any immutable media already exists, compare the existing manifest/payload identity before retrying. A mismatch is a release-pipeline defect: stop rather than overwriting or rebuilding under the same version. **Exception — CI-only re-trigger false alarm:** if the mismatch is caused by CI/test-only commits landing on the same tag after a fully successful release run (the manifest commit is the original version-bump SHA, the deploy SHA is a later CI-fix commit, and `git log --oneline <manifest-sha>..<deploy-sha>` shows only `.github/`, test, or CI-config changes), the guard is working correctly. The deployed binary is functionally identical. Report the failure as a false alarm, verify the release is live, and take no re-tag/bump/rerun action. See `github-actions-run-triage` skill, `references/post-tag-ci-only-retrigger-false-alarm.md`.

### Release verification interrupted after runner queueing

When a release verification job starts late on a shared self-hosted runner and its test process exits `143` / `SIGTERM` without a terminal assertion failure:

1. Do not label the currently displayed test file as the failing product surface. Capture the exact signal, test file in progress, job start/completion timestamps, and whether any assertion or Bun timeout summary appeared.
2. Correlate the job interval with the runner service journal. A sequence of unrelated CI jobs immediately before the release verification job is concrete evidence of runner contention/queue interaction; record it separately from test failures.
3. Inspect the runner unit's effective `RuntimeMaxUSec`, stop signal, and timeout values, plus current disk headroom. These distinguish an OS/service cap or capacity condition from a queued-workload failure. Do not infer a service runtime cap merely from SIGTERM.
4. Check downstream release jobs. If publish and deployment jobs are skipped, state precisely that no immutable release media or runtime deployment occurred; the tag itself remains immutable.
5. Reuse an existing shared-suite/self-hosted-runner reliability card when one already owns the mechanism. Add the release run URL, SHA/tag, job/log evidence, and non-publication boundary rather than filing a duplicate release incident.
6. Do not rerun the release during notification triage. After a bounded mitigation and fresh verification, rerun the same immutable tag only if no release media was created or changed.

### Release-tag / package.json version-gate mismatch

When a tag-triggered release workflow fails fast in a `Resolve release version` (or equivalent version-gate) step with an error of the form `Release tag v<X.Y.Z> must match package.json version v<A.B.C>`:

1. Classify this as a **release-process / tagging mistake**, not a runner, workflow-config, or product-test failure. The gate script (for example `.github/deploy/resolve-release-version.sh`) is working as designed: it requires the pushed tag to equal `v$(package.json version)`.
2. Verify live state before reporting: read `package.json` `version` at the tag's commit, list tags with `git tag --sort=-creatordate`, and check whether earlier sibling tags (for example the prior `v<X.Y.Z-1>`) were also cancelled/failed for the same reason. Multiple consecutive mismatched tags means the version was never bumped across several releases.
3. The durable fix is to make tag and manifest agree, then re-trigger the immutable tag pipeline:
   - bump `package.json` `version` to the intended release (on `master`, via the normal PR/commit path — do not edit the canonical checkout directly if a worktree/PR policy applies),
   - delete the bad tag locally and on origin (`git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z`),
   - re-create the tag on the version-bump commit and push it (`git tag vX.Y.Z && git push origin vX.Y.Z`), which re-fires the tag-triggered Release workflow.
   - Alternatively cut the next version (`v<X.Y.Z+1>`) if the mismatched tag was never meant to ship. Confirm the intended target version with the operator before deleting/re-pushing tags.
4. Do **not** weaken or bypass the version gate to force the run green; the mismatch is real and the gate is protecting immutable release identity. Do not move a tag silently — record the delete/re-tag in the handoff.
5. Downstream deploy/publish jobs will show as skipped (`-`) because the verify job failed first; state precisely that no immutable release media or runtime deployment occurred.

### Post-publication GitHub-artifact quota failure in a release channel

When a release workflow has already uploaded immutable payloads and signed manifests to its durable release store (for example R2), then fails at `actions/upload-artifact` with a GitHub artifact-storage quota/API error:

1. Capture the run URL, SHA/version, failed job/step, and exact quota/API text. Inspect preceding steps to prove which immutable uploads, public-origin refetches, signatures, or byte comparisons completed before the failure.
2. Inspect downstream jobs before calling the upload best-effort. If a channel/pointer job downloads those GitHub artifacts, the artifact service is part of the release control plane; a blanket `continue-on-error` would create missing-input or unsafe-publication risk.
3. Separate the two concerns: immutable payloads may be durably present while release/channel publication is incomplete. Do not report the release fully published, rerun the immutable workflow, move tags, or manually advance a stable pointer during inbox triage.
4. Search for a card owning the exact upload surface. A prior quota-tolerance repair for unrelated CI evidence does not automatically cover a runner/release artifact-transport contract.
5. When unowned, file one scoped repair: have channel construction obtain and validate the exact signed manifests from a durable immutable provenance-checked source, or keep it fail-closed with a precise error. Preserve target/version binding, signatures, immutable upload/refetch verification, and stable-pointer compare-and-swap. Test both normal publication and artifact-service unavailability.

### Local release-proof contract drift

When a release workflow compiles/publishes a candidate binary but fails in a local CLI installation or diagnostic-proof step before an environment deploy:

1. Identify the exact phase boundary: distinguish immutable artifact publication from local proof, SSM/runtime deployment, and public freshness verification. Do not report a skipped environment deploy as a runtime failure.
2. Reproduce the probe against the exact tagged SHA and compiled candidate under the same bounded conditions (especially an empty temporary `HOME` and no configured vault). Capture stdout, stderr, exit status, and the installer assertion.
3. Compare the probe's expected structured contract with the candidate output. A common failure is a stale exact profile/version assertion after a CLI JSON projection evolves while retaining the required semantic fields.
4. Preserve the fail-closed release proof. Repair it to validate an explicitly supported structured contract (profile compatibility plus required non-secret fields), and add fixtures for accepted current output and rejected malformed/missing/incompatible output. Do not simply delete the check or broadly accept arbitrary JSON.
5. Add a pre-publication CI gate that compiles the candidate and executes the same local-install proof, so this class of mismatch cannot first appear after immutable release media is published.
6. Treat the failed tag as immutable: do not move it, overwrite its media, or perform a manual one-off environment deploy. Create one scoped repair card for a fresh normal release path, unless an equivalent live card already owns it.

### Workflow-source contract failures after a verifier insertion

When a platform-boundary job passes checkout, runtime setup, dependency installation, and most tests but fails an exact-string/source-contract assertion after a deploy workflow gains a new verifier or bootstrap fragment:

1. Treat it as a deterministic in-diff test-contract failure, not macOS/runner infrastructure, provided the failure occurs inside the test command and the changed-file set includes the workflow or its verifier path.
2. Capture the expected and received serialized fragments, including ordering. The new security or provenance verifier must remain in the runtime script in the reviewed order; update the test contract to assert that order rather than removing or bypassing the verifier.
3. Keep this repair on the existing PR/source-card lane unless the evidence identifies a separate off-diff mechanism. Do not file a duplicate runner rescue card merely because the notification says “platform boundary.”
4. Re-run the focused platform suite, then wait for every required sibling job to reach a terminal state before calling the PR review gate resolved. A passing browser sibling does not clear a failed platform-boundary check, and a pending build job remains an open gate.

### Route-registration failures cascading into browser gates

When a PR adds a server route but omits a required route-composition/ownership registry entry, platform-boundary tests may fail deterministically and browser jobs may fail secondarily when their web server cannot boot. Classify the lanes together when the browser log shows the same startup exception: the macOS/platform job is the primary in-diff failure, while the browser assertion (often a generic `response.ok()` failure) is a consequence, not evidence of browser-runner instability.

1. Capture the exact missing route key and registry file/line from the primary job's bounded log or annotations.
2. Compare the PR changed-file set: confirm the route implementation is in-diff and the registry file is absent or incomplete before assigning ownership.
3. Inspect browser setup/runtime steps and retry behavior. If checkout, browser install, runtime preflight, and both attempts pass setup but the web server emits the same missing-registry exception, preserve it as corroborating evidence for the PR-local lane.
4. Do not open a browser-infrastructure rescue card or modify browser tests merely because a cross-browser job is red.
5. If any same-head required sibling remains queued or in progress, do not rerun or create a rescue card during notification triage. Reconcile after all current-head checks are terminal, then keep one PR repair lane covering the registry fix and rerun proof.

### Fixture/runtime contradiction in browser artifacts

When a browser failure artifact reports a runtime state that contradicts the exact test fixture (for example, the UI says a challenge expired even though the intercepted response supplies a far-future `expiresAt`), classify this as an evidence contradiction first—not as proof of clock skew, stale source, or runner failure.

1. Retrieve the test and relevant app-shell/config files at the failed SHA, and confirm the PR changed-file set. If the failing test and expiry logic are unchanged, mark the failure off-diff and keep the feature PR's repair lane clean.
2. Inspect the retained `error-context.md`/trace for the page snapshot, request URL, response body, and source frame. Verify that the route interception pattern actually matches the request origin/path and that the checked-out bundle contains the expected fixture consumer.
3. Reproduce the smallest failing test on current base and, when relevant, the affected runner lane. Compare `Date.parse(expiresAt)` and `Date.now()` at the consumer boundary; do not “fix” the test by disabling expiry or broadly increasing timeouts.
4. Reuse an existing owner only when the mechanism matches. A deterministic auth/fixture contradiction is a separate lane from generic browser throughput or `/dev/shm` timeouts, even when both occur on the same runner. Add bounded evidence to the source card and create one narrowly scoped follow-up card when no owner exists.
5. For mocked OTP expiry specifically, record the fixture's far-future `expiresAt`, the rendered disabled verify button, and whether the in-job retry reproduces the same state. Treat a repeated contradiction as a browser/runtime owner lane; do not edit unrelated auth/session code merely because the required check is red. Rerun only the failed job on the unchanged head before changing attribution.

### Source-path verification before board handoff

When a browser or route test fails during setup, inspect the failing helper in the exact test file before naming the request endpoint or route family in a board comment. CI log prose may identify a generic API failure while the helper reveals the actual call (for example, a folder-create helper posting to `/api/vault/folders`, not a nearby tree-delete route). If a prior comment names the wrong endpoint, append a concise correction; preserve the run, attempt, and attribution evidence rather than rewriting history.

### Browser request URL contradiction: source/config versus observed relative request

When a browser-job log reports a relative-path parse error (for example, `TypeError: "/api/..." cannot be parsed as a URL`) despite the failed SHA containing a helper that calls `new URL(path, baseURL)`:

1. First establish whether the supplied numeric ID is a **job** ID or a run ID. For a job ID, query `GET /repos/<owner>/<repo>/actions/jobs/<job-id>` to obtain the canonical `run_id`, SHA, runner, and job URL.
2. Prove the runner checkout from the checkout log (`HEAD is now at <sha>`), then retrieve the exact test file and Playwright config at that SHA via the GitHub contents API. Do not rely on a potentially stale local checkout.
3. Capture all application-specific E2E variables from the actual test-step env block. If no explicit port/run-ID override exists, derive the configuration's base URL from its documented GitHub run-ID inputs and the workflow job key. Label it as a **config-derived** base URL, not a runtime echo.
4. Attribute precisely: `new URL(relative, absoluteBase)` returns an absolute URL. Playwright's `context.request.post` can emit the quoted relative-path parser wording when it receives a relative value. If the initial failure log/artifact contains no file-frame stack, say that directly; do not invent a stack frame. Report the source/config-versus-observed-value mismatch as a contradiction that requires follow-up rather than asserting the source explains it.
5. Inspect retries separately. A retry that reaches an already-used bootstrap/claim setup failure after the first attempt is setup-state contamination, not independent reproduction of the original URL failure.

### Trace-normalized URL contradicts a relative-path parse error

When the checked-out source explicitly resolves an API path with `new URL(relativePath, testInfo.project.use.baseURL)`, but the failure text says the relative path cannot be parsed:

1. Treat the contradiction as an evidence problem, not proof of an empty or relative `baseURL`.
2. Inspect the retained Playwright trace, not only the reporter text. Compare context creation (`baseURL`), the API call's recorded `params.url`, the protocol/network resource URL, and the call's source-frame path/line.
3. If all trace layers show the absolute URL while the error preserves the original relative path, classify the observed evidence as a request-layer/error-reporting mismatch or an uninstrumented internal parse. Do not claim stale source or an alternate application code path without a file-frame or request event proving it.
4. Run a disposable probe using the exact config inputs and print `testInfo.project.use.baseURL`, its type, and `new URL(relativePath, baseURL).toString()`. Disable only the probe's web server, keep the project/config merge and environment inputs unchanged, and create the probe under `/tmp`; remove it after verification.
5. Report the boundary precisely: the trace can establish what URL Playwright recorded/emitted, but cannot establish the deeper internal parser frame when the error event has no stack.

See `references/trace-normalized-url-contradiction.md` for the bounded evidence and probe recipe.

### Runner-loss first attempt followed by a reproducible rerun

A rerun can invalidate an earlier narrow classification without making the earlier evidence false. When attempt 1 ends in a self-hosted runner communication loss during a test step, but attempt 2 on the same head reaches terminal application assertions or interaction timeouts:

1. Preserve the attempt-1 runner-loss fact with its job and runner identity.
2. Treat the completed rerun as the current PR gate. Extract every terminal failing test, retry outcome, and changed-file attribution from attempt 2.
3. If the failures touch the PR's changed surface, classify the rerun failures as PR-local blockers; do not keep calling the entire workflow infrastructure noise.
4. Correct the source-card annotation promptly. State that the prior classification applied only to attempt 1, link both job URLs, and keep one existing PR/card repair lane rather than opening a competing rescue card.
5. Keep independent in-diff failures from other required workflows (such as policy ratchets) as separate gates in the same source-card handoff.

## Reference recipes

- `references/zero-step-actions-admission-followup.md` — bounded evidence and board-reconciliation recipe for recurring account-level Actions budget/admission failures.
- `references/pr-merge-ref-and-mixed-lane-triage.md` — correlate synthetic pull-request merge refs with authored heads and split in-diff versus runner/browser failure lanes.

## GitHub-notification email containment

### Cancelled required jobs rendered as `fail` by `gh pr checks`

`gh pr checks` can render a cancelled required job as `fail`, even when the canonical check-run conclusion is `CANCELLED`. Before treating that row as a product failure, query the run metadata, attempt-specific jobs, and check-run annotations. An annotation such as `The job was not acquired by Runner of type self-hosted even after multiple attempts` means no checkout or test ran; classify it as runner dispatch evidence. If another required workflow for the same head is still `queued` or `in_progress`, the PR remains an open CI gate: do not rerun again, create a rescue card, or claim the feature is broken until the pending sibling reaches a terminal state.

When reconciling this evidence into an existing board card, re-query the live PR head SHA and `gh pr diff --name-only`; do not trust a stored card head or changed-file count because the PR may have advanced since the card was created. Append a correction with the current head, canonical run/job URLs, and corrected diff scope, preserving the old comment as history. Reuse the existing PR owner and keep the current-head pending sibling as the explicit merge gate rather than opening a duplicate rescue lane.

When a GitHub Actions alert arrives through a read-only operational inbox, treat the email strictly as intake—not a conversation target. Record bounded run evidence in the board/source-card lane and do not reply to `notifications@github.com` or emit progress/tool payloads into that thread. If the channel adapter offers a normal threaded reply after investigation, return exactly its documented silent sentinel (typically `[SILENT]`); never put operational notices, configuration diagnostics, or a status summary in that email thread. Automated delivery adapters can retry such replies, consume organizational mail quota, and generate mailer-failure noise without changing the CI outcome. If the inbound channel reports a delivery failure, stop replying to that thread; preserve the investigation and handoff in Kanban instead.

### Rerun attempt cancelled after setup-only failures

When a notification reports a failed workflow but live metadata shows a later rerun attempt ended `cancelled` with no runner and no steps, treat that attempt as non-evidence rather than a new regression. Inspect the preceding attempts explicitly: if they failed in `Set up job → Getting action download info` with `Bad Gateway`, `Service Unavailable`, or equivalent provider errors on different runners, classify the lane as a GitHub Actions service/setup outage; no checkout or product test ran. Keep any earlier in-diff test failure from a separate workflow or earlier attempt as its own lane. Query the paired required workflows and the PR rollup before acting: a sibling job still `queued` means the gate is open, not resolved. Add one correction to the existing source/repair card, do not create a duplicate rescue card, and do not issue another rerun while required siblings remain queued. For read-only automated inboxes, preserve the correction in Kanban and return the channel's silent sentinel.

### Notification is already superseded by a queued retry

A failure email may arrive after GitHub has already started a failed-job rerun. Treat the email's red attempt as historical immediately when live run metadata shows `run_attempt` increased and the replacement job is `queued` or `in_progress`:

1. Query the canonical run API and `/jobs` endpoint, not only the email or default `gh run view` summary. Record the old failed job URL/runner/step and the replacement job URL/status.
2. Query the live PR rollup (`gh pr checks <number>` or `statusCheckRollup`) and confirm the current head SHA still matches the failed run. Keep sibling checks' current state separate from the superseded failure.
3. Do not create a rescue card, rerun again, or attribute root cause while the focused replacement is pending. A queued replacement is evidence of an open gate, not a verdict.
4. If the failed job stopped during workflow setup with errors such as `Failed to resolve action download info`, `Service Unavailable`, or `Bad Gateway`, classify that attempt as a GitHub Actions service/setup lane with no product test executed. Reconcile the replacement attempt before deciding whether an infrastructure owner card is warranted.
5. For a read-only automated mailbox, preserve evidence in Kanban/source-card state when an owner exists and return only the channel's silent sentinel; never put the triage summary in the notification thread.

## Cross-workflow action-download outage with a rerun

When a replacement attempt fails during `Set up job → Getting action download info` with `Bad Gateway`, `Service Unavailable`, or equivalent provider errors, and the same setup-only failure appears across different runners or hosted platforms (for example Linux/self-hosted browser, Linux build, and macOS), classify that lane as a GitHub Actions service/setup outage. The failed jobs did not reach checkout or product tests; do not attribute them to the PR diff, runner image, or browser suite. Preserve any earlier attempt's completed in-diff test failures as a separate lane on the existing source card. Before creating a rescue card, re-query every affected run's `run_attempt`, terminal conclusion, job URL, runner, and `gh pr checks`; reuse the existing source/owner card and defer rerun until action-download resolution has recovered. A passing sibling job does not clear the failed required checks, and a notification naming one workflow may conceal the same provider outage in sibling required workflows.

## Good evidence bundle

A durable handoff should include:
- run URL
- attempt number(s)
- failed job and step per attempt
- exact failing error lines
- SHA / tag / branch
- whether the failure is runner-state, workflow-state, or code-state
- whether production/runtime later advanced despite the earlier failed attempt
- which board card owns each blocker lane

## Installed `gh` schema fallback

`gh pr view --json` projections vary by installed GitHub CLI version. If a requested field is rejected (for example `baseRefOid`), do not keep retrying nearby guessed field names during incident triage. Use the supported projection for the fields needed (`baseRefName`, `headRefOid`, `files`, `statusCheckRollup`) and query the pull-request REST endpoint when an immutable base SHA or another omitted field is required. The rejection is a CLI-surface mismatch, not evidence that the PR metadata is unavailable.

### Immutable release rerun: re-audit downstream gates

When a pre-publication release attempt fails at a bounded runner-capacity gate and the same immutable tag is rerun after capacity recovery, do not stop when the originally failed job turns green. A failed-job rerun can unlock downstream deployment, collaboration, and finalization jobs that were skipped in attempt 1. Re-query the full attempt-2 jobs list until terminal, then inspect every newly executed downstream failure separately. Distinguish: (1) capacity recovery and publication success, (2) runtime deployment/verification results, (3) collaboration or release-finalization configuration failures, and (4) whether the GitHub Release object was actually finalized. Never claim the release is complete solely because publication succeeded; the run's terminal conclusion and finalization job are authoritative. Record the immutable SHA, attempt number, canonical job URLs, and any new downstream configuration failure on a separate owner lane rather than reopening the resolved capacity incident.

## Shared-suite timeout with artifact-quota evidence

When a required PR job fails because a repository-owned full-suite harness reaches its wall budget and emits SIGTERM/SIGKILL or exit 124 without a terminal product assertion:

1. Retrieve the raw job log through the jobs API and reduce it to bounded terminal markers (`Bun test suite timeout`, harness wall-budget lines, `exit code 124`, and the governance result). Do not begin with an unbounded `gh run view --log-failed` dump.
2. Record the exact lane, elapsed budget, runner, and whether the harness identified a currently executing file. Treat files listed as “not proven complete” as incomplete evidence, not failed tests.
3. Compare the PR changed-file set with the harness/workflow and failed test surfaces. If the harness is off-diff and governance passes, classify the current PR gate as red but the evidence as shared-suite/workload reliability, not a feature assertion regression.
4. Treat an accompanying `Failed to CreateArtifact` / storage-quota error as a separate evidence-transport problem. It does not explain the test timeout and does not make the required check green. Record the artifact boundary once and stop retrying the artifact path unless quota recovery is independently verified.
5. Reuse the existing PR review/source card as the sole merge-gate owner; append bounded evidence and avoid a duplicate rescue card unless repeat evidence establishes a distinct persistent owner lane. A passing browser sibling corroborates separation but does not clear the failed required job.

This pattern is captured in `references/shared-suite-timeout-and-artifact-quota.md`.

## Current-state reconciliation after an account-level admission incident

A prior zero-step Actions billing/admission failure is historical evidence, not a permanent gate. Before preserving a blocker or refusing fresh CI proof, query current run metadata and jobs. If a newer run acquires a runner, reaches checkout/dependency setup, and executes tests, explicitly reconcile the owner card to the live state. Keep the old admission incident for history, but do not let stale blocker comments suppress current claimability or misclassify the newer run.

When the newer run executes and fails later, decompose the result: (1) in-diff deterministic test/contract failure, (2) separate artifact-storage or evidence-publication failure after validation, and (3) any remaining admission issue affecting other workflows. Artifact quota/API errors after the test command do not explain a failed assertion and do not make the required check green. Append one correction to the source and incident cards naming the fresh run/job, runner acquisition, terminal failure, and whether the old blocker remains active.

## Pitfalls

- Treating the latest attempt as if it were the only attempt.
- Treating a GitHub CLI projection error or an absent `gh release view <tag>` result as release-state evidence. The installed CLI's accepted release fields can differ (for example, `targetCommitish` rather than `target`); retry with the fields listed by the error, and use `gh api repos/<owner>/<repo>/releases` as the authoritative fallback to distinguish a missing release object from a CLI schema mismatch.
- Treating a recurring scheduled watchdog admission failure as a new incident on every notification. Reuse the existing billing/admission owner, append one bounded run/job corroboration, and separately reconcile the observed release run's publication, deployment, finalization, and GitHub Release-object state.
- Querying attempt metadata through `gh run view --json` / `gh run list --json`: the CLI run schema has no attempt field (requests for `attempt` or `runAttempt` are rejected with "Unknown JSON field", though the error usefully prints the valid field list). Use `gh api repos/<owner>/<repo>/actions/runs/<run-id>` for `run_attempt` and the `/attempts/<n>/jobs` endpoint for per-attempt job lists; the `--json jobs` projection only reflects the latest attempt.
- Filing one blended incident card when attempts actually show two independent lanes.
- Reporting a deploy as still broken without checking whether a later rerun already advanced production.
- Treating runner-capacity failures as code regressions in the release PR.
- Losing earlier attempt evidence after a later attempt fails deeper in the workflow.
- Calling a failure flaky after reruns fail at the same wall-clock-sensitive assertions. A SHA can pass earlier and fail later without code drift when real time crosses a fixture expiry/refresh threshold; compare run timestamps and follow the injected clock through nested calls.

## Verification checklist

- [ ] Run metadata captured from live GitHub output.
- [ ] Attempt-level jobs/logs inspected, not just latest-attempt summary.
- [ ] Distinct blocker lanes separated when evidence supports it.
- [ ] Existing board cards reused when appropriate.
- [ ] Live runtime/deploy state rechecked before final reporting.
