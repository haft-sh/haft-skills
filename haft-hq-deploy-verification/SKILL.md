---
name: haft-hq-deploy-verification
description: Verify, diagnose, and repair Haft HQ (`<hq-hosted-origin>`) deployment drift; confirm the live runtime is current; and expose a bounded public build-confirmation surface without dirtying the canonical checkout.
---

# Haft HQ deploy verification

## When to use
Use this when:
- `<hq-hosted-origin>` appears stale relative to repo `master`
- a newly added HQ route returns `404` in production
- Epic / PR rollout depends on confirming that Haft HQ is actually serving current code
- you need to prove which commit is live on the HQ host
- you need to add or verify a public-safe build fingerprint / status endpoint for HQ

## Core rule
Treat **public route shape** as deployment evidence.

For HQ routes that exist on current `master`, a public `404` on `<hq-hosted-origin>` is strong evidence of deploy drift. If the route should exist but is auth-gated, the expected public behavior is usually an auth-shaped `401`/`403`, not `404`.

## Operator workflow
1. **Check repo truth first.** Confirm the route exists on current `master` and record the local repo SHA.
2. **Check public prod behavior.** Hit `https://<hq-hosted-origin>/api/v1/health` and the route in question. Distinguish:
   - route missing (`404`) -> likely stale prod runtime
   - auth-shaped denial (`401` / `403`) -> route is live, continue with product/auth debugging
3. **Inspect the actual HQ runtime path.** Determine whether prod is running:
   - source-tree Bun service (`bun src/index.ts`), or
   - binary-swap runtime
4. **Compare live host SHA to current repo SHA.** If the host is stale, update the runtime using the path it is *actually* on; do not assume the newer deploy path is already active.
5. **Verify locally on the host after restart.** Check loopback health and the target route before relying on the public edge.
6. **Verify publicly again.** Re-run the public route check and confirm the behavior changed as expected.
7. **If no bounded public build fingerprint exists, file follow-up work immediately.** Operators should not need SSM host access forever just to confirm the deployed commit.
8. **When signed provenance is required, verify the trust chain and runtime separately.** A KMS signature can verify successfully while the binary still crashes under systemd. Provision the asymmetric key, independently verify a real signature, deploy Dev → Gly → HQ, and test the exact binary under each effective service sandbox. See `references/kms-provenance-and-bun-systemd-rollout.md`.

## Haft-specific facts
- HQ production host: `i-085957aeb58cda332`
- Public base: `https://<hq-hosted-origin>`
- Expected bounded public health: `GET /api/v1/health`
- HQ service name: `haft-hq.service`
- Current runtime may still be source-tree based even if newer binary deploy workflows exist in-repo.

## Canonical checkout discipline
If you need to change repo files to add a deploy-confirmation endpoint or related fix:
- do **not** dirty `<haft-repo-root>` for implementation work
- use a worktree + branch + PR
- if you accidentally edit canonical, move the change into a worktree immediately and restore canonical cleanliness before reporting success

### Untracked canonical files during a release
`bun run canonical:sync` refuses a dirty checkout, including untracked files. Do not delete an untracked file merely to make a release proceed. First identify it; if it is unrelated to the release but must be preserved, use a named `git stash push --include-untracked -m '<purpose>'`, verify the stash exists, then sync/check and release from clean canonical `master`. Include the stash reference in the final handoff so its owner can restore it; do not drop that stash as part of release work.

## Practical verification pattern
- Local repo `master` contains the route
- Public `<hq-hosted-origin>` route returns `404`
- Host runtime SHA is behind current `master`
- After deploy/restart:
  - host loopback route returns expected auth-shaped response
  - public route also returns expected auth-shaped response

That is enough to prove deployment drift was real and the rollout corrected it.

## Approved Caddy compression changes

For a bounded, approved edge-compression change on a managed Haft runtime:

1. Re-verify DNS → instance identity, active service state, and the exact pre-change Caddy stanza before editing.
2. Treat the terminal approval control as a separate safety boundary. If the terminal rejects the mutation for missing consent, stop; do not rephrase or bypass the same mutation. After the operator confirms the approval control was actually used, retry the same validated command once.
3. Make a timestamped backup, apply only the scoped `encode zstd gzip` directive, run `caddy validate`, then reload Caddy. Do not report success from an SSM receipt alone.
4. Independently probe the public bounded JSON route with `Accept-Encoding: zstd, gzip`; require HTTP success plus `content-encoding: zstd` (or the explicitly selected supported encoding). Also re-check the application's health endpoint.
5. Record the backup path, target identity, config-validation result, reload result, and public headers in the deployment handoff. Compression enablement does not prove that a newer application binary or its instrumentation is deployed.

## Deployment proof is not functional-recovery proof

For auth, enrollment, or central-identity incidents, report these as separate facts and lead with the first one the operator asked for:

