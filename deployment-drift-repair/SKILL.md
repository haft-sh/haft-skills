---
name: deployment-drift-repair
description: Diagnose and repair application deployments when the live runtime, deploy workflow, and repo state disagree — especially isolated hosts, self-hosted runners, and SQLite-backed app state.
---

# Deployment Drift Repair

## When to use

Use this when:
- a public/dev URL is not serving the expected code or auth posture
- a deploy workflow says it succeeded but the runtime behavior is wrong
- the app moved to a different host or topology than older notes assumed
- the host repo is dirty/drifted and no longer cleanly follows git-based deploys
- SQLite-backed runtime state breaks startup or silently downgrades the app into onboarding/fallback behavior

## Core principle

Do not jump straight from a wrong webpage to "bad code." Separate four layers and verify each one:

1. **Topology** — which host/service actually serves the URL now?
2. **Deploy path** — what workflow/runner/SSM or SSH path updates that host?
3. **Repo state on host** — is the checkout at the intended ref, with a clean working tree and working remote auth?
4. **Runtime state** — is app data/schema/config forcing fallback behavior even when code is present?

## Procedure

1. **Verify topology from live repo docs and host metadata first.**
   - Read the repo README/ops docs before assuming an older host layout.
   - Confirm instance id, service name, app dir, and deploy mechanism.

2. **Inspect live behavior before touching code.**
   - Check root page.
   - Check the smallest diagnostic/auth endpoints.
   - For public/auth-gated apps, prefer status-shape checks over simplistic expectations like "root must be 401".
   - **For client-side rendering bugs** (wrong layout, clipped/cropped media, missing styles): fetch the deployed CSS/JS bundle and compare it against source before assuming a code defect. A "works on master but broken on the live site" report can be deploy drift OR an inherent design defect that only manifests at runtime — distinguish these early. See `references/client-side-bundle-forensics.md` for the exact extraction recipe (minified-CSS regex, property-override scan, hashed-chunk re-fetch).

3. **Check deploy workflow assumptions.**
   - Read the workflow YAML.
   - Separate failures in the deploy step from failures in the post-deploy verification step.
   - If the verify step asserts the wrong surface contract, fix that first.

4. **Check host repo drift explicitly.**
   - Verify the host app directory, branch/HEAD, remote URL, and whether fetch works.
   - If the deploy model is git-based, the remote must be both reachable and cleanly resettable.
   - For self-healing deploys, prefer `git checkout -B <branch> FETCH_HEAD && git reset --hard FETCH_HEAD` before cleaning/installing.

5. **Check deploy artifact vs runtime launch target.**
   - If the workflow deploys a compiled binary, verify the service actually launches that binary.
   - Compare the deploy destination (for example `/srv/app/haft`) with `systemctl show -p ExecStart -p WorkingDirectory <service>`.
   - A common false-success shape is: the workflow swaps `/srv/app/haft`, restarts the service, but `ExecStart` is still `bun src/index.ts` from a stale working tree. In that case deploy logs look healthy while the public app keeps serving old code.
   - Treat this as a runtime-launch mismatch, not merely a stale checkout. Repair either the service unit to run the deployed binary or the deploy path to update the source tree the service truly runs.

6. **Check runtime data/schema drift separately from code drift.**
   - If logs show onboarding/fallback mode or missing tables/files, inspect app-state and schema validation paths.
   - A current code checkout can still boot incorrectly because runtime SQLite/schema state is stale.
   - For SQLite catalogs, inspect `PRAGMA integrity_check`, `PRAGMA user_version`, the exact missing table/index, and whether opening the catalog creates repeated migration backups. A catalog can be structurally intact yet lack a compatibility index at the current schema version.

7. **Repair in the narrowest durable way.**
   - Workflow contract wrong → patch workflow verification.
   - Host checkout dirty → reset to fetched head in deploy path.
   - Current-version SQLite missing compatibility tables → make migration/schema repair idempotent for current-version catalogs too.

7. **Verify both local and public surfaces after repair.**
   - local service health endpoint(s)
   - auth/status endpoint shape
   - anonymous protected-route denial shape when applicable
   - only then report success

## Verification contract design

For public/auth-enabled dev surfaces, prefer assertions like:
- `/` returns a normal success page (often `200`)
- `/api/auth/status` is **not** `disabled`
- `claimState.status` is one of the expected states (`unclaimed`, `active`, `revoked`)
- anonymous calls to protected app routes fail with the expected typed code such as `route.gate-denied`

Do **not** hard-code an expectation that the root HTML must itself be `401` unless the product contract explicitly says so.

