---
name: branch-integration-safety
description: Use when merging a stale feature branch safely.
version: 1.0.0
---

# Branch Integration Safety

## Purpose

Use this before merging a long-lived feature, environment, release, or integration branch into the default branch. This is a functional-safety review, not a merge-conflict exercise.

A feature can be correctly isolated and still be unsafe to merge if the branch is far behind the default branch. Separate these claims:

- **Feature default safety:** the new feature remains dormant when its configuration is absent.
- **Integration safety:** the branch can be merged without regressing unrelated current behavior.

Never turn the first claim into the second without merged-artifact verification.

## Procedure

1. **Establish live Git topology.**
   ```bash
   git fetch origin --quiet
   git rev-list --left-right --count origin/<default>...origin/<branch>
   git merge-base origin/<default> origin/<branch>
   git log --oneline origin/<default>..origin/<branch>
   ```
   Record both sides of divergence. A large default-branch lead is integration debt: a conflict resolution can silently drop newer work.

2. **Classify branch-only changes.**
   Inspect unique commits and changed paths. Separate the intended feature from changes to shared startup, route composition, deployment configuration, systemd/worker units, CI/release workflows, shared UI, auth, persistence, or performance paths.

3. **Trace default-off behavior through runtime construction.**
   Do not stop at an environment-example comment. Follow config parser/defaults, activation predicate, startup/client/worker construction, request behavior when a dormant mode is selected, and tests for absent/false configuration.

   A default-off provider is adequately isolated only when an unset/false flag plus absent endpoint/credential avoids constructing a client or starting work, and requests truthfully use their bounded fallback.

4. **Inspect deployment semantics.** Confirm that merging code does not alter non-target instances through shared environment defaults, deploy workflow behavior, service installation, or auto-started units. Treat a service example as inert only after verifying it is not referenced by deployment automation.

5. **Build the real candidate.** From current default, create a disposable integration worktree and merge the branch there. Resolve conflicts with current default behavior authoritative outside the approved feature surface. Do not test by changing the canonical checkout or merging directly to default.

6. **Verify the merged artifact.** Run focused default-off/fallback tests plus typecheck, build, and the repository's normal CI gate. Then deploy first to a non-target environment with the feature configuration absent. Verify via authenticated runtime/operator evidence—not a guessed public endpoint—that the feature remains disabled and ordinary workflows retain expected performance.

7. **Make the decision.** Use one exact conclusion:
   - **Safe to integrate after merged-artifact verification**
   - **Feature defaults safe, but branch integration unproven/unsafe**
   - **Unsafe due to a traced shared side effect**

## Evidence standards

Report the merge base and divergence counts; activation predicate and source locations; provider/worker construction behavior with configuration absent; fallback tests; deployment/configuration surfaces inspected; commands actually run; and the remaining required gate.

## Pitfalls

- A branch can contain only feature-named commits while still conflict with newer shared work that exists only on default.
- `git diff default...branch` describes cumulative change since the merge base; use unique commits and a real integration merge to avoid over-attributing unrelated history to the branch.
- A public `403` status response proves a boundary exists, not a runtime feature state. Use an approved authenticated operator path.
- Do not enable a feature on a non-target environment merely to test the merge. First prove the default-off contract there.
- Do not install/configure a companion worker just because its code or a systemd example merged.

## References

- `references/bbt-semantic-branch-case.md` — anonymized example of default-off semantic provider code on a substantially stale environment branch.