1. **Deploy status:** workflow outcome and immutable SHA selected.
2. **Runtime freshness:** verify the SHA on HQ loopback plus cache-busted public health (use a unique query value and `Cache-Control: no-cache`). A cached public response can be stale while the host has the correct binary.
3. **Functional recovery:** exercise the actual state transition and user-facing flow. `/health` proves a process is live; a generic auth-status `claimed` result does not prove a legacy claim upgraded to central identity or that hosted OTP works.

Do not describe a deployment as "recovered" until functional-recovery proof is complete. If deployment succeeded but recovery is blocked, state that in the first sentence, name the exact remaining stage, and avoid a long recap of completed deploy steps.

For managed enrollment, resume the saved journal rather than resetting claims. If it advances past the original remote failure but fails locally, distinguish the new local installer error from the fixed remote defect. Inspect safe ownership/mode metadata for all configured verifier/JWKS paths before changing ownership; a public JWKS file may not be the only artifact being persisted. Never print journals, credentials, grants, tokens, or private keys.

## Config-vs-code check for partially finished HQ surfaces
When a public HQ feature looks "half built" (for example a landing-page form that renders but returns an unavailable message), do not jump straight to "implementation incomplete".

Use this split:
1. **Verify the UI seam exists in repo** (landing page/form or route references).
2. **Verify the API route exists in repo** and read the fail-closed branches.
3. **Probe the live route with both invalid and valid inputs**:
   - invalid input returning a bounded validation error (for example `400 beta-signup.invalid-email`) proves the route is live and request parsing works
   - valid input returning a bounded configuration/storage error (for example `503 beta-signup.not-configured`) usually means the feature is implemented but missing runtime config
4. **Check prod secret/env presence only** on the host before changing code. For HQ beta signup, the decisive check is whether `HAFT_HQ_CLOUDFLARE_ACCOUNT_ID`, `HAFT_HQ_BETA_SIGNUP_KV_NAMESPACE_ID`, and `HAFT_HQ_CLOUDFLARE_API_TOKEN` are present in the locked-down service env file.
5. **Only after that** decide whether the blocker is code, deploy drift, or missing operator config.

This prevents turning a production configuration gap into a misleading product/implementation conclusion.

## Pitfalls
- Do not treat missing `/api/app/status` on `<hq-hosted-origin>` as proof of HQ drift by itself. That is a Haft Local surface, not the canonical HQ confirmation surface.
- Do not treat a green `GET /api/v1/health` as proof the HQ database is healthy. Health can succeed without touching central identity storage; for DB cutovers, query the central DB and exercise an auth/remote-target route.
- Do not treat a green HQ deploy workflow as proof the compiled binary for the merged SHA is live unless health reports the deployed SHA from embedded build metadata. If `/api/v1/health` shows `build.source: "runtime-git"` or a stale host-checkout commit, the deploy verification is too weak even if root HTML changed. Patch the build step to compile with `HAFT_EMBEDDED_BUILD_*` env, then make both SSM localhost health and public health assert `build.commit == DEPLOY_SHA` and `build.source == "embedded"`.
- When adding a public HQ nav link, verify the destination route shape too. A landing page can contain `href="/docs/"` while `https://<hq-hosted-origin>/docs` still 404s because no HQ route or static docs serving exists. Public deploy checks should curl the linked route, not only grep the root page.
- Do not assume Docusaurus docs exist in production because `apps/docs` exists in the repo. Until HQ is wired to serve the static build artifact, either add a bounded HQ `/docs` route or make the deploy package include and serve the generated docs assets, then verify `/docs` publicly.
- Do not assume GitHub Actions dispatch is available from the current token. If Actions dispatch is blocked, use the operator path you actually have.
- Do not assume the production host can `git fetch` a private repo unauthenticated.
- Do not enable `MemoryDenyWriteExecute=true` on compiled Bun services without running the exact binary under the exact unit sandbox. A provenance-verified binary can still abort with executable-memory exhaustion; preserve the rest of the sandbox and disable only this incompatible directive when proven necessary.
- Do not treat an overall red workflow as proof the binary deployment failed. Inspect the SSM deploy result, embedded live SHA, and job step that failed; a final DNS/public check may fail after a successful swap.
- Do not claim prod is current just because local `origin/master` is current.
- Do not claim a Turso/libSQL cutover is live just because `/etc/haft-hq.env` has `HAFT_HQ_DATABASE_DSN`; verify `HAFT_HQ_DATABASE_AUTH_TOKEN` is also present and the runtime code actually passes it into the DB opener.
- Do not leave implementation edits in canonical while preparing deployment or operator fixes.
- Do not rely on `gh run view <run-id> --log-failed` for jobs killed by signal (SIGTERM / exit 143) or for jobs that failed in a cleanup/setup step — it can return empty output. Fall back to the REST API: get the failed job id via `gh api repos/<owner>/<repo>/actions/runs/<run-id>/jobs --jq '.jobs[] | select(.conclusion=="failure") | .id'`, then `gh api repos/<owner>/<repo>/actions/jobs/<job-id>/logs` and grep for `error|exit code|SIGTERM`. This reliably surfaces the real failure line.

