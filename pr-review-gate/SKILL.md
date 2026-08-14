---
name: pr-review-gate
description: "Automated PR review gate for haft-sh org."
version: 1.0.0
author: JP Lew
license: MIT
metadata:
  hermes:
    tags: [github, pr-review, automation, haft-sh]
    related_skills:
      - herdr-team-agent-automation
      - github-pr-workflow
---

# PR Review Gate (Retired)

This standalone gate was retired on 2026-08-14. Its cron job and `<shared-scripts-root>/pr-review-gate.py` were removed; the master Haft PR/CI/board operations workflow is the sole active review path.

Historical incident lesson: the old validity heuristic treated words such as `diagnostic`, `monitoring`, or `operational` as suspicious, then recognized only conventional programming-language suffixes as code. It therefore misclassified legitimate `.github/workflows/*.yml` changes as “not a code change.” Workflow, build, test, packaging, migration, infrastructure-as-code, and configuration diffs must be reviewed on technical merit and repository ownership—not rejected by filename extension or operational vocabulary. A reviewer must inspect the actual diff and documented repo policy before abstaining.

## Historical Architecture

- **Reviewer**: `haft-reviewer` (GitHub user)
- **Token**: `GITHUB_HAFT_TOKEN` in `<hermes-home>/profiles/orchestrator/.env`
- **Permissions**: Org owner on `haft-sh`

## Branch Protection

All private repos have `master-guard` ruleset:
- Required reviews: 1
- Dismiss stale reviews: Yes
- Required status checks: CI must pass (strict)
- Bypass: OrganizationAdmin via `--admin`

### Protected Repos

- `haft` (master) — ruleset ID 20835589
- `tokenhungry` (main) — ruleset ID 20843061
- `rooftop-pro` (main) — ruleset ID 20843063
- `haft-private-skills` (main) — ruleset ID 20843064

## Cron Job

**Job ID**: `c139a1fe6f07`
**Name**: "PR Review Gate"
**Schedule**: Every 20 minutes
**Script**: `<shared-scripts-root>/pr-review-gate.py`
**Skills**: `software-development/herdr-agent-dispatch-orchestration`
**Delivery**: local

**Concurrency**: Max 4 concurrent reviews

## Workflow

### Automated Loop (every 20m)

1. Scan all open PRs across `haft-sh`
2. Check status: CI, reviews, merge state
3. **Validity gate**: Assess if PR solves real problem and belongs in repo
   - If concerns → abstain, comment, tag @jplew
   - If valid → proceed with review
4. Review PRs:
   - CI green + no changes requested → approve
   - CI red or changes requested → request changes
5. Dispatch rescue jobs to Yogendra when:
   - CI is red
   - Branch is behind master
   - Branch has conflicts

### Validity Gate

Checks for:
- Speculative language ("proactive", "might", "could be")
- Operational concerns that don't belong in code (thermal, temperature, hardware)
- Refactors without clear problem statement
- Very short descriptions (<100 chars)

If concerns detected:
- Leave comment with concerns
- Tag @jplew
- Abstain from review
- Suggest improvements to ticket generation

### Manual Override

JP can bypass:
- GitHub UI: "Merge without waiting for required reviews"
- CLI: `gh pr merge <number> --admin --repo haft-sh/<repo>`
- Orchestrator: Instruct to merge with `--admin`

## Script Details

**Location**: `<shared-scripts-root>/pr-review-gate.py`

**Key functions**:
- `load_token()`: Read token from .env
- `get_open_prs()`: Scan all repos
- `check_pr_status()`: Check CI, reviews, merge state
- `assess_pr_validity()`: Validity gate
- `review_pr()`: Approve or request changes
- `dispatch_rescue_job()`: Send work to Yogendra

## Pitfalls

1. **Token security**: Never echo token. Use Python urllib with masked output.
2. **Self-review**: GitHub blocks self-approval. Reviewer must differ from PR author.
3. **Stale reviews**: Ruleset dismisses stale reviews on new pushes. Cron must re-review.
4. **Branch protection API**: Use PUT (not PATCH) for ruleset updates.
5. **Herdr dispatch**: Use `herdr-team-agent-automation` skill. Never use bare `hermes`.

## Verification

```bash
# Check ruleset
gh api repos/haft-sh/haft/rulesets/20835589 | jq '{name, enforcement}'

# Check cron
hermes cron list | grep "PR Review Gate"

# Check open PRs
gh pr list --repo haft-sh/haft --state open

# Manual review
gh pr review <number> --repo haft-sh/haft --approve
```
