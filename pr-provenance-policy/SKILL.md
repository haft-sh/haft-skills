---
name: pr-provenance-policy
description: "Use when creating or reviewing any JP-owned repository PR."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, pull-request, provenance, agent, model]
---

# PR provenance policy

## When to Use

Apply this policy whenever an agent creates, updates, or reviews a pull request in a JP-owned repository.

## Required PR-body block

Every PR body must contain completed `Work origin` and `Execution provenance` sections.

### Work origin

Select exactly one source:

- **Kanban ticket:** include any stable ticket ID; include its dashboard URL when available.
- **GitHub issue:** include the direct GitHub issue URL.
- **Ad hoc request:** say that it was ad hoc, summarize who/what requested the work and why, and provide the best available originating session title, stable session ID, or session link.

### Execution provenance

Record:

- Hermes agent/profile, or `Human/manual`;
- safe machine/host label;
- provider and model; for Mixture-of-Agents, record the preset and acting/aggregator model, and list reference models when known;
- stable session/run ID or link when available;
- every additional agent/model that materially authored the change.

Use `not available` only when runtime metadata is genuinely unavailable. Do not infer or fabricate metadata. Never include credentials, tokens, grants, private document bodies, private prompts, or sensitive machine details.

## Canonical Markdown shape

```markdown
## Work origin

- Source type: Kanban ticket / GitHub issue / Ad hoc request
- Kanban ticket: `<ticket-id>` — `<ticket-url or not available>`
- GitHub issue: `<issue-url or not applicable>`
- Ad hoc context: `<requester, request, and reason, or not applicable>`
- Originating session: `<session title and stable ID/link, or not available>`

## Execution provenance

- Hermes agent/profile: `<agent/profile or Human/manual>`
- Machine/host: `<safe hostname or machine label>`
- Model/provider: `<provider:model, or MOA preset plus acting/aggregator model>`
- Session/run ID: `<stable ID/link or not available>`
- Additional contributors: `<agents/models or None>`
```

Delete or mark non-selected origin fields `not applicable`; do not leave angle-bracket placeholders in a submitted PR.

## Creation workflow

1. Establish source identity before opening the PR.
2. Read safe runtime metadata; do not assume uniform environment-variable names.
3. Fill the canonical block in the body file used by `gh pr create --body-file` or the equivalent API payload.
4. Create/update the PR.
5. Re-read the live PR body and verify the source, agent, machine, model, and session fields rendered without unresolved placeholders.

## Review behavior

Check provenance independently from technical correctness. Missing, contradictory, or placeholder provenance causes a precise **provenance evidence hold**, not a claim that the repository change is invalid. Continue inspecting the actual diff. Request the smallest body-only correction and resume the verdict when the live body is corrected.