## If the host is source-tree based
If `haft-hq.service` is still running `bun src/index.ts`, repair the *actual* source-tree deployment path first. A newer binary-swap workflow existing in the repo does not mean the host is already using it.

If the host checkout cannot fetch the private repo, use a transient authenticated fetch/reset path, then restore the normal public remote URL after the update.

## Deployment automation audit
When asked whether Haft HQ deploys automatically, audit workflow triggers and live deploy evidence separately instead of inferring from artifact scripts.

Checklist:
1. Read `.github/workflows/deploy-hq-production.yml`, `.github/workflows/deploy-dev.yml`, `.github/workflows/ci.yml`, and any deprecated fallback workflow.
2. Classify each trigger explicitly:
   - `workflow_dispatch` only = manual deploy.
   - `pull_request.closed` + `merged == true` = merge-driven deploy, but only for that workflow/environment.
   - `push: master` + `needs:` = direct auto-deploy after in-workflow verification.
   - `workflow_run` = possible SHA-drift risk; prefer a single workflow with `needs:` when possible.
3. Inspect recent workflow runs with `gh run list --workflow <name>` and note event type (`workflow_dispatch`, `pull_request`, `push`) so the report distinguishes actual behavior from intended design.
4. Probe `https://<hq-hosted-origin>/api/v1/health` and compare `build.commit`/`shortCommit` to `origin/master`. If the live commit is an ancestor but not equal to current `origin/master`, production is healthy but not automatically current.
5. Keep **Haft HQ server binary deployment** separate from **public user CLI release publishing**. HQ deploys upload a service binary such as `deploy/artifacts/<sha>.haft-hq`; CLI releases need their own public manifest/install-script/channel under the release domain.

Pitfall: do not say “binaries deploy on every merge” just because `.github/deploy/upload-hq-binary.sh` exists. The workflow trigger decides automation; the upload script only proves the manual deploy path is binary-artifact based.

## Semantic release tag rollout (HQ → Gly → Dev)

### Release-failure triage discipline (read first)

When a release workflow fails, **classify the failure before rerunning**. A blind `rerun` of a deterministic failure just burns another full cycle — in one observed session, three consecutive reruns of a SIGTERM-killed test suite cost ~2 hours before anyone fixed the root cause. Triage order:

1. **Get the real failure line** (not the job name). Use the REST API fallback for signal-killed/cleanup jobs — `gh run view --log-failed` returns empty for SIGTERM/exit-143 and cleanup-step failures. See the pitfall in "Pitfalls" below.
2. **Classify:**
   - *Deterministic* (version mismatch, assertion failure, typecheck error, missing dep) → **fix the source, do not rerun.** A rerun reproduces the same failure.
   - *Infrastructure/transient* (SIGTERM under runner contention, action-fetch 429, cleanup race, deaf listener) → fix the infra condition, then rerun or re-tag.
3. **Prefer fixing the pipeline over rerunning.** If the same failure class recurs across releases (e.g. test-suite SIGTERM), the fix is a pipeline change (remove/guard the step), not another rerun.
4. **Re-tag, don't reuse, after a source fix.** After merging a fix, delete the stale tag, re-tag on updated `origin/master`, and push — the new tag triggers a fresh run. Cancel the old run only if it still holds the `haft-release-deploy` concurrency group.

For the concrete canonical cut sequence and the public-media recovery decision tree, see [references/release-cut-media-recovery.md](references/release-cut-media-recovery.md).

Use this when JP asks to redeploy **Gly** through the normal release path rather than dispatching a one-off environment workflow.

