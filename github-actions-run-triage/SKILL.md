---
name: github-actions-run-triage
description: Triage GitHub Actions failures, reruns, and ambiguous alerts.
metadata:
  hermes:
    tags: [github, github-actions, ci, deploy, triage, workflow-runs]
    triggers:
      - "A GitHub email or alert says a workflow failed"
      - "Investigate a deploy run failure"
      - "Decide whether to file follow-up work from a workflow notification"
      - "Check whether a workflow is still failing or already recovered"
---

# GitHub Actions Run Triage

Refs: `references/`; budget gates: `actions-budget-admission-triage.md`; zero-step admission: `references/zero-step-actions-admission-failures.md`. For an off-diff failure whose exact focused test passes on clean base and PR head, follow `references/off-diff-contract-mismatch-and-rerun.md`: comment evidence, rerun the unchanged head, and avoid unrelated rescue code.

## Review-card CI holds

See `references/shared-browser-projection-repro.md` for exact-head reproduction and source-card ownership.

When a failed run maps to an existing source card in `review`, preserve that card as the sole owner of an in-scope repair: add a compact evidence comment with the live PR head SHA, run URL/ID, failed job and assertion, and whether a focused local reproduction confirms it. Do not create a duplicate CI-rescue card for the same branch.

Some Kanban installations accept `block` only from `running` or `ready`, not `review`. If a review-card block transition is rejected, do not use a direct DB mutation just to change presentation. Leave the evidence comment, report that the card remains `review` despite the CI hold, and treat the red required check as a merge stop. File a separate repair card only for a deterministic failure that is demonstrably outside the source PR's diff; cite the source PR/card and preserve the tested contract.

## Superseded PR-head notification triage

A failed notification can already be obsolete when a corrective commit is pushed immediately afterward. Before filing a CI-repair card or treating a Review card as blocked:

1. Resolve the notification run and record its failing head SHA, job, and failing step.
2. Read the live PR (`gh pr view <n> --json headRefOid,statusCheckRollup,mergeable,mergeStateStatus`) rather than assuming the notified SHA is still current.
3. If `headRefOid` differs, inspect the intervening commit(s) and the current changed-file list to determine whether they directly address the failure.
4. If the current head has a fresh pending rollup, add provenance to the source card and hold for those checks; do **not** create a duplicate repair card.
5. Create a repair only when the failure persists on the current head, the corrective change is unrelated or insufficient, or the current checks fail again.

Keep the distinction explicit in the card comment: *notification head failed; current head is pending, failed, or green*. This avoids dispatching workers against a repaired branch while preserving the original failure evidence.

## Truncated notification URLs and short IDs

Do not pass a visibly shortened Actions run ID from an email alert straight to `gh run view`: GitHub notification renderers can truncate long numeric IDs in the displayed URL (for example, showing `30505` for a full run ID beginning with those digits), which yields a misleading API 404.

When an alert includes a commit SHA, workflow name, title, branch, or finish time, resolve the live run instead:

```bash
# First try the full SHA when present.
gh run list --repo <owner/repo> --commit <full-sha> --limit 20 \
  --json databaseId,displayTitle,workflowName,headSha,headBranch,status,conclusion,url,createdAt,updatedAt

# If the commit filter cannot resolve it, inspect recent runs for the named workflow.
gh run list --repo <owner/repo> --workflow <workflow-name> --limit 30 \
  --json databaseId,displayTitle,workflowName,headSha,headBranch,status,conclusion,url,createdAt,updatedAt
```

Match on the full head SHA plus the alert's title/branch and time window, then use the returned `databaseId` for `gh run view`. Record both the notification's displayed value and the verified live URL when they differed. Do not claim the workflow is unavailable merely because the shortened URL 404s.

## When to use

Use this skill when the input is a GitHub Actions failure signal rather than a direct code/task request:

- notification emails about failed workflows
- chat alerts pasted from GitHub Actions
- deploy alarms tied to a workflow run URL or run id
- questions like "did this deploy fail?" or "what should we queue from this run?"

This skill is about **workflow-run truthfulness**: prove the live state of the run before creating follow-up work or telling the user production is broken.

## Core rule

A failure notification is evidence that **some attempt or job failed at some point**. It is **not** proof that the workflow is still failing when you investigate.

Always separate:

1. **Current live run state** — is the run now `in_progress`, `completed/success`, or `completed/failure`?
2. **Attempt history** — did attempt 1 fail and a later attempt succeed?
3. **Underlying issue** — if the run recovered, is there still a narrower reliability problem worth tracking?

## Required triage sequence

1. Query the live workflow run by run id.
   - Capture `status`, `conclusion`, `run_attempt`, `head_sha`, `head_branch`, and `html_url`.
2. Query the current job list for the run.
   - Identify which jobs are currently completed, running, skipped, or failed.
3. If the run has reruns / multiple attempts, inspect the earlier attempts explicitly.
   - Compare attempt 1 / attempt 2 / latest attempt job results.
   - Practical CLI note: `gh run view <run-id> --json ...` may not expose the attempt number. When you need authoritative rerun data, query `gh api repos/<owner>/<repo>/actions/runs/<run-id>` for `run_attempt`, then inspect attempt-specific jobs with `gh api repos/<owner>/<repo>/actions/runs/<run-id>/attempts/<n>/jobs`.
4. Only after proving the current state, decide the message:
   - **Current run failed** → report active failure.
   - **Current run succeeded after rerun** → report that production/deploy is now green, but preserve the failed-attempt evidence.
5. If a recovered run exposed a real reliability issue, create a **narrow follow-up item** for the root cause instead of describing the whole deploy as still broken.

## Important pitfall: post-tag CI-only commits re-trigger an already-completed immutable release

A tag-triggered release workflow can be re-triggered when CI-only fix commits land on the same tag after the initial release run already succeeded. The publish script's immutability guard detects that the existing release manifest commit does not match the new deploy SHA and exits with a mismatch error such as `release manifest commit mismatch: <old-sha> != <new-sha>`. This is a **false alarm**, not a release failure.

Common shape:

- the first Release run (triggered by the version-bump commit) succeeded fully — CLI binaries published, all environments deployed;
- one or more CI/test-only fix commits then land on the same tag (for example `fix(ci): ...` PRs merged after the bump);
- the tag is re-pushed or the workflow re-triggers on the new commits;
- the publish script finds the existing immutable release in object storage, compares the manifest commit to the new deploy SHA, and exits with the mismatch error.

Required sequence:

1. Capture the failing run's deploy SHA and the error's manifest commit.
2. List recent runs for the same workflow and tag: `gh run list --workflow=Release --limit 5 --json databaseId,status,conclusion,headBranch,createdAt,displayTitle`.
3. If an earlier run on the same tag has `conclusion=success`, inspect its jobs to confirm all release stages completed (CLI publish, HQ deploy, dev, gly).
4. Trace the commit range between the manifest commit and the deploy SHA: `git log --oneline <manifest-sha>..<deploy-sha>`. If every commit in the range is CI/test-only (no application code changes), the deployed binary is functionally identical.
5. Verify the release is live: check the public release manifest URL and environment health surfaces.
6. Report the failure as a **false alarm** — the immutability guard worked as designed. No re-tag, bump, or rerun is needed.
7. Do not create a rescue card. Optionally note the friction: the workflow should either skip re-triggering on CI-only tag updates or the publish script should exit 0 with a skip message when the version is already published.

Good pattern:

> The email named run 30313634889 (v0.1.49), which failed with `release manifest commit mismatch: 2a00cb92 != 4db02f3b`. But run 30311741032 on the same tag succeeded fully — CLI published, HQ/dev/gly deployed. The four commits between the manifest SHA and deploy SHA are all CI-only fixes. The release is live and the mismatch is the immutability guard working correctly. No action needed.

Reference: `references/post-tag-ci-only-retrigger-false-alarm.md`

## Important pitfall: concurrent duplicate release runs on the same tag

A tag-triggered release workflow can produce **multiple distinct run IDs** for the same tag — for example when a concurrency group cancels the first run and a retry creates a new one, or when the tag is pushed twice in quick succession. The failure notification names one run, but a sibling run on the same tag may be actively succeeding.

Required sequence:

1. After resolving the alerted run, list recent runs for the same workflow filtered by the same `head_branch` (the tag name): `gh run list --workflow=Release --limit 5 --json databaseId,status,conclusion,headBranch,createdAt`.
2. If another run exists on the same tag with `status=in_progress` or `conclusion=success`, inspect its jobs before reporting the release as failed.
3. Classify the alerted run precisely: if its latest attempt is `cancelled` and a sibling run is actively deploying, the alert is **superseded** — not a release failure.
4. Report the sibling run's live job state (which stages passed, which are in progress) as the authoritative release status.
5. Do not create a rescue card from the cancelled/failed run when the sibling is progressing normally.

Good pattern:

> The email named run 30313306940 (v0.1.49), which was SIGTERM'd during tests and then cancelled on attempt 2. But run 30311741032 on the same tag is on attempt 5 with verify passed, CLI published, and HQ deploy in progress. The release is proceeding normally; the alert is stale.

## What to report

### If a fan-out release workflow is only partially failed

Some release workflows are a single top-level run that fans out into multiple deploy jobs or environments. In that shape, do **not** summarize from the workflow conclusion alone.

Required sequence:

1. enumerate the live jobs for the run;
2. classify which environment/job actually failed;
3. verify live version/health per environment;
4. compare each environment's live commit against the intended release commit;
5. if one environment failed but others already serve the new build, report a **partial release failure** rather than a global release outage;
6. if the failing environment rolled back and stayed healthy on the previous version, open at most one narrow deploy-rescue item for that environment instead of reopening the merged source PR broadly.

Good pattern:

> The release workflow is red overall, but HQ and GLY are already on the new release commit while dev rolled back and stayed on the prior healthy build. Report the release as partially failed and queue one narrow dev deploy rescue.

Reference: `references/merged-source-release-fanout-single-env-failure.md`

### If the latest attempt is successful

Say plainly:

- the workflow is currently green
- which earlier attempt(s) failed
- what the earlier failure was
- whether that earlier failure indicates a follow-up reliability task

Good pattern:

> Live state is success now. Attempt 1 failed at X, attempt 2 also failed at X, attempt 3 succeeded. The production deploy is no longer blocked, but the earlier failures justify a follow-up task for Y.

### If the latest attempt is still failing

Report:

- exact failing job and step
- whether downstream jobs were skipped
- whether the failure is code, environment, capacity, credentials, deployment target, or policy
- the concrete next owner/action

## Important pitfall: email subjects embed commit SHA prefixes or internal IDs, not run IDs

GitHub failure notification emails include a parenthetical identifier in the subject line, for example `[repo] Run failed: Workflow Name (4f11b4f)` or `[repo] Run failed: CI - branch-name (5194628)`. This value can be:

- a **commit SHA prefix** (hex string like `4f11b4f`),
- a **GitHub-internal notification or database ID** (decimal number like `5194628`), or
- occasionally a truncated run-id fragment.

None of these are usable as Actions run IDs. Run IDs are large decimal numbers (e.g., `30313744421`). Passing any of the above to `gh run view` returns a 404.

Required recovery:

1. Do **not** attempt `gh run view <parenthetical-value>` — it will always 404 regardless of format.
2. If the email body contains a run URL, extract the numeric run ID from it — but verify it is complete (truncated URLs like `.../runs/303174` also 404).
3. List recent runs for the named workflow or branch: `gh run list --repo <owner>/<repo> --branch <branch> --limit 5 --json databaseId,status,conclusion,headBranch,createdAt,displayTitle`.
4. Match by `headSha` prefix, `headBranch`, workflow name, and approximate timestamp from the email.
5. Once the real numeric `databaseId` is found, proceed with normal run-id triage.

This also applies when the email URL is truncated and only a partial run ID is visible.

## Important pitfall: notification-supplied run ids can be truncated, stale, or otherwise unusable

Notification emails and pasted alerts sometimes carry a run URL or run id that does not resolve cleanly during triage — for example a truncated URL, a malformed copied id, or an alert that links to a no-longer-usable run page.

If a notification-supplied run id returns 404 or otherwise fails lookup:

1. do **not** immediately conclude the repo access is wrong or that the run disappeared;
2. recover the live run by listing recent runs for the named workflow and matching on:
   - workflow name,
   - PR title / display title,
   - branch,
   - approximate timestamp from the alert,
   - and current PR head SHA when available;
3. once the candidate run is found, switch back to normal run-id triage (`gh run view <run-id>`, run-attempt APIs, failed logs, jobs).

Good recovery pattern:

- `gh run list --repo <owner>/<repo> --workflow <workflow> --limit 20 --json databaseId,workflowName,displayTitle,status,conclusion,headSha,headBranch,event,url,createdAt,updatedAt`
- `gh pr list --repo <owner>/<repo> --state all --limit 30 --json number,title,state,headRefName,headRefOid,url,updatedAt`
- match the alert against the live PR/run pair before creating work or commenting on the board.

**Faster alternative when the email subject contains a commit SHA prefix or PR title:** resolve the PR first, then list runs by branch. This avoids scanning all workflow runs and is the preferred two-step chain (SHA/title → PR → branch → run):

1. `gh pr list --repo <owner>/<repo> --search "<sha-prefix>" --json number,title,headRefName,state` — finds the PR from the commit SHA in the subject line. "PR run failed" notification subjects also include the full PR title, so title-keyword search works equally well: `gh pr list --repo <owner>/<repo> --search "OTP throttling" --state all --json number,title,headRefName,state`. Use `--state all` since the PR may be open, closed, or merged.
2. `gh run list --repo <owner>/<repo> --branch <headRefName> --limit 3 --json databaseId,status,conclusion,createdAt,headSha` — lists only runs for that branch, newest first.
3. Pick the run matching the email's timestamp and SHA, then proceed with normal run-id triage.

This chain is faster and more targeted than listing all workflow runs, especially on repos with many concurrent branches.

This matters because a bad alert link is a notification-ingestion problem, not evidence that the workflow itself is untriageable.

When the truncation is in the email **body** `View results:` URL itself (e.g. `/runs/30357` when the real id is `30357393328`), the fastest recovery is resolving the PR from the subject's branch name then listing runs by branch. See `references/truncated-run-url-email-body-pr-branch-recovery.md`.

For the combined pattern of a truncated email run URL plus off-diff full-suite timeouts that recover on a failed-job rerun, use `references/truncated-email-off-diff-timeout-recovery.md`.

For the narrower master-push variant where a notification supplies only a run-id prefix and one off-diff timing lower-bound assertion recovers on rerun, use `references/truncated-master-run-timing-recovery.md`.

## Important pitfall: version-bump or chore PR notifications can mask the actual regression source

A CI failure email can name a `chore: bump version` or other non-functional commit in its subject while the actual regression was introduced by a feature PR that merged minutes earlier. The version-bump run is the first CI run that includes both the feature code and the bump, so it carries the failure.

Required sequence:

1. Capture the failing run's `headSha` and `headBranch` from the notification or `gh run list`.
2. List recent runs for the same workflow and identify whether a feature PR merged shortly before the chore/bump PR.
3. Trace the commit range between the feature merge commit and the chore commit: `git log --oneline <feature-sha>..<chore-sha> -- <failing-test-files>`. If empty, the chore PR did not touch the failing surface.
4. Confirm the feature PR's diff touches the failing test or its implementation: `git diff <feature-sha>~1..<feature-sha> --stat -- tests/ apps/`.
5. File the fix card citing the **feature PR** as the regression source, not the chore/bump PR. Include both run URLs and both merge commits for traceability.

Good pattern:

> The email subject blamed `chore: bump package.json version to 0.1.49`, but the two failing E2E specs were introduced/regressed by PR #1337 (`feat: add responsive media grid focus and context commands`), which merged 6 minutes before the bump. The bump PR touched no test or app code. File the repair against the feature PR's changes, not the version bump.

## Important pitfall: attempt-specific failures

GitHub notification emails and run pages can point at a failure from an earlier attempt while the same run id later finishes green after rerun. Do not file a "deploy failed" card until you confirm the **latest attempt** is still red.

Instead:

- verify the final attempt result first
- inspect attempt-specific jobs/logs for the earlier failure
- if recovered, file a **root-cause follow-up** (for example runner-capacity hygiene, flaky deploy preflight, or transient host issue)
- describe the original deploy as recovered, not failed

## Important pitfall: empty failed logs on self-hosted runner disconnects

Sometimes `gh run view <run-id> --log-failed` returns little or nothing useful because the job did not fail inside the test command — the self-hosted runner itself lost communication with GitHub mid-job.

When the visible failed logs are empty or incomplete:

1. Query the failed jobs directly.
2. Pull the full job log via `gh api repos/<owner>/<repo>/actions/jobs/<job-id>/logs` — this works for normal step failures too, not only runner disconnects, and is the most reliable log source when `--log-failed` returns nothing.
3. Inspect the check-run annotations for the failed jobs.
3. If the annotation says the runner lost communication, classify that as an infrastructure/transient signal first, not immediate product-regression evidence.
4. Re-run the failed job(s) on GitHub and re-check the latest attempt before opening a code-fix card.
5. If the workflow includes browser tests, match the CI environment locally before trusting a repro — for example install the Playwright browser payload first if CI does so.

Good pattern:

- `gh api repos/<owner>/<repo>/actions/jobs/<job-id>`
- `gh api repos/<owner>/<repo>/check-runs/<check-run-id>/annotations`
- local repro that mirrors CI setup, such as `bunx playwright install chromium` before the smoke/a11y commands when the workflow installs Chromium explicitly

If the merged push run or rerun finishes green and the local repro passes after matching CI setup, report the original email as a transient runner failure and avoid creating a speculative product bug.

## Important pitfall: inlined remote shell payloads can shift line numbers and break helper guards

Some deploy workflows do not execute one remote script file directly. They assemble a payload from exported env lines plus one or more helper scripts and then pipe the combined result into `bash -s` over SSH/SSM.

When the failed log shows a remote shell error such as:

- `SSM status: Failed`
- `/bin/bash: line N: BASH_SOURCE[0]: unbound variable`

triage it this way:

1. pull the failed job log and capture the first concrete remote-shell error;
2. inspect the workflow step that assembles the remote payload;
3. reconstruct the concatenation order locally and print line numbers;
4. map the reported `line N` back to the actual helper or script source;
5. check whether a helper's standalone-execution guard assumes `BASH_SOURCE[0]` exists under `bash -s`.

A common failure mode is a helper containing:

```bash
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  ...
fi
```

Under `set -u`, that can crash when the payload is executed from stdin/inlined context. Classify this as a **deploy payload / helper-script regression**, not generic infra noise.

Before you claim production is down, verify the live endpoint or health route and compare the serving commit with the intended deploy SHA. A healthy old commit usually means the swap never completed.

Reference: `references/ssm-inlined-payload-line-mapping.md`

## Important pitfall: follow-up scoping

When a deploy recovered on rerun, do **not** reopen the merged feature PR or create a broad "production broken" ticket unless the latest attempt proves that is still true.

Prefer a scoped follow-up such as:

- runner disk/capacity stabilization
- cache cleanup / workspace hygiene
- flaky preflight hardening
- host-specific deployment reliability
- better diagnostics for future reruns

## Important pitfall: merged PR does not automatically supersede a failing PR-only workflow

A failure email can arrive after the PR already merged, and post-merge branch CI can even be green. That does **not** automatically make the PR failure stale.

Use this sequence when the workflow matrix differs between `pull_request` and `push`:

1. verify whether the failing workflow actually runs on the post-merge branch event;
2. if branch CI is green but it is a **different workflow surface**, do not treat that as proof the PR-only failure disappeared;
3. check the latest PR-head runs on the final head SHA, not just the pre-merge failing SHA;
4. if the latest PR-head run is still red, inspect the exact failing test/assertion;
5. if needed, reproduce the failure locally on current `master` after syncing the canonical checkout, especially when the merge commit already contains the suspect code;
6. if local repro on current `master` confirms the same behavior, file a **new narrow follow-up card against current master** rather than calling the email stale.

Good example shape:

- PR merged
- PR-head CI recovered green
- PR-head E2E is still red on the latest head SHA
- push-to-master CI is green, but that push workflow does not cover the failing PR-only E2E surface
- local repro on synced `master` still fails
- conclusion: merged regression is real; create a focused follow-up card for the surviving E2E break

## Important pitfall: Playwright `--with-deps` on self-hosted runners can fail before the spec ever starts

When a browser workflow fails in a setup step like:

- `Install Playwright browser`
- `Install Playwright system dependencies on autoscaled runners`
- `bunx playwright install --with-deps chromium webkit firefox`
- `bunx playwright install-deps chromium firefox` (standalone deps step, no browser download)
- followed by `sudo: a terminal is required` / `sudo: a password is required`

