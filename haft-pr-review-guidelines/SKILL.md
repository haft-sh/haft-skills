---
name: haft-pr-review-guidelines
description: "Use when reviewing any Haft pull request."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, github, pr-review, ci, workflow]
---

# Canonical Haft PR Review Guidelines

## When to use

Apply these rules to every automated or agent-assisted review of a Haft pull request. These rules govern review judgment; cron prompts govern scheduling and orchestration. If a heuristic, older skill, reviewer habit, or generated suggestion conflicts with this skill, this skill wins.

## Required evidence before a verdict

For the PR's current head SHA, inspect all of the following:

1. PR title and body, including the stated problem and acceptance evidence.
2. The complete changed-file list and actual diff—not only filenames, extensions, labels, or summary statistics.
3. The linked Kanban card when one exists, repository `AGENTS.md`, and relevant neighboring code or configuration.
4. Live required-check contexts and results from the repository ruleset or protected-branch configuration. Never infer required checks from names or historical runs.
5. Current reviews, unresolved threads, mergeability, and whether new pushes made prior evidence stale.

Green CI is evidence, not a substitute for reviewing the diff. A board card is useful scope evidence but is not required for an otherwise legitimate repository PR.

## PR-body provenance

Every PR body must contain a completed work-origin and execution-provenance note. Check this independently from technical validity.

Required origin evidence is exactly one of:

- Kanban-originated work: a Kanban ticket ID, preferably with its stable dashboard link;
- GitHub-issue-originated work: a direct issue link;
- ad hoc work: a short context statement and the best available originating session identity, including which agent received or spawned the request.

Required execution evidence is:

- Hermes agent/profile, or `Human/manual`;
- safe machine/host label;
- provider/model, or the MOA preset plus acting/aggregator model;
- stable session/run ID when available;
- any additional agent/model that materially authored the change.

Never require or record credentials, grants, private document bodies, or sensitive machine details. `Unknown` is acceptable only when the author explains why the metadata is unavailable; do not invent provenance.

If provenance is missing, incomplete, contradictory, or still contains template placeholders, leave a precise provenance evidence hold and request the smallest body correction. Do not describe the code as invalid, do not manufacture a technical defect, and do not let missing provenance replace the actual diff review. Once corrected, re-read the live body and continue the technical verdict against the same current head SHA.

## Repository ownership and validity

A change is reviewable repository work when its intended behavior is owned by files in the repository. This includes:

- application and library code;
- tests, fixtures, and generated-artifact governance;
- GitHub Actions and other CI/CD workflows;
- shell scripts, build and packaging files;
- configuration, schemas, migrations, and infrastructure as code;
- deployment and operational automation;
- documentation that defines or changes supported behavior.

Never classify or reject a PR using a programming-language-extension allowlist. Never treat words such as `CI`, `ops`, `operational`, `infrastructure`, `workflow`, `diagnostic`, `monitoring`, `alerts`, `runner`, `deploy`, or `release` as evidence that a change does not belong in the repository.

Keep these questions separate:

1. Repository ownership: Is the proposed remedy implemented in a surface this repository owns?
2. Technical correctness: Does the diff safely and correctly implement the intended behavior?
3. External follow-up: Is a host, account, runner, credential, deployment, or human action also needed?

External follow-up may be necessary without invalidating a legitimate repository change. State it separately.

Only raise a scope or validity concern when concrete evidence shows that the diff is unrelated to its stated purpose, belongs to a different repository or system, duplicates or is superseded by existing work, contains generated/noise-only changes, or cannot satisfy the stated outcome. Cite that evidence. Ambiguous wording, a short body, small size, file type, title prefix, or operational subject matter is not enough.

## Review the actual changed surface

### Product or library code

Check correctness, boundary conditions, error handling, compatibility, security and privacy boundaries, API contracts, state transitions, and focused test coverage.

### Tests and fixtures

Check that assertions prove intended behavior, failures cannot pass vacuously, timeouts or retries are not hiding defects, and fixtures do not create delayed failures or unsafe side effects.

### CI and workflow configuration

Treat `.github/workflows/*.yml` and equivalent pipeline files as first-class code and configuration. Check:

- triggers, branch/path filters, job dependencies, matrices, and concurrency or cancellation behavior;
- exact required-check names and whether the change removes, renames, skips, or weakens a required gate;
- job and step `if` expressions, failure semantics, retries, timeouts, and preservation of failure evidence;
- permissions, secrets exposure, fork or untrusted-input boundaries, shell quoting/injection risks, and action pinning;
- runner labels, host assumptions, locks, temporary storage, cleanup bounds, and platform-specific behavior;
- artifact selection, existence guards, upload conditions, retention, size/quota impact, and whether cited proof comes from the changed path and current head;
- focused validation for reusable scripts or expressions where practical.

Do not require application-code changes for a workflow PR to be meaningful. Do not block on skipped optional checks; determine required checks from live policy. Do not approve merely because CI is green if the workflow diff weakens the gate that produced that result.

### Configuration, packaging, migrations, deployment, and infrastructure as code

Check schema and format validity, defaults and backward compatibility, rollout and rollback safety, idempotency, least privilege, environment separation, destructive effects, and whether runtime/operator actions are separated from repository changes.

### Documentation-only changes

Check factual accuracy, consistency with live behavior and public/private boundaries, broken commands or links, and whether documentation conceals a missing implementation that the card requires.

## Findings and verdicts

Every blocking finding must:

- cite the file and line or exact workflow, job, or configuration key;
- describe the failure mode and impact;
- explain why existing checks do not cover it when that is not obvious;
- request the smallest concrete correction or missing proof.

Use these outcomes:

- APPROVE: Current-head diff satisfies scope and acceptance criteria, required checks are green, and no concrete blocker remains.
- REQUEST_CHANGES: A concrete correctness, safety, scope, or acceptance-evidence defect exists. Name it precisely.
- COMMENT/HOLD: Evidence is incomplete or a required check is genuinely pending. State exactly what is missing; do not characterize the PR as invalid.
- HUMAN ESCALATION: A product decision, credential/production boundary, destructive operation, or unresolved ownership question requires JP. Keep the PR technically reviewable and ask the smallest exact question.

Never post a generic automated abstention. If confidence remains insufficient after evidence inspection, leave the board truthful and escalate without inventing a defect.

## Regression case: Haft PR #1627

A PR changing only `.github/workflows/ci.yml` and `.github/workflows/e2e.yml` to adjust diagnostic-artifact upload conditions or retention is valid repository-owned work. Words such as `diagnostic` or `CI`, and the absence of `.ts` or `.py` files, are not validity concerns. Review it for workflow semantics, required-gate preservation, artifact correctness, permissions, quota impact, and current-head proof. Missing branch-run artifact evidence is an evidence hold—not grounds to dismiss the change as operational or non-code.

## Completion proof

Record the reviewed head SHA and verify the resulting GitHub review or comment live. Scheduler success, an opened reviewer session, a stale review on an older SHA, or a generated summary is not completion evidence.