1. Fast-forward the canonical checkout to current `origin/master`; never tag a stale local commit.
2. **HARD GATE — verify version before tagging.** Run `git show origin/master:package.json | grep '"version"'` and confirm the version matches the intended tag (e.g. `0.1.49` for `v0.1.49`). Do NOT push a tag until this passes. Tag-triggered workflows fail closed at `resolve-release-version.sh` on mismatch. Note: `workflow_dispatch` skips this check, so a prior dispatch-based release can mask drift that the next tag-triggered release catches. If the version is stale, bump it via worktree + PR first (see "Version-mismatch recovery" below).
3. If a new release is needed, make the smallest reviewed version-bump commit on `master`, run the release-focused tests plus full test/typecheck/build, then push that commit. Do not move or reuse an existing tag. If the current `master` CI is red, inspect the exact failing job before tagging: a single bounded test timeout that does not reproduce in a fresh full local suite may be rerun once; do not call it green merely because an earlier run passed or because every other job passed. Wait for the rerun's terminal result, then retain both the rerun URL and local command evidence.
4. Create and push an annotated matching tag. The release orchestrator deploys HQ first, then Gly and Dev from the same resolved immutable SHA.
5. Wait for the GitHub Release workflow to complete; do not infer Gly completion merely because the tag was accepted or HQ passed. **Do not present a release as complete while this workflow is still in progress.** An interim update may give the immutable tag and workflow URL, but the final rollout report requires terminal workflow evidence.
5a. Check for a **GitHub Release object** with `gh release view v<version>`. The supported `bun run release:cut` path creates a non-draft release after its exact tagged workflow succeeds; do not create tags/releases manually during a normal cut. **Recovery exception:** the cutter process can be interrupted (for example, gateway/session restart **or a terminal deadline expiring while it waits for GitHub Actions**) after it pushes the immutable tag but before it reaches `ensureGitHubRelease`; it can also exit after a failed workflow whose later rerun succeeds. Do **not** rerun the cutter or move the tag. First inspect the exact remote tag SHA and workflow state; if the workflow is still running, monitor that exact run (a tracked background `gh run watch <run-id> --exit-status` is appropriate) and wait for its terminal result. If that workflow succeeded but `gh release view` reports no release, create the non-draft GitHub Release with the exact `gh release create <tag> --verify-tag --generate-notes --title "Haft <tag>" --target <sha>` command that `release:cut` itself uses, then re-query tag/SHA/draft state. Never move the tag or overwrite immutable media payloads. File follow-up work only if the supported cutter cannot make this recovery idempotently.
5b. Verify the **public CLI channel**, not only the workflow: fetch `https://media.<hq-hosted-origin>/releases/latest.json` and require its `version` and `build.gitCommit` to match the tag and immutable SHA. Then run `haft update` and `haft version --json` on an installed CLI, and confirm the requested newly released command appears in `haft <command> --help`. The manifest is the updater’s source of truth; a GitHub Release with no assets does not prove the installer channel advanced.

### Final release evidence checklist

Before reporting a clean cut as complete, independently collect all six facts rather than relying only on the cutter's final summary:

- `git rev-parse v<version>^{}` equals the release SHA.
- `gh run view` is terminal `success` for that exact SHA.
- `gh release view` is a non-draft, non-prerelease release targeting that SHA.
- Both the version manifest and `latest.json` report the version and `build.gitCommit` for that SHA.
- HQ, Gly, and Dev health each report `ok: true`, the version, the exact commit, and `build.source: "embedded"`.
- `haft update --version <version>` followed by `haft version --json` reports the same embedded version and commit.

If the canonical cutter finishes normally, it should create the GitHub Release itself. Use the recovery exception only when evidence proves the tag workflow passed but the cutter was interrupted or exited before that final step.

6. Independently fetch all three live health surfaces after workflow success: `https://<hq-hosted-origin>/api/v1/health`, `https://<gly-hosted-origin>/health`, and the Dev public health endpoint. For each, verify `ok: true`, `build.commit` equals the tagged release commit, and `build.source` is `embedded`. Report the workflow URL and per-runtime proof; a green workflow alone is not deployment-freshness proof.
7. When health exposes a semantic version, verify both release identities on every runtime: `build.version` must equal the tag version without its `v` prefix, and `build.commit` must equal the tagged immutable SHA. Semver is the recognizable release identity; the embedded commit is the forensic proof.
8. If a health surface lacks a semantic version, do not infer it from the commit or report a guessed release. Keep commit/source verification as the release proof and file a narrowly scoped follow-up to add public-safe `build.version`, sourced from the embedded release version with a validated package-version fallback for source/dev runs. The follow-up must cover HQ health, managed-target health, and local `/api/app/status`.

### Public CLI media gate: R2 binding versus HQ bridge

A release can publish immutable CLI payloads successfully yet fail before HQ/Gly/Dev deployment because the **public** media URL is unavailable. Diagnose that boundary before retrying:

