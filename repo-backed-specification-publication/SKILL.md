---
name: repo-backed-specification-publication
description: Use when turning a product decision into a repo spec, PR, and remote artifact.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Repo-backed specification publication

## Use when

A user wants a product/architecture decision documented in a repository, reviewed through a pull request, and persisted to a product knowledge/document destination such as a managed Haft instance.

## Core workflow

1. **Establish a source baseline.** Fetch the remote default branch and create a dedicated worktree from the immutable current base. Keep the canonical checkout clean.
2. **Write an implementation-ready spec.** Include the goal, current state, locked decisions, explicit security boundaries, exact likely files/tests, harness or vendor handoffs, non-goals, and review gates. Separate advisory discovery from authority-granting behavior.
3. **Make user-consent behavior explicit.** For a download/install flow, define TTY prompting, default answer, decline behavior, non-TTY/JSON semantics, and automation flags. Detection must not silently select, install, or imply readiness.
4. **Verify and publish the source artifact.** Run `git diff --check`; commit, push, and open a PR using the repository PR template. Record only actual verification results.
5. **Persist the exact bytes through the sanctioned product path.** Hash the source file, import it through the installed product CLI with machine-readable completion, and retain the returned remote path, job/batch ID, hash, and indexing outcome.
6. **Keep source and destination revisions honest.** The PR is the reviewable source of truth. A remote artifact is a distribution/reading copy; it must identify the source commit and must not be described as merged canonical content before merge.
7. **Create implementation runway only after the spec is durable.** Link implementation cards to the spec PR/commit and state whether the PR must merge before workers begin.

## Remote overwrite mismatch

When a remote import with `--on-duplicate overwrite --force` returns an identity-mismatch conflict, do not claim the existing destination artifact changed and do not bypass the product seam. If the user authorizes immediate persistence, import once with `--on-duplicate clone`, record the renamed destination path and hash, and label it a distinct revision. See `references/remote-overwrite-identity-mismatch.md`.

## Pitfalls

- Do not write the spec in a stale or dirty canonical checkout.
- Do not report generated or planned test results as actual verification.
- Do not use duplicate artifact fallback to imply overwrite success.
- Do not make CLI PATH detection select a harness or confer runtime authority; it is advisory UX only.
- Do not auto-install vendor CLIs or accept install prompts by default.

## Verification checklist

- [ ] Spec names source commit/branch and clear non-goals.
- [ ] PR exists and its live CI state was checked.
- [ ] Remote import returned a completed machine-readable result.
- [ ] Source SHA-256 equals the imported file SHA-256.
- [ ] If a clone fallback was used, its renamed destination path is recorded as a distinct revision.
- [ ] Implementation cards cite the durable source and preserve review/deployment boundaries.
