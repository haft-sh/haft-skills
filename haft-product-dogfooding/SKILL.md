---
name: haft-product-dogfooding
description: "Use when dogfooding Haft as a product: importing/viewing artifacts, interpreting failures as product-boundary issues, and filing worker-ready tickets instead of normalizing user pain away."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, dogfooding, imports, product-boundaries, kanban]
    related_skills: [haft-vault-operations, kanban-orchestrator-operations]
---

# Haft Product Dogfooding

## Use when

Use this skill when operating Haft as a user would, especially while:

- importing or dropping HTML/Markdown/media into a Haft vault,
- opening artifacts in the Haft shell, reader, or rendered view,
- diagnosing artifact-view failures discovered during dogfooding,
- deciding whether to workaround locally or file a product bug,
- writing Kanban tickets from dogfood observations.

## Core stance

Haft is a local-first artifact system. When dogfooding, judge failures from the user's product expectation first, not from the implementation's current internal contract.

Do **not** require the user to understand internal Haft profile details such as:

- `hv:*` metadata,
- `data-hv-block-id`,
- `section[data-hv-section]`,
- `hv:script-policy`,
- catalog/manifest implementation details.

Those may be valid internal normalization targets, but they are not user-side prerequisites.

## Reader media-loading diagnosis

When a user reports a blank Reader image stage, spinner, or inaccurate-looking progress bar, separate **derivative selection** from **client presentation** before deciding that thumbnail generation failed.

1. Identify the exact artifact path from the report or screenshot and run the destination's scoped thumbnail audit. Record eligibility plus available/pending/failed/stale state and remote readiness for that one asset.
2. Trace the Reader's initial-preview resolver and deployment identity. Establish whether `thumbnail-first-when-available` selected the fresh thumbnail or fell back to the original.
3. Independently trace the browser component from resolved URL to painted pixels. Flag manual `fetch` + full response buffering + `Blob`/object-URL conversion + `hidden`-until-`onLoad` as a rendering gate: it prevents normal browser progressive image manifestation even when the selected URL is a thumbnail.
4. Do not infer thumbnail usage from a successful audit alone, and do not blame the thumbnail pipeline merely because a spinner is visible. State both conclusions separately: *what URL/source policy selected* and *what the browser is allowed to paint while it loads*.

For the progressive-reader remediation, preserve thumbnail-first initial preview and explicit full-original modal behavior unless the user explicitly changes that product contract. Prefer a native `<img src>` of the resolved initial URL with an unobtrusive visual transition that does not suppress browser rendering. Do not keep a byte/progress estimate when the browser does not have trustworthy total-size metadata. Require a slow-network browser regression proving a preview element is visible/paint-eligible before completion, plus fallback/error, reduced-motion, accessibility, and modal-original coverage.

## CLI reading pitfall: `haft get` positional arg is a slug

The positional argument to `haft get` expects a **slug**, not a page ID:

- `haft get page-2026-07-25-daily-notes --remote dev` → HTTP 404
- `haft get 2026-07-25-daily-notes --remote dev` → success
- `haft get --page page-2026-07-25-daily-notes --remote dev` → success (explicit flag)

When you have a page ID from `haft query --json` results, use `--page <id>` or strip the `page-` prefix to get the slug. Do not burn a round trip on a 404 before realizing the distinction.

## Operating pattern