1. Record the failed release workflow/job and verify whether both the R2 publish and HQ media-mirror SSM steps succeeded separately.
2. Probe the new version manifest and `latest.json` at the configured public release URL, plus one previously published version. If old and new versions all return Cloudflare R2 `Object not found`, classify it as a public-host binding/origin outage—not a bad new payload.
3. On the configured HQ host, verify the staged `install.sh`, `latest.json`, and `v<version>/manifest.json`; then make a local TLS probe using the media Host/SNI name. A local `200` alongside public `404` proves the host-side bridge is ready while DNS/custom-domain routing is not.
4. Repair the R2 custom-domain binding when possible. If the product has an explicitly documented emergency bridge, temporarily route the media hostname to the HQ Caddy file server only with valid DNS authority; verify all three public URLs after propagation.
5. Do **not** cut another release or move/reuse the tag. Before rerunning a failed workflow, compare the first successful HQ-media mirror's manifest/artifact hashes against the current R2 manifest. A retry can rebuild the same source SHA into different bytes (for example from generated timestamps) and may overwrite R2 while the HQ immutable guard correctly refuses replacement.
6. If the bytes differ, **do not force a retry or deployment**. Preserve the original immutable HQ payload, stop the rollout, and file/fix an idempotent-release-publish repair: a retry must verify existing tag artifacts and continue safely, or fail before mutating published assets. Only rerun the workflow once the release retry boundary is deterministic and the expected media identity is consistent.
7. If the bytes match, rerun the failed workflow against the same tag, then continue normal runtime-health verification.

### R2 and KMS credential-boundary gate

The release job can legitimately use two AWS-compatible credential domains: narrow R2 S3 credentials for immutable artifact storage and the runner's AWS/OIDC role for KMS provenance signing. Treat them as separate security contexts.

