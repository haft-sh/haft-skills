---
name: self-hosted-ci-operations
description: "Use when diagnosing or operating self-hosted CI runners."
version: 1.1.0
---

# Self-Hosted CI Operations

## Purpose

Operate and repair CI failures where the fault may be in runner-host state rather than the repository: shared locks, service identities, temporary artifacts, runner queues, or host capacity.

## Procedure

1. **Classify the failure boundary.** Download or inspect the failed job log. Establish whether the protected command started. A failure opening a lock, cache, workspace, or temporary path before the command runs is host state, not an application-test failure.
2. **Identify the execution host before touching anything.** In a multi-host runner pool, the failing job almost certainly ran on a **different machine** than the one you are sitting on. Before applying any host-level fix, query which runner executed the job: `gh api repos/<owner>/<repo>/actions/runs/<run-id>/jobs --jq '.jobs[] | {name, runner_name, labels}'`. Then enumerate the full pool: `gh api repos/<owner>/<repo>/actions/runners --jq '.runners[] | {name, status, labels: [.labels[].name]}'`. Map runner names to physical hosts or EC2 instances (for AWS: `aws ec2 describe-instances --filters "Name=tag:Name,Values=<runner-name-prefix>*"`). If the runner is remote, the fix must be applied there — via SSM (`aws ssm send-command --instance-ids ...`), SSH, or a provisioning script — not on the local machine. **Fixing the local machine and rerunning will fail identically** because the rerun dispatches back to the same remote pool. This is the most common wasted-cycle mistake in multi-host CI triage.
3. **Identify the execution domain.** Record the runner name, physical host or instance, Unix service account, runner-service units, and all peer runners on that host. Do not infer shared ownership from runner labels alone.
4. **Gather read-only evidence first.** Inspect path ownership/mode/ACLs, each runner account's UID/groups, active `flock` holders, active workers, and recent job attempts. Compare both attempts before calling the issue transient.
5. **Preserve the required concurrency semantics.** If the design calls for host-wide serialization, do not substitute `$RUNNER_TEMP`; it is normally per runner and weakens the domain to job-local/per-runner serialization. Provision a root-managed shared lock directory, dedicated Unix group, setgid directory, and group-writable lock file instead.
6. **Drain safely.** Stop new work from being assigned to the affected pool, wait for existing workers and lock holders to finish, update service-account group membership, and restart runner services. Do not restart an active runner or replace a held lock file.
7. **Verify both accounts and live CI.** Test nonblocking acquisition as every runner user. Then inspect a fresh CI process to prove it opens the intended lock path and that waiting—not permission failure—occurs under contention.
8. **Handle cross-runner temporary artifacts explicitly.** Test suites can leave `0700` paths owned by another runner. Keep cleanup prefix-allowlisted and age-bounded, serialize it under the same shared lock, and use a deliberate privileged cleanup capability only where the CI host already grants it. Verify cleanup is a distinct post-test stage.
9. **Make remediation durable.** Store the runner provisioning contract and operator verification commands in repository-owned documentation or host bootstrap configuration. Include the shared path, group, file modes, service restart requirement, and verification command.

## Deaf listener: runner online but not dispatching

A runner can report `online` and `busy: false` via the GitHub API while its listener has stopped accepting job dispatches. The process heartbeats (RSA key reloads every ~50 min in `_diag/Runner_*.log`) but never picks up queued work.

**Trigger:** a job stays `queued` for >15 minutes while all runners with matching labels show `online` and `busy: false`.

**Diagnosis:**
1. Confirm no concurrency group is blocking: check all runs in the same workflow for non-terminal status.
2. Confirm label match: the job's `runs-on` labels must be a subset of a runner's labels.
3. Inspect `_diag/Runner_*.log` tail: if the last entries are only RSA key reloads with zero `JobDispatcher` activity for hours, the listener is deaf.
4. Check for a preceding cancellation or lost-communication event that may have wedged the listener state.

**Fix:** restart the runner's systemd service (`sudo systemctl restart actions.runner.<org>-<repo>.<runner-name>.service`). The listener re-registers and picks up queued jobs within seconds.

**Prevention:** a watchdog that verifies dispatch liveness (not just process liveness) would catch this. The GitHub API has no native signal for "listener is accepting jobs." See `references/deaf-runner-listener.md`.

## Setup-step failures: verify host state before concluding a binary is missing