## Pitfalls

- **Stale host assumption:** older conversations may mention the wrong EC2 or runtime host; re-read current README/ops docs first.
- **False "latest code" diagnosis:** wrong runtime state (missing SQLite table, missing catalog, onboarding fallback) can masquerade as stale code.
- **Deleted runtime cwd on the wrong host:** a service can keep serving from `<path> (deleted)` after its deploy directory was removed or replaced, but only treat that as deployment drift after confirming this process is actually in the request path for the hostname under investigation. Read the current repo README/ops docs first, identify the authoritative host/instance/service, then check that service's live `WorkingDirectory`/cwd. A stale same-named service on an old DevSpace/orchestration host is noise, not proof that the public URL is stale.
- **Dirty host worktree:** a deploy that only checks out/fetches without a hard reset can leave manual hotfix drift in place.
- **Wrong remote provenance:** a clean dedicated runtime clone can still track an upstream or obsolete fork. Resolve the operator-requested repository's branch tip independently, prove the merged PR is contained in it, validate that tip, then make the runtime checkout's remote and branch tracking explicit. See `references/dedicated-systemd-runtime-checkout-deploy.md`.
- **Merge SHA mistaken for “latest branch”:** if the target branch advanced after the named PR merged, equality with the PR merge SHA is the wrong assertion. Verify ancestry and validate every commit in the actual branch tip before deployment.
- **Opaque background validation notifications:** when install/test/typecheck/build runs in a tracked background process, record the process/session id, command, cwd, exact SHA, and purpose as soon as it starts. A delayed `notify_on_complete` message can arrive after the result was already consumed and the deployment finished; identify it explicitly as the pre-deploy validation job so it is not mistaken for an autonomous worker or a second deployment.
- **Restarted long-lived clients mistaken for regression:** systemd replacement legitimately closes existing MCP/WebSocket sessions. Verify the new process and protocol contract, then tell dogfood clients to reconnect before judging the build.
- **Worker-reported artifact handoff mistaken for proof:** confirm the exact live SQLite record, regular non-symlink file, size/digest, safe structured stage/stat events, and absence of a supported copy event before asserting that a native artifact stayed outside repositories. Scope “not copied” to the logs and roots actually checked, and distinguish duplicate retry records by ID/hash. See `references/private-artifact-handoff-runtime-verification.md`.
- **Bad post-deploy assertion:** a workflow can fail even after a good deploy because verification checks the wrong public contract.
- **Treating auth-enabled/unclaimed as auth-disabled:** these are different states and imply different next steps.
- **Treating `delivery: queued` as inbox delivery:** for OTP/email flows, queued only proves the app accepted the send path. Separately verify provider/account state, sandbox/suppression/bounce/event logs, and that safe request/delivery logs are actually queryable.
- **R2/S3-compatible credential chain collision:** when a self-hosted runner has an EC2 instance role, the `aws` CLI picks up the 20-char IAM key by default. R2 requires a 32-char key. Always explicitly set `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` from secrets — never rely on the default credential chain for R2 operations.
- **Embedded-build proof for binary deploys:** a binary-swap deploy can restart successfully while health still reports `runtime-git` from a stale host checkout. For compiled service binaries, inject build metadata at compile time (for Haft, `HAFT_EMBEDDED_BUILD_COMMIT`, `HAFT_EMBEDDED_BUILD_SHORT_COMMIT`, `HAFT_EMBEDDED_BUILD_BUILT_AT` with `bun build --env=HAFT_EMBEDDED_BUILD_*`) and make both localhost and public post-deploy health checks assert the exact deployed SHA plus `source='embedded'`.
- **Public-link verification:** if a deploy adds or changes navigation to a public route, curl the linked route in the deploy verification. Grepping the landing page for `<html>` or the nav link can miss a destination 404.
- **`workflow_run` SHA drift:** two-hop triggers (`CI` → `deploy` via `workflow_run`) can resolve a different SHA than what CI tested, especially on rapid merges or re-runs. Collapse into a single workflow with `needs:` to guarantee the tested SHA is the deployed SHA.
- **Public release distribution is a separate deploy target:** a successful R2/S3 upload does not prove the custom public hostname serves that object. Require immutable `vX.Y.Z/` directories, atomically updated moving aliases, exact version/commit checks from the public origin, and at least one real artifact probe. When repairing a tagged workflow, do not move or rebuild the old tag from a later commit; merge the fix and prove it with a new patch release. See `references/tagged-release-public-distribution-verification.md`.
- **Late rollout failure burns an otherwise published release:** a tag workflow can publish an immutable manifest and successfully deploy HQ/Gly, then fail on Dev health while leaving the GitHub Release object unfinalized. Treat this as a partial release with a consumed version, not a failed build: inspect the exact SSM invocation, verify `systemctl` readiness separately from listener/public health, never move or reuse the tag, and recover with the next patch after repairing the target. See `references/haft-release-late-target-failure.md`.
- **Release-runner cleanup can race dependent jobs:** clearing caches before a workflow begins may not help when an earlier verification job repopulates them before publication preflight. Put bounded reproducible-cache reclamation immediately before the fail-closed capacity check, or provision durable headroom. Use an exact allowlist under an absolute non-root cache home, preserve unrelated state (QMD indexes, worktrees, app data, release artifacts), log reclaimed KiB, and test with a fake-home sentinel. See `references/tagged-release-public-distribution-verification.md`.
- **Fragile SSM payload string-building:** avoid multiline `sed` injection for remote scripts. Build the SSM JSON payload with Python + base64 + `json.dumps` so GitHub Actions expressions, shell parameter expansion (`${VAR:?}`), secrets, and braces cannot break quoting. See `references/binary-artifact-deploy-pattern.md`.
- **SSM `bash -s` changes script execution semantics:** deployment workflows often concatenate helper scripts and execute them over stdin. Under `set -u`, a normal direct-execution guard such as `${BASH_SOURCE[0]}` can abort because `BASH_SOURCE` is unset. Use a guarded expansion such as `${BASH_SOURCE[0]-}` and add a regression test that feeds the composed script to `bash -s`, not only `bash helper.sh`.
- **Projection-signer rotation requires destination trust refresh:** proving that HQ publishes a material-derived JWKS key is not enough. Managed destinations may retain the previous JWKS and reject newly signed delegated grants as malformed or untrusted. Refresh each destination's managed projection/JWKS, verify the expected `kid`, restart only if the verifier loads keys at boot, then issue a fresh grant and run the canary. A later `scope-denied` result means signer trust is repaired but authorization scope is still wrong; do not broaden permissions blindly. See `references/signed-projection-key-rotation-and-ssm-stdin.md`.
- **Binary cutover can reveal hidden runtime-state drift:** switching systemd from `bun src/index.ts` to the compiled binary may immediately expose different boot behavior (for example onboarding mode, auth posture changes, or catalog-migration failures) even when the binary itself is correct. After the unit switch, verify three things separately before removing Bun or deleting the host checkout: (1) `systemctl show -p ExecStart` and `/proc/<pid>/cmdline` prove the binary is the live process, (2) a direct localhost probe of the binary in a non-gated mode confirms the embedded build fingerprint is present, and (3) the normal runtime state/config/vault/auth surfaces still boot correctly. Treat repo/Bun removal as a second phase after those checks pass, not as part of the initial cutover.
- **"Service started" logs can be a false positive after CLI cutovers:** a compiled CLI command may log `Haft running at ...` and still exit immediately, leaving no listener for the reverse proxy. After any entrypoint change, check both `systemctl is-active <service>` after a short delay and `ss -ltnp | grep :<port>`; do not treat startup logs alone as proof the service is durable.
- **Hardened systemd units can invalidate friendly executable paths:** when falling back from a compiled binary to a source-runtime Bun entrypoint, inspect `systemctl cat`, `systemctl show -p User -p Environment`, and the real target of any executable symlink. A path like `/usr/local/bin/bun` may resolve into the service user's home and fail under `ProtectHome=tmpfs`, while a system path like `/opt/bun/bin/bun` works. Verify the exact executable path under the unit's sandbox before concluding the runtime itself is broken.
- **Public-mode gate denial can be healthy while OTP/login is actually broken:** in Haft-like public deployments, anonymous `GET /api/app/status` returning typed `route.gate-denied` can be the expected contract. If the UI simultaneously reports `Human auth state requires an active vault.`, do not "fix" the app-status gate first. Verify localhost `/api/auth/status` and whether the runtime lost its active vault during dynamic/public app composition. A configured vault in `missing_catalog` or transient `error` state may need auth/runtime selection repair rather than a route-policy change.
- **SSM database queries fail on missing CLI binaries or shell escaping:** When you need to query a remote SQLite/database directly via SSM (SSH blocked, Session Manager plugin missing), be prepared for `command not found`, JSON parameter quoting traps, and truncated output. Use full binary paths, prefer `bun:sqlite` on Bun-based hosts, or—better yet—use the app's own API endpoints. See `references/aws-ssm-remote-database-query-patterns.md` for the concrete patterns and workarounds.
- **Restarting an expired managed-projection host can turn a login failure into a 502:** an old binary may keep serving until restart, then reject stale/inconsistent local projection facts at boot. Before restart, prove it supports projection renewal or prepare an explicit, time-bounded recovery with a backup. Do not edit only `projection.expiresAt`: local-host identity checks require server/vault/projection synchronization facts to remain consistent. See `references/hosted-managed-projection-expiry-recovery.md`.

