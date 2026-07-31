---
name: haft-agent-session-operations
description: Use when editing one existing Haft document through a local or managed remote AgentSession; covers installed-CLI preflight, exact artifact targeting, draft review, explicit Apply, bounded evidence, and bootstrap failure classification.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, agent-session, remote-editing, hermes, drafts, approval]
    related_skills: [haft-vault-operations, haft-agent-api, software-development-lifecycle]
---

# Haft AgentSession Operations

## Overview

Use this skill for conversational edits to one existing Haft document when the required lifecycle is:

1. resolve one exact page or artifact
2. start or attach one isolated AgentSession
3. run a bounded agent turn against the session draft
4. validate the sandboxed draft preview
5. inspect the diff
6. Apply only after explicit approval with the expected draft revision

The AgentSession draft is a proposal workspace. The canonical source must remain unchanged until the explicit Apply command succeeds.

## Do Not Substitute Another Write Lane

A remote AgentSession bootstrap or authorization failure is not permission to:

- import a replacement copy
- overwrite the whole file through remote import
- call `document_patch` directly
- patch a canonical source path
- ask the user for a raw path, selector, bearer, or credential
- fall back to a manually configured static-bearer remote
- apply automatically after a turn

Classify the failure and repair the AgentSession path instead.

## Installed CLI Preflight

Use the installed product binary rather than an arbitrary source-tree invocation for dogfood evidence.

```bash
HAFT=haft
command -v "$HAFT"
"$HAFT" version --json
"$HAFT" update --check
```

Record:

- semantic version
- embedded commit/build identity
- whether an update is available
- the exact binary path

For formal managed-remote evidence, also verify the authenticated HQ session and destination projection:

```bash
"$HAFT" whoami --json
"$HAFT" remotes list --json
```

The destination must advertise:

- operation `agent-session-start`
- operation `agent-session-review`
- operation `agent-session-edit`
- route family `agent-sessions`
- capabilities `agent.session.write`, `agent.session.review`, and `agent.session.draft.write`

Do not treat discovery alone as proof that a real session mutation works.

## Exact Targeting

Prefer a durable artifact identity supplied by Haft:

```bash
ARTIFACT_ID=artifact-page-example
"$HAFT" --json agent-session start --remote dev --artifact "$ARTIFACT_ID"
```

Equivalent durable handle form:

```bash
"$HAFT" --json agent-session start \
  --remote dev \
  --handle "haft://artifact/$ARTIFACT_ID"
```

Page ID, slug, and page handles remain supported when they are the actual product identity available to the operator.

Rules:

- provide exactly one locator
- never guess among multiple pages
- never translate the locator into a raw vault path on the client
- an artifact must resolve destination-side to one current local editable HTML or Markdown page
- removed, quarantined, stale, remote-only, unsafe, non-page, and unknown artifacts fail closed

Record the returned:

- `sessionId`
- canonical `pageId`
- disposition: `started` or `attached`
- base hash
- active draft revision/hash

## Managed Remote Edit Recipe

After start or attach:

```bash
SESSION_ID=agent-session_example

"$HAFT" --json agent-session turn "$SESSION_ID" \
  --remote dev \
  --runner hermes \
  --instruction "Update today's Daily Note with the approved summary."

`turn` requires an explicit runner selector (`hermes`, `codex`, or `claude-code`). Verify the chosen runner is available before treating a turn failure as an authorization or document-editing failure.

"$HAFT" --json agent-session preview "$SESSION_ID" --remote dev
"$HAFT" --json agent-session diff "$SESSION_ID" --remote dev
```

The preview command validates one transformed sandboxed draft and returns bounded revision/hash/security facts. It does not print the draft HTML body.

Before Apply, establish that:

- turn completed
- draft revision advanced as expected
- preview is sandboxed and `no-store`
- diff is reviewable and scoped to the selected document
- canonical content/hash remains unchanged

Apply only with the exact reviewed revision:

```bash
REVISION=1
"$HAFT" --json agent-session apply "$SESSION_ID" \
  --remote dev \
  --expected-revision "$REVISION"
```

A revision mismatch must fail rather than applying a newer unreviewed draft.

## Authorization Model

Managed start uses a short-lived one-shot grant bound to:

- exact destination public origin
- one supplied page, slug, page handle, or artifact handle
- operation `agent-session-start`

The destination resolves that locator to one canonical page before consuming the grant and before creating or attaching a session.

Subsequent turn transport uses `agent-session-edit`, bound to:

- destination public origin
- canonical page ID
- exact session ID

Status, preview, diff, and Apply use one-shot `agent-session-review` grants bound to the same canonical page ID and session ID.

The destination public origin comes from the active signed managed claim projection. Reverse-proxy internal request origins and arbitrary `Forwarded` or `X-Forwarded-*` headers are not authority.

## Failure Classification

### `route.gate-denied` with `auth.central-grant.wrong-origin`

Meaning:

- HQ issued or exchanged a grant
- the destination rejected the grant's origin binding
- this is a managed bootstrap/authentication defect or stale origin projection

Action:

- confirm the destination's active signed public origin projection
- confirm the target advertised origin matches it exactly
- refresh/redeploy the managed destination when code or projection is stale
- retry the same AgentSession command

Never fall back to import overwrite or direct canonical patching.

### Managed-origin projection errors

Examples:

- `auth.central-grant.managed-origin-claim-missing`
- `auth.central-grant.managed-origin-claim-invalid`
- `auth.central-grant.managed-origin-claim-inactive`
- `auth.central-grant.managed-origin-projection-expired`
- `auth.central-grant.managed-origin-missing`
- `auth.central-grant.managed-origin-invalid`

These are destination bootstrap failures. Repair or refresh managed enrollment/projection state before retrying.

### Artifact targeting errors

Examples:

- `agent_session.target_not_found`
- `agent_session.target_invalid`
- `agent_session.source_unsupported`
- `agent_session.artifact_not_local`
- `agent_session.artifact_stale`
- `agent_session.artifact_removed`
- `agent_session.artifact_quarantined`
- `agent_session.artifact_unsafe`

Do not guess another target. Re-resolve from current Haft product identity or ask the user to choose among visible current artifacts.

### Revision or binding failures

A replay, wrong page/session, adjacent artifact, or revision mismatch must remain denied. Start a fresh grant exchange or re-review the current draft; do not widen the binding.

## Bounded Dogfood Evidence

A controlled real-remote proof should record only bounded operational facts:

- installed CLI path/version/embedded commit
- target slug and advertised operations/capabilities
- command phase and HTTP status
- request IDs and non-secret diagnostic codes
- supplied artifact ID or durable handle
- resolved `pageId` and `sessionId`
- base/draft/canonical hashes
- draft revision
- preview sandbox/no-store facts
- changed-file or diff summary
- proof canonical hash was unchanged before Apply
- Apply receipt and post-Apply canonical identity/hash

Do not attach:

- delegated bearer material
- HQ session handles
- credentials
- full document bodies
- private prompts
- private filesystem paths
- `.haft/agent-sessions` contents

Fixture coverage is necessary but not sufficient for a live dogfood claim. Run the installed CLI against the controlled destination after the relevant code is deployed.

## Completion Checklist

- [ ] Installed binary/version/update preflight recorded
- [ ] HQ identity and exact destination capability projection verified
- [ ] One exact artifact/page locator used; no raw path or selector supplied
- [ ] Start or attach returned one canonical page and session
- [ ] Turn changed draft only
- [ ] Preview returned bounded sandbox/revision/hash facts without body leakage
- [ ] Diff reviewed
- [ ] Canonical identity/hash proven unchanged before Apply
- [ ] Explicit revision-guarded Apply performed
- [ ] Post-Apply identity/hash verified
- [ ] No import overwrite, direct canonical patch, static bearer fallback, or credential exposure
- [ ] Controlled real-remote evidence attached after deployment