When a job fails in a **setup step** (`Setup Bun`, `actions/checkout`, dependency install, or a `flock`-guarded cleanup) rather than in the application test command, the fault is almost always runner-host environment or provisioning, not the PR. Two recurring shapes:

### "Unable to locate executable file: <bin>" when the binary IS installed

A setup action (for example `oven-sh/setup-bun` extracting a release zip) can report `Unable to locate executable file: unzip` even when the binary exists on the host. Do not conclude the package is absent from the runner image until you verify:

1. The binary on disk: `which <bin>` and `ls -la $(which <bin>)`.
2. The runner's configured PATH: read `<runner-dir>/.path` and the live process environment (`cat /proc/<runner-pid>/environ | tr '\0' '\n' | grep -i '^PATH='`).
3. Whether the job ran in a container/chroot with a different root: `ls -la /proc/<runner-pid>/root/usr/bin/<bin>`.

A binary that is present on disk and on PATH but still "not locatable" points to action-internal resolution, a transient runner environment, or a container boundary — classify it as runner-environment and prefer a rerun plus host verification over a product fix. Do not open a source-code rescue from a setup-step "missing binary" that the host already provides.

**When all three checks pass** (binary on disk, in `.path`, in the live process environment) and a later attempt of the same run succeeds without any host change, the failure is confirmed transient action-internal resolution. No host provisioning change is needed — the rerun is the fix. Record the evidence (which attempts failed, which succeeded, runner name) and move on. Do not file an infra repair card for a self-healed single-run flake unless the same signature recurs across multiple unrelated runs.

For EC2 runners reachable via AWS SSM, use the concrete verification recipe in `references/ssm-runner-host-verification.md`.

### `flock: cannot open lock file ...: No such file or directory` (exit 66)