See `references/haft-dev-cli-serve-exits-and-bun-path-recovery.md` for the concrete Haft dev-host recovery pattern when a binary/CLI cutover leaves Caddy returning 502 while the service exits immediately or the Bun path fails under systemd hardening.

## Immutable release identity for all-environment Haft rollouts

When an operator asks to redeploy **HQ, gly, and dev** after a merge, preserve the release identity instead of dispatching the normal release workflow against an untagged `master` ref.

1. Fetch and canonical-sync the clean canonical checkout; confirm the merged SHA and `package.json` version.
2. If the current `package.json` version already has an immutable `v<version>` tag at an older SHA, prepare a new patch release in a worktree. Update the version and the version-contract tests together.
3. Run focused version/release tests locally, open the release-prep PR, and merge only after required CI is green.
4. Canonical-sync again, verify `package.json` matches the intended version, then create and push a new annotated `v<version>` tag at that merged SHA.
5. Let the tag-triggered release orchestrator run HQ first, then gly and dev in parallel. Record and monitor the release run.
6. Verify live runtime build evidence after it completes; only then run downstream production canaries that require all three surfaces.

Do not retag an existing release version at new code. A manual `master` dispatch can technically work while producing CLI artifacts whose release metadata collides with an existing semantic version; it is not an equivalent substitute for the tagged rollout.