classify it as a **runner/workflow setup blocker first**, not as a product regression inside the E2E spec body.

**Pool-wide recurrence signal:** when three or more consecutive runs across *different* PRs or branches fail identically in the same setup step with the same sudo/provisioning error, the failure is pool-wide by definition. Do not create per-PR rescue cards. Instead:

1. Search the live board for an existing infra card owning the same failure class (for example a "install browser deps on runner pool" card).
2. If one exists and is claimable (`ready` or `running`), add the new run IDs as confirming evidence to that card and stop.
3. If none exists, create one infra card at high priority naming the pool, the exact step, the sudo error, and acceptance criteria requiring a fresh run that reaches the test step.
4. Note the friction: the workflow should be gated behind a runner-capability check or disabled until the pool is repaired, so PR authors are not chased by phantom failure emails that look like code regressions.

Required sequence:

1. confirm the failing step is the browser install/setup step and that the actual test step never started or was skipped;
2. capture the exact install command and the sudo/escalation error text;
3. check whether the PR head recently expanded browser scope or changed workflow install behavior;
4. if other checks on the same head are green, keep the rescue scope narrow to the browser-install path;
5. if an older rescue card on the same PR covered a different earlier-head spec/assertion failure, treat that card as **historical evidence only** rather than reviving it for the new blocker;
6. create or update one current-head rescue item for the install-path failure class — unless pool-wide recurrence applies, in which case link to the existing infra card instead.

Good pattern:

> The latest PR head is red in `Playwright import render smoke`, but the job dies in `Install Playwright browser` with a `sudo` requirement before `Run E2E smoke` starts. Other checks on the same head are green. This is a current workflow/setup blocker on the self-hosted runner, not a stale copy of an older spec-level E2E failure.

### Per-browser-engine system dependency gaps (partial browser failure)

A self-hosted runner can have enough system libraries for Chromium but not for Firefox or WebKit. The Playwright install step succeeds (browsers download), Chromium tests pass, but Firefox/WebKit tests fail at `browserType.launch` with:

```
Host system is missing dependencies to run browsers.
Please install them with the following command:
    sudo npx playwright install-deps
Alternatively, use apt:
    sudo apt-get install libgtk-3-0t64
```

Key diagnostic signals:

- N-1 of N extended browser tests pass (e.g. 42/43); only the Firefox- or WebKit-specific test fails.
- The error is in `browserType.launch`, not in any test assertion — the browser never starts.
- Chromium tests on the same runner pass, proving the code is fine.
- The failure is deterministic across retries (same missing library).

Required sequence:

1. Confirm the failing step is browser launch, not a test assertion. The test body never executes.
2. Note which engine failed and which passed. A Chromium pass + Firefox launch failure is infra, not product.
3. Classify as **runner host dependency gap**, not code regression. Do not create a product-code rescue card.
4. The fix is host-level: `sudo apt-get install libgtk-3-0t64` (Firefox GTK) or `sudo npx playwright install-deps` (all engines). Prefer the workflow-level durable fix: add a setup step that runs `npx playwright install-deps` before tests so the workflow self-bootstraps regardless of runner image state.
5. If the PR's core CI checks (test, typecheck, build, Chromium browser gate) are green, report the PR code as verified and the extended-browser failure as a runner-env gap.
6. File a narrow runner-infra ticket if no existing card owns it. Do not block the PR merge on a Firefox-only runner gap when Chromium gates pass and the code is otherwise green — unless Firefox coverage is a required merge gate.

This is distinct from the `--with-deps` sudo failure pattern above (where the *install step itself* fails before any browser downloads). Here the install succeeds but one engine cannot launch at runtime due to missing host libraries.

## Important pitfall: `gh run rerun --failed` can falsely suggest the workflow is broken when a rerun is already underway

On some runs, `gh run rerun <run-id> --failed` can return a misleading message such as:

- `run <id> cannot be rerun; its workflow file may be broken`

while the same run has in fact already been rerun and is now on a newer in-progress attempt.

Treat that CLI message as non-authoritative until you re-check the live run object.

Required sequence:

1. after any rerun command failure, query the live run again with the REST API;
2. inspect `status`, `conclusion`, and especially `run_attempt`;
3. if `run_attempt` increased or `status` is now `in_progress`, classify the rerun as active rather than failed;
4. if you need to trigger rerun explicitly, use the lower-level rerun endpoint (`POST /actions/runs/<run-id>/rerun-failed-jobs` or equivalent) and read its response carefully;
5. a successful rerun request can return `201 Created` while the run object still briefly reports `status: queued` and the old `run_attempt`. Treat the `201` as acceptance, then poll the live run until `run_attempt` advances and the rerun job is actually `in_progress` or completed; do not classify the old attempt during that transition;
6. if that endpoint says the workflow is already running, do not create board work from the stale first-attempt failure — wait for the new attempt result first;
7. only after the latest attempt completes should you decide whether the alert still needs a rescue card or just evidence on the source card.

Good pattern:

> `gh run rerun --failed` claimed the workflow file might be broken, but the live run object showed `run_attempt: 2` and `status: in_progress`. The correct action was to wait for attempt 2, then classify from the final result instead of filing work from the stale attempt-1 failure.

The same false `cannot be rerun; its workflow file may be broken` message can also appear for a **plain** `gh run rerun <run-id>` (not only `--failed`) even when no newer attempt is already in flight. The rerun may in fact have been accepted.

Required sequence:

1. Re-query the live run (`gh api repos/<owner>/<repo>/actions/runs/<run-id> --jq '{status,conclusion,run_attempt}'`); queued status or an advanced attempt proves rerun acceptance even if CLI stderr disagrees. Confirm the same run ID with `gh run list`.
2. A queued self-hosted job with matching runners busy is queue wait, not a broken workflow; use `self-hosted-ci-operations` only after >15 minutes with idle matching runners.
3. Do not create a rescue card from CLI text; live state drives follow-up. A failed-job rerun may create a new job ID beneath the same run, so re-query its jobs at terminal state and cite the new job as retry evidence.
4. `gh run watch <run-id> --exit-status` exits nonzero when the rerun remains red. Run later log/JSON capture separately or with `;`, not `&&`, so that expected red exit cannot suppress evidence collection.

### In-progress re-run on an unchanged SHA is not new evidence

When triaging a failure, you may find a newer run already `in_progress` on the same branch/head SHA as the failed one, with **no new commits pushed** between them (for example an automatic or manual re-run triggered immediately after the failure). That re-run reuses the identical code and will fail identically for any deterministic assertion failure.

Required handling:

1. Confirm the in-progress run's `head_sha` matches the failed run's `head_sha` and that the PR/branch has no newer commit.
2. If the failure is a deterministic assertion (a concrete `expect(...)` mismatch or a reproducible timeout in PR-touched code), do **not** wait for the redundant re-run to finish before classifying or filing work — it cannot change the outcome.
3. Only defer to a re-run when the original failure was transient (runner disconnect, capacity, off-diff timeout that passed focused repro). A deterministic PR-owned failure needs a code push, not another run of the same SHA.

Good pattern:

> Run A failed on head X with a deterministic assertion. Run B is in progress on the same head X with no new commit. Classify from run A and file the repair now; run B will fail identically and is not a recovery signal.

### Rerunning multiple failed jobs can leave one lane unverified

`rerun-failed-jobs` reruns every failed job in a workflow. If one rerun job has a deterministic failure while another previously had a self-hosted-runner disconnect, GitHub can finish the overall attempt as `cancelled` before the transient lane executes.

Required sequence:

1. Inspect every latest-attempt job independently; do not summarize from the workflow-level `cancelled` conclusion.
2. Record a deterministic job's current failure from its latest completed attempt.
3. If the runner-disconnected job is cancelled or has no executed test step, call that lane **unverified**, not recovered or product-failed.
4. Scope repair only to the deterministic failure; do not change browser/product tests based on an unexecuted rerun lane.
5. Require a fresh PR-triggered run after repair. A workflow-dispatch rerun is evidence for its pinned SHA/environment, not a merge gate for a later PR head.

Good pattern:

> The rerun's build job failed again in deterministic assertions, while the browser job was cancelled without execution after a prior runner-disconnect annotation. Queue the build-lane repair; leave browser status unverified and require a fresh PR run.

### Combined alert-recovery pitfall: one truncated notification can mask multiple failure lanes

A short run-id prefix can resolve to several nearby runs, and the resolved PR can have a separate in-diff browser/product failure plus an off-diff CI assertion failure on the same head. Recover the full run by title, branch, SHA, and time; then enumerate the complete PR check rollup before deciding ownership. Keep the in-diff deterministic blocker on the existing Review/source card, and rerun only the off-diff failed job before filing separate work. A `201 Created` rerun response is not recovery: while the new attempt or job is queued/in progress, report it as **unverified**. See `references/truncated-pr-alert-mixed-failure-queued-rerun.md` for the evidence and board-comment pattern.

## Important pitfall: PR head can typecheck while GitHub's synthetic merge ref fails

For `pull_request` workflows, Actions may test a synthetic merge commit (`github.sha`) rather than the PR head SHA. If `master` advanced after the branch diverged, that merge can combine an upstream change with the PR refactor and fail even though the source branch passes locally.

Common shape:

- the PR-head file removes or stops using an import;
- current `master` adds that import or otherwise changes the same file;
- the synthetic merge retains both the upstream import and the PR refactor;
- CI fails typecheck for an unused import, while `bun run typecheck` at the PR head passes.

Required sequence:

1. capture the synthetic merge SHA from the CI log (or `github.sha` output) and inspect its parents;
2. fetch the failing file at both the PR head and that merge SHA using the GitHub API or `git show`;
3. compare it with current `origin/master` and identify the exact merge-only difference;
4. do not dismiss the CI failure just because PR-head verification passes;
5. keep ownership on the existing source Review card; instruct the PR owner to rebase or merge current `master`, resolve the merge-result source, push, and obtain a **fresh PR workflow run**;
6. do not create a duplicate rescue card when the error belongs to the source PR's mergeability.

A rerun of only the failed job is useful for clearing a separate transient failure, but it reuses the same synthetic merge context. It cannot prove a merge-only defect is fixed; a new PR-head push is required.

## Important pitfall: an alerting `workflow_dispatch` run can lag behind the current PR head

