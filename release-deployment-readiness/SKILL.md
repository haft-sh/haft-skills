---
name: release-deployment-readiness
description: Use when hardening release deployment health gates.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [release, deployment, readiness, health-checks, rollback, ci]
---

# Release Deployment Readiness

Use this skill when a release pipeline falsely fails because a newly restarted service becomes healthy shortly after a fixed readiness window, or when a deployment timeout does not provide enough evidence to distinguish slow startup from a dead service.

## Core procedure

1. Reproduce the timing from workflow logs and the target host. Establish whether the service eventually becomes healthy, whether it ever binds the expected port, and whether the health response matches the intended immutable commit/build identity.
2. Replace fixed iteration counts with an explicit bounded deadline. Make the grace period configurable, validate it against a conservative minimum and maximum, and choose a default large enough for the observed cold-start path.
3. Bound each individual probe (`curl --max-time`, or equivalent). A loop deadline is not sufficient if one network call can hang beyond it.
4. Validate the complete health contract, not just HTTP success: expected app/service identity, runtime, build commit, and embedded/source provenance.
5. On deadline expiry, emit safe, bounded diagnostics: systemd active/substate/main PID, service status, and whether the expected listener exists. Avoid dumping environment files, credentials, or unbounded logs into CI output.
6. Keep rollback behavior intact. A readiness timeout must still trigger the existing rollback trap, while diagnostics must not mask the original failure or make cleanup failures fatal.
7. Add source-contract regression tests for the timeout configuration, workflow wiring, deadline/probe behavior, and timeout diagnostics. Run shell syntax checks plus focused deployment tests, then install locked dependencies and run typecheck/build when the checkout is fresh.
8. Review the release workflow semantics separately: if immutable artifacts are published before every environment gate passes, a late gate failure burns the version. Never move or reuse an immutable tag; recover by fixing the gate and using the repository's supported rerun/fix-forward procedure.

## Acceptance checklist

- [ ] Readiness duration is bounded but not an unnecessarily tight fixed loop.
- [ ] Per-request timeout prevents a hung probe from defeating the overall deadline.
- [ ] Timeout output identifies service state and listener state without leaking secrets.
- [ ] The expected release/build identity remains enforced.
- [ ] Existing rollback and observability verification still run.
- [ ] Regression tests cover both the deployment script and workflow configuration.
- [ ] Fresh verification evidence distinguishes targeted tests from full typecheck/build.

## Pitfalls

- Increasing only the CI job timeout does not fix a remote readiness gate that still exits after its own short deadline.
- Retrying an immutable release may be safer than allocating a new version only when the repository explicitly supports rerunning the failed deployment/finalization path; do not retag the same version at a different commit.
- Public endpoint checks can be auth-gated or proxy-sensitive. Prefer authenticated checks or host-local readiness evidence for the service gate, and classify 401/403/502 separately.
- Do not claim independent review if the configured reviewer/delegation surface is unavailable; record that gate as unavailable.

See `references/slow-start-release-gate-incident.md` for the validated incident pattern and concrete test/diagnostic shape.