## Proactive workflow audit

When a deploy workflow is *brittle by design* (not just broken today), diagnose the architecture before patching symptoms:

1. **Identify the "build-on-target" antipattern.** If the deploy host runs `git fetch + install + build`, it is a build machine pretending to be a deployment target. Any dirty state, network hiccup, or credential drift breaks future deploys silently.
2. **Identify `workflow_run` chaining fragility.** Two-hop triggers (CI workflow → deploy workflow via `workflow_run`) introduce SHA drift, cancelled/re-run edge cases, and opaque failure modes. Prefer a single workflow with a gated `needs:` job.
3. **Identify `concurrency: cancel-in-progress` risk.** On deploy jobs, this can cancel a mid-deploy, leaving the host in a partial state. Use `cancel-in-progress: false` for deploy steps or scope concurrency to the deploy job only.
4. **Decouple health checks.** Verify `localhost:PORT` via SSM/SSH first (app health), then optionally check the public URL as a non-blocking informational step. A Caddy/TLS hiccup should not fail the deploy.

The fix for build-on-target is usually a **binary artifact pattern**: compile once in CI, upload to object storage, download and swap atomically on the target. See `references/binary-artifact-deploy-pattern.md`.

## Runtime checkout isolation and live-agent edits

Before treating a dedicated-looking runtime path as an independent clone, compare `git rev-parse --git-common-dir` and `git worktree list --porcelain` from the canonical and runtime paths. Linked worktrees share branch refs: moving canonical `main` from the runtime can move another checkout underneath a stale index and create apparent staged reversions. Prefer a separate runtime clone; otherwise deploy a detached exact SHA or runtime-only branch.

Do not expose the live runtime checkout as a writable MCP/coding-agent workspace. A remote agent with `edit`, `bash`, build, and restart access can leave a healthy service running uncommitted code that differs from both `HEAD` and `origin/main`. When this happens, inspect first, preserve the diff in a proper worktree, review and test it, repair canonical index drift only after classifying it, then restore and redeploy a clean merged SHA. Service logs prove MCP tool activity but do not identify a named actor unless identity fields are explicitly recorded.

Follow `references/shared-worktree-runtime-hotfix-reconciliation.md` for detection, stale-index proof, evidence capture, and safe reconciliation.

When the recovered capability must later be proposed to the original upstream repository, do not open a PR from the fork's accumulated `main`. Reconstruct the smallest portable contract in a worktree based on the original `upstream/main`, explicitly remove fork-only public surfaces, squash to one commit, and finish asynchronous review before calling it clean. See `references/upstream-pr-minimization-after-runtime-repair.md`.