1. Before retrying a workflow that failed while creating deploy provenance, inspect the exact failed step. A successful earlier `sts get-caller-identity` does **not** prove a later KMS call is using the same credentials.
2. In publisher scripts, scope `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, and R2 endpoint/region overrides to only the R2 `s3`/`s3api`/`presign` invocations. Do not globally export R2 credentials and then invoke `aws kms sign` or `aws kms get-public-key` in the inherited environment.
3. A KMS `UnrecognizedClientException` immediately after immutable R2 artifact reuse is evidence of credential-environment leakage, not artifact corruption. Preserve the tag and existing payload; do not rebuild, overwrite, force the swap, or keep rerunning.
4. Fix the credential boundary with regression coverage, then cut a new patch version after merge. Do not reuse the failed immutable tag if the workflow never reached all runtime deployments.

Keep evidence bounded to workflow/job URL, immutable tag/SHA, sanitized manifest build identifier/hash comparison, public status codes, and local bridge status. Never print R2 credentials, presigned URLs, Cloudflare tokens, or full deployment environment.

### HQ docs and deploy-check contract gate

Treat the release workflow's public checks as executable contracts, not incidental smoke probes. Before cutting a release that embeds or changes the HQ docs site:

1. Read the docs route implementation and its focused tests together with the deploy workflow. Check whether paths under `/docs/` are deliberately reserved from the static Docusaurus handler.
2. Probe the exact public and loopback URLs that the deploy job asserts. A `404` from both boundaries is an application-route contract, not a DNS/cache failure.
3. Require route tests and deploy verification to agree. Do not assert `/docs/json` as JSON if the docs-site contract intentionally reserves it as `404`; either expose a safe OpenAPI endpoint outside that reserved namespace or replace the obsolete check with meaningful docs-site and health assertions.
4. If the SSM swap and embedded health succeed but a later docs probe fails, record the deployed SHA separately. Do not call the release complete or dispatch downstream environments manually.
5. Repair the conflicting source/test/workflow contract on `master`, then cut a **new** patch version. Do not move, reuse, or repeatedly rerun the immutable tag merely because its HQ binary is already live.

### Release-runner and local verification capacity gate

A release cut consumes disk in two distinct places: the local canonical checkout runs the full suite before it publishes a tag, and the GitHub/self-hosted release runner needs the configured free-space threshold before it may publish immutable media. Treat disk exhaustion as an operational capacity condition, not a product test regression. For the safe classification and reclaim sequence, see [references/release-runner-capacity-recovery.md](references/release-runner-capacity-recovery.md). For queued-but-idle runner recovery, bounded pre-publication action-fetch retries, and post-rerun release-object recovery, see [references/release-runner-queue-recovery.md](references/release-runner-queue-recovery.md) and [references/release-runner-prepublication-retry.md](references/release-runner-prepublication-retry.md). For a cleanup-step race that kills the Publish job before upload, see [references/release-cleanup-race-recovery.md](references/release-cleanup-race-recovery.md). For a missing materialized workspace dependency before publication, or a Dev local-CLI proof failure after immutable publication, use [references/release-preflight-dependency-link-and-dev-gate.md](references/release-preflight-dependency-link-and-dev-gate.md).

1. If a local `bun run test` suddenly produces broad unrelated failures, check `df -h` before investigating application code. `No space left on device` can cause hundreds of fixture/state tests to fail together.
2. If the local cutter reports that it rolled back its version change and published no refs, reclaim only regenerable, scoped test scratch/cache data; rerun the full suite and a fresh release dry run before attempting the cut again.
3. If a pushed immutable tag's workflow fails at `Preflight release runner capacity` *before* artifact publication, inspect the failed job's exact free-space value and threshold. Reclaim only regenerable caches/dependency directories from **completed, inactive** worktrees; do not remove source, active workspaces, public media, tags, or release artifacts.
4. Re-check available space against the workflow threshold before rerunning failed jobs. A rerun is safe only when the failure occurred before immutable publication and no artifact identity was produced.
5. Before rerunning a pre-publication failure with `SIGTERM` / exit 143, establish process attribution: inspect the failed job log, runner journal/diagnostics, and active host processes. If other full-suite Bun jobs are sharing the deploy host, wait for or clear those legitimate competing jobs first; do not mislabel a polite termination as an assertion failure or blindly rerun under the same contention. Record whether the test itself failed, the runner canceled it, or host pressure was present.
6. If the rerun succeeds after the cutter already exited, follow the documented GitHub Release recovery exception: verify tag SHA, terminal workflow success, public channel, and live runtimes, then create the non-draft release with the cutter's exact `gh release create` form.

### Verify job no longer runs the test suite (post-2026-07-27)

The `deploy-hq-production / Verify release candidate` job no longer runs `bun run test`. It was removed in PR #1347 after repeated SIGTERM/timeout release failures (v0.1.47, v0.1.49). The release SHA already passed CI on master; re-running 3000+ tests added ~6 min and was the primary source of release-blocking failures on the shared runner. The verify job now does: checkout → setup bun → install → resolve version → typecheck → deploy.

**Implication for this skill:** the "Single flaky-test failure in the verify job" and SIGTERM-in-test-suite sections below are **historical context** for understanding old failure runs. They should not recur in new releases. If a future release fails at the verify step, the failure is in version resolution, typecheck, or dependency install — not the test suite.

### Single flaky-test failure in the verify job (HISTORICAL — pre-PR #1347)
When `deploy-hq-production / Verify release candidate` fails with exactly **1 fail** out of thousands (e.g. `1 fail / 27899 expect() calls / Ran 3047 tests`) and the one failure is a long-duration timeout (a single test at ~12s while peers pass), classify it as a flaky/timeout, not a product regression:

1. Confirm the version gate passed first (look for `Resolved Haft release v<X>` in the log) so you know the failure is in the test stage, not `resolve-release-version.sh`.
2. Find the one failing test: `gh api repos/<owner>/<repo>/actions/jobs/<job-id>/logs | grep "(fail)"`.
3. Rerun only the failed job rather than the whole workflow: get the job id via `gh api repos/<owner>/<repo>/actions/runs/<run-id>/jobs --jq '.jobs[] | select(.conclusion=="failure") | .id'`, then `gh api repos/<owner>/<repo>/actions/jobs/<job-id>/rerun -X POST`.
4. Watch the same run id to terminal state. Do not move the tag or cut a new version for a single recovered timeout.
5. If the same test recurs across releases, file a scoped flaky-test ticket (root-cause the heavy-fixture timeout category) rather than rerunning indefinitely. See `references/flaky-test-rerun-and-intake.md`.

**Rerun cost:** `gh api .../jobs/<id>/rerun` re-executes **every** step in the job, not just the failed one. For the Verify job that means another full ~6-minute test suite. Before rerunning, confirm the failure is genuinely transient (single timeout, SIGTERM, action-fetch 429) rather than a deterministic assertion — a deterministic failure will just burn another full cycle.

### Cleanup-step race in the Publish job
When `deploy-hq-production / Publish Haft CLI release binaries` fails at an early **cache-reclamation** step (e.g. step 5 "Reclaim reproducible release runner caches") with `rm: cannot remove '.../.bun/install/cache': Directory not empty`, the actual publish step never ran. This is a `set -e` + shared-runner race: a concurrent bun process writes into the cache dir while `rm -rf` deletes it. Classify it as infrastructure, not a release defect:

1. Confirm the binary was never uploaded: `curl -sI https://releases.<hq-hosted-origin>/releases/<version>/haft-linux-x64` returns `404`.
2. Fix the cleanup script to tolerate the race (`rm -rf -- "${target}" 2>/dev/null || true`) via worktree + PR; best-effort disk reclamation must never block a release.
3. After merge, delete the stale tag, re-tag on updated `origin/master`, push — the new tag triggers a fresh run. Cancel the old failed run only if it still holds the `haft-release-deploy` concurrency group.

Audit rule: any `rm`/`find -delete`/cache-purge under `set -e` targeting a shared path on a self-hosted runner should be `|| true`. See `references/release-cleanup-race-recovery.md`.

### Version-mismatch recovery (tag already pushed)

If a tag was pushed before discovering that `package.json` does not match, the tag-triggered workflow fails fast at `resolve-release-version.sh` with `Release tag v<X> must match package.json version v<Y>`. Recovery:

1. Bump `package.json` to the tag version via a worktree + PR (do not edit canonical directly).
2. Squash-merge the bump PR.
3. Delete the stale remote tag (`git push origin :refs/tags/v<X>`), delete the local tag, fetch, re-tag on updated `origin/master`, and push the new tag.
4. The new tag push triggers a fresh release run automatically.

**Pitfall:** `workflow_dispatch` skips the tag-match check entirely (the script only enforces it when `GITHUB_EVENT_NAME == "push"`). A release that "succeeded" via `workflow_dispatch` while `package.json` was stale masks the drift — the next tag-triggered release then fails. Always verify `package.json` matches the intended tag *before* tagging, regardless of which trigger path you plan to use.

### Immutable-version retry rule

Release tags and their public CLI/media payloads are immutable. If a later commit is released while `package.json` still names an already-published version, the CLI media mirror should fail closed rather than replace the existing version with different bytes. Do **not** move the tag or overwrite release media. Instead:

1. Determine whether the prior tag reached any runtime deployment stage and preserve that evidence.
2. Repair the release-blocking defect on `master` and rerun focused plus full verification.
3. Bump `package.json` to the next unused patch version, commit it, and create a new annotated matching tag.
4. Run the normal release orchestrator from the new immutable SHA, then verify HQ, Gly, and Dev freshness separately.

**Partial-publish version burn (observed 2026-07-28):** When a release attempt publishes the immutable R2 manifest for commit A but then fails before binary upload or deployment, and fix PRs subsequently merge (moving `origin/master` to commit B), re-tagging the same version on B triggers `release manifest commit mismatch: A != B` in the Publish job. The version is burned — the R2 manifest is pinned to the old commit and the guard correctly refuses replacement. The only recovery is to bump to the next patch version (e.g. v0.1.50). Do not attempt to delete or overwrite the R2 manifest. Signature in logs: `[release] Reusing existing immutable CLI release v<X>; no rebuild or version-prefix upload will occur` followed by `release manifest commit mismatch: <old-sha> != <new-sha>` and exit code 1 in the Publish job, with the Verify job already green.

When the blocker is a wall-clock-sensitive fixture, fix the test data with a safely historical timestamp or inject a deterministic clock; do not merely retry the release.

Use a manual `Deploy gly` dispatch only for bounded break-glass redeploys or a known-good tagged rollback; it is not a substitute for a new semantic release when package version changes.

### BBT release, binary swap, and browser-acceptance gate

When a semantic release must advance a separately managed BBT runtime, use `references/release-and-bbt-rollout-recovery.md`. It separates immutable release recovery from the BBT artifact swap, requires checksum-before-symlink verification plus loopback/public runtime proof, and records the authenticated Playwright storage-state prerequisite for a real private-vault browser matrix. In particular, verify GET-only browser instrumentation with a real GET rather than `curl -I` (HEAD), and do not misclassify an auth/bootstrap `403` from a fresh browser context as a route or performance regression.

### Numbered release is not automatic compatibility-retirement approval

When a feature first ships through a canary or deployment tag, a later numbered release is the first production-release prerequisite for retiring its compatibility paths. It is **not** approval to remove them by itself.

Before unblocking an API/fallback-retirement card, record all of:

1. the numbered tag contains the cutover commit (verify ancestry, not only a feature name);
2. the release workflow and every target health surface attest to the exact embedded version/SHA;
3. the documented stable observation and rollback window has elapsed without a rollback-triggering regression; and
4. any linked scale, performance, or consumer-acceptance gates are Done, or their acceptance policy has been explicitly re-baselined.

During later cleanup, keep route methods distinct: a legacy `GET` compatibility read may share a path prefix with active `DELETE`/`PATCH` mutation contracts. Do not call or remove the entire route family as obsolete.

### Release success does not prove remote write authorization

For a newly released managed remote operation, verify these independently and report the first failing layer:

1. **Release/runtime:** the GitHub Release workflow is green, and HQ plus the destination health endpoints report the exact release SHA with `build.source: "embedded"`.
2. **CLI/runtime parity:** `haft version --json` reports the same version/SHA; do not assume an older local CLI exposes the new command.
3. **Central target projection:** `HOME=<dev-host-home> haft remotes list --json` includes the requested operation (for atomic HTML edits, `agent-document-patch`). A private destination returning public `403` is expected and does not negate readiness.
4. **Operation authorization:** only then perform the managed grant exchange and dry-run. Do not use a manual static bearer, raw filesystem access, or direct DB changes to bypass a missing operation.

If step 3 is missing, the deployment is successful but the dogfood is authorization-blocked. Treat enabling an edit capability as a separate security-boundary decision. Require explicit operator approval for any temporary broad-path bootstrap grant; prefer a short expiry, target/vault binding, exact path prefix once known, and immediate revocation after verification. Never read or print wallet/session credentials merely to construct an ad hoc request.

