---
name: haft-release-operations
description: Cut Haft releases and operate the tag-triggered release pipeline — version bumps, tag/push, failure diagnosis, runner health, burned-version recovery.
---

# Haft Release Operations

Use when JP asks to "cut a release" / "tag and release" / "new release" for Haft, or when a Haft Release workflow run fails and needs diagnosis/recovery.

Repo: `<haft-repo-root>` (canonical, keep on clean `master`). Board: `haft`. Release host: `https://releases.<hq-hosted-origin>`.

## The release-cut workflow (do it in this order)

The release pipeline's "Verify release candidate" gate enforces `tag == package.json version` on tag-triggered runs. **Always bump `package.json` BEFORE tagging**, or the gate rejects the run.

1. `git fetch origin --tags --quiet` and check `git log --oneline v<last>..origin/master | wc -l` to confirm there's something to release. If the count is zero, stop: do not burn an immutable patch version for an empty release.
2. Before creating the release PR or tag, inspect the release workflow for required downstream gate configuration. Confirm required secret names in repository/environment scopes without exposing values, then prove any external test infrastructure behind them actually exists and is ready (for example mailbox bridge reachability, alias routing, and synthetic identity bindings). Secret-name presence alone is not a sufficient preflight. If a required gate is absent, unprovisioned, or undecided, stop before tagging; do not publish immutable artifacts only to discover that finalization cannot run.
3. In a worktree off `origin/master`, bump `package.json` `"version"` to the next patch, commit `chore: release v0.1.X`, push branch.
3. `gh pr create`, wait for all required checks to pass, then `gh pr merge <n> --squash --delete-branch`; poll until `MERGED`. (This repository does not permit GitHub auto-merge.)
4. `git fetch origin --quiet && git tag v0.1.X origin/master && git push origin v0.1.X` — tag the UPDATED master, never a stale SHA.
5. Arm a background watcher (see script) and report the run id.

Do NOT tag first and bump later — that burns a version (see pitfalls).

## Diagnosing a failed Release run

```
gh run view <RUN_ID> --json jobs --jq '.jobs[] | "\(.name) | \(.conclusion)"'
JOB_ID=$(gh api repos/jplew/haft/actions/runs/<RUN_ID>/jobs --jq '.jobs[] | select(.conclusion=="failure") | .id')
gh api repos/jplew/haft/actions/jobs/$JOB_ID/logs 2>/dev/null | grep -B5 -A2 "error\|exit code" | grep -v "(pass)" | tail -20
```

Known failure modes and fixes are catalogued in `references/release-failure-modes.md`. Read it before guessing.

## Pitfalls

