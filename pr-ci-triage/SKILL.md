---
name: pr-ci-triage
description: Diagnose failing PR checks by separating environment/setup noise, stale-branch drift, and true regressions before changing unrelated code.
---

# PR CI Triage

## When to use
- A PR is failing CI and you need to determine whether the branch actually introduced the failure.
- Especially useful when the visible diff is narrow (docs, skills, config, comments) but the failing checks are in unrelated product code.

## Core rule
Do **not** assume every red PR means the diff is broken. First determine whether the failure comes from:
1. unprepared local environment,
2. stale branch drift versus current base,
3. or a true regression caused by the PR.

## Workflow
1. **Use a worktree, not the canonical checkout.**
   - Keep canonical clean.
   - Create a dedicated review/worktree for the PR branch.

2. **For GitHub notification emails, resolve identifiers carefully.**
   - A short SHA in an email subject is not an Actions run id; `gh run view <sha>` will 404.
   - Notification payloads can also truncate a numeric Actions run ID (for example, `30448` instead of `30448592092`); do not retry the shortened number. Resolve the commit SHA to its PR, then recover the full run ID from `statusCheckRollup[].detailsUrl` or `gh run list --branch <branch>`.
   - Map SHA → PR first, e.g. `gh pr list --repo OWNER/REPO --search "<sha>" --json number,title,headRefName,headRefOid,url,state,statusCheckRollup`.
   - Extract the real run/job URL from `statusCheckRollup[].detailsUrl` or `gh run list`, then call `gh run view <run-id> --log-failed`.
   - Reduce failed logs to: failed check name, command, failing file/test, top error, stack top, PR URL, run URL.
   - If the email points at a workflow-dispatch or branch-specific deploy run, compare the branch's workflow file against current base **before** assuming the failure is still current-base work. A useful pattern is to fetch the branch version directly from GitHub even when the branch is deleted or not present as a local ref, for example `gh api repos/<owner>/<repo>/contents/.github/workflows/<workflow>.yml?ref=<branch> -H 'Accept: application/vnd.github.raw'`, then compare it to the current checked-out/base workflow. This quickly separates stale-branch workflow drift (old env vars, old versioning scheme, missing deploy inputs) from live `master`/`main` blockers that still deserve a repair card.

3. **For board-backed projects, create a focused fix card instead of burying CI evidence in chat.**
   - Leave the source PR/card in Review while CI is red.
   - Comment concise failure evidence on the source card.
   - Create a Ready external-worker fix card with the source card id, PR URL, run URL, branch to push to, and acceptance criteria.
   - **Unboarded-PR fallback:** do not skip repair intake merely because no source card can be found. Record that discovery in the repair card, include the PR URL/current head/base-or-parent SHAs and the exact reproduction result, then create one claimable card that targets the existing PR branch. This preserves a durable owner without inventing a source-card relationship.
   - Validate any claimable worktree card with the project helper before reporting it as runway.
   - **Haft-specific:** use `python3 <shared-scripts-root>/haft_ready_worktree_card.py create ...` for the follow-up card, then immediately run the helper `validate <task_id>` so the Ready lane is confirmed claimable (`assignee=null`, repo-root workspace, non-empty branch metadata) before handing it to workers. The helper enforces branch-name uniqueness, so if the fix must land on the PR's own branch (the usual case), the PR's source card already holds that branch slug and `--branch <pr-branch>` fails closed with `branch_name already exists on another task`. Use a unique synthetic worktree slug and state the real PR branch + PR URL in the card body as the push target. See `ready-worktree-card-creation` → "Targeting an existing PR branch".
   - If the failure is operational checkout/deploy state rather than the PR diff (for example canonical checkout divergence), capture the exact run/job URL, failed step, local/remote SHAs, and remediation acceptance criteria in the card body rather than opening a speculative code-change task.
   - **Blocked-owner split:** an existing incident card can be the right historical owner yet be blocked on a separate human approval (for example a service restart) while a newly observed CI-container provisioning repair is executable without that approval. Do not leave the executable repair trapped behind the unrelated blocker. Add cross-linked evidence to the existing incident, then create one focused, claimable repair card for the separable runner/image/runtime contract. Explicitly exclude the approval-gated operation from the new card and keep the source PR in Review until its own fresh rollup is green.
   - **Partial-intake repair expansion:** a notification can first expose one deterministic PR failure while another required workflow is still running. If a claimable repair card already owns that PR branch, wait for the current run's terminal rollup, inspect every failed job, and append newly confirmed failures to that same card rather than creating a competing rescue card. Establish attribution by running the exact failed test on the PR's actual base in a disposable worktree: a base pass plus a PR-head failure makes even an unchanged test an in-diff regression lane. Keep the PR in Review until the repaired head has a fresh all-required-check rollup.