When the operator then wants the live runtime pinned to that exact upstream PR head, treat it as a cross-fork canary rather than a normal deploy. Prove the PR head from both GitHub and the remote branch, state which fork-only surfaces the reduced tree removes, preserve an annotated rollback ref, use a detached exact SHA when runtime and canonical checkouts share git refs, verify the built tool surface plus process/local/public contracts, and distinguish deployment health from a real native-connector transfer. See `references/exact-cross-fork-pr-runtime-canary.md`.

## Durable fixes worth preferring

- **Binary artifact deploy** — compile in CI, upload to S3/R2, download + atomic swap on host. Eliminates dirty-state, network-at-deploy-time, and credential-on-host classes of failure entirely.
- In git-based host deploys, ensure the remote deploy command hard-resets to fetched head before cleanup/install.
- In SQLite-backed app catalogs, let current-version validation failures caused by missing compatibility tables repair in place via idempotent schema creation/compatibility helpers.
- Add targeted tests for "current version but missing compatibility table" so future runtime drift is caught before deploy.

## References

- `references/client-side-bundle-forensics.md` — fetch the deployed CSS/JS bundle and compare against source to classify a client-side rendering bug as deploy drift vs inherent design defect: minified-CSS regex extraction, property-override scan, hashed-chunk re-fetch, CDN cache-busting.
- `references/private-artifact-handoff-runtime-verification.md` — verify a reported native artifact handoff directly against live SQLite state, private-file metadata/digest, safe structured stage/stat/copy events, checked repository roots, and the exact deployed runtime without exposing connector secrets.
- `references/upstream-pr-minimization-after-runtime-repair.md` — extract one portable, minimal upstream PR from a divergent fork after live-runtime repair: base on original upstream, cherry-pick selectively, remove fork-only surface, squash, use cross-fork PR syntax, and verify automated review suggestions locally before exact-lease amendments.
- `references/exact-cross-fork-pr-runtime-canary.md` — canary the exact head of an upstream-based PR on a divergent fork runtime: prove SHA identity, preserve rollback, detach shared worktrees safely, verify built/process/public contracts, and separate deployment health from native-connector proof.
- `references/shared-worktree-runtime-hotfix-reconciliation.md` — detect linked canonical/runtime worktrees, prove stale-index drift, attribute MCP-driven live edits carefully, preserve uncommitted hotfixes, and restore a clean reviewed runtime.
- `references/aws-ssm-remote-database-query-patterns.md` — When SSH/Session Manager fail: use `aws ssm send-command` to query SQLite/database directly via SSM.
- `references/dedicated-systemd-runtime-checkout-deploy.md` — deploy the verified tip of an operator-requested fork/branch when the development checkout is dirty or not live: prove PR ancestry and remote provenance, validate in a temporary worktree, preserve a rollback ref, promote through the dedicated runtime checkout, and verify process plus local/public contracts.
- `references/haft-isolated-dev-runtime-repair.md` — concrete Haft example: isolated EC2 dev host, workflow assertion drift, host git auth drift, and catalog-table repair.
- `references/embedded-build-sha-verification.md` — pattern for compiled binary deploys where health must prove the exact embedded deployed SHA and public route links must be probed, not just the root page.
- `references/haft-master-push-cli-release-and-hq-deploy.md` — Haft-specific pattern for one verified `master` SHA publishing public CLI binaries (`install.sh`/`latest.json`) and deploying the HQ service binary in the same workflow.
- `references/haft-dev-binary-runtime-mismatch.md` — concrete failure shape where a binary deploy succeeds but systemd still launches `bun src/index.ts` from a stale/dirty checkout, plus the verification gap that lets it pass CI.
- `references/haft-dev-otp-observability-and-deleted-runtime.md` — Haft OTP/email debug pattern for queued-but-not-received mail, HQ allowed-origin checks, SES diagnostic gaps, safe tracing fields, and the wrong-host deleted-cwd false-positive pitfall.
- `references/haft-public-auth-gate-and-vault-selection.md` — public-mode `route.gate-denied` can be correct while OTP/login is broken because auth runtime selection dropped a configured vault in `missing_catalog`/`error` state.
- `references/hosted-instance-login-recovery.md` — map a public hostname to the real EC2 target before SSM repair; distinguish active claims from expired projections; validate refresh-credential metadata without exposing handles; and restore HQ before testing the central OTP path.
- `references/tagged-release-public-distribution-verification.md` — verify tag-triggered runtime deploys, versioned manifests, moving aliases, installers, and artifact URLs as separate release products; diagnose object-storage/public-origin mismatches and weak CI checks that pass against stale manifests.
