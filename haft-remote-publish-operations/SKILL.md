---
name: haft-remote-publish-operations
description: "Diagnose and operate Haft remote publishing flows: right-panel publish failures, publish_remote_package, remote counterpart publishing, target readiness, audit/bookkeeping compatibility, and bounded diagnostics."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, remote-publish, diagnostics, r2, publish-audit, ui]
    related_skills: [haft-agent-api, haft-vault-operations, haft-pr-reconciliation]
---

# Haft Remote Publish Operations

## When to use

Use this skill when working on Haft remote publish behavior, especially:

- right-side reader panel publish errors
- `POST /api/agent/publish_remote_package`
- `POST /api/agent/publish_remote_counterpart`
- owner-local R2/S3 target readiness
- Haft-managed publish entitlement/namespace behavior
- publish audit/catalog/bookkeeping failures
- UI diagnostics for publish failures

## Configuration control surfaces

Do not conflate a workstation’s registered Haft remote with the publishing target stored by that destination vault.

- Local CLI registration (`haft remote add/status/remove`, `haft remotes list`) manages destination discovery and transport metadata on the workstation.
- Managed enrollment/pairing establishes destination identity and claims.
- Owner-local R2/S3 configuration belongs to the destination vault and is exposed through authenticated Settings plus `GET/POST/PATCH /api/app/remote-publish-target`.

Before claiming that a remote publish target can be configured from the CLI, inspect the installed `haft --help` and `haft remote --help`. Do not invent a `configure` command or assume that an instance/service bearer is authorized for the `admin-write` app route. An unauthenticated `403 route.gate-denied` proves the route is protected, not that it is missing or unconfigured. Keep provider credentials out of literal command arguments.

The detailed capability-check and answer pattern lives in the companion `haft-cli-auth-and-remotes` reference `references/remote-registry-vs-publish-target-configuration.md`.

## Standard diagnostic workflow

1. Start from the user-visible route or slug and resolve it through the reader API to get the current `pageId`.
2. Check remote target status and whether the UI is using owner-local or Haft-managed mode.
   - Run `haft remote publish-target show <slug> --json` before attributing a constructed `media.*` URL’s Cloudflare 404 to bucket ACLs or unlisted/public visibility. `configured: false` means no destination storage target exists to receive the object; the 404 is then expected and does **not** prove public access is disabled. Configure or repair the target, perform one real counterpart publish, and verify its returned URL before changing bucket-public settings.
   - Treat **remote discovery** and **vault auto-publish policy** as separate facts. A `haft remotes list` entry only proves a known destination; it does not prove that the destination verifier is ready, that the vault selected a target, or that auto-publish is enabled.
   - For a slow media grid, first run the bounded read-only audit on the exact vault/path: `haft thumbnails audit --path <scope> --vault <vault-root> --json`. Report aggregate eligible/available/pending/failed/stale/missing counts and the readiness state. Do not infer an exact authenticated-destination count from a similarly named local vault.
   - `Local only` cards without a verified-thumbnail indicator are evidence that visible grid tiles fall back to originals, not proof that remote publishing is configured. Compare the grid's catalog-artifact count with the audit's eligible-image count rather than assuming they must match.
   - For an authenticated, central-discovered destination, run `haft remote publish-target show <slug> --json`. This is the bounded source of truth for configured/not-configured state, target mode, bucket/endpoint/public base URL, and credential *presence*; it must never expose credential values.
   - Do not misclassify `haft remote status <slug>` returning `403` when it explicitly says it checked public `/api/app/status` **without destination credentials**. That result establishes only public-route reachability; interpret the CLI's separate HQ-projected readiness field and use the grant-backed publish-target show for configuration evidence.
3. Reproduce the exact route call against `/api/agent/publish_remote_package` or `/api/agent/publish_remote_counterpart`.
4. Run the same request as `dryRun: true`.
   - If dry-run succeeds but live publish fails, the page/target/request shape is probably valid; focus on storage adapter, verification, audit, catalog, or publish bookkeeping.
5. Inspect the bounded route diagnostic, but do not trust `remote-publish.request-invalid` blindly. Confirm whether the Zod failure came from request parsing or from an internal helper after parsing.
6. If needed, call the server helper directly with a no-op storage adapter to expose internal exceptions without uploading.
7. When filing a Kanban bug, include: page slug, page id, target mode, route response, dry-run result, internal stack/function chain if available, and redaction constraints.

## Universal raw mirrors vs. HTML page packages

When a user says “publish any file to R2/S3,” treat that as a **remote counterpart** request, not necessarily static-site publication.

Haft has two deliberately different execution paths:

- `POST /api/agent/publish_remote_counterpart` mirrors the original bytes of a permitted user-owned vault file. Its `vault-file` subject is the correct path for Markdown, text, images, video, audio, PDFs, and other inert files. It must retain containment, hidden-state exclusion, regular-file, size, deterministic-key, redacted-credential, and hash-verification controls.
- `POST /api/agent/publish_remote_package` produces a derived multi-file static page package. It invokes static export and therefore correctly requires a validated HTML profile page; it is not a generic file-upload route.

Do not tell a user to convert Markdown to Haft-profile HTML merely to obtain an R2 mirror. Preserve the original source as canonical and choose the raw counterpart path. Validated HTML pages may still use the package path because their shareable result can include generated HTML, referenced assets, CSS, manifests, and link rewriting.

### Diagnostic signature: ordinary document sent to page-package route

If an imported Markdown/document artifact produces `Only validated HTML profile artifacts can be published.` from `publish_remote_package`:

1. Verify the artifact/page source kind and MIME in the catalog or authenticated reader projection.
2. Check whether the UI maps every non-asset “page” to `publishPagePackage(...)` instead of choosing by publish semantics.
3. Inspect `publish_remote_counterpart` for a `vault-file` subject. It may already provide the raw-byte backend capability even when the UI does not route document artifacts to it.
4. Reconcile adjacent seams before describing the fix as complete: counterpart status and default/auto-publish queues may have started asset-only even though the counterpart contract permits `vault-file`.
5. File the product fix as a universal remote-mirror routing problem: raw files → `vault-file` counterpart; validated HTML profile pages → derived package. Do not hide the Publish control as the durable solution.

Public/unlisted intent remains an explicit owner choice; it is not a reason to reject an otherwise permitted Markdown or media mirror.

See `references/universal-remote-counterpart-vs-page-package.md` for the repository evidence and implementation checklist.

## Pitfalls

### Status reads must degrade safely; mutation and execution must remain fail-closed

If a destination's `GET /api/app/remote-publish-target` returns a private-state safety error such as `private-json.directory-mode` while no target is configured, do not treat it as a publish-provider failure or retry it from every reader selection.

1. Reproduce the exact user-named destination URL first. Do not substitute a similarly named environment (for example, BBT and Dev are separate runtime targets).
2. Trace whether the status projection directly calls the private JSON reader without handling `PrivateJsonStoreError`.
3. For the **read-only status projection only**, map a private-store read failure to the normal redacted `configured: false` response so the UI can render setup-required state and cache the successful response.
4. Do **not** apply that fallback to target saves, policy writes, or publish execution. Those operations must retain the private-store failure and fail closed.
5. Add both a configuration-level regression and an app-route/browser-contract regression, then verify that the shared readiness resource retains the successful unconfigured snapshot across selection mounts.

This preserves the security invariant while preventing missing-target or unsafe-private-state conditions from becoming repeated Reader 500s.

### Managed remote discovery can fail before publish, and the failure mode matters

For Epic 20 / Haft-managed remote flows, do not jump straight to import or publish debugging. First prove which layer is failing:

1. **Public HQ route presence**
   - `GET https://<hq-hosted-origin>/api/v1/health` should return the bounded HQ health payload.
   - `GET https://<hq-hosted-origin>/api/v1/remote-targets` should exist on current prod. For an unauthenticated caller, an auth-shaped denial such as `401 invalid-central-session` is expected.
   - A raw public `404 NOT_FOUND` on `/api/v1/remote-targets` indicates production drift or a route not mounted in the live HQ runtime, not a CLI/local-vault problem.

2. **CLI central auth**
   - `haft whoami --json` must show a valid central session.
   - If login works but discovery still yields no targets, auth is no longer the primary blocker.

3. **Managed target discovery**
   - `haft remotes list --json` returning `cli-remote.central-no-targets` means HQ did not project any entitled targets for the authenticated account.
   - If the destination machine is locally claimed (`haft doctor --json` shows active `serverClaim` and `vaultClaim`) but HQ still returns zero targets, treat that as an HQ entitlement / target-projection / claim-metadata mismatch, not a deploy drift issue.

4. **Only after discovery succeeds**
   - proceed to remote readiness/import/publish debugging.

See `references/managed-remote-discovery-triage.md` for the concrete verification sequence and evidence pattern.

### A configured target can still fail because the browser publish call bypasses CSRF attachment

If target reads succeed but the publish write returns `403 auth.csrf.required`, inspect whether the panel used raw `fetch(...)` instead of the shared CSRF-aware client. Treat this as a browser request-construction and error-classification bug; do not tell the user to reconfigure R2/S3. See `references/remote-publish-csrf-client-bypass.md`.

### Deployment drift can preserve a misleading publish error after the source fix exists

Before opening a new UI/configuration bug, establish the **deployed** release identity as well as source behavior.