- **Merged-rescue freshness trap:** an earlier CI-rescue PR may be merged, then incorporated through an update-branch/merge commit, while the original PR's fresh run still fails the same browser tests. Do not assume the old rescue remains the owner or reopen its completed card. Run the exact affected specs on both current `origin/master` and the current PR head using isolated Playwright ports. If base passes and head fails, classify the failure as current-PR-local even when it names an apparently off-diff browser seam. Keep the source card in Review, comment the two results and fresh run/job, and create one synthetic-branch Ready repair card that explicitly pushes back to the existing PR branch. Require a fresh extended-suite green result on the repaired current head.
   - If the failing run is a **post-merge push on `master`/`main`** rather than the PR's own checks, treat it as a follow-up investigation, not proof the merged PR's implementation card was wrong. Comment the source card with the failing test/job, locally rerun the exact failing test (repeat it several times if it smells flaky), trigger a failed-job rerun on GitHub, and create a separate Ready worktree follow-up card for the CI investigation when the result is still uncertain.
   - If the PR is already merged and there is already a follow-up implementation/recovery card tied to that merge or spec, prefer adding the fresh CI evidence to that existing card instead of opening a duplicate rescue card. When the failed-job rerun finishes green and the targeted current-base repro passes repeatedly, stop at the evidence comment and classify it as transient/flaky.
   - For narrow release/version bump PRs, compare the diff against the failing test names before assuming infrastructure. If the PR only updates `package.json` or one version test but CI failures mention CLI/version/release-tag expectations, search the repo for remaining version-coupled assertions and runtime manifests first; these PRs often fail because parity updates were incomplete, not because base is broken.

4. **Hydrate the worktree before trusting failures.**
   - Install dependencies.
   - Re-run the failing commands only after the worktree is actually ready.
   - Missing deps (`Cannot find package ...`, missing generated assets, missing lockfile installs) are setup noise, not evidence the PR is wrong.
   - For fixture-driven failures involving secure/private persistence, inspect the fixture's filesystem setup before debugging route logic. A fixture that pre-creates a directory with default `mkdir` permissions (commonly `0755`) can deterministically fail a storage layer that correctly requires private subdirectories to be `0700`. Compare the exact directory mode with the storage invariant, then prove attribution by changing the mode only in a disposable worktree and rerunning the exact test. Repair the fixture/helper; do not weaken the production security check.