`flock` does **not** create parent directories. If the workflow points a lock at `/var/lock/<product>/<name>.lock` (note: a job-level `env:` can override a workflow-level default, so read the effective value from the failed step's environment block, not just the workflow top level) and that directory is absent on the assigned runner, the lock step fails immediately with exit 66 before the guarded command runs.

**Three distinct root causes for the absent directory:**
1. **Never provisioned** — the runner was added to the pool without the directory. Fix: provision on every runner in the pool.
2. **Provisioned but lost on reboot** — `/var/lock` is a symlink to `/run/lock`, which is **tmpfs-backed** on most Linux distros including EC2 Ubuntu. Any directory created under `/var/lock/` is silently wiped on reboot. A workflow comment like "Provisioned on the dedicated build host" is a lie after the first reboot. This is the more common and insidious variant: the runner was correctly set up, CI worked for weeks, then a routine reboot (kernel update, EC2 maintenance event) breaks it with no provisioning change. Diagnose with `mount | grep /var/lock` or `stat -f /var/lock` for tmpfs. Do not waste time auditing provisioning scripts — the fix is the same either way.
3. **Provisioned but raced at boot** — a tmpfiles rule (`/etc/tmpfiles.d/<product>-ci.conf`) exists and `systemd-tmpfiles-setup.service` is in the boot chain, but a CI job dispatched immediately after boot hits the lock path *before* tmpfiles completes. The directory is absent at job time but **present when you inspect post-facto**, making the failure look phantom. Diagnose by comparing the directory's `mtime` (close to boot time) against the job's `startedAt` timestamp, and confirming the tmpfiles rule exists. The fix is the same workflow-level `mkdir -p` — do not rely on tmpfiles timing. Secondary finding: tmpfiles rules specify ownership (e.g. `ubuntu:ubuntu`), but if another process (manual `mkdir`, a prior root-run script) created the file first, tmpfiles may not correct ownership on an already-existing file. Verify with `stat -c '%U:%G %a'` and correct to match the rule.

This is distinct from the *permission* drift covered by `github-actions-run-diagnostics` (`self-hosted-runner-shared-locks.md`): there the directory exists but the lock mode/owner blocks a second account; here the directory is absent entirely. Fix by provisioning the lock's parent directory (root-owned, correct group/modes per the shared-locks reference) on **every** runner in the labeled pool — not by moving the lock to a broadly writable path, which weakens the intended host-wide serialization. **The durable fix is a workflow-level `mkdir -p "$(dirname "$HAFT_CI_HOST_LOCK")"` step before any `flock` call**, so the workflow self-heals after any reboot without depending on immutable runner-image state. For belt-and-suspenders, also add a systemd tmpfiles rule (`/etc/tmpfiles.d/<product>-ci.conf` with `d /var/lock/<product> 2770 root <group> -`) so the directory is recreated at boot even before the workflow runs.

When the same workflow also calls a root-owned `sudo -n /usr/local/sbin/<helper>` cleanup step that is absent on the runner (`command not found`), provision both the lockdir and a bounded, prefix-allowlisted, age-bounded helper. Exact host fix commands and the known-good helper script body are in `github-actions-run-triage` → `references/missing-host-prereq-remediation-recipe.md`.

### `sudo: a terminal is required to read the password` in dependency-install steps

A workflow step that runs `bunx playwright install --with-deps` (or any `sudo apt-get install`) can fail intermittently across a runner pool when **sudoers NOPASSWD config is inconsistent** — some runners have it, some don't. The error is:

```
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: a password is required
```

**Diagnostic signature:** the same workflow on the same PR/branch produces runs where some get past the install step and run tests (e.g. 41-42 pass, 1 fails on a real test) while others die at the install step before any test runs. This proves pool-level inconsistency, not a single broken runner.

**Fix:** ensure `/etc/sudoers.d/` has a NOPASSWD entry for the CI user on **every** runner in the pool (e.g. `ci-user ALL=(ALL) NOPASSWD: /usr/bin/apt-get, /usr/bin/dpkg`), then install the actual browser deps. If runners have a provisioning script, add the sudoers line there so it survives re-provisioning.

**Classification:** runner-environment, not code. Do not open a per-PR rescue. Track on a single infra card covering the whole pool.

### New-runner pool expansion provisioning gaps

When expanding a runner pool (adding runners `-3`, `-4`, `-5` alongside existing `-1`, `-2`), the new runners often lack baseline provisioning that the originals received during initial setup. The diagnostic signature is: **the same workflow fails on new runners with setup-step errors while old runners pass the same steps**.

Common gaps on freshly provisioned runners:
- Missing system packages (`unzip`, `jq`, `rsync`) that setup actions shell out to — unlike the transient "binary IS installed" case above, these are genuinely absent
- Missing lock directories (e.g. `/var/lock/<product>/`) that the workflow's job-level `env:` override points to
- Missing root-owned helper scripts (`/usr/local/sbin/<product>-clean-*`) and their sudoers allowlists
- Missing browser system dependencies for Playwright (`libgtk-3-0t64`, etc.)

**Diagnosis:** correlate failed runs with runner names via `gh api repos/<owner>/<repo>/actions/runners --jq '.runners[] | {name, labels: [.labels[].name]}'`. If failures cluster on runners with names new to the pool (higher suffix numbers, missing labels the originals have), it's a provisioning gap, not a code issue. Compare the label sets: new runners may lack labels like `devspace` that the originals carry, hinting they were provisioned from a different baseline.

**Fix:** apply the same provisioning used for the original runners to every new runner. Verify with a targeted rerun that lands on a new runner. Track on a single infra card covering the whole expansion batch, not per-PR rescues.

**Prevention:** maintain a runner provisioning checklist or bootstrap script covering: system packages, lock directories with correct modes, helper scripts + sudoers, browser deps, and runner service registration. Run it for every new runner before adding it to the pool.

### Cross-PR corroboration

If two or more unrelated PRs fail identically in the same setup step across one pool within a short window, that is a shared provisioning gap, not per-PR breakage. Record the runner names, exact failed step, and error; rerun once the host is provisioned; and keep ownership on one runner/host card rather than opening per-PR rescues. The triage-side classification and repair-card shape live in `github-actions-run-triage` ("Runner-pool system-tool and host-infrastructure prerequisites").

## Dockerized runner acceptance: distinguish dispatch from container prerequisites

When GitHub assigns a job to a Dockerized self-hosted runner and the job reaches its guarded command, runner registration and label routing are already proven. Diagnose the exact failed step before editing workflows or product tests.

### Build-container shared-memory and helper contract

If a Bun CI harness rejects `HAFT_CI_TEST_TMPFS_ROOT` because `/dev/shm` is smaller than its documented minimum, that is a container-runtime configuration failure before tests, not an application regression. A common Docker default is a 64 MiB `/dev/shm`, while a memory-backed test lane can deliberately require 1 GiB or more.

- Preserve the test preflight and its threshold; do not lower it or move the test temp root to a weaker location merely to pass.
- Configure a **container-local** tmpfs for `/dev/shm` at the required size in the runner's Compose/Docker definition (for example `shm_size: 1gb` or an equivalent tmpfs size), not through a host mount or privileged container.
- If an always-run bounded cleanup command is absent from the image, treat it as a second independent image-prerequisite failure. Bake the existing allowlisted helper and its narrow noninteractive execution contract into the image; do not remove the cleanup step.
- Validate a fresh CI job reaches the required test command, then its cleanup, before calling the build lane repaired.

### Browser-container OS libraries

If `bunx playwright install firefox` succeeds but `browserType.launch` fails before an assertion with `Host system is missing dependencies to run browsers`, the browser binary download is not enough: the runner image lacks Firefox's OS libraries.

- Bake the lockfile-compatible Playwright Firefox dependency set (`playwright install-deps firefox` equivalent) into the separate, digest-pinned browser runner image.
- Do **not** add `sudo`, `apt-get`, or `playwright install-deps` to the GitHub workflow as an auto-remediation path when the runner's security contract prohibits new runtime privilege. A non-mutating preflight is acceptable only if it gives a clear operator action.
- Preserve separate build/browser labels and pools. Do not add deployment labels, Docker socket mounts, privileged mode, host mounts, or credential/token expansion to repair browser dependencies.
- Prove the exact Firefox spec reaches and passes its product assertion on a fresh runner-image deployment; a successful Chromium sibling alone does not validate Firefox prerequisites.

If the Docker/Compose definition is owned outside the application repository, do not create a cosmetic application-repo PR that cannot change runtime behavior. Provide a reviewed, bounded change request to the owning definition and request its source path/PR for review.

### Acceptance triage: attribution, attempts, and environment-vs-product

When validating a candidate runner image (temporary validation PR, rerun lane), conclude per-runner and per-attempt, never per-workflow:

1. **Resolve attempts first.** Multiple failed build windows on one head SHA are often attempts of ONE run (`run_attempt > 1`), not separate runs. Enumerate with `gh api repos/<owner>/<repo>/actions/runs/<id>/attempts/<n>/jobs` for n=1,2,3... The bare `/attempts` list endpoint and `/timeline` can return 404 even when numbered attempt endpoints work; job objects also carry `run_attempt`.
2. **Attribute every job to its runner before concluding anything.** Pull `runner_name` per job per attempt. A "passed" sibling job (e.g. the required browser gate) may have landed on a *different* runner than the candidate — it validates nothing about the image under acceptance.
3. **Apply the environment-vs-product rubric.** On a comments-only or no-product-diff validation PR: moving failures (each attempt fails a *different* timing/IO-sensitive test) + a green control run on a managed runner in the same window + suite wall time several× the governance baseline + PSI IO pressure in the runner-context log = runner environment, not product regression.
4. **Discriminate job timeout vs workflow concurrency.** A canceled job whose start→cancel span equals its `timeout-minutes` is a job-level timeout, not a concurrency cancel — even when an earlier run on the same PR genuinely was concurrency-canceled. Verify a later push exists before blaming concurrency.
5. **Browser downloads must fit the timeout budget.** A Playwright browser not baked into the image can exhaust the job timeout mid-download at cold speeds (observed ~5.5 MiB/min for a 104.9 MiB Firefox against a 20-min budget). Pre-bake browsers into the acceptance image, and force at least one required-gate run onto the candidate browser runner — a gate that never landed on it proves nothing.

Concrete commands, thresholds, and a worked case are in `references/runner-image-acceptance-triage.md`.

## Bun runtime-transpiler cache suspicion after an exact checkout

When a persistent self-hosted runner appears to execute older TypeScript/JavaScript behavior despite a reported exact checkout, do not assume Bun's dependency cache is a transpiler cache. First attribute the failed job to its live runner, inspect both job and runner/container `BUN_*` environment, enumerate persistent mounts, and separate `~/.bun/install/cache` from any actual transpiler artifact. An unset `BUN_RUNTIME_TRANSPILER_CACHE_PATH`, no discovered transpiler cache, and no persistent mount to one rules out the configured/persisted cache explanation; it does not prove an unknown runtime defect impossible. The detailed, read-only evidence sequence is in `references/bun-transpiler-cache-diagnostic.md`.

## Queued jobs with idle runners: label-selector mismatch

When jobs queue for >5 minutes while multiple runners show `online` and `busy: false`, the most common cause is a **label mismatch** between the workflow's `runs-on` selectors and the runners' registered labels — not a dispatch failure, not a deaf listener.

**Diagnostic signature:** `gh pr checks` shows jobs `pending`/`queued`; `gh api repos/<owner>/<repo>/actions/runners` shows multiple runners `online`/`busy: false`; but the jobs never dispatch.

**Procedure:**

1. **Extract the exact label set from the queued job.** Use the REST API, not `gh pr checks` (which may abbreviate): `gh api repos/<owner>/<repo>/actions/runs/<run-id>/jobs --jq '.jobs[] | {name, labels, runner_name, status}'`. A `runner_name: ""` with `status: "queued"` means no runner matched.
2. **Extract the label set from every online runner.** `gh api repos/<owner>/<repo>/actions/runners --jq '.runners[] | select(.status=="online") | {name, busy, labels: [.labels[].name]}'`.
3. **Compare as a subset check.** GitHub Actions requires the workflow's `runs-on` labels to be a **subset** of a runner's labels. A runner that has `haft-ci` but not `haft-ci-build` does NOT match a job requiring `haft-ci-build`. Partial overlap is not enough.
4. **Look for approval-label gates.** Labels like `*-approved` (e.g. `haft-ci-build-approved`, `haft-ci-browser-approved`) are intentional admission gates. A runner without the approval label is correctly excluded — not broken. Do not add approval labels to unvalidated runners as an emergency workaround.
5. **Check for single-instance bottlenecks.** If exactly one runner matches the selector and is `busy: true`, all subsequent jobs queue behind it regardless of how many other runners exist. The fix is adding more runners with the correct labels, not relabeling existing ones away from their current pool.
6. **Verify runner-name-vs-physical-host provenance.** A runner named `yogendra-build` may actually be a Docker container on a different host. Check `runner_name` against physical host evidence (Docker containers, SSH hostnames, service units) before assuming capacity lives where the name suggests.

**Common shapes:**

- **Pool expansion without label parity.** New runners were registered with a base label set but lack the approval labels the originals received during initial provisioning. Fix: re-register or relabel the new runners with the full label set.
- **Workflow relabel without runner relabel.** The workflow's `runs-on` was updated to require a new label, but existing runners were not updated to carry it. Fix: update runner labels to match.
- **Cross-pool confusion.** Runners from a different org/repo/pool (e.g. Athabasca runners on a shared machine) show up in `ps` output but are irrelevant to the current dispatch. Filter by `serverUrl` or runner registration metadata.

**Do not:**

- Do not restart runners to fix a label mismatch — the labels are registered at config time, not at runtime.
- Do not remove approval labels to unblock the queue — this weakens the admission gate.
- Do not conclude the runners are "broken" or "deaf" when they are correctly idle due to label mismatch.

## Approved-label pool exhaustion and fallback diagnosis

When required jobs use an approval label such as `haft-ci-browser-approved`, do not diagnose the outage as a single host failure until you enumerate the entire runner pool.

1. Pull the job's effective labels and confirm whether it ever received a runner. `runner_name: ""` with `steps: []` means the job was queued/cancelled before execution; it is not test evidence.
2. Enumerate all repository runners and compare their `status`, `busy`, and labels. A runner is eligible only when its label set contains every `runs-on` label; GitHub Actions does not fall back from an approved label to a merely compatible unapproved runner.
3. Separate lanes. A browser runner being offline does not imply the build lane is unavailable, and an online build runner cannot execute a browser job without the browser labels.
4. Treat labels like `*-approved` as an intentional security/runtime admission gate, not a generic capacity label. Do not remove or add one as an emergency workaround without validating the candidate runner's image, browser dependencies, checkout contract, isolation, and cleanup/runtime prerequisites.
5. If every approved runner for a lane is offline, the safe options are: restore a healthy approved runner, validate and promote a standby runner, or explicitly authorize a temporary workflow-label change. Do not restore a host with a known hardware-safety problem merely to satisfy CI.
6. Record the exact fallback gap in the handoff: required labels, eligible online runners, excluded online runners and the missing label, and which lane is actually blocked.

The workflow's `cancel-in-progress: true` can turn an unassigned/queued job into an opaque cancelled required check when a run is superseded. Inspect the live runner inventory and current PR head before attributing the cancellation to application code. A run that has no assigned runner and no steps should be classified as dispatch/capacity evidence first.

## Safe approval-label promotion and live capacity proof

Promote an existing runner in stages; label state alone is not runtime proof.

1. Query the runner's current labels and preserve its existing custom labels. The GitHub **set custom labels** endpoint rejects the default labels `self-hosted`, `Linux`, and `X64`; filter those three before sending the replacement JSON, then read the effective labels back. Add only the lane labels being promoted, uniquely.
2. Validate the exact lane on the physical host before adding `*-approved`: for browser lanes, run the repository's current Playwright runtime preflight from a disposable checkout and prove a real headless launch; for build lanes, prove the lock, cleanup helper, shared-memory, toolchain, and checkout contract under the runner account. Do not add a build approval label just because browser validation passed.
3. Add the approval label only for the validated lane. Trigger a real workflow or dispatch run and inspect the Jobs API `runner_name`, `labels`, status, and conclusion. A successful label PUT without a job landing on the candidate proves only registration, not dispatch or test compatibility.
4. When a rerun remains queued, enumerate active runs and their non-terminal jobs before restarting anything. A busy approved peer, a concurrency group, or an in-flight PR run can fully explain the queue. Keep the original failed run as evidence and use `gh run rerun <id> --failed` once, not repeated blind retries.
5. Read the actual workflow command before diagnosing a host lock. A workflow-level `HAFT_CI_HOST_LOCK` environment variable does not prove every job uses `flock`; inspect each job step and its timestamps. In a multi-browser workflow one job may serialize under the host lock while a sibling runs directly, so do not file a concurrency fix from labels or env blocks alone.

See `references/runner-label-promotion-and-capacity.md` for the bounded promotion, API, and load-sensitive test evidence sequence.

## Runner identity and safe quarantine

Before routing a shared runner failure or removing an approval label, prove the GitHub runner's physical-host provenance and enumerate alternate approved capacity. A runner name, SSH hostname, and remote worker host are not interchangeable identities. See `references/runner-identity-and-quarantine.md` for the evidence sequence, board-ownership correction, and fail-closed quarantine decision gate.

## Diagnostic pitfalls

- **Do not route by broad failure class alone.** Separate release/deployment, build, and browser capacity domains by exact runner identity. A generic “disk/capacity” owner can resume the wrong session and leave the real host untouched.
- **`gh run view <id> --log-failed` returns empty for SIGTERM-killed jobs.** When a job is terminated by signal (exit 143) rather than failing an assertion, the CLI's `--log-failed` flag may produce no output. Fall back to the REST API: `gh api repos/<owner>/<repo>/actions/jobs/<job-id>/logs` and grep for `error|SIGTERM|exit code`. Get the job ID from `gh api repos/<owner>/<repo>/actions/runs/<run-id>/jobs --jq '.jobs[] | select(.conclusion=="failure") | .id'`.
- **A SIGTERM during tests is not a test failure.** If every logged test shows `(pass)` and the log ends with `script "test" was terminated by signal SIGTERM` / exit 143, classify it as runner/host pressure (timeout, OOM, resource cap), not a code regression. Check for competing jobs on the same host before rerunning.

## Safety gates

- Never remove a lock file until holder checks show it is unused.
- Never broaden `/tmp` permissions or make arbitrary cleanup paths privileged.
- Treat a green test suite followed by cleanup failure as a failed job with a separate root cause.
- Keep browser and build pools separate unless they are demonstrably on the same physical capacity domain.

## Fleet capacity and provenance audits

When jobs queue despite a large self-hosted fleet, or a listener appears to belong to the wrong host, use the bounded evidence sequence in `references/runner-fleet-capacity-audit.md`. The critical rule is to correlate GitHub runner ID/name, effective `runs-on` labels, `.runner` metadata, process/container/service provenance, and physical-host headroom before relabeling, expanding, quarantining, or killing anything. `online=true,busy=false` proves neither selector eligibility nor dispatch liveness, and a listener running as `ssm-user` may be a valid registered Docker runner.

## Evidence checklist

Use the checklist in `references/self-hosted-ci-locks.md` for a concise command sequence and remediation design.
