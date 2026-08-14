---
name: haft-agent-dogfooding
description: Use when operating Haft for JP. Capture friction and improve flows.
version: 1.0.0
---

# Haft Agent Dogfooding

## Purpose

Use this operational overlay whenever an agent is using Haft on JP's behalf: importing or retrieving content, creating HTML artifacts, editing an existing document, testing a remote flow, or filing a Haft improvement card.

The goal is not to report incidental tool noise. It is to turn reproducible agent-facing friction into bounded product evidence while still completing the user's actual task.

## Operating loop

1. Complete the requested Haft operation through the intended product seam.
2. Verify the user-visible outcome: canonical Reader URL for a document, or the relevant rendered/reader surface for HTML.
3. Notice friction only when it changes agent cost, ambiguity, reliability, or requires unnecessary discovery/retries.
4. In the user-facing result, add a concise **Friction** line only when material friction occurred. State observed fact, impact, and a practical improvement; do not speculate about root cause.
5. Append concise evidence to the Dev **Haft Agent Friction Log** when it is durable product-intake evidence. Do not create a Kanban card for every entry. File a scoped card when the issue is reproducible or materially impedes a normal agent workflow.

## Intake-source reconciliation

When an inbound message triggers Haft work but its body is empty, truncated, or otherwise incomplete:

1. Treat the visible text as incomplete; never infer the missing requirements.
2. When the intake is an email and a message ID is available, retrieve the full message using the live email `get` surface before accepting a card's “empty body” or truncated-snippet claim. Search/list snippets and historical cards are not authoritative for the email body.
3. Check the live Haft Kanban card or other durable intake record before creating duplicate work or changing scope.
4. If the full message supplies requirements missing from the card, reconcile the card scope or file bounded follow-up work. If it adds nothing material, preserve the existing scope and add a concise reconciliation comment.
5. Do not reply through a read-only operational inbox unless the current user explicitly authorizes outbound email.

This keeps source discrepancies auditable without speculative scope expansion.

### A2A task-deliverable validation

When a Haft intake arrives through Inkbox A2A and the sender requires a ticket URL/ID, do not treat the task lifecycle state as proof that the requested work was done.

1. Retrieve the task message history and inspect the actual agent response before reporting success.
2. A `completed` state is insufficient if the response is unrelated, boilerplate, or lacks the requested ticket handle; report the message as received but the requested deliverable as unfulfilled.
3. Search the live Haft board for an existing canonical owner before creating work. If none exists, create a worker-claimable Haft card with the required reproduction, privacy boundary, and acceptance contract; return its stable card ID (and a PR URL later, if applicable).
4. Separate implementation/merge proof from live recovery: after a fix PR merges, query the cache-busted target runtime's embedded build identity. Do not claim the inbound incident is recovered until the target includes the fix and the specified user-facing canary passes.
5. When a new canary proves a later fault boundary than a related card or PR claims, inspect the live PR’s changed-file list and acceptance scope before reusing it. A browser/session-status PR can legitimately leave a server-side route-gate or membership-projection defect unresolved. Create one new canonical card for the non-overlapping remaining boundary, and add reciprocal cross-links so no worker mistakes the earlier PR for closure.
6. Record only bounded evidence: A2A task ID, card ID, PR/release identity, public build version/SHA, and canary outcome. Never include OTPs, session handles, invitation URLs/tokens, or grant material.

## Destination and path discipline

A conversational name for a remote instance is not automatically a vault, folder, or content-path prefix.

- Select the target instance with its configured remote selector.
- Keep the document/asset path separate from the remote name.
- Query the imported/retrieved page afterward and return the canonical Reader URL.
- A successful remote-import receipt can prove the write with a `vaultPath` and content hash while omitting the Reader URL. Do not pass that path to `haft get`, which accepts only a slug, Reader URL, page/chunk ID, or durable handle. Use one bounded `haft query` with a distinctive title term, matching `sourcePath` plus content hash, only to verify the current result and return its `readerUrl`.
- Treat this as a product-contract gap, not the normal desired workflow: the indexed-content import receipt and CLI output should include safe canonical page/Reader identity. File or extend that scoped contract work; keep links absent for skipped items, assets, and unindexed results, and preserve replay behavior.
- Never invent a folder from a nickname used in prose.