- **Dev readiness race**: the binary swap readiness gate must use a bounded deadline (currently 180 seconds by default), a per-request timeout, and actionable systemd/listener diagnostics on expiry. A service can become healthy just after the old 60-second window; verify the recovered target locally/authenticated before classifying the binary as bad.
- **Recovered immutable release**: if a tagged release's only failure is a transient readiness-window race, do not move or reuse the immutable tag. Verify the target is now healthy, then rerun the failed jobs for the existing workflow/tag so finalization can complete. Use a new patch version only when the artifact or deployment itself is actually wrong.
- **Tag/`package.json` drift**: tag-triggered runs require exact match. Bump first. `workflow_dispatch` runs skip this check — useful as an emergency recovery only when a prior same-tag run failed before immutable publication and the tag still points to the intended commit; run `gh workflow run release.yml --ref v<version>`, then verify the dispatched run resolves the exact tag SHA. Do not use dispatch to bypass a failed validation or to retag a published version.
- **Burned version**: once a CLI release partially publishes to R2, the immutable manifest pins that version to a specific commit forever. Re-tagging the same version at a different SHA fails with `release manifest commit mismatch: <old> != <new>`. **Recovery = bump to the next version**, never re-tag.
- **Deaf runner listener**: the `devspace-haft` runner can show `online`/`busy:false` in the GitHub API while not accepting jobs (often after a job cancellation). Runs sit `queued` 90+ min with `runnerName: null`. All runners idle but job not dispatching = this. Fix: `sudo systemctl restart actions.runner.jplew-haft.devspace-haft.service`.
- **Release-runner capacity gate**: if `Preflight release runner capacity` fails before `Publish CLI release binaries`, inspect the actual free KiB and threshold, then reclaim only regenerable scoped data. First tier: stale `/tmp` test/PR scratch and direct `node_modules` directories in stale Haft task/DevSpace worktrees; deleting those dependency trees preserves source, Git refs, and worktree metadata and they can be recreated with `bun install --frozen-lockfile`. Do not delete source worktrees, branches, runner state, credentials, or retained cleanup backups as part of this gate. Before removing prior Actions-runner version trees, prove `bin` and `externals` symlink to the newer version with `stat -c '%N'`; then an unreferenced older `bin.<version>` plus `externals.<version>` pair is safe to remove. Recheck `df -h` and the gate's KiB threshold before rerunning. If the failure predated immutable publication, rerun the existing workflow—never move the tag or allocate a replacement version. If publication already began, stop cleanup/retry and treat the version as immutable; diagnose using the burned-version procedure.

  For Yogendra runner capacity failures, **prove the runner identity and deployment model before choosing Docker or native-service diagnostics**. GitHub `online` proves that some listener is heartbeating the registration; it does not prove that listener runs on the expected Yogendra host. Correlate runner ID/name, job machine identity, listener PID/executable/cwd, service unit, `.runner` metadata, work/diag paths, mounts, quotas, and exact failing filesystem. If the intended architecture is native listeners under the Yogendra user, ask a verified native Yogendra agent through Herdr and inspect native processes/services first. Do not infer Docker solely from `/home/runner`, a container-looking hostname, or checked-in Compose files. If GitHub reports a runner online but no corresponding native listener exists on the intended host, classify it as a stray/stale registration heartbeated elsewhere until proven otherwise. Never remove approval labels, restart/unregister/re-register, or clean storage until the owning runtime is proven; if all alternate approved runners are offline, quarantine intentionally halts CI and requires explicit approval.

  **Do not close this incident after one later green release.** A later successful tag proves only that that run had enough capacity; it does not invalidate the retention defect. On every new capacity failure, reconcile current disk state and the release owner card against live evidence, append the exact run/job/attempt, free KiB, threshold, reclaimed KiB, and publication boundary, and keep the retention owner active until bounded cleanup or a disk-budget guard is implemented. If `devspace.service` owns the retained private `/tmp`, treat restart or ad-hoc deletion as an approval-gated operational action; do not rerun or retag while the service is active and the capacity gate remains below threshold. When publication did not start, verify the versioned manifest is 404, `latest.json` still points to the prior version, and no artifacts were produced before recommending the same immutable tag be rerun.
- **`gh pr merge` may misreport from a linked worktree**: it can print a local `master is already used by worktree` error after GitHub has actually merged the PR. Before retrying, deleting branches, or attempting a fallback mutation, run `gh pr view <number> --json state,mergedAt,mergeCommit,url` and fetch `origin/master`. Treat the live PR state as authoritative; only tag after updated `origin/master` contains the version bump.
- **`gh run view --log-failed` returns empty** for SIGTERM-killed jobs. Use the REST logs endpoint (`gh api .../jobs/$JOB_ID/logs`) and grep instead.
- **GLY SSM fast-failure**: an immediate `Failed` invocation with response code `1` and empty output can occur despite an Online, reachable instance. Capture command/instance identities, reproduce once with a bounded read-only SSM command, and repair the SSM/host execution lane before reusing the normal signed deploy path. Do not move the tag or overwrite immutable release media. See `references/gly-ssm-fast-failure-triage.md`.
- **Release-host verification**: CLI release artifacts and `latest.json` are served from `https://releases.<hq-hosted-origin>/releases`. Verify that host’s versioned manifest and `latest.json` match the tag and commit. `media.<hq-hosted-origin>` is a remote-publish target, not a CLI release/updater origin; do not probe it as release evidence.
- **Re-running a failed job re-runs ALL its steps**, not just the failed one — costs a full test cycle. Prefer fixing forward and re-tagging over `rerun`.
- **Best-effort cleanup steps under `set -e`** can block releases (e.g. `rm -rf` racing a concurrent bun process writing the cache). Guard non-critical steps with `|| true`.
- **`hermes kanban create` CLI chokes on markdown bodies with parentheses/special chars.** Use the `kanban_create` tool instead for ticket bodies.

## Mailbox-backed deployed gates: prove the infrastructure, not only secret names

Before asking an operator to populate mailbox-related GitHub secrets, trace the workflow and deployed test end to end. Determine whether CI sends real OTP/invitation email and polls a separate authenticated bridge, which identities must share an account, which must be fresh per run, and whether the introducing PR ever executed the live lifecycle rather than merely discovering it with dummy configuration.

Secret-name presence is insufficient when there is no evidence that the bridge endpoint, bearer credential, alias/catch-all routing, exact-recipient preservation, or synthetic account bindings were provisioned. Do not invent addresses. Only tokens are intrinsically secret; URLs and synthetic address templates may be configuration, while real addresses are privacy-sensitive. Make that classification intentionally.