A manually dispatched CI run is pinned to the SHA selected when it starts. The PR branch may advance while that run is queued, failing, or being rerun. A rerun of its failed job is evidence about the **alerted SHA and workflow environment**, not a merge gate for the newer PR head.

Required sequence:

1. Capture the alerting run's `head_sha`, event, latest attempt, failing job, and exact failure.
2. Query the PR separately for its current `headRefOid`, check rollup, and merge state; compare its SHA to the alerting SHA.
3. If the old run proves a durable runner/workflow incompatibility that is still present in the current workflow, record it on the source Review card, but do not call the result the current PR status.
4. If the current head has no matching PR checks yet, call it **unverified**, not recovered or green.
5. Require a fresh PR-triggered check on the actual current head after repair or rebase. Include both SHAs and that requirement in the board reconciliation comment.
6. Keep unrelated failures from that dispatched lane (for example host-specific decoder prerequisites) out of a reproducible product-contract repair unless current-head evidence establishes the same cause.

Keep ownership on the existing Review card unless the failure requires genuinely separate implementation work.

Reference: `references/pr-head-advanced-beyond-alert.md`

### Notification points to an obsolete manual head after a PR rebuild

A notification can be accurate for its own run yet obsolete as a merge signal when it came from `workflow_dispatch` on an older PR head and that branch was later rebuilt, rebased, or force-updated.

Required sequence:

1. Recover the full run ID and record its `event`, `head_sha`, `head_branch`, latest attempt, failed jobs, and exact failures.
2. Query the PR separately and compare its current `headRefOid` to the alerted run SHA.
3. If they differ, label the alert **superseded evidence**. Do not assign the old failures to the reconstructed head or create a duplicate rescue solely from them.
4. Enumerate fresh `pull_request` checks on the current SHA. If any are queued or in progress, report the PR as **unverified** and do not merge.
5. Add one concise source-card comment linking the old run, both SHAs, the supersession boundary, and fresh run URLs. Do not repeat diagnostics already recorded on the card.

Good pattern:

> The email resolves to a failed manual run on head A. PR #N now points to rebuilt head B. The old failures are historical evidence; CI and browser checks for B are queued/in progress, so the PR is unverified rather than currently red for the same reason.

## Merged workflow-policy PR superseded by a newer open migration PR

A CI-policy or runner-routing PR can merge before its delayed PR workflow finishes, then fail because an assertion still names the former runner or trigger contract. Before opening a repair from that historical alert:

1. verify the failed run's exact assertion and confirm that its PR is merged;
2. inspect the current workflow and policy test on `origin/master`, not a potentially stale canonical checkout;
3. inspect open PRs modifying the same workflow/test surface, especially a newer runner or trigger migration;
4. search the live board by that newer PR number and relevant runner/contract terms;
5. if a current claimable repair card already owns the newer migration, add the historical run evidence there and do **not** create a separate rescue for the merged PR;
6. validate the existing Haft Ready worktree card before presenting it as the active owner.

Report the old run as **failed but superseded**. Do not call it recovered without a fresh successful run on the current repair head. If current-base CI is still running, call it **unverified** even if a sibling browser job is green.

## Board-reconciliation race: inspect the source card after gathering CI evidence

In a multi-agent sweep, another worker may already have triaged the same notification and created a narrowly scoped rescue while you are reading logs. Before creating a card, posting a duplicate diagnosis, or reporting that new work is needed:

1. identify the mapped source card from PR provenance/body;
2. re-read its live comments and children **after** collecting run/job evidence;
3. if a current comment already records the same run, SHA, failure surface, and rescue card, verify the rescue is actually claimable (`ready`, unassigned, repo-root worktree anchor, explicit branch) rather than creating a duplicate;
4. report that rescue as the active owner and retain the source Review card as the PR anchor;
5. comment only for a materially newer attempt, a distinct failure lane, or a corrected diagnosis.

This preserves one repair owner per failure class when a GitHub email is processed concurrently.

### Fresh PR runs can expose a distinct runner-bootstrap lane

A review PR may include a policy or contract adjustment for a runner migration, yet its fresh `pull_request` run can fail **before tests start** during dependency installation. Treat that as a separate runner-bootstrap signal, not proof that the PR's product fix is wrong.

Required sequence:

1. capture the failing setup step and exact command/error, plus runner name and labels from the job API;
2. state which downstream tests/checks were not executed;
3. inspect live board `running` and `ready` cards for an existing runner-contract, image-parity, or bootstrap owner before creating work;
4. if one exists, add the new run evidence there and add a concise status note to the source Review card; do not duplicate the rescue;
5. require a fresh PR-triggered run after the bootstrap repair. Until then, call the source PR **unverified**, even if focused local verification passed.

Good pattern:

> The source PR's tests did not run because its assigned runner failed dependency setup. Its code-level change remains unverified on GitHub; the runner-bootstrap card owns the setup repair.

## Important pitfall: post-suite artifact-upload quota failures can mask a green test suite

A required CI job can finish red even though all repository tests passed because a later evidence/artifact upload is rejected by GitHub Actions storage quota. Typical evidence:

- the test-suite step completed with `0 failures`;
- the failed step is an upload step such as `Upload ... evidence`;
- the log or check annotation says `Failed to CreateArtifact: Artifact storage quota has been hit`;
- downstream typecheck/build steps are marked `skipped` because the upload step is fatal.

Required sequence:

1. Inspect the complete job-step list and the upload failure annotation; do not summarize from workflow conclusion alone.
2. State tests separately from unexecuted gates: a passing suite is real evidence, but skipped Typecheck and Build are **not verified**.
3. Classify this as a GitHub Actions storage/quota blocker, not a source-code regression, unless another job independently reports a product failure.
4. Add concise evidence to the source Review card: run URL, head SHA, passed test count, exact failed upload step/error, and skipped gates.
5. Do **not** rerun until artifact capacity or retention is restored; a rerun before that is expected to fail in the same upload step.
6. Do not create a product-code rescue card. If the recurring workflow behavior is under repository control, track a narrow reliability follow-up to make nonessential evidence upload non-blocking after successful tests, or enforce storage/retention headroom before required CI.

Good pattern:

> CI's required suite passed 3,201 tests with 0 failures, but the post-suite governance-evidence artifact upload hit GitHub's storage quota. Cleanup passed; Typecheck and Build were skipped. The PR is not code-red, but it remains unverified for merge until quota remediation and a fresh required run execute the skipped gates.

## Evidence standard

Before you claim a workflow is green, have real output for:

- current run `status` and `conclusion`
- latest attempt number
- job-level conclusion for the latest attempt

Before you claim a workflow failed, have real output for:

- current/latest attempt still red
- failing job name
- failing step or log excerpt

## Review-card handoff when the alert is for an open PR

When the failing workflow belongs to an **open PR that is already parked in Review** on a board-backed repo, do not automatically create a new rescue/fix card from the email.

Use this sequence instead:

1. verify the latest run state and attempt history;
2. if the latest attempt is green, keep the source implementation/review card in Review;
3. add a concise evidence comment to that source card with:
   - PR URL
   - run URL
   - latest conclusion
   - which attempt failed
   - the exact transient annotation or failure class
4. only create a separate follow-up card if the latest run is still red **or** the recovered run exposed a distinct reliability problem that truly needs separate ownership.

This keeps the board truthful: a recovered PR is still awaiting review, not silently converted into fake implementation work.

### Open Review PR + off-diff CI timeout recovery

When the alerting workflow belongs to an open PR already in Review and the exact failing surface appears **outside the PR diff**, treat the first failure as potentially transient until you prove otherwise.

Required sequence:

1. capture the exact failing test/spec/assertion from the failed job, not just the workflow name;
2. compare that failing surface against the PR diff;
3. if the PR does not touch that test or its immediate implementation surface, run a focused local repro in both:
   - the PR worktree, and
   - an isolated worktree at current base;
4. bootstrap a fresh isolated worktree from its lockfile before judging the repro (for example `bun install --frozen-lockfile`); a missing package is setup noise, not test evidence;
5. if the focused repro passes in both places, rerun only the failed GitHub job on the same run;
6. re-check the latest `run_attempt`, `status`, and `conclusion` before reporting board action;
6. if the rerun recovers green, keep the source Review card as the PR anchor, add evidence there, and create **no** separate rescue card from the stale first-attempt email.

Good pattern:

> Attempt 1 timed out in one exact test inside the broad CI job, but that test surface is off-diff for the PR. The focused repro passed in the PR worktree and canonical checkout, the failed job rerun succeeded, and the PR is now green again. Keep the existing Review card; do not seed duplicate rescue work.

For the combined malformed/truncated notification-ID and timeout-recovery variant, see `references/truncated-run-id-pr-timeout-recovery.md`.

### Off-diff browser failures already owned by an existing rescue

When the alerted PR's diff is purely server-side (or entirely outside the failing browser/E2E surface) and the exact same deterministic failures are already tracked by an existing rescue card or in-flight fix PR from a different source PR, do **not** rerun, repro locally, or create a duplicate card. Add one evidence comment to the source card and stop. The alerted PR just needs a rebase after the fix lands.

Required checks: (1) confirm zero overlap between PR diff and failing test/UI surface via `gh pr diff <n> --name-only`; (2) find the existing rescue card or in-flight PR owning the same failure signatures; (3) verify the alerted branch hasn't rebased to include the fix (`git merge-base --is-ancestor <fix-sha> <pr-head-sha>`). Then comment evidence and stop.

See `references/off-diff-already-owned-evidence-only.md` for the full sequence and anti-patterns.

### Post-merge push CI: off-diff timeout recovery

Apply the same reasoning when the alert is for the `push` run on `master` created by an already-merged PR:

1. Resolve the full run ID from the alert and prove its `head_sha` is the merge commit.
2. Inspect the failed tests and compare them with the merged PR diff.
3. When failures are isolated timeout cases outside that diff, sync the clean canonical checkout to the exact `origin/master` SHA and run each affected file directly.
4. If focused repros pass, rerun **only the failed jobs** for the existing run. Do not push an empty commit or create a speculative repair card.
5. Re-query the run and its latest-attempt jobs. Call it recovered only after the rerun completes green, and leave the canonical checkout clean.

A timeout that reproduces locally or belongs to a file changed by the merged PR is a current-master regression: file a narrowly scoped repair card instead.

Reference: `references/open-pr-off-diff-timeout-recovery.md`

### Open-PR rescue scoping when the source card is already in Review