## Duplicate-state incident triage

When a remote Daily Notes or other configured-document update reports an overwrite conflict while the document still appears readable:

1. Keep the suspected source and any clone copy untouched unless the user explicitly authorizes mutation.
2. Collect two independent **read-only** views before diagnosing: the configured resolver (`haft daily show --remote <slug> --date <date> --format json --json`) and a broad catalog query (`haft query --path-prefix <configured-root> --remote <slug> --include metadata --limit 50 --json`). The resolver can select one configured source path while the catalog still exposes multiple active suffixed copies.
3. Record only bounded identity facts: source path, page/artifact handle, content hash, revision when returned, request ID, and Reader URL. Do not record document bodies or credentials.
4. Trace overwrite code separately from page lookup: a source-path query can remain valid while an exact replacement fails because its artifact-registry ID is stale, removed, or no longer bound to the same logical path.
5. Treat a generic move failure as an observability gap until the server returns a bounded error class/diagnostic. Do not infer that the source path was deleted or that the move was safely rolled back from a generic failure alone.
6. File or extend one live owner card with the read-only evidence and require a regression sequence: initial import → update → simulated stale identity/overwrite rejection → idempotent recovery → exactly one active configured path. Do not create a duplicate card when a current owner already covers the contract.

## Existing-document edit discipline

For social/web-source additions to an existing living document, load `references/social-source-editing.md` for source/fact separation, citation handling, and bounded runner recovery.

For an existing remote document, use AgentSession draft → preview → diff → explicit Apply. Do not replace a document through import merely because a direct overwrite collides or an AgentSession operation fails.

For long dictated or multi-section edits:

- Treat the original user request as authoritative; do not silently omit requirements to fit an instruction envelope.
- If a bounded runner rejects the instruction, verify no draft mutation occurred, then retry with a shorter semantic directive that asks the runner to compose the requested section.
- Preserve the same exact target, preview/diff the retry, and require explicit Apply.
- Treat an arbitrary short instruction ceiling as a product issue: client/server should share one documented bound and offer a discoverable long-form input path.

## Content capture and HTML collection

When collecting supplied images into HTML:

1. Count actual received files; do not assume an anticipated attachment count.
2. Use a self-contained HTML gallery when durable portable review matters, with descriptive title, accessible alt text, and neutral labels.
3. State the exact received count and leave the document easy to extend when more assets arrive.
4. Import/index the artifact through the selected remote, query it, and return the canonical Reader URL.

## Approved local runner-host verification

When a local AgentSession runner-host regression is approved for bounded verification:

1. Use the installed Haft binary with the intended host `HOME`; record `version --json` and `update --check` before changing runner-host state.
2. Run `agent-session doctor --runner hermes`, then explicit `agent-session setup --runner hermes --yes`. An `already-ready` result is a valid current-state outcome; record it rather than claiming a repair occurred.
3. Prove one managed remote lifecycle on an exact existing artifact: start → runner turn that changes only the draft → preview → diff → discard. Query the same artifact afterward and compare its canonical content hash to the pre-session value.
4. Verification approval is not publication approval: do not Apply a valid draft or append a log entry unless the user explicitly authorizes Apply.
5. Record bounded source-card evidence: installed version/commit, runner host/version/protocol, lifecycle phases, draft revision/file count, discard status, and pre/post canonical hash. Do not record session credentials, document body, private paths, or runner internals.
6. Treat a prior successful setup/doctor or completed verification card as historical only. A later live `agent-session.runner-install-invalid` before draft mutation supersedes that claim: discard the new session, verify canonical effect remains `none`, append a correction to the existing owner card, and reopen that card after checking its live status rather than filing a duplicate. Keep the original authorization boundary; do not substitute import, direct patching, static credentials, or automatic Apply.

This distinguishes an already-remediated host state from a release defect without weakening the AgentSession safety model.

## Managed-session cleanup friction