### Scoped remote-edit dogfood: target selection and cleanup

Before issuing a temporary `artifact.edit` grant, obtain an explicitly approved, currently resolvable destination page locator: a reader URL, exact current slug, or `hv://page/...` handle. Do not infer a page ID from an external filename, artifact-host URL, or historical route fragment, and do not enumerate or brute-force private vault content to find a candidate.

Use this flow:

1. Confirm the released CLI exposes `remote edit-access grant`, then verify remote discovery projects `agent-document-patch` only after the grant is active.
2. Create one short-lived target-bound grant. If all-path bootstrap scope is needed before source-path discovery, make it explicit in operator approval and keep the TTL short.
3. Resolve artifact routes deliberately. For a supplied Haft artifact route such as `artifact-page-...`, the associated page id is normally the same identifier without the `artifact-` prefix (`page-...`). Validate it through `inspect-targets`; do not infer a page from an external filename or unrelated media URL.
4. Run `inspect-targets` first. A bounded `404` can mean an unresolved page rather than a missing deployed route; do not retry guessed identifiers indefinitely. A `403` after exact-page resolution can instead indicate that a narrow source-path prefix does not match the destination's actual source binding.
5. Treat remote inspection as a redacted structural view: it can expose page identity, block IDs, selectors, and stale hashes while intentionally withholding raw HTML, previews, and current reference values. If the requested semantic target cannot be uniquely identified from that projection (for example, an imported text-only document has no `assetTargets`), do not guess an `imported-block-N` or submit a dry-run. Obtain an explicit block ID from the owner or add a bounded semantic-label projection before retrying.
6. If inspection cannot resolve or safely identify the approved target, revoke the grant immediately, remove temporary request files, and report that no dry-run or mutation occurred.
7. An all-path bootstrap grant is acceptable only with explicit operator approval and a short TTL. Use it only after a documented narrow-path mismatch, retain the exact page target, and revoke it immediately after inspection or the completed edit.
8. Only after successful semantic identification: construct the stale-hash patch input, dry-run, make one commit, verify the reader, and revoke the grant.

Record only bounded evidence: release SHA, workflow URL, approved locator, grant status/expiry, operation projection, hash transition, snapshot ID/timestamp, and reader verification. Never record grant bearers, access handles, raw HTML, private source paths, or generated request input files.

## Public CLI media hostname verification

A successful release cutter can verify its configured media manifest while a similarly named public hostname/path still returns an R2 `404`. Treat those as separate facts; do not claim the user-facing installer URL works just because the workflow or cutter reports media verification success.

After a successful cut, probe the exact documented public updater URL and the exact canonical hostname/path exposed to users. Require structured manifest JSON with the expected version and commit—not merely a successful workflow. If the probe returns an R2 `Object not found` response, report it as a hostname/path contract mismatch, preserve immutable release media, and file a bounded routing/configuration follow-up. Do not rerun or retag the successful release merely to repair that public path.

## Mixed-version browser/API compatibility incidents

An active browser tab can retain a prior immutable JS bundle while the server has already deployed an additive API response field. A strict older Zod decoder may then render the whole app unavailable even though the current deployed bundle and runtime are healthy.

Diagnostic and response sequence:
1. Prove runtime freshness first with the public health build identity and the target service's active release identity.
2. Fetch the current public HTML and its referenced hashed JS asset. Inspect the bundled response schema for the newly added field; do not infer a current-bundle defect from an old-tab error alone.
3. Compare the pre-change browser contract with the API-addition commit. If the older contract was strict and lacks the field while the current one accepts it, classify the incident as a mixed-version compatibility failure.
4. Immediate user recovery is a hard refresh or a fresh private-window navigation. A failure in a fresh window rules out the stale-bundle diagnosis and requires normal runtime/API investigation.
5. File a focused compatibility repair when reproducible: use an explicit API/build compatibility mechanism or one guarded reload path. Preserve strict validation for malformed values and unrelated unknown keys; never globally relax `.strict()` merely to mask additive-field rollout drift. Require coverage for no reload loop, auth/route-gate preservation, and legacy-client recovery.

## Long-term improvement
Prefer a bounded public HQ confirmation surface that exposes a deploy/build identifier (commit SHA, short SHA, or build fingerprint) through either:
- an extension of `GET /api/v1/health`, or
- a sibling public-safe endpoint

The response must remain support-safe and must not expose secrets, paths, or private configuration.

## References
- `references/epic20-hq-remote-targets-drift.md` — concrete Epic 20 drift signals, host/runtime findings, and the public `404` -> `401 invalid-central-session` verification pattern.
- `references/kms-provenance-and-bun-systemd-rollout.md` — asymmetric KMS bootstrap/narrowing, independent signature verification, sequential signed rollout, and compiled Bun systemd sandbox compatibility.
