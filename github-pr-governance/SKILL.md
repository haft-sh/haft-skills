---
name: github-pr-governance
description: "Use when standardizing PR policy across repositories."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, pull-request, governance, provenance, templates]
    related_skills: [pr-provenance-policy, haft-pr-review-guidelines, github-pr-workflow]
---

# GitHub PR Governance

## When to use

Use this class-level workflow when defining or rolling out pull-request policy across repositories, especially PR-body templates, work provenance, agent/model identity, reviewer enforcement, and fleet-wide verification.

For ordinary implementation inside one repository, use the normal GitHub PR workflow. Use this skill when the task changes the rules or metadata contract governing PRs.

## Governance layers

Treat PR governance as three layers:

1. **Authoring prompt:** `.github/PULL_REQUEST_TEMPLATE.md` tells humans and agents what to provide.
2. **Creation discipline:** PR-producing agents populate actual runtime metadata and read the live body back after submission.
3. **Review enforcement:** reviewers place a precise evidence hold on missing or contradictory governance metadata.

A template alone is not enforcement. API-created PRs and custom scripts can bypass it. Pair every template rollout with creation instructions and reviewer-side validation; use a required automated check only when the repository intentionally wants a hard merge gate.

## Provenance contract

Every PR body should include `Work origin` and `Execution provenance`.

### Work origin

Select exactly one:

- **Kanban:** stable ticket ID; dashboard link when available.
- **GitHub issue:** direct issue URL.
- **Ad hoc:** who or what requested the change, why, and the best available originating session title, stable ID, or link.

Do not force an invented ticket for ad hoc work.

### Execution provenance

Record:

- agent/profile, or `Human/manual`;
- safe machine/host label;
- provider and model;
- stable session/run ID or link when available;
- additional agents/models that materially authored the change.

For Mixture-of-Agents work, record the preset and the acting/aggregator model. Reference models may be listed when known, but distinguish advisory references from the model that made the final decision.

Runtime metadata differs across Hermes, Herdr, Codex, Claude Code, and other harnesses. Inspect the actual safe runtime context; do not assume one environment-variable convention and never infer missing identity.

Use `not available` with a short reason when metadata cannot be recovered. Never fabricate or retroactively guess provenance for older PRs. Ask the author or session owner to supply it when necessary.

Never place credentials, tokens, grants, private prompts, private document bodies, or sensitive infrastructure details in a public or shared PR body.

Copy the canonical block from `templates/pr-provenance-block.md` and adapt surrounding repository-specific sections without deleting them.

## Cross-repository rollout

1. Confirm the exact repository scope. Do not interpret “all repos” without resolving organization/account boundaries and whether archived, forked, empty, sample, or legacy repositories are included.
2. Inventory each repository’s default branch, existing template, branch protection/rulesets, contribution instructions, and open rollout PRs.
3. Preserve repository-specific sections and ordering. Insert the provenance block at a natural review boundary instead of replacing useful test, risk, or demo sections.
4. Use isolated branches/worktrees from each current default branch. Repositories may mix `main` and `master`.
5. Commit and push one scoped template change per repository.
6. Open each rollout PR with a fully populated provenance block so the rollout demonstrates its own policy.
7. Read every live PR body back from GitHub and verify the rendered source, agent, host, model, and session fields, not merely the local body file.
8. Verify each PR changes only intended governance files and inspect live checks/review gates separately per repository.
9. Report rollout PR URLs and distinguish merged policy from merely proposed policy.

See `references/cross-repository-provenance-rollout.md` for fleet edge cases and the detailed verification checklist.

## Review behavior

Check governance metadata independently from technical correctness:

- Missing, placeholder, or contradictory provenance produces a **body evidence hold**.
- Continue reviewing the actual diff; do not call repository-owned work invalid because metadata is incomplete.
- Request the smallest body-only correction.
- Re-read the live body after correction and continue against the same current head when appropriate.

A provenance hold must identify the missing field precisely. Do not use it to manufacture a code defect or replace substantive review.

## Existing open PRs

A new policy normally governs new or updated PRs. For older open PRs:

- inventory missing provenance;
- backfill only from verified card, session, author, branch, or runtime evidence;
- never infer model, machine, or session from writing style, commit author, or branch naming alone;
- accept `not available` when truthful recovery is impossible;
- avoid mass body edits that erase repository-specific context.

## Verification checklist

- [ ] Exact repository scope is confirmed.
- [ ] Existing templates and repository-specific sections were preserved.
- [ ] One origin type is completed per rollout PR.
- [ ] Agent/profile, safe host, model/provider, and session/run identity are populated or truthfully unavailable.
- [ ] MOA preset and acting/aggregator are distinguished.
- [ ] No unresolved angle-bracket placeholders remain in submitted bodies.
- [ ] Live GitHub bodies were read back after creation or update.
- [ ] Each rollout diff contains only intended governance files.
- [ ] Review policy provides an enforcement backstop.
- [ ] Proposed templates are not reported as active until merged.