1. Resolve the live instance from current DNS/public-IP or infrastructure inventory; do not rely on historical instance IDs after a migration.
2. Run a read-only, redacted target check on that instance: config exists and parses, credential fields are present, policy-file presence, and service state. Never return credential values.
3. Collect a bounded recent journal **code count** for `auth.csrf.required`, `remote-publish.*`, and `haft-publish.*`; this is safer and more useful than dumping logs.
4. Compare the deployed binary's embedded version/commit with the source commit that contains the intended error projection.

If the target is valid and a current `auth.csrf.required` appears while the deployed binary predates the CSRF recovery/error-copy fix, classify the immediate work as **deployment drift**, not a missing target setup. Tell the user that the target is configured and recommend a reload/sign-in retry as a temporary recovery; the durable remedy is deploying the release that classifies the session error correctly. Add this evidence to an existing deploy-repair card when one exists rather than creating a duplicate product-code card.

For owner-local policy, an absent policy file defaults to `autoPublishMode: disabled` and `remoteMediaMode: local-first`. That disables automatic mirroring; it does not by itself invalidate a configured manual-publish target.

### `request-invalid` can mask internal publish bookkeeping failures

A right-panel error with HTTP 400 and `remote-publish.request-invalid` does not always mean the browser request is malformed. In one live failure, dry-run publish succeeded and the actual fault was a private publish-audit compatibility parse error from legacy `hypervault-publish-audit-v0` records after the Haft rename.

Before telling the user the request is invalid, distinguish:

- **Request schema failure**: route input fails `remotePublishPackageRouteInputSchema` before target resolution.
- **Internal bookkeeping failure**: publish/audit/catalog helpers throw a `ZodError` after request parsing.

Internal bookkeeping failures should be fixed or surfaced as bounded catalog/audit/internal diagnostics, not reported as user request-invalid.

See `references/remote-publish-request-invalid-diagnostics.md` for the concrete repro pattern.

## Redaction rules

Remote-publish diagnostics must not expose raw private audit bodies, local filesystem paths, credentials, provider internals, full object keys, namespace IDs, vault hashes, raw payment payloads, or other private state in browser-visible UI, screenshots, audit summaries, or Kanban handoffs.

## Provider target replacement (R2/S3)

When replacing a broken BYO storage target, preserve the old target until the replacement has passed a real publish and public-URL verification. A valid Haft target record only proves its configuration parses; it does not prove the provider credential can write objects.

1. Prefer the privileged managed CLI seam, not the Haft browser UI:
   - `haft remote publish-target show <slug> --json`
   - `haft remote publish-target set <slug> ... --access-key-env <name> --secret-key-env <name>`
2. Preflight the cloud-provider control-plane credential separately before creating a bucket, custom-domain binding, or R2/S3 access key. If authentication fails, stop before changing the Haft target; stale credential retries cannot repair provider-side access.
3. For a dedicated environment prefix, verify URL construction from the source contract: Haft publishes `publicBaseUrl + "/" + objectKey`, and `keyPrefix` is already part of `objectKey`. Therefore use root `publicBaseUrl` plus `keyPrefix=dev` to produce `https://media.example.com/dev/...`; do not put `dev` in both fields.
4. Save replacement credentials through environment-variable references only. Never place cloud secrets in CLI arguments, logs, Kanban comments, or documentation.
5. Read the saved target back with the CLI, then perform a real publish and verify its returned public URL. Only then retire or delete the old provider resource.

For Cloudflare R2 specifically, do not diagnose an account-level token using user-token endpoints. Verify it at `/accounts/<account>/tokens/verify`, and use short-lived provisioning credentials separately from durable publish credentials. For custom domains, `POST /accounts/<account>/r2/buckets/<bucket>/domains/custom` **attaches** a new domain (with `domain` and `zoneId`); `PUT .../domains/custom/<domain>` only updates an existing attachment and may return `404` / `10053` before attachment even when the zone is active. Verify zone presence directly before attributing a 10053 to cross-account ownership.

### R2 token propagation and UI freshness

A newly created bucket-scoped Cloudflare Account API token can return `Unauthorized` to its first signed R2 S3 request before propagation completes. Do not reject the documented `id` + `sha256(value)` credential derivation or revoke it after one immediate probe. Poll a bounded signed `ListObjects` or harmless object operation every five seconds for up to roughly two minutes. Retain a durable target credential only after that probe succeeds; revoke diagnostic tokens afterward. This is a propagation check, not a reason to broaden permissions.

After configuring a target out of band through the CLI/API, browser panels can retain stale target/readiness state. Refresh before treating an inline `not configured` report as a server configuration failure. Independently verify the destination target through the CLI or authenticated app status before changing credentials again.