1. Reproduce or inspect the user-visible failure.
2. **Board dedup first.** Before proposing fixes or filing new tickets, search ALL board statuses (todo, ready, blocked, triage, review, running) for existing coverage of the reported symptom. JP explicitly requires this: "make sure that this isn't a known bug that's already reflected in the existing Kanban tickets." Use `kanban_list` with each status filter. If an existing card covers the root cause, report it with its current status and PR link instead of filing a duplicate. A bug that is already in review with an open PR is further along than a new todo card.
3. Identify whether the operation used a product path or a raw developer shortcut.
3. If a raw shortcut was used, prefer re-running through the supported product import/API path before judging behavior.
4. If the product path still requires internal-format knowledge, treat that as a product bug.
5. If a temporary unblock is needed, label it explicitly as a workaround and avoid presenting it as the correct durable behavior.
6. When a user reports a reproducible dogfood failure and asks for investigation, treat a worker-ready Kanban ticket as part of the default deliverable unless they explicitly request diagnosis only. Do not stop after explaining the root cause.
7. File the ticket with concrete reproduction, product expectation, live request/error evidence, likely code areas, acceptance criteria, and a genuinely claimable Ready worktree shape. Attach supplied screenshots as real Kanban attachments rather than leaving only a transient chat-cache path in prose. Use `kanban_attach` directly for local chat-cache images; do not pass a localhost URL to `kanban_attach_url` because internal-address SSRF protection rejects it. If base64 transport would truncate the attachment payload, create a clearly named, legible downscaled evidence copy for the card and retain the original only as transient source material.

### Approval and Kanban semantics

A Kanban card is executable work, not a duplicate approval request. When the user explicitly authorizes an operational action in conversation, treat that authorization as sufficient for the scoped action and proceed through the safe product/operator path.

- Do not create a card titled or blocked as “approval required” merely to restate an approval the user already gave.
- External-worker implementation cards must be genuinely claimable: unassigned, Ready, worktree-backed, and scoped to work the worker can perform.
- For a production operator action, create an execution record only when it carries a runnable procedure and an owner. State the actual remaining gate (for example, a fresh dry-run result), not approval itself as the work.
- If a newly observed prerequisite prevents an already authorized action, create a narrowly scoped executable remediation card; do not turn the original request into another abstract approval loop.
- A merged or deployed implementation does not close a historic-data incident without the separately required live backfill/canary evidence.

**Screenshot analysis efficiency:** full-resolution screenshots (≈600 KB+) can make `vision_analyze` time out, costing a diagnostic round-trip. Before analyzing, downscale to a legible copy (e.g. `python3 -c "from PIL import Image; im=Image.open(src); im.thumbnail((1600,1600)); im.save(dst)"`) and pass the smaller file. This keeps the symptom details (cropped band, blur, layout proportions) readable while avoiding payload timeouts.

## Important lessons

### Remote overwrite is not an AgentSession edit

When a user asks to test or perform a natural-language edit of an existing remote document, establish the mutation semantics before acting.

A remote CLI import such as:

```bash
HOME=<dev-host-home> haft import /absolute/path/to/document.md \
  --remote dev --target-folder <folder> \
  --on-duplicate overwrite --force --wait --json
```

is a **direct canonical replacement**. Use it only with explicit overwrite authorization and a known complete replacement file. It does not itself provide remote-source materialization, draft revision conflict detection, diff/preview review, or an explicit apply boundary.

Do not describe that path as an AgentSession workflow. Before claiming a remote-session dogfood pass, inspect the installed `haft agent-session --help` and verify the entire chain exists: destination-session start/attach, exact session-scoped authorization, one-document draft materialization, revision-checked draft writes, diff/preview, and explicit apply. If those capabilities are not available through the selected product surface, use overwrite only as an explicitly labeled fallback and report the missing session lifecycle/transport capability as a product gap.

For a successful overwrite, retain the returned `batchId`, `jobId`, `vaultPath`, `sha256`, `collision`, `duplicateAction`, and `indexed` facts. **Verify the receipt against the requested target:** `vaultPath` must equal the requested logical path and `collision` must be `overwritten` (or `new` when no prior target existed). If a response claims overwrite but returns a suffixed sibling or a renamed/clone collision, classify it as a product-contract defect; do not tell the user an in-place edit succeeded. Never auto-delete the sibling—inspect identities, hashes, and a bounded diff first. For a true session edit, retain the session ID, draft revision, review evidence, apply outcome, and any conflict/recovery state.