If the alerting workflow belongs to an **open PR that already has a Review card**, keep the board model truthful:

1. treat the existing Review card as the **PR anchor**;
2. if the latest alerting run is still red, identify the **exact failing surface** from the failed job log (specific spec, assertion, selector, route, or step), not just the workflow name;
3. create a **new narrow rescue/fix card** only for that exact failing surface when the failure needs implementation work before review can continue;
4. add evidence comments to **both** cards:
   - source Review card: run URL, head SHA, exact failing surfaces, and the new rescue-card id;
   - rescue card: source PR/card link, alerting run URL, exact failing job/spec, and the branch/PR it must update;
5. if the PR has **other failing checks** beyond the alerting workflow, note that fact, but do **not** broaden the rescue card unless those checks are part of the same concrete failure class.

Good pattern:

> PR is still open and parked in Review. The alerting E2E run is still red. Create one focused repair card for the exact E2E regressions, keep the source Review card as the PR anchor, and leave broader CI instability out of scope unless the evidence shows it is the same bug.

This keeps the board honest: one card tracks the feature PR under review, and a separate narrowly scoped card tracks the concrete regression blocking review.

### Runner-image dependency-lifecycle prerequisite failures

A failure during dependency installation can be a runner-image/bootstrap incident rather than a product regression. Typical signals are a lifecycle/postinstall command reporting an absent executable (for example `node: command not found`) and exiting before any test, typecheck, build, or browser step runs.

Required sequence:

1. capture the failed step, exact error/exit status, and skipped downstream verification;
2. query the job object for runner name and labels;
3. compare the PR diff with the workflow/bootstrap surface;
4. corroborate on at least one unrelated PR/head using the same runner pool before calling it a shared image incident;
5. look for an existing runner-image or workflow-bootstrap repair card before creating work;
6. keep the affected source PR in Review because its required checks remain red, but do not create a speculative product-code rescue when the PR does not own the setup surface;
7. require a fresh `pull_request` run on the source PR after the prerequisite repair. A green repair-PR run does not verify a different head.

The repair should restore the runtime prerequisite through the runner image or explicit workflow bootstrap. Do not bypass lifecycle scripts, suppress postinstall hooks, or weaken tests merely to make installation pass.

See `references/runner-image-dependency-lifecycle-prerequisite.md` for the evidence and board-handoff shape.

### Runner-pool system-tool and host-infrastructure prerequisites

A distinct sub-class: the failure is not in the project's own install step but in a **setup action's system dependency** or a **workflow-assumed host path**. Common signatures:

- `Unable to locate executable file: unzip` — a setup action (e.g. `oven-sh/setup-bun`) downloads an archive and needs a system tool the runner image lacks;
- `flock: cannot open lock file /var/lock/<name>/<file>.lock: No such file or directory` — the workflow assumes a host directory exists for serialization, but the runner image never created it;
- Any `command not found` in a setup-action step (not in the project's `bun install` / `npm ci`).

These fail **before any project code executes**, so they are never product regressions.

Required sequence:

1. Confirm the failing step is a setup action or workflow infrastructure step, not a project test/build step.
2. Capture the exact missing tool or path from the error.
3. Identify the runner pool (runner name prefix) and corroborate on at least one **unrelated run** dispatched to the same pool — if the same error appears on a different PR/branch, it is pool-wide by definition. **Fast-path A**: if the live board already has a `ready` or `running` repair card documenting the same failure class on the same pool (with prior evidence from multiple runners), skip independent corroboration — add the new runner instance as confirming evidence to that card instead. **Fast-path B (self-heal)**: if the same run's later attempt succeeded on the same pool without any host change (verify via `gh api repos/<owner>/<repo>/actions/runs/<run-id>` for `run_attempt` and attempt-specific job conclusions), classify as a transient action-internal flake. No cross-PR corroboration or infra repair card is needed — record the evidence and move on. Only escalate to a repair card if the same signature recurs across multiple unrelated runs.
4. Check whether a sibling job on a different runner pool passed (proves the code is fine, the pool is broken).
5. If a queued rerun exists on the same pool, note it will fail identically — do not wait for it.
6. File one infra repair card at high priority naming: the pool, the missing prerequisites, the exact fix commands (host-level and workflow-level), and acceptance criteria requiring a fresh run that reaches the test step. **If a repair card already exists and is claimable, do not create a duplicate** — add evidence and stop.
7. Keep the source PR in Review with an evidence comment; do not create a code rescue.

Durable fix preference: make the workflow self-bootstrapping (e.g. `mkdir -p` before flock, or a step that installs missing system tools) so the workflow does not depend on immutable runner-image state. Host-level installs are a point fix; workflow-level bootstrap survives image rebuilds.

**Misleading email duration:** when the notification reports a multi-hour duration but the failure is a setup/infrastructure step, query job-level `started_at`/`completed_at` — the run duration is dominated by self-hosted queue wait, not execution. A seconds-long job with hours-long run duration = queue wait + instant infra failure. See `references/long-duration-masking-instant-lockdir-failure.md`.

See `references/runner-pool-system-tool-and-lockdir.md` for the evidence pattern and repair card shape. For the concrete host fix commands (lockdir creation + bounded sudo cleanup-helper script body), the verify-before-rerun checks, and the pool-wide provisioning requirement, see `references/missing-host-prereq-remediation-recipe.md`.

### Common transient signal: self-hosted runner lost communication

If failed jobs share the GitHub annotation:

> The self-hosted runner lost communication with the server.

classify it as an infrastructure/transient signal first. If a later attempt succeeds and PR checks are green, report the recovery plainly and avoid opening a speculative code-fix card from the alert alone.

When `gh run view <id> --log-failed` returns no useful output, fall back to the run/job metadata view (`gh run view <id> --json ... jobs ...`) and classify from the failed jobs/step states instead of guessing from the email subject. See `references/gh-run-metadata-fallback.md`.

### Same-head multi-workflow runner disconnects on an open PR

A single alert email can understate the real PR state when multiple workflows on the **same PR head SHA** are running at once.

Common shape:

- workflow A (for example `CI`) failed on attempt 1 with the runner-disconnect annotation;
- GitHub or an operator reran workflow A and it recovered on attempt 2;
- workflow B (for example `E2E smoke`) on the **same head SHA** is still red from the same runner-disconnect class;
- the PR still looks unstable until every failed workflow on that SHA has been rechecked.

Treat this as one transient infra incident, not as unrelated product regressions.

Required sequence:

1. confirm the failing workflows share the same `head_sha` and runner-disconnect annotation;
2. inspect each workflow's latest attempt state separately;
3. if one workflow has already recovered, rerun any remaining red workflow(s) with the same transient signature before creating board work;
4. only call the PR recovered when the PR-level check surface is green (`statusCheckRollup` / merge state clean), not just when one workflow recovered;
5. if all affected workflows succeed on rerun, report a recovered transient incident and create no new fix card.

Good pattern:

> The CI alert was stale by triage time: CI attempt 1 failed because the self-hosted runner lost communication, CI attempt 2 succeeded, E2E on the same head had the same transient failure, rerunning E2E also succeeded, and the PR is now green. No new implementation card is warranted.

### Rerun reveals a real PR-owned failure after the transient disconnect clears

Sometimes the first attempt fails only because the runner disconnected, but rerunning the remaining red workflow exposes a **real assertion failure** on the same PR head.

Common shape:

- the alerting `CI` run fails on attempt 1 with only the runner-disconnect annotation;
- another workflow on the same PR head (for example `E2E smoke`) also failed on attempt 1 with the same transient annotation;
- rerunning the failed workflows clears the infrastructure noise;
- one workflow then goes green, but another rerun fails in a concrete test/assertion;
- the failing test file or surface is part of the PR diff.

Required sequence:

1. prove the first-attempt failures were transient runner disconnects, not product assertions;
2. rerun every still-red workflow on that same head before deciding ownership;
3. once a rerun surfaces a concrete failure, capture the exact workflow, job, test file, line/assertion, and head SHA;
4. compare that concrete failing surface against the PR diff;
5. if the failing surface is in the PR diff or plainly belongs to the source implementation card, keep ownership on the source card / PR lane;
6. add reconciliation evidence to the source card naming both phases:
   - attempt-1 transient runner-disconnect evidence, and
   - rerun attempt's exact real blocker;
7. do **not** create a separate rescue card just because the original email was a CI failure alert.

Good pattern:

> Attempt 1 failed because the self-hosted runner lost communication. After rerun, `CI` recovered green but `E2E smoke` failed in one exact Playwright assertion inside a test file touched by the PR. Treat the transient disconnect as cleared noise, keep ownership on the source PR/card, and comment the exact rerun assertion instead of spawning duplicate rescue work.

### Verify-lane runner migrations can expose CI-contract and dependency-parity failures

When a PR intentionally changes a required CI job from a self-hosted runner to a GitHub-hosted runner (or the reverse), treat the first red run as a **workflow-contract migration** until each failure is classified. Do not call it a product regression merely because application tests fail in the new lane.

Required sequence:

1. Capture the intended runner change from the PR diff and the exact current head SHA/run URL.
2. Identify policy tests that statically assert `runs-on`, environment variables, locks, or temporary-storage paths. If the workflow changed intentionally, update those policy assertions to the new documented contract rather than reverting the runner change just to satisfy stale text.
3. Separate runner-provisioning failures from application assertions. Typical hosted-runner signs include an unavailable optional runtime/profile, native decoder/tool absence, or platform-specific test fixture expectations.
4. Repair the workflow bootstrap or make test setup runner-neutral only when that preserves the assertion's product intent. Do not weaken assertions, skip suites, add blanket retries, or change product behavior to fit a runner.
5. If a source PR is already in Review and concurrent remediation owns a different failure class (for example governance metadata), keep ownership split: one narrowly scoped Ready repair per class, both updating the existing PR branch without force-pushing. Record the coordination boundary on the source Review card.
6. Re-query a fresh run on the **actual current PR head** after each repair. A manual `workflow_dispatch` run may be useful evidence while PR rollup data is empty, but it is not a merge-ready signal unless the required PR check surface is also current and green.

Good pattern:

> A PR deliberately moved verify to GitHub-hosted infrastructure. The run failed because its policy test still expected the old runner and two tests assumed self-hosted-only runtime/decoder prerequisites. Keep the feature card in Review; queue a focused verify-lane contract repair beside any separately owned metadata repair, then require fresh current-head checks.

### PR-owned failures from intentional behavior changes (expectation drift)

A PR can deliberately change a product contract — slug generation, dedup ordering, naming conventions — and break existing tests that assert the *old* contract. These are deterministic, PR-owned, and not regressions: the implementation is doing what it intended, but the test expectations have not been updated to match.

Common shape:

- a unit test asserts an ordering, name, or slug that the PR's dedup/reconciliation logic intentionally changed;
- an E2E test asserts a URL or selector that now includes a new prefix or suffix the PR introduced (for example `artifact-page-` prepended to HTML slugs);
- both lanes (unit + E2E) fail on the same head SHA with concrete `expect(received).toEqual(expected)` or `toHaveURL` mismatches;
- the failing surfaces are clearly in the PR's diff or directly caused by it.

Required sequence:

1. Extract the exact assertion mismatch from each failing lane (unit and E2E independently — they may have different root causes even when both stem from the same PR change).
2. Confirm the mismatch is caused by the PR's intentional change, not an accidental regression: inspect the PR diff for the slug/ordering/naming logic that produces the new value.
3. Classify as **expectation drift**, not regression. The fix is to update test expectations to match the new intentional behavior, *or* fix the implementation if the new behavior is unintended.
4. File one repair card that names both lanes, the exact assertions, and gives the worker a decision framework: "If the prefix is intentional, update the E2E expectations. If unintentional, fix the slug generation." Do not pre-decide for the worker unless the PR description makes the intent unambiguous.
5. Include both run URLs, the head SHA, and the PR URL in the card body.

Good pattern:

> PR #1353's dedup logic prefixes HTML artifact slugs with `artifact-page-` and changes recently-imported ordering. The unit test asserts the old name order; the E2E test asserts the old slug without the prefix. Both are deterministic PR-owned failures. File one card: update expectations if the prefix is intentional, fix slug generation if not.

This is distinct from the "PR-owned failures in off-diff tests" pattern below (where the PR accidentally regresses a surface it did not intend to change). Here the PR changed exactly what it meant to change, and the tests need to catch up.

#### Source-text assertion drift from JSX/formatting changes

A PR can reformat JSX or other code (single-line → multi-line, attribute reordering, prettier pass) without changing behavior, breaking tests that assert against raw source text via `toContain("<SheetContent side=\"right\"")` or similar string matching.

Signals:

- the assertion is `expect(sourceText).toContain(...)` or `expect(fileContent).toMatch(...)` reading a component/file as a string;
- the PR diff shows the same code reformatted (line breaks, indentation, attribute splitting) but semantically identical;
- the test is not testing behavior — it is testing that specific text exists in a source file.

Required sequence:

1. Confirm the PR diff shows only formatting changes to the asserted code (no semantic change).
2. Classify as **source-text formatting drift**, not a product regression.
3. The fix is to update the assertion to tolerate multi-line formatting (regex, normalized whitespace, or AST-based check), or to match the new formatting exactly. Do NOT revert the formatting.
4. File as part of the PR-owned repair scope; this is mechanical.

Good pattern:

> The PR reformatted `<SheetContent side="right" className="...">` across multiple lines. The test at line 57 asserts `toContain("<SheetContent side=\"right\"")` against raw source text. Fix: update the assertion to match the new multi-line format or use a whitespace-normalized match.

This is distinct from the config-schema parity drift below (which compares two maintained data files) and from behavioral expectation drift (which tests runtime output). Here the test reads source code as a string.

#### CI-policy and workflow-contract expectation drift

The same class applies when a PR's own commits change a source-of-truth file but a **policy or contract test** that statically asserts parity with that file still expects the old state. Two common shapes:

**Shape A — workflow content assertion:** the PR's CI-infrastructure commits change a workflow file (removing an env var, renaming a step, changing a runner label) but a policy test reads the workflow YAML and asserts `toContain("HAFT_E2E_WEBKIT=1")` or similar. The PR removed that string without updating the assertion.

**Shape B — multi-file parity assertion:** the test compares keys/entries from two independently maintained files (for example a Zod config schema in `apps/hq/src/config.ts` vs a contract array in `scripts/haft-hq-env-check.ts`) and asserts exact equality via `expect(contractNames).toEqual(schemaNames)`. The PR adds entries to one file (the schema) but not the other (the contract). The error shows `Expected - N, Received + 0` with a diff listing the missing entries.

Signals:

- the failing test is a CI-lane/policy/contract test (for example `tests/playwright-ci-lanes.test.ts` or `tests/hq-env-runbook-contract.test.ts`), not a product test;
- the assertion is `expect(contractNames).toEqual(schemaNames)`, `expect(workflowContent).toContain(...)`, or `expect(configContent).toBe(...)`;
- the PR's own commits modified one side of the parity (schema, workflow, config) but not the other (contract array, policy assertion);
- the expected entries/strings are absent from the branch's version of the contract file.

Required sequence:

1. Confirm the PR diff touches the source-of-truth file (schema, workflow, config) that the policy test reads.
2. Verify the expected entries are genuinely absent from the branch's version of the contract/assertion file (`git show origin/<branch>:<contract-path> | grep <expected>`).
3. Classify as **self-inflicted policy drift** — the PR changed one side of a maintained parity but forgot the other.
4. The fix is mechanical: for Shape A, remove or update the stale assertion; for Shape B, add the missing entries to the contract file with correct metadata (logPolicy, phase, requiredIn, description).
5. Note in the repair card that this is distinct from any product-test failures on the same PR — they may have different root causes and owners.
6. For Shape B, list the exact missing entries in the card body so the worker can add them without re-deriving from logs.

Good pattern (Shape B):

> PR #1387 added 11 `HAFT_HQ_MEDIA_*` vars to the HQ config schema but not to the env-check contract. The parity test at `tests/hq-env-runbook-contract.test.ts:23` failed with `Expected - 11, Received + 0`. File one mechanical repair: add the 11 entries to `hqEnvContract` with presence-only logPolicy for secrets and value-ok for the rest.

Reference: `references/config-schema-contract-parity-drift.md`

### PR-owned failures can surface in off-diff tests and documentation contracts

Do not classify a failure as unrelated solely because the failing test file is absent from the PR diff. A source change can alter an existing UI contract or an automatically checked documentation invariant.

Required sequence:

1. Run the focused failing test on the PR head and a freshly bootstrapped isolated `origin/master` worktree.
2. If it fails only on the PR head, inspect the changed implementation surface that provides the failed behavior (for example a Reader component that now fails a pre-existing navigation/search E2E test).
3. For registry/documentation checks, compare the PR's classification or schema delta against the static count/text asserted by the failing test. Adding a new classified route can require updating a declared count or, preferably, deriving it.
4. If the PR-only repro and causal surface are clear, keep the failure on the source Review card and request a targeted push; do not create a separate rescue card.
5. If another failed test passes in focused repro on both PR and base, label it transient timing evidence—not part of the repair scope—and avoid speculative fixes.

Good pattern:

> A Reader PR failed an existing search E2E test and a route-count documentation check. Both focused failures reproduced only on the PR head: the Reader component change explained the E2E regression, and a newly added private route made the documented count stale. A separate vertical test timeout passed on both heads. Keep the two concrete fixes on the source Review card and record the timeout as transient.

Reference: `references/open-pr-runner-disconnect-rerun-exposes-pr-owned-failure.md`

### Mixed CI failures: source-owned governance blocker plus off-diff timeouts

A broad test job can report more than one failure class at once. Do not collapse them into one diagnosis.

Required sequence:

1. Separate deterministic, PR-diff failures (for example a governance policy rejecting newly added test files that lack required invariant/justification metadata) from off-diff timeout failures.
2. Run the timed-out test files focused on both the PR head and a freshly bootstrapped current-base worktree. If a fresh base checkout first reports missing package resolution after `bun install --frozen-lockfile`, retry with `bun install --frozen-lockfile --force`, then rerun the focused tests; the initial missing package is setup noise, not test evidence.
3. If the focused off-diff tests pass on both heads, record them as transient shared-suite evidence and do not expand the source repair to alter those tests or CI policy.
4. Keep the deterministic blocker source-owned. If the implementation card is already in Review and external-worker follow-up is needed, create one narrow, claimable repair card that cites the PR, source card, run URL, head SHA, exact failed check, and affected files.
5. Require the repair worker to start from the current PR branch and update that branch without force-pushing, then verify the fresh GitHub check surface before calling the source card reviewable.

Good pattern:

> The CI job reported missing metadata in two newly added test files and three unrelated timeout cases. The timeout tests passed focused runs on both PR head and current base. Queue only the metadata repair against the existing PR branch; leave the timeout tests untouched and retain the source review card as the PR anchor.

### Governance can fail after every test passes

A standard CI job may run all tests successfully and then exit nonzero only after its governance report. Do not call this a flaky test or runner problem.

Required sequence:

1. Read past the `0 failures` test summary to capture the final `test:ci`/governance violation exactly.
2. Confirm the named top-level test file is new in the PR diff and repair only the required invariant/justification metadata; do not weaken policy, add retries, or alter unrelated product behavior.
3. Keep the existing Review card as the PR anchor. If separate external-worker ownership is needed, create one narrow rescue card that cites the source card, PR URL, run URL, SHA, failing job, exact metadata requirement, and existing PR branch.
4. Require the worker to update that branch without force-pushing and verify a fresh `pull_request` run on the new PR head.
5. On Haft, create and validate the rescue through `haft_ready_worktree_card.py` so the Ready card is unassigned, repo-root anchored, branch-named, and actually claimable.
6. In the rescue body, name the exact missing comment contracts and affected file. For the common test-governance form, require both:
   - `// test-invariant: <durable product or safety invariant>`
   - `// test-file-justification: <why an existing top-level file cannot own this coverage>`
   Keep scope to those metadata comments unless live evidence identifies a distinct failure.

Good pattern:

> The suite passed 2,845 tests with zero test failures, but the post-suite report rejected a new top-level test file missing its required durable-invariant and file-justification comments. Queue only that metadata repair; the previously green browser gates do not make the PR merge-ready while standard CI is red.

If the workflow skips typecheck/build after the governance failure, report those as **not executed**, not passing or independently failing. See `references/ci-governance-after-green-suite.md` for the compact evidence and branch-update handoff.

### Merged PR-only governance failure can be non-blocking when master is green

A pull-request CI run can fail its governance report after all tests pass because it evaluates newly added top-level test-file metadata relative to the PR base. Once that PR merges, the corresponding push-to-`master` run may legitimately pass because the same file is no longer new relative to `origin/master`.

Required sequence:

1. Capture the PR run's exact final governance violation; distinguish it from a test failure.
2. Confirm the PR is actually merged and record its merge-commit SHA.
3. Query the **push-to-master CI run for that exact merge commit**; do not infer its result from the PR run.
4. Require the latest master attempt and both job-level conclusions to be green before calling the issue non-blocking.
5. If master is green, add evidence to the source card and do **not** create a repair card solely to make the historical PR-only governance run green.
6. If master is red for the same metadata violation, create one narrow current-master metadata repair card; do not reopen or misclassify it as a product-test regression.

Good pattern:

> The PR run passed every test but failed only because a new top-level test lacked its governance comments. The PR was merged; the exact merge commit's push CI passed test, typecheck, build, and browser gates. Record the PR-only failure as historical and create no repair.

## Release workflow failure: tag-pinned code lags behind a master-merged fix

A tag-triggered release workflow executes the workflow files and helper scripts **as they exist at the tag's commit**, not current `master`. If the exact failing step was already fixed on `master` but the tag points at an older commit, the release will keep failing on the old code no matter how many times you rerun it.

Common shape:

- a release tag `vX.Y.Z` points at commit A (for example a `chore: bump version` commit);
- a CI/deploy fix PR merged to `master` as commit B, after commit A;
- the release run fails in a step that commit B already repaired;
- rerunning the same tag re-executes the old broken script at commit A and fails identically.

Required sequence:

1. Capture the failing job, step, and exact error from the run (use `gh api repos/<owner>/<repo>/actions/jobs/<job-id>/logs` when `--log-failed` returns empty).
2. Read the failing script or workflow file **at the tag's commit** (`git show <tag-sha>:<path>`).
3. Check `git log --oneline <tag-sha>..origin/master -- <failing-file>` to see if a fix merged after the tag.
4. If a fix exists on master but the tag predates it, report that the fix is already merged and the tag is stale — do not create a duplicate repair card.
5. Present the operator with the two standard recovery options:
   - **re-tag** the same version at current `master` (includes the fix) and re-trigger;
   - **bump** to the next version and release fresh.
6. Do not re-tag or bump autonomously unless the operator confirms — both have release-semantics implications.

Good pattern:

> `v0.1.49` failed in "Reclaim reproducible release runner caches" with `rm: cannot remove ... Directory not empty`. The fix (`rm -rf ... || true`) already merged to master as `c5a3b6bb` (#1345), but tag `v0.1.49` points at `2a00cb92`, which predates it. Rerunning the same tag will fail identically. Options: re-tag `v0.1.49` at current master, or bump to `v0.1.50`.

Reference: `references/tag-pinned-release-lags-master-fix.md`

## Release cleanup race on shared multi-tenant runners

A release cache-cleanup step (`rm -rf` under `set -euo pipefail`) can fail with `rm: cannot remove '<path>': Directory not empty` when concurrent jobs on the same self-hosted runner are actively writing to the cache (e.g. `bun install` populating `.bun/install/cache` while the release job deletes it). This is a **shared-runner concurrency race**, not a disk-capacity or product-code issue.

Required sequence:

1. Capture the exact `rm` error and the contested path from the failed job log (use `gh api repos/<owner>/<repo>/actions/jobs/<job-id>/logs` when `--log-failed` returns empty).
2. Check for concurrent processes writing to the same path (`ps aux | grep 'bun install'` or similar).
3. Confirm disk space is adequate — the failure is file-level, not space-level.
4. Classify: if the cleanup script is best-effort (the capacity preflight is the actual gate), the root cause is that `set -e` makes a non-critical cleanup step fatal.
5. The durable fix is to make `rm` non-fatal with retry + warn-and-continue. Do not weaken the capacity preflight itself.
6. For the immediate rerun: do **not** just "wait and rerun" — on a busy shared runner the long-lived services (agent dashboards, gateways, watchers) hold open handles in the cache and repopulate them between reruns, so attempts can fail identically (this incident failed attempts 2 and 3 the same way). The reliable recovery is to **manually clear the contested cache path on the runner host** (`rm -rf <path>` succeeds from an interactive shell once the racing writer is momentarily idle and does not abort on transient "Directory not empty"), then rerun the failed jobs. The cache is reproducible, so clearing it is safe.
7. If all runners with the deploy label are busy, the rerun will sit in `pending` — report this as queued, not failed.
8. After a green attempt, verify every fan-out environment's health surface serves the intended tag/commit before calling the release recovered.
9. If the fix is already on `master` but the release tag predates it, apply the tag-pinned-lag pattern above (rerun will fail identically; re-tag or bump).

See `references/release-cache-cleanup-race-shared-runner.md` for the full evidence pattern.

## Release workflow failure: self-hosted runner capacity gate

A tag-triggered release can fail before any artifact publication or environment swap because a self-hosted runner's disk-capacity preflight fails. Treat that as an **active release-blocking infrastructure incident**, not a product regression and not a successfully deployed release.

Required sequence:

1. Capture the immutable tag and SHA, latest `run_attempt`, failed job/step, and the exact disk annotation (free space versus required threshold).
2. Enumerate all fan-out jobs. State explicitly which stages were skipped (for example CLI publication, HQ binary swap, Gly, or Dev) rather than calling the overall run simply “red.”
3. Probe the live HQ, Gly, and Dev health surfaces and compare embedded version/commit to the intended tag. A healthy prior release proves availability only; it does not prove the failed release reached that environment.
4. Check that the runner is online and not busy before proposing cleanup. Inspect disk consumers first; never blindly delete workspaces, credentials, or service data.
5. If the workflow failed before immutable CLI publication or an HQ swap, a retry of the same tag may be safe **after** capacity is restored. Do not move/recreate the tag or manually overwrite release media. Require more headroom than the workflow minimum (for example 6 GiB free for a 4 GiB gate) before rerunning.
6. If there is no source PR/card because this was direct release work, create one narrow operator/reliability card that records `source card: none`, the run URL, tag/SHA, failed capacity check, safe-cleanup boundary, rerun requirement, and per-environment health verification. Do not invent a retrospective source implementation card.

Good pattern:

> `vX.Y.Z` failed in the self-hosted runner’s capacity preflight with 1 GiB free against a 4 GiB minimum. Candidate verification completed, but CLI publishing and all runtime deploy jobs were skipped. HQ/Gly/Dev remain healthy on the prior embedded release. Restore runner headroom, then rerun the unchanged immutable tag and verify every environment’s embedded build.

## Release failure can be partially remediated outside the failed Actions run

A release workflow may remain red even though an operator or separate automation completed part of the intended release after the job failed. Do not infer deployment state solely from Actions job conclusions such as `skipped`.

Required sequence:

1. Capture the workflow's actual stop point: failed job, exact setup/step error, and all downstream skipped jobs.
2. Independently verify each release surface that matters:
   - public CLI manifest / `latest.json`, including version and immutable commit;
   - HQ health provenance;
   - Dev health provenance;
   - GLY health provenance.
3. Compare each observed version and commit to the intended immutable tag SHA.
4. Classify the outcome precisely:
   - **unreleased** — none of the target surfaces reached the intended build;
   - **fully recovered outside Actions** — all target surfaces match despite the red workflow;
   - **partially recovered** — some surfaces match while others remain healthy on a prior build.
5. Before rerunning, check for an active remediation and whether a rerun would repeat a production fan-out that already partly completed. Do not rerun merely to make Actions green.

Good pattern:

> The release run failed during checkout download with a 429 and marked downstream jobs skipped. The CLI manifest and HQ health nevertheless serve the intended immutable build, while Dev and GLY remain healthy on the prior build. Report a partial recovery and require an explicit decision before another production fan-out.

### Post-suite cleanup EFAULT on a self-hosted build host

A CI job can pass its test suite and governance report but fail immediately afterward in stale-temporary-artifact cleanup. Treat this as a **runner/filesystem cleanup incident**, not a source-test failure, when the log has a filesystem syscall error such as:

```text
fs.rmSync(...): EFAULT: bad address in system call argument
```

Required sequence:

1. Inspect the job-step list, not just the workflow conclusion. Record successful tests/governance separately from skipped `typecheck` and `build` steps.
2. Pull the failed cleanup log and capture the concrete syscall, errno, and one affected path. Do not include private artifact contents in board notes.
3. Rerun only the failed job once. If a second attempt fails with the same syscall on a different stale path, classify it as recurring host/cleanup behavior rather than a one-off bad directory.
4. Check current open or recently merged PRs for an existing cleanup/runner remediation before creating new work. If a current repair makes cleanup bounded/best-effort while retaining an observable warning and its own full CI run passes, treat that repair as the active owner.
5. Do not claim the original run recovered merely because the repair PR is green: its own rerun or a fresh relevant CI run remains separate evidence. If the old rerun remains red but current-master repair CI is green, report the old alert as a confirmed historical failure with a verified forward fix.

Avoid deleting arbitrary `/tmp`, runner workspaces, credentials, or service data to clear the alert. Host-level remediation should be scoped separately from CI's false-negative cleanup policy.

### Open integration-branch PR: post-suite cleanup failure already owned elsewhere

An open PR into a long-lived integration branch can pass its governed suite and browser gate but fail at post-suite cleanup because its base has not absorbed the active runner-cleanup repair. Treat this as shared CI/host evidence when the failure is an approved-temp-prefix filesystem error (such as `fs.rmSync` `EFAULT`), the product PR does not modify cleanup/workflow code, and a live claimable cleanup/privilege-contract card already owns remediation.

Required action:

1. Add one concise source Review-card comment with the run URL, head SHA, passed/failed/skipped lanes, and cleanup-card ID.
2. Keep the source card in Review but mark it **unverified**; do not create a duplicate product rescue or ask the feature author to change unrelated code.
3. State `typecheck` and `build` as **skipped/not executed** if cleanup prevented them from running.
4. Require a fresh PR-triggered run after the shared repair is integrated into that PR's actual base branch. A green repair PR on another base does not verify this source PR.

## Master/push CI failure: self-hosted runner filesystem exhaustion

A push CI run can fail without executing any repository test if the self-hosted runner cannot write its own diagnostics. Typical evidence is a failed job whose test/typecheck/build step has no conclusion plus a check-run annotation such as:

```text
System.IO.IOException: No space left on device
.../actions-runner/<runner>/_diag/Worker_<timestamp>.log
```

Treat this as an **active runner-capacity incident**, not product-regression evidence.

Required sequence:

1. Recover the full run id if the notification URL/id is truncated, then query its latest attempt and jobs.
2. Confirm whether a sibling job (for example browser gate) passed and whether the failed job stopped before its test step.
3. Query the failed check-run annotations. The runner diagnostic write error is stronger evidence than an empty failed-job log.
4. Inspect the runner host before changing anything: root filesystem free space, runner online/busy state, runner work/diagnostic usage, caches, logs, and deleted-but-open files.
5. Do not blindly prune Docker images, worktrees, credentials, service data, or arbitrary user directories. Identify a scoped cleanup plan and require materially more free space than the workflow needs; use at least 6 GiB headroom for a 4 GiB-style CI gate.
6. Add a concise board comment to the active affected implementation/review card: run URL, SHA, exact infrastructure annotation, and that implementation must not be judged from this run.
7. After headroom is restored, rerun only the failed job (or failed jobs), then re-query `run_attempt`, final run state, and latest-attempt job conclusions before calling CI recovered.

Do not create a speculative source-code repair card from a docs-only or otherwise off-diff master push merely because this failure email arrived after merge.

### Truncated PR alert after merge, with a new base run queued

A notification can show only a short numeric Actions-run prefix (for example `30253`) while the PR merges and starts a separate push-to-base run. Do not conflate the two runs or call the merge commit green from a sibling browser gate.

1. Recover the complete PR-run ID by matching workflow name, display title, short SHA, branch, and notification time.
2. Read the failed job's check-run annotations. An empty failed log plus an unfinished test step can still be a runner diagnostic-write failure, not a test failure.
3. Query the PR merge commit, then separately query the push-to-base run for that exact SHA.
4. Inspect live runner disk/headroom and busy state before retrying. If capacity is restored, rerun **only** the alerted failed job. A rerun endpoint response of `201 Created` proves acceptance only; poll until `run_attempt` advances and the job completes.
5. If either the rerun or the base push is `queued`/`in_progress`, report both as unverified. Create no source-code rescue card unless a current attempt identifies a product failure.

### Post-merge rerun exposes rotating off-diff timeout failures

A focused pass plus one failed-job rerun is not enough to call a master-push timeout recovered when the rerun fails in a **different** off-diff test surface.

Required sequence:

1. Capture each attempt's exact timed-out tests, runner identity, and whether sibling gates passed.
2. Verify the initial failing file in a freshly bootstrapped isolated worktree at the alert SHA; a focused pass is evidence against a deterministic source regression, not proof that the full suite is healthy.
3. Rerun only the failed job once. If the rerun succeeds, report recovery under the normal off-diff-timeout flow.
4. If the rerun fails with a different off-diff timeout set, classify this as a **persistent rotating full-suite reliability incident** (contention, shared state, resource pressure, or lifecycle leak), not as a failure of the merged source PR.
5. Check for a prior CI-reliability remediation/card before opening work. If it exists but did not prevent the new evidence, create one successor card that explicitly audits the earlier mitigation rather than duplicating its scope.
6. Keep the merged source card Done and add the attempt-by-attempt evidence there. Create one separate, claimable reliability card with the run URL, SHA, runner names, exact timeout surfaces, focused repro result, and an explicit no-blanket-timeout/no-test-skipping boundary.

Good pattern:

> Attempt 1 timed out in five cases from one unrelated test file; that file passed 8/8 in a clean worktree at the same SHA. Attempt 2, on a different self-hosted runner, instead timed out in two other unrelated files while the browser gate passed. The right outcome is a persistent full-suite reliability investigation, not reopening the merged feature card.

### Repeated protocol-contract failure on a docs-only PR and its exact master commit

A docs-only PR can surface a real, pre-existing runtime or harness regression. Do not attribute the failure to the documentation change, but do not dismiss it solely because a focused local run passes.

Required sequence:

1. Prove the PR diff is documentation-only (or otherwise outside the failing implementation/test surface).
2. Inspect the push-to-base CI run for the **exact merge commit** separately from the PR run.
3. If the same exact assertion fails in both runs, classify it as a recurring current-master regression even when a clean focused local run passes; that local pass is evidence of execution-order/load sensitivity, not recovery.
4. Record the expected-versus-received contract, not merely the test name. For protocol fixtures, preserve the fail-closed invariant (for example, a valid receipt followed by extra stdout must not be accepted as a completed result).
5. Search the live board for a card already owning the same file and failure class. If none exists, create one narrow claimable repair card; keep distinct nearby runner/timing incidents separate unless shared-cause evidence emerges.
6. Do not create a repair card for an additional one-off timeout from the PR run unless it also persists, reproduces, or recurs on master.

Good pattern:

> A documentation-only PR's CI and the CI run on its exact merge commit both accepted trailing protocol output as a completed runner result. The focused test passed in a clean worktree, so the failure appears execution-order-sensitive rather than resolved. Create one protocol-finalization repair card, not a docs-PR rescue or a broad CI-flakiness ticket.

### Metadata-only follow-up commit can surface a recovered browser miss

A PR can first pass an extended/browser workflow on a functional head, then receive a metadata-only follow-up (for example test-governance comments) whose fresh browser run fails in an interaction test. Do not attribute the regression to the metadata edit merely because it is the new head.

Required sequence:

1. Compare the two PR heads and prove whether the follow-up changed executable code, test behavior, or only comments/metadata.
2. Capture the exact failed browser assertion and whether Playwright retry reproduced it within attempt 1.
3. Inspect the immediately preceding functional-head workflow result for the same browser suite.
4. Rerun only the failed job, then re-query `run_attempt`, final conclusion, and latest-attempt job outcome.
5. If attempt 2 passes and the preceding functional head also passed, record recovered transient browser evidence on the source Review card; keep it in Review and create no additional rescue card.

If the rerun endpoint reports that the workflow is already running, re-query live state immediately; it indicates an active newer attempt, not a permission or workflow-definition failure.

### Self-hosted checkout corruption can fail before dependency installation

A self-hosted runner may fail in `actions/checkout` before repository code, dependency installation, or tests run. Useful signatures include `fatal: bad object refs/remotes/origin/<branch>`, a first fetch reporting broken local remote refs (for example `cannot lock ref 'refs/remotes/origin/<branch>': reference broken`), or a checkout retry ending with `fatal: --unshallow on a complete repository does not make sense`.

Required sequence:

1. Confirm the failed job stopped at **Checkout** and record whether install/test/typecheck/build steps were skipped or never started.
2. Capture the runner identity and the first broken-ref error plus the retry error; do not summarize it as a source-code or dependency failure.
3. Check whether sibling jobs passed on other runners. A green browser gate is not proof the required verify lane ran.
4. Query the PR's current head separately from the alerted SHA and inspect any targeted ref-cleanup change. If current-head checks are queued or in progress, call the PR **unverified**, not recovered or still code-red.
5. Attach the evidence to the existing runner/workspace remediation owner and to the affected source Review card; do not create a product-code rescue from this signal.
6. Repair runner checkout/workspace hygiene without weakening fetch coverage, then require a fresh PR-triggered run on the same head (or its repaired successor) before calling the source PR verified.

See `references/checkout-stale-remote-ref-pr-recovery.md` for the compact stale-alert/current-head evidence shape.

Good pattern:

> CI attempt 2 is still red, but required verification never reached Bun install: checkout hit broken origin refs and its retry used `--unshallow` against a complete clone. The browser sibling passed elsewhere. Treat this as a runner workspace-corruption incident, preserve the source PR's separate deterministic blocker, and require a fresh PR run after runner repair.

## Important pitfall: a cleanup remediation can introduce a non-interactive privilege failure

A repair for cross-runner-owned temporary state can change an unprivileged cleanup command to `sudo`. Treat the first red run after that change as a new workflow/host-contract failure, not proof that the original cleanup error persists.

Required sequence:

1. inspect the cleanup step's terminal output and distinguish the original filesystem error (ownership, `EFAULT`, or containment refusal) from a new `sudo`/authorization error;
2. record which suite steps completed and which later gates were skipped; do not call typecheck/build green if cleanup prevented them from running;
3. retain serialization and cleanup path allowlists while scoping a least-privilege, non-interactive mechanism;
4. never recommend broad `NOPASSWD`, an unrestricted runtime/interpreter command, shell wildcards, or arbitrary `/tmp` deletion;
5. if no source card exists and the latest run is still red, create one narrow repair owner that requires fresh PR CI and explicitly excludes unrelated off-diff timeouts.

### Combined off-diff timeout plus post-suite cleanup failure

One required job can contain two independent lanes: a suite timeout and a later runner-cleanup failure. Do not collapse them into a source-PR regression.

Required sequence:

1. Capture the timed-out test, threshold, duration, and relation to the PR diff.
2. Re-run that exact test repeatedly on both the PR head and freshly bootstrapped current base. If it passes on both and is off-diff, treat it as transient full-suite evidence.
3. Inspect later cleanup steps independently. An interactive/unauthorized `sudo` means a rerun can recover the test lane yet still leave the whole job red.
4. Repair cleanup separately while retaining the lock and path allowlists: use a narrowly scoped, non-interactive root-owned helper or equivalent least-privilege mechanism. Never grant broad `NOPASSWD`, shell wildcards, or generic interpreter/script execution.
5. State typecheck/build as **skipped** if preceding failures prevented them from running. Keep the PR in Review until a complete fresh required job is green.

Good pattern:

> An off-diff asset test timed out but passed repeated PR-head and base runs. Later cleanup failed because `sudo` demanded a terminal. Rerun the failed job to verify the test lane, but separately repair the cleanup privilege contract; do not edit the source PR merely to chase either runner failure.

Good pattern:

> The original cleanup failed on stale cross-runner files. Its follow-up then failed because `sudo` requested a terminal/password. Queue only the cleanup-privilege repair; preserve the lock and containment rules, and triage unrelated suite timeouts separately.

## Verification checklist

- [ ] Live run queried by run id
- [ ] Current `status` / `conclusion` captured
- [ ] Latest `run_attempt` identified
- [ ] Attempt-specific failures compared when reruns exist
- [ ] Final user-facing statement reflects the **latest** attempt, not just the first notification
- [ ] Any follow-up work narrowed to the real underlying issue when the run recovered
- [ ] For open PR alerts on board-backed repos, the source review card was updated before considering any new fix card
- [ ] When the notification names a chore/bump PR, the actual regression source was traced to the feature PR that introduced the failing code