If the production-mutating lifecycle is mandatory, validate bridge/identity readiness before immutable publication. Otherwise surface an explicit product decision to move the full email lifecycle to a scheduled/manual synthetic canary while retaining bounded release readiness and authenticated smoke checks. Never silently waive the gate or burn a new immutable version while its external test infrastructure is unprovisioned.

See `references/mailbox-backed-release-gates.md` for identity roles, bridge contract, configuration classification, and the release-boundary decision checklist.

## Release-gate configuration preflight and attempt reconciliation

When a tag-triggered release reaches publication/deployment but fails in a later collaboration or acceptance gate:

1. Inspect every attempt explicitly. A first attempt may fail before immutable publication (for example, runner capacity), while a rerun publishes successfully and then exposes a separate deterministic configuration failure. Keep those lanes separate; do not attribute the final red status to the earlier failure.
2. Prove the immutable boundary before recommending recovery. If the versioned manifest and `latest.json` serve the tagged version and exact SHA, the payload is published and the tag is burned. Never move or reuse the tag, overwrite the manifest, or cut a replacement version merely because a downstream gate failed.
3. Verify deployed target health/build identity independently. A failed finalization gate does not imply HQ, Gly, or Dev are stale if their health responses report the exact release version and commit.
4. Treat strict missing-secret/configuration validation as a configuration lane. Record only secret names and empty/unset status, never values. Check both repository and environment-scoped secret inventories before claiming provisioning is complete. For the controlled mailbox gate, the six production-environment names are `HAFT_COLLAB_RELEASE_MAILBOX_URL`, `HAFT_COLLAB_RELEASE_MAILBOX_TOKEN`, `HAFT_COLLAB_RELEASE_OWNER_EMAIL`, `HAFT_COLLAB_RELEASE_OWNER_ALT_EMAIL`, `HAFT_COLLAB_RELEASE_EXISTING_EMAIL`, and `HAFT_COLLAB_RELEASE_NEW_EMAIL`; the two collaborator templates must contain `{run}` and the bridge URL must be HTTPS. **A newly merged workflow gate can be the first consumer of newly introduced secrets:** compare the gate's introduction commit/PR with the last successful release, and search repository history for provisioning evidence. If the names are absent and no provisioning path exists, classify this as likely never-provisioned configuration rather than claiming GitHub deleted the secrets; GitHub's repository secret inventory does not provide secret values or a complete deletion history. When a later release reproduces an existing configuration failure, reconcile the existing canonical Kanban owner with the new run/job URL, immutable SHA, publication boundary, target health identities, and Release-object state instead of opening a duplicate. Trust the live card status over historical blocked comments; if the remaining gate is human-only secret provisioning, block that canonical card with `kind=needs_input` and state the exact out-of-band prerequisite. Never place secret values in Kanban, source, or handoff metadata.
5. Do not manually create the GitHub Release object or bypass the gate during triage when the workflow owns finalization. Provision the approved environment configuration, then rerun only the affected gate/finalization path according to the workflow's immutable-release contract. If the normal `gh run rerun --failed` is rejected because the workflow file is considered broken, a `workflow_dispatch` against the exact immutable tag/ref is an acceptable recovery only when the prior attempt failed before immutable publication; verify the dispatched run's resolved SHA before trusting it. After publication, do not use dispatch to bypass a missing downstream gate—repair configuration first, then recover finalization on the same published tag.
6. Prefer a non-secret preflight before side-effecting publish/deploy jobs when a required downstream configuration can be checked without exposing values. This avoids spending a full release cycle only to fail on absent configuration while preserving fail-closed validation. For mailbox-backed collaboration gates, validate the bridge URL/token availability, owner identity pair, and `{run}` collaborator templates before publication; do not hard-code them into YAML or source. The owner/alternate-owner pair must be distinct verified identities resolving to one account, while existing/new collaborator templates must materialize as distinct per-run identities.

The bounded evidence recipe and redaction rules are in `references/release-gate-config-reconciliation.md`.

## HQ configuration failures after immutable publication

When `Build and deploy Haft HQ binary to production` fails during restart/health verification after CLI publication:

1. Inspect the SSM invocation result, not only the GitHub annotation. Capture the command ID, response code, bounded stdout/stderr, and the exact health status/diagnostics. Treat a systemd `active` state as insufficient: `/health` must be HTTP-successful and report `ok=true`, the expected service, embedded commit, and `source=embedded`.
2. Check the public or authenticated HQ health endpoint independently. A 503 `configuration-error` with named missing variables is a deterministic host-runtime configuration defect, not a readiness race. Do not rerun the same job until the host-owned settings are repaired through the canonical operator path.
3. Pay special attention to conditional configuration changes. If a release changes `allowed origins`, feature flags, or another activation switch so that a previously optional group becomes all-or-nothing, compare that activation state with the host environment before tagging future releases. Never print secret values; record names and presence only.
4. Once CLI/R2 publication has succeeded, the version is immutable even if HQ deployment or finalization fails. Do not move the tag, delete the manifest, or cut a replacement version merely to recover a downstream deployment failure. Repair the host or source on a new change, then rerun only the permitted affected path under the release contract.
5. Verify rollback independently. If the failed deploy leaves the new binary serving a 503, or reports `rollback_result=unknown`, treat rollback as incomplete and escalate the deploy-script behavior for repair; do not describe the target as recovered merely because systemd is active.