A target set/readback is configuration evidence only. Before retiring the prior target, prove the newly derived S3 credential with a signed write and public URL read; if it fails, preserve the evidence and do not report repair complete. See `references/byo-r2-target-replacement.md`, `references/cloudflare-r2-account-token-and-custom-domain.md`, and `references/cloudflare-r2-byo-target-api-runbook.md` for reusable provider/CLI sequences and redaction rules.

## Existing-artifact media resolution and bounded manual publish

When asked to publish one existing media artifact by durable handle, treat the operation as a two-phase workflow: resolve and verify the source first; only then execute one bounded publish.

1. Resolve the exact artifact ID/handle through the authenticated remote catalog. `haft query` and `haft get` are document-oriented and may legitimately return no media match; do not substitute a browser hash URL or construct a guessed public source URL.
2. If the remote CLI cannot resolve the media handle, inspect the live destination runtime's active vault read-only. Derive the vault root from the service unit/environment and query the exact artifact row. Do not assume a catalog schema: inspect `PRAGMA table_info(artifacts)` before selecting optional fields.
3. Establish the source location from the row before reading bytes. Record only the exact artifact's `storage_state`, `source_ref`, `logical_path`, `source_url`, `remote_backing_url`, MIME, and catalog hash. A `local-only` row with no source URL/backing URL requires locating exactly one matching file under the active vault; do not search or copy a wildcard set.
4. Verify the unique file's MIME, byte count, and SHA-256 against the catalog before any upload. A bounded temporary staging copy is acceptable only when the supported authenticated publisher cannot read the destination-local source directly; remove it after verification.
5. Prefer the catalog-preserving remote counterpart route with the original source artifact handle/provenance. Do not use `haft import --publish` for this case if it would create a duplicate catalog artifact. Do not mutate the catalog just to make the bytes publishable.
6. Probe the exact route/auth boundary once. A local unauthenticated request returning `route.gate-denied`, or a public-runtime classification that disables `/api/agent/publish_remote_counterpart`, is an authorization/runtime blocker—not evidence that the file is missing. Stop rather than bypassing the gate or reading/exposing credentials.
7. If publication succeeds, verify the returned destination object/artifact ID, canonical public URL, HTTP status, MIME, size/hash, source provenance, idempotency result, storage state, and provider readability. If it cannot be invoked safely, report the exact catalog row, verified source bytes, route/status blocker, and explicitly state that no destination object was created.

See `references/existing-artifact-media-publish.md` for the reusable preflight and evidence schema.

## Direct service-host R2 publication when the app route/CLI is unavailable

For a single explicitly authorized artifact, if the public counterpart route is blocked and the deployed service bundle does not expose the repository adapter or a usable CLI upload command, a bounded direct provider upload is an acceptable fallback only when the user explicitly authorizes it.

1. Resolve the active service vault and read the exact owner-local target configuration from `.haft/private/remote-publish-target.json`; never print credential values.
2. Validate target identity, kind, bucket, endpoint, public base, and key prefix against the requested target before reading the source bytes.
3. Verify the exact source file's byte count and SHA-256 against the catalog before any PUT. Do not use a wildcard or a guessed URL.
4. Use a deterministic full object key including the configured prefix (for example `dev/references/<filename>`), and make the key the idempotency boundary.
5. Perform a signed HEAD first. If the object exists, replay only when size, content type, Haft hash metadata, and source-artifact-handle metadata match; abort on any mismatch rather than overwriting an unknown object.
6. For a new object, issue one bounded SigV4 PUT with `Content-Type`, `x-amz-meta-haft-sha256`, `x-amz-meta-source-artifact-handle`, and a deterministic idempotency metadata value. Keep credentials process-local and remove any temporary uploader script in a trap/finally path.
7. Verify with a signed provider HEAD and an unauthenticated external/public HEAD. Report host-local/public discrepancies separately; a service-host 403 does not override an independently verified external 200.
8. A direct S3/R2 object PUT does not create a Haft catalog artifact or counterpart row. Report the object key/ETag as the destination identity and explicitly state that no catalog destination ID exists unless a catalog-preserving route was used.

Do not change service permissions, install packages, restart services, write the original into the local vault, or treat a direct object PUT as equivalent to catalog-preserving publish. If the target config cannot be read safely or signed HEAD/PUT cannot be performed, stop with the exact blocker.

## Verification expectations

For a remote-publish fix, prefer focused tests first, then broader checks as appropriate:

```bash
bun test ./tests/remote-publish-package.test.ts
bun test ./tests/remote-publish-target-ui.test.ts
bun run typecheck
bun run build
```

Add regression coverage for both the server route behavior and the UI diagnostic projection when the bug affects the right-side panel.