If a managed AgentSession start/attach succeeds without canonical mutation but immediate remote `discard` is denied, do not substitute import, overwrite, direct patching, broader grants, or a guessed server-side cleanup path. Record bounded evidence (installed CLI build, remote slug, operation, HTTP status/code, and that no turn/preview/diff/Apply occurred). When reproducible, file one focused lifecycle-contract ticket requiring either a correctly scoped remote discard capability or an honestly gated CLI surface, terminal-state proof, canonical-content non-mutation, and preserved wrong-session denial. Do not claim the friction log was updated if the only available session could not be cleanly discarded.

### Remote turn no-mutation handling

When a managed remote `agent-session turn` returns a no-mutation result—for example, the draft revision and hash are unchanged, `changedFileCount` is zero, and the runner reports a bounded failure—treat the write as unsuccessful, not as delayed or implicit success. Verify the canonical hash remains unchanged, discard the still-active session to close its lifecycle, and report the exact phase/code without relaying vendor-controlled diagnostic text or document content. Do not Apply revision 0 or use import/direct patching as an automatic fallback. If a direct canonical fallback would materially weaken the reviewed-edit boundary, ask the caller for explicit authorization before taking it; otherwise leave the document unchanged and state that the requested artifact was not persisted.

## Hermes skill-source configuration without regressions

When installing an externally owned/private skill repository for a Haft agent:

1. Inspect and record the existing `skills.external_dirs` value before changing configuration.
2. Confirm private repository access with the authenticated GitHub identity, clone to an absolute stable path, and validate the checkout remote before configuring it.
3. Use `hermes config set` rather than hand-editing `config.yaml`. Then verify the **stored type** with `hermes config get skills.external_dirs --json`; a path list must remain a YAML/JSON list when multiple source directories are intended.
4. If the installed config setter only persists a scalar and cannot safely encode an additional list entry, preserve existing sources with a dedicated overlay directory containing symlinked `SKILL.md` files from each approved source. Point the recognized external-skills setting at that overlay. Keep a requested compatibility/alias key only if the caller explicitly requires it, but verify discovery through the recognized live setting.
5. Use a fresh `hermes skills list --source local --enabled-only` process with a wide terminal width before reporting success; table truncation can hide an otherwise discoverable full skill name.
6. Report the clone path, pre-existing source, active recognized source, and exact verified skill IDs. Never put tokens or other secrets in config, overlay files, or handoff text.

This is an operator-side preservation technique, not a reason to discard existing external skill sources.

## Hosted synthetic canary scheduling

When a real-provider acceptance flow is intentionally moved outside release CI/CD, keep it as a machine-local, alert-only watchdog:

1. Merge and deploy the cleanup capability before the first live canary; never run the production canary from an unmerged branch.
2. Run one controlled canary manually after deployment and verify every bounded stage, including central cleanup, local membership cleanup, and denial of the prior session.
3. Inspect the deployed destination's actual service unit and binary path before trusting canary defaults. Environment-specific unit names can make an otherwise healthy cleanup command fail; use an explicit reviewed override immediately, then schedule a follow-up to make the configuration discovered or deployment-configured.
4. Schedule a script-only daily job with overlap protection, explicit `HOME`, canonical checkout, silence on success, and bounded failure output. It must not trigger releases, retries, tags, GitHub mutations, or email replies.
5. Treat scheduler creation as transport evidence only; verify the manual canary's output independently and distinguish an asynchronously triggered watchdog run from a completed watchdog result.

## Scheduled automation acceptance

When dogfooding a recurring Haft cron or autonomous pipeline, distinguish scheduler completion from operational success.

- Re-read the live outcome the job owns after every manual verification run. Examples: Ready depth, active ticket-bound workers, current PR checks, mailbox query evidence, and exact board transitions.
- A scheduler result of `ok` is transport/execution evidence only. Do not call the workflow healthy when its postcondition remains false, such as `Ready = 0` after a runway-curation pass.
- Encode a measurable postcondition in the cron prompt. If the target cannot be reached, require a named current blocker for each deficit instead of nominal success.
- When a capability is available through an installed CLI but may not appear as a dynamically loaded tool, put the bounded read-only command directly in the prompt and require the job to execute it before claiming the capability is unavailable.
- For mailbox-triggered CI automation, keep ingestion read-only, treat notification mail as discovery only, and reconcile every alert against live GitHub state before dispatching work.
- Split frequent jobs by ownership so they cannot race: implementation-pool continuity, PR/CI reconciliation, runway curation, and human briefing should have explicit non-overlapping mutation boundaries.