A condensed evidence recipe and redaction-safe example are in `references/hq-config-failure-triage.md`.

## Filing follow-up tickets

Release friction that's reproducible and material → file a scoped Kanban ticket on board `haft` (JP prefers internal Kanban over GitHub issues). Use the `kanban_create` tool, not the CLI.

## Semantic-feature rollout with disabled runtime gates

When a merged feature adds an optional semantic/provider integration but its gate must remain off:

1. Use the normal immutable release cutter unless JP explicitly requests a Dev-only or break-glass deployment. The standard rollout is HQ → Gly + Dev from one signed SHA; do not silently serialize targets because an earlier plan was cautious.
2. Treat provider configuration as host-owned runtime state, not a release-workflow input. The binary deployment does not establish `HAFT_QMD_SEARCH`, `HAFT_QMD_HYBRID_SEARCH`, or `HAFT_QMD_ENDPOINT`; never infer their state from source code or a prior environment.
3. After Dev is live, use the authenticated operator/deployment path—not anonymous public access—to prove `GET /api/app/status` reports `semanticSearch.semanticRouting: "disabled"`, `hybridRouting: "disabled"`, and no endpoint/provider credential.
4. Separately collect only redacted host/deploy evidence that the QMD flags are absent or false, the endpoint is absent, and the deploy did not install or start a QMD provider process/service. Never expose raw environment files, endpoint addresses, or credentials.
5. Exercise bounded normal-flow smoke checks: keyword search plus Reader navigation. Disabled semantic integration must not regress ordinary Dev behavior.
6. A normal binary rollout does not authorize changing Gly provider configuration or enabling semantic/hybrid routing. Any activation remains a separate private-provider, safety, latency, and UX acceptance decision.

## Canonical checkout and immutable-version recovery

- Preflight `git status --short` on `<haft-repo-root>` before a cut. If unrelated local edits would make the release workflow's canonical-sync job reject the checkout, preserve them with a named `git stash push -m '<purpose>' -- <paths>`, verify the stash exists, and restore it with `git stash pop` after the rollout. Never delete or silently overwrite local work; report the stash preservation/restoration.
- Build the release worktree from `origin/master`, not the dirty canonical checkout. The canonical checkout may be locally behind while `origin/master` contains the intended release head.
- If a tag-triggered run publishes immutable CLI/media artifacts but fails later in deployment, do not rerun it blindly or move the tag after changing source. Fix the defect on a new PR and cut the next unused patch version; the published version is burned even if runtime deployment did not finish.
- When a deployment script is concatenated into `bash -s` under `set -u`, do not assume `BASH_SOURCE[0]` is populated. Guards must tolerate an unset value, e.g. `${BASH_SOURCE[0]:-}`, and shell syntax/concatenated-input behavior should be tested before tagging.

## Verification

A release is done when the watcher reports `completed success` AND `curl -fsS https://releases.<hq-hosted-origin>/releases/v<version>/manifest.json` returns the expected version and immutable commit. The artifacts are versioned by Bun target (for example `haft-v<version>-bun-linux-x64`), so do not probe the obsolete unversioned `haft-linux-x64` path; derive any binary URL from the manifest. Don't trust the run status alone.

The release workflow now owns GitHub Release-object finalization. After a successful tag workflow, verify `gh release view v<version> --json isDraft,isPrerelease,targetCommitish,url`; require a non-draft, non-prerelease object targeting the immutable release SHA. Do not manually create a Release object unless live workflow evidence proves finalization was skipped or interrupted.

After deployment, query every intended target's `/health` endpoint and verify the embedded build version and commit. Do not assume HQ, GLY, and Dev share the same JSON envelope: parse each response as an object, inspect `build.version` and `build.commit`, and report only bounded schema-safe fields. A successful HTTP response with an unexpected schema is a verification/parser issue to repair, not evidence to ignore.

For the exact cut/merge/tag/manifest/release-object/target-health sequence, see `references/release-cut-checklist.md`.
See `references/release-manifest-contract.md` for the tag-prefixed public manifest contract and verification checklist.
