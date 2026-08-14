---
name: hypervault-dogfooding-workflows
description: Use when agents are operating Hypervault itself in a local/dogfood environment — importing notes, media, and HTML artifacts, verifying ingestion, and avoiding raw-vault shortcuts that bypass product behavior.
---

# Hypervault Dogfooding Workflows

## When to use

Use this skill when:
- storing notes, screenshots, audits, or other artifacts into a local Hypervault vault
- deciding between raw filesystem writes versus Hypervault import/upload routes
- verifying that Hypervault accepted and normalized content the way the product intends
- dogfooding operator workflows where the product itself should be the source of truth, not direct SQLite inspection or manual vault mutation

Do **not** use raw file copy as the default just because it is faster. For agentic workflows, the product path matters.

## Core rule

For **agentic ingestion of external or newly-created content**, prefer the **Hypervault import/upload endpoints** over direct writes into `content/` or `assets/`.

Default preference order:
1. Live Hypervault app/API route
2. Hypervault server/import handler invoked locally
3. Raw vault file placement only for recovery, debugging, or controlled admin backfill

Why:
- upload/import runs normalization and placement policy
- import captures provenance and metadata consistently
- product acceptance is stronger evidence than "file exists on disk"
- raw writes can bypass the HTML profile and produce misleading validation noise

## Pitfall: raw vault writes are not equivalent to import

Directly copying HTML into a vault and rebuilding the index is **not** the same as importing it through Hypervault.

Typical consequence:
- HTML that looks acceptable to a human can still trip profile diagnostics such as missing semantic sections or missing block IDs
- the page may be indexed, but that does not prove the product ingestion path is correct
- a narrow subtree refresh can make the file visible in the vault browser while the corresponding artifact-registry row is still missing, leading the reader UI to fail with `Artifact is unavailable` / `Reader API returned 500`
- even after reader/index state is repaired, the `Rendered` tab may still refuse the document with `Rendered view requires an HTML profile with scriptPolicy none.` because raw-written HTML is not automatically treated as a Hypervault HTML-profile artifact

If a newly visible HTML page crashes the reader with a backend error like `row.artifact_id`, treat that as an artifact-registry backfill problem first. Run a full `bun run index:rebuild -- <vault-root>` and re-check the reader routes before blaming the HTML body. Then separately check whether the page qualifies for Rendered-view projection; arbitrary HTML in `content/` is not enough by itself. See `references/raw-html-ingest-artifact-registry-pitfall.md` and `references/manual-html-rendered-view-and-registry-gap.md`.

Use raw writes only when you intentionally want a low-level storage operation rather than a product-level ingestion test.

## Standard workflow for HTML + screenshot notes

When creating an HTML note that includes screenshot evidence:

1. Prepare the screenshot as a real asset file.
2. Do **not** embed the screenshot as a `data:` URL by default.
3. Upload/import the screenshot through Hypervault media import first when possible.
4. Reference the screenshot from the HTML note via a real vault asset path.
5. Upload/import the HTML note through Hypervault's document import route.
6. Verify the resulting normalization/ingestion response and the resulting vault-relative path.

Rationale:
- `data:` embeddings are a poor default for Hypervault dogfooding because they bypass the product's asset handling model
- real asset paths better reflect how the product is meant to store and serve media-backed artifacts

## Verification guidance

Prefer verification in this order:

For remote-publish/storage questions, first check whether Hypervault already has a product surface for the capability before declaring it missing. In particular, verify:
- owner-local remote publish target config status,
- whether the config UI is actually rendered in the live app,
- whether the current publish path is page/package-oriented versus direct asset-only publish.

For target-setup questions, prefer the product API first:
- `GET /api/app/remote-publish-target` to confirm whether the active vault is already configured,
- `POST /api/app/remote-publish-target` to save the owner-local target programmatically,
- then report the vault-private persistence model truthfully: the target is intended as a one-time-per-vault setup unless later replaced.

If local vault persistence works but Hypervault-controlled remote publish is still awkward, say that precisely instead of reducing everything to a yes/no capability claim.

See `references/remote-publish-dogfood-gap.md` for the recurring pattern and planning guidance.
See `references/remote-publish-target-api-and-ui-pitfalls.md` for the owner-local setup API, persistence path, and the known contradictory-UI pitfall where asset publish can say `not configured yet` even though the target status route is already configured.
See `references/remote-publish-target-api.md` for the verified API contract, persistence path, and env-vs-owner-local precedence notes.

## Pitfall: 'persist this to R2' means vault-first, then Hypervault remote publish

When JP asks to persist an artifact and write it to R2 in a Hypervault/Haft dogfood session, the expected sequence is:

1. place the artifact in the active local vault first (normally the default vault under `~/.hypervault/vaults/default`),
2. confirm the app-level remote target with `GET /api/app/remote-publish-target`,
3. use the live local Hypervault API to remote-publish via the configured target (`/api/agent/publish_remote_package` for exported page/package artifacts, or `/api/agent/publish_remote_counterpart` for inert asset mirrors),
4. verify the remote publish result itself (`status: mirrored`, verification `ok: true`, and a direct fetch of the remote object URL),
5. return the verified URL from the configured remote target's `publicBaseUrl` / mirrored object path.

Do **not** substitute a public marketing/domain deployment path (for example `<hq-hosted-origin>`) for this workflow unless the user explicitly asked for a public-site deployment. A successful local static export or canonical URL guess is not the same thing as a Hypervault-controlled remote publish.

For page/package remote publish, remember that `/api/agent/publish_remote_package` expects a minimal `remoteTarget` object (`targetId`, `kind`, `displayName`, `bucket`, `publicBaseUrl`, optional `keyPrefix`) and does **not** accept extra config-only fields like `region`, `endpoint`, or top-level `canonicalBaseUrl`.

1. Import/upload API response
   - accepted path
   - normalization state
   - artifact class / classification
2. Product-visible file/path outcome
   - note exists under `content/...`
   - media exists under `assets/...`
3. Manifest/file-level confirmation
4. Raw SQLite inspection only when there is no better product/API surface

Do not reach for SQLite first if the product already exposes the fact you need.

## Dogfood review rule

When evaluating whether Hypervault "supports" a workflow, distinguish these carefully:
- **raw vault storage behavior**
- **index rebuild behavior**
- **true import/upload behavior**

Only the last one should drive product claims about agentic workflows.

## Port and runtime discipline

When talking to a live local Hypervault app, verify the actual running port/process instead of assuming the default dev port. A dogfood environment may be on a non-default port even when docs say `9001` is the nominal default.

## Good final phrasing

Prefer conclusions like:
- "Imported through Hypervault's own media/document routes and verified normalization state"
- "Stored via raw vault placement only; this verifies indexing, not full import behavior"

Avoid overclaiming from filesystem success alone.

## Minimal checklist

- [ ] Used Hypervault import route unless there was a deliberate reason not to
- [ ] Avoided `data:` image embedding as the default for screenshot-backed notes
- [ ] Verified product-visible ingestion result, not just disk presence
- [ ] Distinguished import-path behavior from raw storage/index behavior
- [ ] Avoided raw SQLite as the first verification surface when product/API evidence existed