See `references/autonomous-pipeline-postcondition-verification.md` for the verification and failure-classification pattern.

## Friction-log entry shape

Keep entries short and evidence-based:

```markdown
- **YYYY-MM-DD — short label:** observed behavior.
  - **Impact:** concrete operator/user cost.
  - **Improvement:** scoped product or workflow change.
  - **Evidence:** bounded path, command phase, or user-visible result; no secrets.
```

Never record credentials, raw grants, private document bodies, or speculative root causes.

## Bug-report workflow from video evidence

When JP attaches a screen recording of a UI bug:

1. Copy the attachment to a path without spaces (`find ... -exec cp {} /tmp/name.mov \;`) — `video_analyze` and shell `cp` both choke on raw desktop-attachment filenames with spaces and special characters.
2. Run `video_analyze` on the clean copy. Ask for step-by-step UI narration: what the user does, what the tree/pane shows after each action, and exact error text.
3. Trace the server-side code path from the route handler through the mutation and reconciliation layers. Use `search_files` for the route verb/path, then `read_file` on the handler.
4. Identify the root cause before filing. The ticket body must name the exact function and line range, explain the mechanism, and propose a fix direction with alternatives.
5. File with highest priority when the bug creates garbage state requiring manual cleanup.

Known defect class to watch for: mutation routes that correctly update the artifact registry then call `reconcileMutation`, which re-diffs the filesystem and backfills a duplicate artifact record. The explorer projection renders both rows; the stale row's preview fails. The fix pattern is to skip full reconciliation after a successful registry mutation and call `refreshVaultExplorerProjectionBestEffort` directly.

## Kanban duplicate-ownership reconciliation

When one live Haft incident has accidentally produced overlapping Ready cards:

1. Inspect both full card bodies, comments, and live `status`; do not treat a historical blocker comment as current state.
2. Select one canonical owner only when its scope, evidence boundary, and acceptance contract fully subsume the other card.
3. Add reciprocal provenance comments naming the canonical card before changing state.
4. Retire the duplicate to a terminal non-claimable state. A dependency-style block without an actual unfinished parent can be recomputed and promoted back to Ready, so it is not a safe supersession mechanism.
5. Re-list the Ready column and verify exactly one claimable owner remains. Preserve the duplicate's incident evidence; do not merge it into the canonical card by deleting history.

## Grid placeholders after the rendition-contract repair is deployed

When a Grid shows generic placeholders for image-named artifacts even though a known Grid rendition-projection repair is already in the deployed build:

1. Verify the deployed hostname's health/build identity and compare it with the merged PR that added `thumbnail`, `renditions`, `optimizedPreview`, or `poster` to the bounded Grid DTO. A current build containing that repair rules out treating the incident as the earlier response-shape omission.
2. Preserve the private `folder-grid` route. An unauthenticated `403 route.gate-denied` proves only that the route is correctly protected; it is not evidence of missing renditions and must not prompt an auth relaxation.
3. Trace the client selector: an image with `localBackingPresent: false` intentionally receives no local asset URL. If it has no fresh verified thumbnail, optimized preview, or permitted remote original, `previewHref`/tile URL is absent and the icon placeholder is the designed safe fallback.
4. Classify the remaining boundary as rendition lifecycle/data until an authorized bounded audit disproves it: record aggregate counts for eligible images, local-backed versus remote-only, rendition presence/state, and derivative-request state/error-code buckets. Do not put artifact URLs, source paths, grants, or document bodies in the ticket.
5. For historic remote-only artifacts, trace artifact reconciliation/backfill, destination request reconciliation, HQ entitlement/claim admission, and verified `artifact_renditions` projection. Require an idempotent repair/backfill plus a regression proving a verified rendition reaches the Grid; retain the deliberate placeholder for an artifact with no verified usable source.