If a vault explorer shows two highlighted rows after a primary click, do not normalize it as intended multi-select. A plain click must select one exact row; first distinguish active/current styling from selected-for-batch styling, then check catalog identity reconciliation. Require a regression that uses sibling duplicate-like names and proves the final target, receipt, and single-row click state agree.

See `references/remote-overwrite-receipt-integrity.md` for the evidence checklist and regression shape.

### Recovering paired design evidence from a vault asset

When a user gives an asset path and asks for the accompanying design report, search the active vault root directly — particularly `content/` and `assets/` — using the asset’s exact basename and topic stem. Verify a candidate by reading its relative asset reference, then use the vault manifest’s page/asset linkage when available. A public `<dev-hosted-origin>` authorization denial is not evidence that the local vault lacks the document.

During the Hypervault → Haft transition, search `~/.haft/vaults/...` first. Treat an identical `~/.hypervault/vaults/...` copy as legacy corroboration, not the path to hand off. If the exact companion is Markdown rather than HTML, state that distinction explicitly and identify a broader HTML audit separately; never present a merely related audit as the exact paired document.

- Generic HTML import should normalize toward the Haft HTML profile; users should not author Haft-profile HTML by hand.
- When the artifact must carry generated mockups or supplied images through a remote import, import the image assets to a stable vault path first and reference same-origin vault-asset URLs from a compact HTML profile document. Do not assume base64 `data:` image URIs are accepted by the remote normalizer; retain the document/asset receipts and query-derived Reader URL. See `references/remote-visual-html-imports.md`.
- A rendered-view failure caused by missing profile metadata/block IDs is usually an import/sanitization/normalization gap, not a user error.

### "Preview unavailable" for a local-only artifact after deletion

When a user deletes a file but it remains in the vault tree showing "Preview unavailable — No browser-usable remote backing URL," trace the failure through three layers before concluding it is a new bug:

1. **Catalog state:** check whether the artifact-registry row still shows `storage_state=local-only` with `removed_at=NULL` while the reader `pages` row is gone. This is the "ghost artifact" pattern — incremental reconciliation retired the page but not the artifact row.
2. **Viewer routing:** `DocumentCanvas.tsx` routes `artifact-id` routes with `pageResponse === undefined` into `RemoteArtifactPreview`. The `localContentBacking` guard only covers loading/error sub-states, not the terminal "no page, no asset, local-only" case. A local-only artifact with no reader page silently falls through to the remote preview component, which produces the misleading "no remote backing URL" message.
3. **Known coverage:** this root cause is tracked by `t_ecd49e78` (incremental removals leave active ghost artifacts, PR #1344). The viewer-routing UX gap (conflating deleted-local and remote-only fallbacks) is tracked by `t_7f994f5f`.

Do not file a new ticket for the ghost-artifact root cause while PR #1344 is in flight. The viewer-routing UX follow-up is a separate, narrower card.

See `references/preview-unavailable-ghost-artifact-trace.md` for the full code-path trace.

### Readable artifact marked `missing` but blocked from organization

When a Vault Browser row displays the yellow `FileQuestion` storage icon, inspect the current UI mapping before inferring corruption: it represents `storageState: "missing"`, not an unknown document type. A document can still preview through a retained catalog, rendered, or remote representation while lacking the local backing required for mutations such as move, rename, or AgentSession attachment.

For a report of “preview works but Move fails”:

1. Preserve the exact artifact. Do not retry a destructive import, direct catalog edit, or guessed file placement.
2. Trace the Explorer mutation route and its structured error mapping. `vault_artifact.missing` is the expected local-backing failure class; a bounded read-only `agent-session start` returning `agent_session.artifact_not_local` corroborates the same eligibility boundary. Do not run a turn or Apply merely to inspect it.
3. Treat a readable-but-unmovable artifact as a product-contract gap, not user error. A safe repair must either reconcile/materialize a verified recoverable backing before allowing mutation, or retain fail-closed behavior and show an actionable recovery state *before* drag/drop or Move.
4. File the generalized regression with controlled recoverable and irrecoverable fixtures. Require preview-plus-move consistency, correct revision/index updates after a recoverable move, no duplicate/suffixed sibling, and preserved auth/CSRF/path-collision/compensation safeguards.
5. Attach the reported screenshot to the Haft Kanban card as durable evidence; include the artifact route and bounded error code, but never document bodies or credentials.

### Additive app-status fields and stale browser bundles

When a hosted Dev instance shows a generic unavailable screen with a strict-decoder error such as `Unrecognized key(s) in object: 'semanticSearch'`, do not treat it as an OTP, claim, or server-health failure.

1. Read the exact error field and distinguish app-shell response-contract failure from auth/claim failure.
2. Verify the public layers separately: `/health` build identity, `/api/auth/status` claim state, and anonymous `/api/app/status` route-gate behavior. A healthy claimed auth status plus an expected anonymous 403 does not contradict the browser error.
3. Compare the current deployed HTML/bundle with the server response contract. An older immutable browser bundle can reject a supported additive field after a server rollout.
4. Reproduce with a hard refresh or fresh tab as a diagnostic, not as the durable fix. If that clears the error, record stale-client confirmation and pursue bounded compatibility negotiation/release verification rather than re-bootstrap or repeated OTP retries.
5. Deduplicate against the live Kanban board. If an implementation/review card already owns the additive-field compatibility fix, update it with live evidence and user confirmation; do not file a second bug. Add a dependency-gated post-merge deployment/browser-verification card when that release gate is missing.

Require the durable fix to preserve strict decoding for malformed values and unrelated unknown fields, avoid infinite reload loops, preserve auth/route gates, and verify both retained stale tabs and fresh tabs after deployment. The compact probe and evidence checklist lives in `references/stale-browser-additive-response-fields.md`.

### Expanded auth-bootstrap responses and retained strict bundles

When first navigation shows `App API response contract failed at auth` with additive authenticated fields rejected, but Refresh loads normally, trace `GET /api/auth/session/bootstrap` separately from `/api/auth/status` and `/api/app/status`. A previously shipped compatibility projection on one endpoint does not protect another boot-critical endpoint whose success shape later expands.

Reproduce the exact issue path and rejected keys by running the historical strict bootstrap decoder against a privacy-safe fixture matching the current success shape. If it matches, classify the incident as mixed-version wire skew rather than an OTP, claim, or availability failure. Prefer explicit endpoint contract negotiation: current bundles send a version header; header absence receives a narrowly projected historical shape only after the full current response validates. A client-only reload cannot repair already-retained legacy code. Preserve same-origin, session, CSRF, managed-member repair, authorization, route-gate, and strict malformed/unknown-field rejection.

Require a retained historical-tab canary and a fresh current-tab canary after deployment. Separate the implementation card from a dependency-gated post-merge release/browser-verification card when deployment proof is not in the implementation scope. See `references/stale-auth-bootstrap-response-fields.md` for the evidence sequence, repair contract, and regression matrix.

### Authenticated UI mutations failing CSRF after reload or a fresh tab

When a signed-in user can read the shell but an in-app write returns `auth.csrf.required`, distinguish a correct server-side denial from a broken client-session bootstrap. Trace the mutation route, shared fetch helper, normal shell boot, and login/OTP response separately: a CSRF token captured only at login will be absent in a fresh tab or after `sessionStorage` clears even though the cookie session remains valid. Preserve fail-closed CSRF enforcement; file or implement a bounded same-origin bootstrap/refresh path with regressions for existing-cookie + empty client-CSRF storage → boot → authenticated write. See `references/browser-session-csrf-write-failures.md`.

**Multipart-import pitfall:** boot-time CSRF restoration alone does not protect browser imports if a component sends `FormData` through raw `fetch()`. Inspect every import writer—file/PDF media, document upload, pasted source, and browser-fetched remote content—and route same-origin cookie-authenticated multipart writes through a common CSRF-aware transport. It must preserve `FormData`, attach the current token, and make at most one bounded bootstrap/retry after `403 auth.csrf.required`; never exempt import routes or weaken server validation. Regression evidence must cover an existing authenticated cookie with cleared session storage, PDF import success, and browser readability of the returned asset.
- Prefer product APIs/routes for dogfooding. Direct vault file placement is acceptable only when explicitly preserving an authored/publish-ready artifact byte-for-byte or when clearly labeled as a fallback.
- When an artifact is meant to render visually, verify the rendered/preview surface, not only index presence or reader-shell HTTP 200.
- For public/dev auth dogfooding, separate the proxy boundary from the Haft app principal boundary. A raw `route.gate-denied` / “authorized principal required” screen is safe but product-hostile; prefer filing or implementing an app-owned onboarding/login flow rather than treating SSM/SSH bootstrap-token generation as the product answer.
- When implementing that flow, preserve structured HTTP error metadata in the web client, project `403` + `route.gate-denied` into an `auth-required` boot gate, fetch `/api/auth/status`, then offer central OTP before retrying the original app route. See `references/public-dev-auth-onboarding-dogfood.md`.
- When filing **design-audit or mockup** tickets for external Codex/DevSpace workers, do not assume Hermes-native skill names are visible in that lane. Check the Codex skill library and cite the exact Codex skill names in the card or an immediate follow-up comment when the lane matters. On this host, the design-handoff pattern is documented in `references/codex-design-audit-handoff.md`.

### Grid media previews missing while Viewer opens the same artifact

When a user reports generic icons or blank image tiles in Grid but double-clicking opens the artifact correctly, trace the **bounded Grid response contract** before blaming thumbnail generation or Viewer routing:

1. Capture the exact folder/Grid hash route and attach the screenshot to the Kanban card.
2. Trace the artifact-node projection, the bounded `/api/vault/folder-grid` mapper, its response schema, the client query type/adapter, and the tile URL selector together. Compare fields at each boundary rather than assuming a declared schema field is actually emitted.
3. Verify that `thumbnail`, `renditions`, `optimizedPreview`, and `poster` survive the mapper. Optional schema-supported rendition fields can be silently omitted while the full-tree or artifact-detail path still exposes them.
4. Distinguish failures: no Grid preview URL produces an icon; a derivative URL that fails to load needs a separate bounded client fallback. Do not infer an HQ derivative-generation outage from the Grid symptom alone.
5. File the ticket around the contract: route-level response-shape coverage, client projection from the bounded query shape (not a hand-built full tree), correct image/video/document treatment, bounded derivative-load fallback, and authenticated deployed visual proof. Preserve response-size bounds, private-route auth, freshness/hash checks, and no-retry-loop behavior.

This regression is especially likely after managed media moves from legacy thumbnail records to rendition records: Grid may retain only the legacy field even though Viewer works through a richer detail projection.

### Deployed rendition repair versus historic-media recovery

A merged and deployed Grid/rendition repair does **not** prove existing remote-only media now has thumbnails. Separate these stages:

1. Verify the target health has the expected embedded release commit and that it contains the repair.
2. Read the source-card/PR handoff for an explicit production backfill or canary boundary. If implementation deliberately made no production mutation, do not close the incident from deployment evidence alone.
3. With explicit authorization, run a bounded **dry run first** on the active destination vault under the running service's user/config context. A root/SSM CLI invocation may resolve a different home and no active vault.
4. Treat Grid placeholders as expected until fresh verified thumbnail/optimized-preview rendition records exist. Do not synthesize a local URL or relax remote-original/freshness rules for catalog-only artifacts.
5. Stop before Apply when denied, stale, unsupported, or unexpected aggregate buckets appear. Treat confirmation tokens as sensitive operational material: use only for the immediately authorized canary, and never put them in a card, comment, or final report.
6. Diagnose nonzero `denied` with a second read-only aggregate grouped by request state and sanitized error code. Distinguish least-privilege credential/claim denial from retryable rate-limit or transport pauses; repair the narrow authority path rather than substituting a broad admin, publish, or agent grant.
7. Only after a clean new dry run should an explicitly authorized rate-limited canary run. Poll reconciliation status and confirm a sampled authorized Grid response contains fresh rendition data before expanding.

**Operator-output pitfall:** backfill result fields may mix artifact counts (`scanned`, `actionable`) with rendition-profile counts (`current`, `denied`). Do not compare their sums or interpret profile totals as artifacts. Require clearly labeled artifact and profile summaries plus bounded error-code buckets in future CLI/operator contracts.

### Derived-projection outages and browser retry storms

When a browser-facing Haft route returns a bounded `503` because a disposable derived projection/index is unavailable, treat **operator recovery** and **client resilience** as separate deliverables:

1. Rebuild the authoritative vault index through the destination's approved operator path, then verify the derived store has an active generation and the service remains healthy.
2. Do not claim an anonymous public probe verifies an authenticated Explorer route: public-mode route gates can correctly return `403`. State the proof boundary; when browser authorization is unavailable, report the on-host projection and health facts precisely.
3. If the UI immediately repeats a failed request or can render-loop/crash, file a worker-ready client remediation card. Require bounded/cancellable retries, no immediate retry storm, a recoverable UI state, and a client-level 503 regression test for the actual boot query.
4. Trace the triggering UI hook before writing the card; distinguish the route's server contract from the browser effect/callback that schedules the request.

A repaired derived index restores availability but does not make an unbounded client retry loop acceptable.

## Resurfacing and held-feature diagnosis

When a user says a merged feature produced no visible UI change, distinguish these facts before treating any performance plan as the fix:

1. **Implementation:** inspect the merged browser components and determine the exact visibility rule: route, mode, feature flag, or authorization state.
2. **Release posture:** read current dogfood/release evidence for an explicit default-off or hold decision; a merged UI may intentionally be invisible.
3. **Actual hot path:** trace the failed gate to the code that performs the measured work. Do not assume a broad Reader/Explorer performance plan resolves a Capture Inbox, search, or AgentSession bottleneck merely because all are performance work.
4. **Independent prerequisites:** enumerate benchmark, rollout-control, and deployed-human-evidence gates separately. Reuse an active live-evidence card when its acceptance criteria cover the prerequisite; do not file duplicate dogfood work.

For a feature held because one shared presentation flag controls both a passing surface and a failing optional surface, treat **rollout-control separation** as an independent remediation. It may make the passing experience independently releasable, but it must not silently enable it or weaken route/privacy policy. Keep the final default-enable decision behind fresh deployed evidence.

### Promoting a foundational Inbox surface out of a feature flag

Do not conflate a base product-surface gate with optional contextual rollouts layered on top of it. For Capture Inbox specifically, reconcile all three before proposing a change:

1. **Base Inbox visibility:** whether normal Inbox navigation/capture/review is hidden behind a client build/env/local-storage flag.
2. **Authorized availability:** whether the existing private capability/access response permits that surface for the current vault and principal.
3. **Optional consumption surfaces:** Recent/Revisit and Related captures can have separate rollout/default decisions; do not enable an explicitly held optional surface merely because the base Inbox is becoming normal behavior.

If the user says the foundational surface should not be behind a flag, remove the client visibility gate rather than only setting a deployment flag to true. The normal visibility contract should be **usable vault + authorized available capability**. Preserve server authorization, private-route boundaries, CSRF, size/type limits, and reviewed promotion. Keep a regression that unavailable/unauthorized capability does not advertise Inbox.

For deployed proof, compare Dev and Gly browser bundle identity/build metadata, but do not infer runtime `import.meta.env` values merely from a matching bundle: a bundle can retain dynamic environment reads. Require a clean-browser-profile dogfood pass after the merged release on each target—Inbox navigation and Capture control visible without local storage, harmless fixture captured and reviewed, and already-default contextual focus modes checked. A merged PR is implementation evidence, not this deployed proof.

When filing the remediation backlog, create: (a) a plan/reconciliation card if the bounded data model is not yet reviewed, (b) a dependency-gated implementation card, and (c) a release-evidence/default-decision successor. Keep only genuinely independent planning or flag-separation work in Ready.

## Daily Notes convention

Daily notes are recurring HTML documents imported to Dev under `daily-notes/`:

- **Filename:** `YYYY-MM-DD-daily-notes.html` (e.g. `2026-07-28-daily-notes.html`)
- **Target folder:** `daily-notes`
- **Title:** `Daily Notes — YYYY-MM-DD`
- **Sections:** Today's priority · Friction log · End-of-day carry-forward
- **Import:** `HOME=<dev-host-home> haft import /tmp/<file>.html --remote dev --target-folder daily-notes --wait --json`

Use `templates/daily-note.html` as the plain starter — replace `{{DATE}}` with the ISO date. For a designed note whose CSS must survive import, use `templates/daily-note-styled.html` (the JP design system: evergreen/marigold on warm paper, date masthead, priority banner, checklist, meetings, agent grid) — it carries a valid `haft-html-profile-v0` profile so styling is preserved byte-for-byte. Set its `haft:slug` to the target page's slug for in-place replacement.

### Editing an existing daily note

Do not treat AgentSession setup/doctor readiness as proof that a managed remote edit can mutate a draft. Before relying on `turn --runner hermes`, verify the actual session outcome: the turn must report an accepted draft mutation, and `status`/`diff` must show a changed draft. If setup and doctor pass but the turn returns no draft mutation or a failed/no-op result, classify that as an integration/runtime semantic failure for this operation; preserve the canonical document, do not claim the edit succeeded, and do not reconstruct the full remote source from an indexed text projection for overwrite. Capture the session ID, bounded CLI result, and destination Reader URL, then use an independently verified supported write path or surface the blocker for repair.

A previously observed setup-state failure is not a permanent product rule: rerun the current setup/doctor preflight and trust the live turn plus draft evidence. The import lane remains a fallback only when the caller explicitly authorizes a complete replacement and the full source is available and verified.

**Preferred path — profile-preserved in-place replacement (no duplicate):** author the note as valid `haft-html-profile-v0` HTML whose `haft:slug` meta matches the existing page's slug, then import with `--on-duplicate clone`:

```bash
HOME=<dev-host-home> haft import /tmp/<file>.html --remote dev --on-duplicate clone --wait --json
```

Because the document carries a valid profile, the normalizer preserves it byte-for-byte (styling survives), and the matching `haft:slug` makes Haft place the new content at the canonical slug while **renaming the original to a hash-suffixed backup** (e.g. `2026-07-25-daily-notes-6c280b2cc541`). Result: the styled version owns the clean URL, the original is preserved as a backup, no `-2` duplicate. Verify by comparing the local file's sha256 to the import result's `sha256` field (a match = styling survived). See `references/profile-preserved-html-authoring.md` for the required meta/structure and `templates/daily-note-styled.html` for a ready design.

**Fallback path — plain HTML (creates a root duplicate):** if the note has no profile, re-importing without `--target-folder` lands a new page at vault root rather than updating in place. Report the duplicate transparently. This is the inferior path; prefer the profile-preserved one.

### Pitfall: import normalizer strips styling without a valid profile

Haft's import normalizer rebuilds any HTML lacking a valid `haft-html-profile-v0` profile down to plain text blocks — it drops `<style>`, `<head>`, and structure, keeping only extracted text. This is why an authored/styled daily note renders as bare text in the reader. To keep CSS, the upload must carry the full profile (required `haft:*` meta, ≥1 `data-haft-block-id`, ≥1 `<section data-haft-section>`), no unsafe content, and system fonts only (external `<link>` fonts are rejected; `link`/`script`/media refs must point under `assets/`). Full constraints: `references/profile-preserved-html-authoring.md`.

### Pitfall: `--on-duplicate overwrite` returns 409

`--on-duplicate overwrite --force` returns HTTP 409 `automation.import.commit-failed: Exact overwrite artifact identity does not match the requested path` in two cases:

1. The original was imported with `--target-folder <folder>` (folder prefix not carried into the identity check).
2. The target is **profile-preserved** HTML (the profile-preserved import changes the artifact's stored `logicalPath`/`sourceRef` so the guard at `exact-document-replacement.ts:416` fails).

Overwrite works only for plain normalized documents. For styled/profiled updates use `--on-duplicate clone` with a matching `haft:slug` (above). `haft move` is also denied on the managed remote (403 `vault_batch_move.authorization_denied`), so there is no rename/consolidate path until the repair lands. Tracked: `t_ba24be48` (runner + target-folder overwrite) and `t_4e4c3a7e` (profile-preserved overwrite 409, move 403, daily-notes discoverability).

## Search UX diagnosis and ticket intake

When dogfooding a search report involving spaces, punctuation, or multi-word input, do not infer a backend defect from a no-results screenshot alone. Trace the complete contract in this order:

1. Inspect the input component and query-normalization helper. Confirm whether meaningful internal separators survive; distinguish trimming/collapse from deletion.
2. Inspect the controller/search callback and capture the actual request payload. A visible field, normalized controller state, and network `query` can diverge.
3. Inspect the server query builder and index tokenizer. Verify whether whitespace-separated terms are intentionally ANDed, phrase-matched, or discarded, and preserve the existing authorization/bounded-query contract.
4. Compare deployed bundle behavior with the current source when the checked-in path already appears correct. Treat local unit tests as source-contract evidence, not deployed proof.
5. File the ticket around the unresolved boundary, with acceptance criteria requiring browser-visible value, request payload, and rendered result coverage. Add backend coverage only if the request arrives intact and matching is the failing boundary.

For screenshot-backed tickets, never say an image is durably attached merely because a chat-cache path exists. If the attachment API requires inline bytes and the upload is not verified through `kanban_attachments`, state the evidence limitation in a reconciliation comment and remove or qualify “attached” wording in the card body. See `references/search-input-boundary-diagnosis.md` for the compact trace and regression checklist.

### Social sharing preview asset workflow

When a user asks to replace a website social thumbnail with an existing private Dev Haft artifact:

1. Resolve the exact artifact row read-only from the authenticated Dev runtime; never use the private browser hash URL as a public `og:image`.
2. Verify the source `storage_state`, `source_ref`, MIME, dimensions, byte count, and SHA-256. Preserve the artifact handle as provenance.
3. Transfer only the exact verified bytes through a bounded, fail-closed staging path when the service host cannot be read directly. Remove temporary transfer scripts/artifacts after reconstruction; do not mutate the source catalog.
4. Add the image as a versioned immutable public landing asset, register it in the asset response map, and update only `og:image`/`twitter:image` unless the user explicitly requests hero-image replacement.
5. Add tests for the landing HTML metadata and asset route, then run focused tests, typecheck, build, `git diff --check`, and a source-hash verification.
6. Work in an isolated worktree and open a PR; do not deploy directly unless deployment is explicitly authorized. Report that the live preview remains unchanged until merge/deploy.

This workflow keeps private artifact URLs out of social metadata while preserving exact source provenance and making crawler access independently verifiable.

## References

- `references/generic-html-import-normalization.md`` — dogfood failure pattern and ticket criteria for arbitrary standalone HTML import normalization.
- `references/profile-preserved-html-authoring.md` — the `haft-html-profile-v0` meta/structure required for an authored HTML doc to survive import with styling intact, plus the slug-driven in-place replacement technique.
- `references/public-dev-auth-onboarding-dogfood.md` — public dev auth/onboarding investigation pattern: proxy gate vs app principal gate, central OTP/claim expectation, and bounded evidence rules.
- `references/codex-design-audit-handoff.md` — lane-specific handoff pattern for design-audit/mockup tickets assigned to external Codex workers.