5. **Reproduce the failing check locally.**
   - Run the same class of check CI is running: targeted test first if known, then full `test` / `typecheck` / `build` as appropriate.
   - Preserve the runner family. For a Playwright failure, use `bunx playwright test <exact .playwright.ts path>` (or the project's `test:e2e` command), not `bun test <path>`: Bun can report `0 pass, 0 fail` for a Playwright spec, which is not a reproduction.
   - For a narrow release/version-bump PR whose diff does not touch the failing E2E area, run the exact failed Playwright spec twice locally and rerun the failed GitHub job before classifying it as a blocker. A green rerun plus repeatable local passes is transient evidence; document it rather than changing unrelated release code.
   - **Policy-check versus contract-check split:** a focused policy/lint command can pass while the full suite still fails a stricter source/contract test over the same file (for example, a CSS ratchet measured differently by a UI policy script and a legacy test). Do not treat the focused policy pass as closure. Extract every full-suite failure, run its exact test file on the PR head, and include it in the repair verification. If a second failed test is outside the PR diff, run it on fresh current base before editing it; a current-base pass makes branch freshness/rebase the first repair step, not an invitation to change unrelated code.

6. **Compare the failing area against current base.**
   - Check whether the PR branch is behind current base.
   - Run the same targeted failing suite on clean current `main`/`master` in a separate worktree.

7. **Interpret correctly.**
   - If the failing suite also fails on current base: likely a true product failure unrelated to the branch.
   - If it passes on current base and the PR diff does not touch the failing area: suspect stale-branch drift first, especially if the PR is a merge commit (conflicts may have been resolved against an older base that has since evolved).
   - For a **post-merge push failure on `master`/`main`** where the targeted reruns pass repeatedly on clean current base, a clean current-base full suite also passes locally, and the GitHub failed-job rerun finishes green: classify it as a transient/flaky push failure, document the evidence on the source card, and do **not** open a follow-up fix card.
   - **Billing-gated GitHub-hosted platform job:** if a hosted macOS job fails before execution with an annotation such as `recent account payments have failed or your spending limit needs to be increased`, verify the job has no runner, no steps, and zero billable duration before classifying it as code or runner failure. Do not route a Darwin/platform-boundary job to an existing Linux self-hosted runner; that would silently remove the platform coverage. To suspend automatic PR attempts without creating a missing required check, keep both `pull_request` and `workflow_dispatch` triggers and add a job-level condition such as `if: ${{ github.event_name == 'workflow_dispatch' }}`. This records the PR check as skipped while preserving an explicit manual dispatch path. Note that `workflow_dispatch` still uses the configured hosted runner unless the workflow is separately changed to a real self-hosted macOS label; it does not bypass GitHub billing.
   - **Account-level admission can affect any hosted workflow, not only macOS:** for scheduled/manual workflows, classify a completed zero-step job with `runner_id=0` or an empty runner name, zero duration/billable time, and no logs as provider/account admission failure when the annotation or existing incident identifies billing, payment, or spending-limit gating. Check recent same-workflow runs to establish recurrence, update the existing approval/incident card with the newest run ID, job ID, timestamp, SHA, and recurrence window, and do not edit workflow code or blindly rerun until the operator resolves the account gate. Recovery requires a fresh run that acquires a runner and executes at least its first step. See `references/pre-start-admission-triage.md`.
   - **Self-hosted runner sequence:** a first run can end in runner-communication loss while a rerun reaches a genuine assertion or timeout failure. Preserve both facts. If the rerun fails in a file outside the PR diff, run that exact file at least three times on both clean current base and the unchanged PR head. When all focused runs pass and a further failed-job rerun passes on the same head, classify it as suite/runner-load flakiness rather than modifying the unrelated PR. Record the runner name, failed cases/durations, focused-repeat evidence, and passing rerun URL; create a separate reliability follow-up only if recurrence justifies it.
   - **Full-suite-only repeated failure:** if the same off-diff E2E test fails in its in-job retry and again on a failed-job rerun, including on a different runner, while the exact isolated spec passes three times on clean current base, do not repair the feature PR or call the incident transient. Classify it narrowly as a suspected shared-suite state/isolation failure. Keep the PR in Review because its required gate is red, comment the attempt/job URLs plus the isolated-repeat results on the source card, and defer a separate reliability card until a third independent full-suite recurrence or a concrete shared-state mechanism is found.
   - **Runner I/O pressure evidence from CI governance reports:** Bun test governance reports include a `CI runner context` block with PSI metrics at start and finish (`io-pressure=some avg10=...`). When clustered test timeouts occur in a file the PR does not touch, extract the start and finish `io-pressure` avg10 values. A material spike (for example 0.59 → 6.25) is concrete, citable evidence that the runner was under I/O contention during the run. Combine with the **partial-file timeout pattern**: if only some tests in the off-diff file time out (for example 4 of 9 cases) while the rest pass, the passing cases prove the code is correct and the timeouts prove the runner was slow. Then check the most recent master/main CI run for the same failure *class* (timeouts) even in a *different* file — if master also has timeout failures, this establishes a systemic runner-pool I/O problem without needing local repro. Classify as runner contention, recommend a CI rerun when the runner is less loaded, and file a reliability follow-up only if the pattern recurs across 3+ runs. See `references/runner-io-pressure-timeout-evidence.md`.
   - Rebase or merge current base into the PR branch before editing unrelated code.
   - After rebase, re-run the same targeted checks to confirm whether the fix was branch freshness or a real regression.

8. **Only change code when the failure survives rebasing.**
   - After rebasing, rerun the same checks.
   - If green, the fix was branch freshness.
   - If still red, then debug the actual regression.

## Stale-branch CI-policy/workflow-content assertions (rebase-only fix)

A distinctive stale-branch shape: the failing tests are **CI governance/policy tests that statically assert on workflow file contents** (for example `expect(workflowYaml).toContain("flock ... bun run test:e2e:extended")` or `expect(extendedWorkflow).toContain("bun run test:e2e:extended")`), and the PR branch was cut before master merged unrelated CI-workflow changes. The PR's own code is fine; the assertions read the branch's stale copy of `.github/workflows/*.yml`.

Signals:
- failing test names contain `CI`, `policy`, `governance`, `lane`, `hardening`, `consolidation`, or `contract`;
- the assertion is `expect(<workflow/config string>).toContain(...)` / `.toBe(...)` over a workflow YAML body;
- the PR diff does not touch the asserted workflow file, yet the assertion fails.

Fast diagnosis (two `git log` comparisons, no local test run needed first):
```bash
# What the branch adds over master (the PR's real work)
git log --oneline origin/master..origin/<branch>
# What master changed in workflows since the branch diverged (the drift source)
git log --oneline origin/<branch>..origin/master -- .github/workflows/
```
If the second command lists CI-workflow commits the branch lacks, the failure is stale-branch drift. The fix is a **rebase onto current master**, not a code change.

Required sequence:
1. Run the two `git log` comparisons above to prove the branch predates master's workflow changes.
2. Confirm the asserted string is genuinely absent from the branch's workflow file but present on master.
3. File a narrow rebase repair card: rebase the branch onto `origin/master`, force-push, verify CI goes green. Add the fallback note: if a governance test still fails after rebase (the branch's *own* commits changed a workflow incompatibly), update that test's expectation to the new workflow reality rather than reverting.
4. Do not open a product-code rescue — the PR's feature code is uninvolved.

Good pattern:
> PR #1353's CI failed two governance tests asserting `flock ... bun run test:e2e:extended` and `bun run test:e2e:extended` in the workflow YAML. `git log origin/fix-...-collision..origin/master -- .github/workflows/` showed master merged #1347/#1351/#1352 (workflow changes) after the branch was cut. The branch is stale; file a rebase-onto-master card, not a code fix.

## Stale UI-style-policy baseline drift (rebase-only fix)

A narrowly scoped backend/CLI/path PR can fail `Verify UI style policy` even when it does not touch authored CSS. Treat this as **stale-base policy drift** when all of these hold:

- the failed step is `bun run verify:ui-style-policy` (or its CI wrapper), with an error such as `legacyStylesCss ceilings may not increase`;
- the PR diff does not intentionally change `apps/web/src/styles.css`, `config/ui-style-policy-baseline.json`, or policy scripts;
- current base added or tightened `currentDebtCeiling`, `legacyStylesCss`, or generated-CSS policy files after the branch point; and
- independent browser/platform gates pass.

Diagnosis:

```bash
git log --oneline origin/<branch>..origin/master -- \
  config/ui-style-policy-baseline.json scripts/haft-ui-style-policy.ts \
  apps/web/src/styles.css apps/web/src/styles.tailwind.css
git diff origin/master...origin/<branch> -- \
  config/ui-style-policy-baseline.json apps/web/src/styles.css
```

Repair by rebasing onto current base, retaining the base policy ratchets, and rerunning the style-policy command. Do **not** increase ceilings or add a growth exception merely to make an unrelated PR green; an exception requires actual, justified authored legacy-stylesheet growth. In the board handoff, name the exact failed run/job, current-base policy commits, and the PR branch that must receive the `--force-with-lease` update. Keep the source card in Review and route the rebase through one claimable repair card that explicitly targets the existing PR branch.

## Minimal command pattern
```bash
# In PR worktree
git diff --name-only origin/master...HEAD
bun install --frozen-lockfile
bun test tests/some-failing-suite.test.ts

# Check freshness
git merge-base HEAD origin/master
git rev-parse origin/master

# In clean master worktree
bun install --frozen-lockfile
bun test tests/some-failing-suite.test.ts
```

## References
- `references/non-rerunnable-pr-check-fresh-head.md` — evidence-gated fallback when GitHub refuses failed-job reruns: repeated exact local passes plus a fresh empty PR head, never unrelated code edits.
- `references/github-notification-ci-triage.md` — compact recipe for converting GitHub CI failure emails into actionable PR/run evidence and board-backed fix cards.
- `references/stale-merge-conflict-pattern.md` — diagnosis and fix for failures that occur when a merge commit's conflict resolution becomes misaligned with current base as the base continues evolving.
- `references/post-merge-master-ci-flake-followup.md` — pattern for master/main push failures that appear immediately after merge: extract the failing test, rerun it locally, rerun the failed GitHub job, and split uncertain CI investigation into a follow-up board card.
- `references/bun-governance-failure-drilldown-2026-08-07.md` — session drilldown for the required Bun suite: download `bun-test-governance`, read `governance.md`, then extract the first concrete failing testcase from `junit-required-suite.xml` or the raw job log.
- `references/browser-gate-empty-log-artifact-drilldown.md` — browser-gate runs whose normal log is empty or unhelpful; use the job API plus the downloaded diagnostics artifact to recover the first concrete assertion.
- `references/cancelled-browser-gate-absent-artifact-and-follow-on-timeout-2026-08-10.md` — session note for a browser gate that canceled after retries with no downloadable diagnostics artifact, alongside a separate Bun timeout blocker in the same run.
- `references/architecture-boundary-ci-failure-handoff-2026-07-16.md` — example of an architecture-boundary gate failure inside the shared `bun test · typecheck · build` job and the exact review-card handoff shape.
- `references/test-assumption-drift-hardcoded-id-prefix.md` — when a PR legitimately changes an ID/slug/naming convention and breaks a test pinned to the old prefix; fix by asserting the resolved value the test already fetched, not a new hardcoded prefix.
- `references/runner-browser-deps-heterogeneity-2026-07-28.md` — cross-browser Playwright launch failure from missing system libs on a self-hosted runner pool; classification, response playbook, and fix commands.
- `references/runner-io-pressure-timeout-evidence.md` — using PSI io-pressure metrics from Bun governance reports plus partial-file timeout patterns and cross-run master correlation to classify clustered timeouts as runner contention without local repro.
- `references/source-text-jsx-formatting-brittle-assertion.md` — source-text `toContain('<Component prop=')` assertions that break when JSX is reformatted multi-line; fix the assertion, not the component.
- `references/default-parameter-drift-test-assumption.md` — a PR changes a function's default parameter value; an untouched test implicitly relied on the old default and fails deterministically; fix the test assertion, not the implementation.

## Same-head pending-gate check before rescue-card creation

When a notification exposes deterministic failures but another required workflow for the same PR head is still running, preserve the source card as the sole owner and defer rescue-card creation. Re-query `gh pr checks <number>` and the run/job metadata immediately before creating any repair card; a pending sibling may still produce additional failures or supersede the initial classification. Once every required check is terminal, append one bounded reconciliation comment naming the current head, each failed job, exact terminal error, and any cascade relationship, then create one focused repair card that targets the existing PR branch. Validate the card with the project’s claimability helper before reporting it as Ready.

For route-composition or similar startup-registry failures, distinguish the root failure from browser/test cascades: if a newly added route is absent from a reviewed ownership manifest, app startup can fail across unit, platform-boundary, and Playwright jobs while browser runtime preflights still pass. Repair the registry classification first; do not open separate browser-infrastructure rescues for the downstream failures. Also capture governance metadata failures separately when the same test lane reports missing invariant markers or equivalent policy violations.

## Multi-failure decomposition within a single run

See `references/same-head-startup-cascade.md` for the compact same-head pending-gate, startup-cascade, and single-rescue-card recipe.

A single CI run can contain failures from **different root causes** across its jobs. Do not report "CI is red" as a single diagnosis — decompose each failed job independently and classify each one:

1. **Pull per-job logs.** `gh run view <run-id> --json jobs --jq '.jobs[] | {name, conclusion, runnerName}'` shows which jobs failed and on which runners. Then `gh run view <run-id> --log-failed` gives all failed steps across jobs in one stream — read it fully, not just the first error.
2. **Classify each failure independently.** One job may fail on runner provisioning (missing `unzip`, missing lock dir), another on a real code bug in the branch (duplicate declaration, type error), and a third on a downstream consequence of the code bug (webserver won't start → Playwright can't connect). Report each with its own root cause and fix path.
3. **Identify cascading failures.** A code bug that prevents the dev server from starting will make every Playwright job fail with "WebServer was not able to start" — the Playwright failures are symptoms, not independent bugs. Trace back to the server-start error and fix that first.
4. **Report the decomposition.** Present findings as a numbered list of distinct failures, each with: failed job name, root cause category (runner-env / code-bug / cascade), exact error, and fix. This lets the user parallelize fixes (provision runners in one session, fix code in another).

## Post-merge governance-test follow-up PRs

When a merged PR changes workflow files (`.github/workflows/*.yml`) or config files that governance tests statically assert on, but does **not** update those tests, master's test suite goes red for every subsequent PR. The follow-up PR that fixes the tests is a distinct pattern from stale-branch drift:

- **Stale-branch drift:** the *branch* has old workflow files; rebase fixes it.
- **Post-merge governance breakage:** *master itself* has the new workflow but old test assertions; every branch fails until a dedicated test-alignment PR merges.

**Diagnosis:** the failing governance tests assert strings that are absent from master's workflow files (not just absent from the branch). Verify with `git show origin/master:<workflow-file> | grep <pattern>`.

**Review of the follow-up PR:** verify every added assertion string exists in master's current file, and every removed assertion string is genuinely absent. This is a test-only PR — zero product code changes. Its own CI may be red due to unrelated runner issues; that does not block merge if the assertions are correct.

**Conflict resolution for governance-test follow-up PRs:** these PRs frequently conflict because master merged the parent PR's workflow changes (which the follow-up is aligning to). Resolution strategy: keep master's (HEAD) version as the base — it already has the more precise assertions from the parent merge — and add only the follow-up PR's unique assertions (e.g. a new `playwrightConfig` check or a `--project=firefox` assertion not yet on master). Do not blindly take either side; produce the union. After resolving, verify no conflict markers remain and that indentation is consistent. Use `GIT_EDITOR=true git rebase --continue` in non-interactive shells and `--force-with-lease` for the push.

**Prevention:** workflow-changing PRs should be gated on their own governance tests passing before merge. If the repo has CI-policy tests that assert on workflow contents, those tests must be updated in the same PR that changes the workflow.

## Semantic-control migration regressions

When a PR replaces a custom control with a shared design-system primitive, a browser failure that cannot find the old ARIA role/name may be deterministic test drift rather than an implementation defect. For example, a custom `button` + `menuitem` role picker may correctly become a native/select-backed `combobox`; tests that still click the old button or menuitem will fail on every retry while unrelated checks pass.

Triage sequence:
1. Compare the failing locator and interaction with the PR diff and rendered control contract.
2. Verify the new control's semantic role, accessible label, allowed values, disabled behavior, and request payload—not merely its visual appearance.
3. Update the focused browser test to use the stable user-facing contract (for a native select, `getByRole("combobox", { name })` plus `selectOption`), while retaining assertions for mutation and refresh behavior.
4. Run the focused test on the PR head and current base when attribution is uncertain; do not weaken the shared primitive or add compatibility roles solely to preserve an obsolete test.
5. Keep the PR in Review until fresh required checks pass. If the implementation worker's run is still active, record evidence on the card and wait for the worker to hand off; do not attempt a review-state transition that the active claim cannot accept.

This class of failure is distinct from a product regression: the semantic contract changed intentionally, the implementation's core CI may pass, and repeated browser failures point to stale test assumptions. Preserve independent artifact-quota or upload annotations as separate infrastructure noise rather than conflating them with the assertion failure.

## Pitfalls
- Treating missing dependencies in a fresh worktree as a PR regression.
- Editing unrelated code before checking whether the branch is stale.
- Running repair work in the canonical checkout instead of a worktree.
- Trusting the full red CI surface before narrowing to the exact failing suite.
- **Empty browser logs are not the blocker:** when `gh run view --log` is blank, truncated, or otherwise unhelpful for a browser-gate run, use the job API plus the downloaded `playwright-browser-gate-failure` artifact to recover the first concrete assertion from `test-results/**/error-context.md`; do not assume the run is low-signal or retry the same empty log surface.
- **Focused reruns can hide a stale parallel assertion elsewhere in the suite:** when a PR intentionally changes an API/health/contract response and the updated targeted tests pass, the full CI suite can still fail because an older assertion in a different file was not updated (for example a legacy `tests/serve.test.ts` health contract while new `tests/health.test.ts` coverage passes). After reproducing the failing CI check, search the suite for the old assertion text or endpoint coverage before concluding the PR is green.
- **Self-hosted runner disconnects are infrastructure failures, not immediate code evidence:** if `gh run view <run-id>` or the run annotations say the job failed because the self-hosted runner lost communication with GitHub, do not treat the red check as a product regression by itself. Record the exact annotation, runner name, current PR head, and whether failed logs contain any assertion; a job that died while a test step was `in_progress` without an assertion is runner evidence, not a failed test. Add that distinction to the source card, trigger a failed-job rerun on the unchanged current head, and report the rerun as pending until its terminal result is verified. Do not attribute a deterministic extended-browser failure from another PR/run to this PR merely because it occurs in the same workflow; link the separate repair owner when one exists. Re-run the smallest relevant local verification in the task worktree, and only keep debugging code if the rerun or local verification reproduces a real assertion/build failure.
- **Runner browser-deps heterogeneity is a provisioning gap, not a code regression:** if a cross-browser Playwright suite passes all Chromium tests but fails a Firefox/WebKit test at `browserType.launch` with "Host system is missing dependencies to run browsers" (duration ~3ms, no assertion reached), the runner is missing system libraries (`libgtk-3-0t64` etc.). Confirm the same test passed in Chromium in the same run and/or on a different runner previously. Rerun the failed job (may land on a provisioned runner), comment evidence on the source card, and create an infra card for installing deps across the runner pool. Do NOT open a code-fix card. See `references/runner-browser-deps-heterogeneity-2026-07-28.md`.
- **Known-broken extended-browser workflow noise:** when a repo has a separate "Extended browser regressions" (or similar) workflow that fails identically on every PR due to a known runner-pool provisioning gap (e.g. `sudo: a terminal is required` in `Install Playwright system dependencies`), treat its failure emails as **infra noise, not PR signal**. Separate the core CI job (`bun test · typecheck · build`) from the extended-browser workflow: the core CI result is the merge-relevant signal; the extended-browser failure is tracked by the existing infra card. Do not create per-PR rescue cards for the extended-browser failure. Link the run evidence to the existing infra card and report the PR's code status from the core CI job only. If the extended workflow has failed identically on 3+ consecutive runs across different branches, note the friction: the workflow should be gated or disabled until the pool is repaired.
- **Failed-run reruns can be overtaken by a new PR head:** if you rerun a failed job and the worker pushes a follow-up commit while the rerun is in flight, the rerun may finish green for the old head SHA while the PR now points at a newer commit. After any rerun-based diagnosis, re-query the PR `headRefOid`, inspect the current diff, and verify whether the actual fix was a narrow follow-up commit on the branch (for example a test-timeout adjustment) before reporting the PR state. Treat the current PR head and its checks as authoritative over the historical failed run.
- **Post-merge push runs on `master`/`main` need separate classification:** when the PR checks were green but the later push workflow fails, do not immediately treat the merged implementation card as wrong. Extract the failing test from the push run, rerun it locally on current base, repeat it if flakiness is suspected, rerun the failed GitHub job, and move uncertain investigation into a separate follow-up card.
- **Architecture-boundary job failures are still PR-local blockers:** a failure in `Verify architecture boundaries` inside the shared `bun test · typecheck · build` job can coexist with passing browser smoke / contrast jobs. Do not merge until the exact boundary violation is addressed or the test is converted to a behavioral assertion with rationale.
- **Source-text assertions break on JSX/formatting changes — test brittleness, not product regression:** some tests read component source files and assert on literal text (for example `expect(appSource).toContain('<SheetContent side="right"')`). When a PR adds a prop, reformats JSX from single-line to multi-line, or Prettier reflows attributes, these assertions fail even though the component is functionally correct. Signals: the error is `Expected to contain: "<Component prop="value""` and the received text clearly contains the same component with the same props, just on separate lines. Diagnose by reading the assertion and the received source — if the semantic content is present but the literal string is split across lines, this is a formatting-brittle assertion. Fix: update the assertion to be formatting-agnostic (check for `side="right"` and `<SheetContent` separately, use a regex, or assert on rendered behavior instead of source text). Do not revert the JSX change to satisfy the old assertion. See `references/source-text-jsx-formatting-brittle-assertion.md`.
- **Default-parameter drift breaks untouched tests that relied on the old default — fix the test, not the implementation:** when a PR intentionally changes a function's default parameter value (e.g. `scope = "recursive"` was `"direct"`), any pre-existing test that calls that function without the parameter and asserts old-default behavior will fail deterministically. The test file is NOT in the PR diff, which can mislead triage toward stale-branch or infra explanations. Diagnose by tracing the failing assertion back to the changed default in the diff. Fix the test assertion to match the new default; audit all assertion blocks in the test for old-default assumptions (partial updates are common — the test name may reference the new behavior while a later block still asserts the old). See `references/default-parameter-drift-test-assumption.md`.
- **A PR that legitimately changes an ID/slug/naming convention breaks tests that hardcode the old format — this is test-assumption drift, not a product regression:** when the diff intentionally changes how an identifier is generated (for example a content-hash dedup that reconciles an `artifact-import-*` slug to the canonical catalog `artifact-page-*` identity), an e2e/unit assertion pinned to the old prefix will fail even though the behavior under test is correct. Diagnose by reading the assertion against the new expected value in the failure log (`Expected pattern` vs `Received string`). Fix by asserting the *actual resolved value the test already fetched* (e.g. the slug returned by the navigation/API call it made earlier) rather than swapping one hardcoded prefix for another — value-based assertions survive the next strategy change, prefix swaps do not. See `references/test-assumption-drift-hardcoded-id-prefix.md`.

## Superseded-head notification triage

A GitHub failure email can refer to an intermediate PR commit even when the PR later advanced, passed, and merged. Treat the notification's SHA as a historical observation, not the current PR state:

1. Resolve the short SHA to its full commit with `gh api repos/OWNER/REPO/commits/<sha>`; then locate the PR with `gh pr list --state all --search <sha>` or the commit's pull-request API.
2. Query the live PR's `state`, `mergedAt`, `mergeCommit`, `headRefOid`, and current status checks. Compare the notification SHA with the current `headRefOid`.
3. If the PR advanced to a later head, inspect the intervening commit(s) and the fresh required-check rollup. A later test-only or repair commit that makes the same check green is the owner of the recovery; do not open a duplicate rescue card for the old head.
4. If the PR is merged and the merged/current-base checks are green, record the historical failure and resolution on the existing source card, then stop. Do not reopen implementation work or rerun a stale job solely because an automated notification bounced.
5. Only create follow-up work when the current head or current base still has a reproducible failing required gate. Preserve both the old run URL and the fresh green/current-head evidence.

See `references/superseded-pr-head-notification.md` for the compact command recipe and evidence shape.

## PR head ownership and cleanup reconciliation

Before repairing a red PR, query `state`, `mergedAt`, `mergeCommit`, `headRefOid`, and `headRepository`. Compare `headRefOid` with the live `refs/heads/<headRefName>` SHA using the GitHub API.

A cleanup process can delete and recreate a branch with the same name while an old PR remains attached to an orphaned head. If the implementation is already merged, do not force-push the recreated branch to repair historical CI: rebase the narrow repair on current base, open a follow-up PR, and link it from the merged PR. If an open PR is orphaned, create a replacement PR and verify its `headRefOid` equals the newly pushed branch SHA before reporting status.

### Closed-unmerged stacked child after its base merges

A stacked child PR can be automatically closed when its base PR merges. Its earlier checks may still finish afterward, so a failure email can describe a PR that is no longer mergeable—and whose child implementation is not on `master`.

1. Query both PRs live. Record the parent `mergedAt`/merge commit and the child's `state`, `mergedAt`, `closedAt`, `headRefOid`, and `baseRefName`; do not infer merge from the notification subject or from a Review-card status.
2. Prove ancestry against current base: `git fetch origin master --quiet && git merge-base --is-ancestor <child-head> origin/master`. A nonzero result means the child work remains unmerged. Inspect `git log --oneline origin/master..<child-branch>` to separate the parent commit from the actual child commit(s).
3. Classify the old check independently. When a browser job fails uniformly at `browserType.launch` before application assertions (for example a missing shared library), preserve the exact run/job/runner evidence as infrastructure ownership; do not reopen or alter feature code to compensate.
4. Add a supersession comment to the source card. State: parent merge identity, child closed-unmerged identity, child ancestry result, old-run attribution, and the recovery owner. Historical Review status must not be presented as merge-ready.
5. Create one fresh, helper-backed recovery card against current `origin/master` (new worktree slug, unassigned Ready metadata). Require the worker to transplant only the child delta, not reintroduce the parent; open a replacement PR targeting `master`, run fresh current-head gates, and stop in Review. Keep any runner-image remediation on its existing infrastructure card.

This is a branch-lifecycle recovery lane, not a product rescue unless the fresh replacement PR reproduces an application assertion.

## Same-run fixture failure plus governance metadata failure

A single `bun test · typecheck · build` failure can contain both a deterministic test failure and independent governance violations. Decompose them instead of reporting only the aggregate red check:

- Extract the first failing test and its stack trace from the raw job log; do not stop at the governance summary at the end.
- If the failing test initializes private or security-sensitive persistence, inspect fixture directory modes before changing production code. A fixture that creates `.haft/private` descendants with default `0755` will fail a production invariant requiring `0700`; repair the fixture setup or a shared test helper and preserve the production check.
- Treat missing `test-invariant` / `test-file-justification` markers on newly added top-level test files as a separate, bounded repair in the same rescue card. Do not weaken or disable the governance gate.
- Reproduce the exact focused test command in the PR worktree before creating rescue work. Record the result even when the focused run exposes both pass/fail counts and the full CI run also reports governance failures.
- For Haft, keep the source card in Review, create one helper-backed Ready external-worker rescue card targeting the existing PR branch, and immediately run the helper's `validate <task_id>`; report the validator result, not incidental command output, as claimability evidence.

## Migration-contract drift in broad test suites

When a PR advances a schema, migration, or persisted manifest version, an unchanged backup/compatibility test can fail because it still asserts the previous identity. Treat this as a deterministic PR-local contract gap when the exact test fails on the PR head but passes on clean current base, even if the failing test file is outside the PR diff.

Required evidence:
- exact failing test and source line from the CI log;
- hydrated PR-head reproduction after `bun install --frozen-lockfile`;
- the same test file on clean `origin/master`;
- diff showing the version/schema identity change and the stale expectation.

Repair intake:
- keep the source PR/card in Review;
- create one focused, helper-validated rescue card targeting the existing PR branch;
- when the helper rejects the real PR branch because another card already owns its branch metadata, use a unique synthetic worker-neutral branch slug and state the real push target explicitly in the card body;
- update the smallest justified test contract, retaining stable invariants rather than snapshotting every volatile manifest field;
- require a fresh CI rollup on the new PR head before closing the source card.

Do not classify this as runner flakiness merely because the failing test is off-diff, and do not change production migration code solely to satisfy the old expectation.

## Migration-contract drift in broad test suites

When a PR advances a schema, migration, or persisted manifest version, an unchanged backup/compatibility test can fail because it still asserts the previous identity. Treat this as a deterministic PR-local contract gap when the exact test fails on the PR head but passes on clean current base, even if the failing test file is outside the PR diff.

Required evidence:
- exact failing test and source line from the CI log;
- hydrated PR-head reproduction after `bun install --frozen-lockfile`;
- the same test file on clean current base;
- diff showing the version/schema identity change and the stale expectation.

Repair:
1. Update only the stale contract expectation to the current schema/migration identity; preserve invariant assertions such as profile, checksum shape, validation status, and copied files.
2. Avoid snapshotting volatile fields such as timestamps, content fingerprints, exact checksums, or byte counts unless they are the contract under test.
3. Run the focused failing test and the project's typecheck in the hydrated PR worktree.
4. Push the smallest follow-up commit to the existing PR branch.
5. Verify a fresh required-check rollup on the new head; local targeted success is not closure by itself.

A useful diagnostic shape is a manifest mismatch where the only meaningful drift is `sourceUserVersion`, `targetUserVersion`, and `migrationPlanVersion` after a catalog schema bump. Update those fields to the current version while retaining regex/shape matchers for generated identity and snapshot fields.

See `references/migration-contract-drift-rescue.md` for a compact reproduction and repair recipe.

## Browser accessibility-contract drift after intentional control replacement

When a PR intentionally replaces a custom interactive control (for example, a DropdownMenu button/menuitem picker) with a native/shared primitive (for example, a `<select>`-backed Select), unchanged Playwright specs may fail because they still query the old accessibility role and interaction contract. Treat this as a deterministic test-contract mismatch when the failure is a missing old-role locator (such as `getByRole('button', ...)` or `getByRole('menuitem', ...)`) and the PR diff contains the component replacement.

1. Confirm the exact failed locator and retry behavior from the bounded job log. Repeated failure on the same locator is stronger evidence than a generic browser timeout.
2. Read the exact component at the failed SHA and identify the new accessible role/interaction semantics. For a native select, use the accessible `combobox` locator and Playwright's supported select-option API; preserve the label and option assertions.
3. Search all affected specs for the old role/menuitem contract, including extended-browser suites. Update only those test contracts; do not reintroduce the old component or weaken accessibility merely to satisfy stale tests.
4. Keep the repair on the existing PR branch. If a Ready external-worker card must target an open PR branch, use a unique synthetic worktree branch slug and state the real push target in the body; validate the card with the Haft helper before reporting it claimable.
5. Require focused affected-spec results plus a fresh all-required-check rollup on the new PR head. Local green alone does not clear the PR.

This is distinct from generic runner/browser flakiness: setup, browser launch, and unrelated specs may pass while the stale locator fails deterministically.

## Artifact quota is an evidence-transport lane, not a product diagnosis

When a failed browser job reaches its test summary but `actions/upload-artifact` then fails with `Artifact storage quota has been hit`, preserve the test failure as authoritative and classify artifact upload as a separate evidence-transport problem. Do not change product code, rerun solely to regenerate artifacts, or collapse the two failures into runner instability. Use the raw bounded job log and any available annotations; if diagnostics are unavailable, state that boundary explicitly.

## Same-run capacity cascade decomposition

A single required-suite failure can contain many symptoms from one capacity fault. Extract the first concrete exception and group failures by shared origin before opening rescue work: repeated capacity exceptions across catalog/migration tests plus an off-diff high-fanout timeout usually indicate runner capacity or I/O contention, not a feature regression. Cite runner PSI metrics, free memory, lane completion, and the unchanged PR diff. Keep the source card in Review, attach one bounded evidence comment, and route remediation to the existing runner-capacity owner when available. Require a fresh run on the unchanged head after capacity repair before editing code. Record local host exhaustion separately as orchestration friction; never conflate local disk state with remote CI attribution. See `references/same-run-capacity-cascade.md`.

## Runner disk exhaustion before test execution

When a self-hosted job fails during `Set up job` or before the first test step with an explicit `No space left on device` error (especially while writing runner diagnostics), classify it as runner-capacity/infrastructure evidence, not a product regression. Preserve the exact runner name, job/run URL, failed setup step, and the fact that no test assertion executed. If multiple jobs on the same runner fail this way, group them under one capacity owner rather than opening per-PR code rescues.

If another job in the same run stops mid-test without emitting an assertion, do not infer a code failure from the red conclusion. Record it separately as incomplete evidence; it may be a secondary capacity consequence, but only a concrete assertion or reproducible local test establishes a product defect. Keep the source PR in Review and require a fresh same-head required-check rollup after runner remediation.

When a capacity follow-up already exists, append the new run/job evidence to that owner instead of creating a duplicate incident card. Re-check the current PR head before any rerun because a worker may have pushed a newer commit while the infrastructure issue was being investigated.

## Verification
After triage, record which of these happened:
- setup noise only,
- stale branch fixed by rebase,
- real regression requiring code changes,
- deterministic test/contract drift requiring a focused branch repair,
- merged/orphaned PR requiring a linked follow-up.

If rebasing was the fix, rerun the same CI-equivalent checks and push the updated branch so GitHub reruns from the new head.