This distinguishes a presentational DTO regression from a missing asynchronous data lifecycle and prevents unsafe synthesis of local URLs for remote-only assets.

## Ticket threshold

File a ready, worker-claimable Haft card when all are true:

- the behavior was reproduced or directly observed;
- it blocks, delays, or materially degrades a normal agent/user workflow; and
- a concrete acceptance contract can be stated.

For external-worker cards, use the approved ready-worktree helper so the ticket has `assignee=null`, repo-root worktree metadata, and a neutral branch name. Verify it after creation.

### Hosted-auth E2E incident intake

For a hosted invitation or OTP flow that delivers successfully but fails during browser verification:

1. Separate proved facts by boundary: invitation acceptance, message delivery, central/API-only verification, and hosted-browser verification are distinct facts. Do not treat success in one boundary as proof of another.
2. Before creating a new card, search the live board and recent merged/released auth work for the same route and error class. If a prior repair addressed a different symptom (for example a local-session transport failure), name the distinction so the new card does not reopen or duplicate it.
3. Record only requested, non-secret correlation facts: release/build identity, request IDs, timestamps, response class, and a bounded challenge prefix when available. Never include secret authentication material in the card, fixtures, logs, PR text, or comments.
4. State the likely fault boundary as a hypothesis, not a finding. Require trace comparison across destination relay and central service using privacy-safe correlation data, and enumerate stale browser state/origin/relay-context preservation as checks rather than assumed causes.
5. Preserve production safety in the card: no live grant/account changes, mail/provider changes, configuration edits, relaxed origin/cookie/CSRF protections, or production-only fallback.
6. Require a deterministic regression proving the whole hosted path: accepted invite → fresh destination OTP challenge → same challenge verified through the browser relay → browser session established → protected destination route opens. Keep stale/mismatched challenge rejection and prior degraded-local-session behavior covered separately.

## Browser / UI AgentSession architecture

When dogfooding or reasoning about the Reader UI annotation pipeline, browser-initiated session creation, or runner-attachment design, load `references/browser-ui-annotation-architecture.md`. It covers the full annotation flow (iframe bridge → postMessage → target envelope → feedback endpoint), the server-ready but UI-missing session-creation path, and the auto-dispatch vs. manual-runner-poll design tradeoff.

## Persisting a new report or authored HTML artifact

When JP asks to persist a newly authored report, plan, or other text-only HTML artifact to a Dev Haft instance:

1. Create a valid `haft-html-profile-v0` document with a stable page ID, descriptive title, private visibility, `script-policy=none`, and at least one block and section marker.
2. Import through the installed Haft CLI using the explicit target and clone-safe duplicate behavior:
   ```bash
   HOME=<dev-host-home> <local-bin>/haft import /abs/report.html --remote dev --on-duplicate clone --wait --json
   ```
3. Capture the returned page ID, slug, content hash, indexed status, and Reader URL.
4. Verify the downstream product seam with an exact-title query rather than stopping at the import receipt:
   ```bash
   HOME=<dev-host-home> <local-bin>/haft query --title "<exact title>" --exact-title --require-one --remote dev --json
   ```
5. Return the canonical Reader URL. Browser visual verification is useful when an authenticated browser session exists, but a secure-login screen must not invalidate a successful CLI import plus exact-title/index verification; report that limitation as bounded friction instead.

Do not use AgentSession for a brand-new artifact unless the user specifically asks for an existing-document draft/review/Apply lifecycle. Do not claim success from a shell/app landing page alone; verify indexed identity and the canonical Reader route.

## Verification checklist

- [ ] The requested user artifact/action is completed before product-intake follow-up.
- [ ] Canonical Reader URL was verified and returned when a document was imported or edited.
- [ ] A friction line appears only if material friction occurred.
- [ ] Friction evidence is privacy-safe and bounded.
- [ ] Any ticket has reproducible evidence and acceptance criteria.
- [ ] Existing-document changes were draft-reviewed and explicitly applied.
