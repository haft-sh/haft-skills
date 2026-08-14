---
name: deployed-media-pipeline-debugging
description: Use for missing thumbnails or renditions.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [media, thumbnails, renditions, distributed-systems, production-debugging, canary]
    related_skills: [software-development-lifecycle, systematic-debugging, haft-remote-media-operations]
---

# Deployed Media-Pipeline Debugging

## Overview

Use this skill for missing thumbnails, previews, optimized images, video derivatives, or other generated media where the path crosses a destination app, a central service, a worker, a storage layer, and a viewer. The goal is to prove the failing boundary and restore visible output without confusing stale request history, scheduled work, and completed durable renditions.

## Core rule

Trace the complete data path before changing the UI or broadening access:

`viewer -> destination catalog -> request queue -> central entitlement/credential policy -> source acquisition -> generation job -> durable rendition -> URL/media serving -> viewer`

A green CLI envelope or accepted queue request is not proof of successful processing.

## Workflow

### 1. Establish the visible failure

- Determine whether the UI has no rendition metadata/URL or whether it requests a URL that fails.
- Capture a bounded runtime/build fingerprint for the deployed target.
- Check browser/network behavior only after proving the backend has a candidate rendition.

### 2. Reconcile destination and central state separately

At the destination, aggregate by artifact/request state, last error, retry time, and rendition rows. At the central service, aggregate live request/job states and failure codes from the active production store. Never treat a historical destination error as proof that a newly repaired central path is still failing.

If production uses a remote central store such as libSQL/Turso, do not inspect only a local SQLite fallback. Verify which store the running service and operator actually use.

### 3. Validate policy and runtime configuration

Check, in order:

- exact account/team-scoped entitlement;
- instance credential scope and target binding;
- canonical source HTTPS origin and redirect origins;
- configured source-origin allowlist;
- DNS resolution and public-address policy;
- pinned TLS/SNI fetch behavior;
- source response status, size, and MIME;
- the running process environment after restart.

Failure names can be broader than their label. For example, `source-origin-denied` can mean an empty/mismatched allowlist, non-public DNS, an unapproved redirect, pinned TLS/socket failure, or a non-2xx source response.

### 4. Use a bounded canary

- Reconcile sanitized destination and central identity sets first; choose the canary from their proven intersection rather than from a destination-only/latest row.
- Run a read-only dry run with explicit path scope and a small artifact limit.
- Freeze or cancel historical claimable work before starting a newly installed consumer, so startup cannot become an implicit backlog release.
- Apply only the exact fresh confirmation token, with explicit chunk and rate limits.
- Treat “applied” as scheduled work, not success.
- Poll central jobs and destination reconciliation independently; check for delayed submission before issuing another apply when a poll window expires.
- Require successful central jobs, durable rendition rows, HTTP-200 rendition URLs, and visible viewer output before expanding scope.

For stale/source-expired identity drift, delivery-method discrepancies, bounded one-row recovery gates, and backend-versus-visible acceptance, follow `references/bounded-stale-canary-recovery.md`.

For origin policy repairs, add only exact canonical HTTPS origins discovered from the active source set. Preserve an environment backup. Never use wildcard origins.

### 5. Check retry eligibility

When a backfill operator claims to requeue failed work, inspect both sides:

- Does the operator transition `failed` to a claimable state such as `pending`?
- Does the worker claim predicate include the resulting state and honor `next_retry_at`?

Updating only `next_retry_at` while leaving `state='failed'` is a no-op if the reconciler excludes failed rows. The durable code fix should make the explicit backfill transition claimable and add a regression test; manual catalog repair is only a bounded operational recovery.

### 6. Deploy or recover a missing worker safely

Before enabling a newly installed worker:

- prove the live API host and compare API/worker database-secret fingerprints without printing values;
- require a separately issued, revocable worker database token—never clone the API application's token as a fallback;
- verify the deployment artifact contains the worker entrypoint, or compile a standalone artifact from the exact deployed commit and verify its checksum;
- inspect claimable queue depth and staged-source expiry so startup cannot become an accidental bulk backfill;
- treat an expired staged source as non-resumable even if its request still says `queued`;
- require codec verification plus an explicit worker-ready event before submitting a canary.

For compiled Bun workers, do not copy generic systemd hardening blindly: Bun/JSC needs executable memory, the valid executable condition is `ConditionFileIsExecutable=`, and a localhost deny may need an explicit loopback DNS-stub allowance. Retain all other compatible sandbox controls and verify the final unit. Validate a dedicated worker database credential with a read-only client probe and fingerprint comparison before installation; transfer it through an approved secret store or envelope-encrypted host channel, and keep service activation as a separately verified step.

See `references/compiled-bun-media-worker-production-preflight.md` for the validated credential-separation, encrypted-transfer, SSM/Bash execution, cleanup, preflight, systemd, and stale-identity guards. For the complete credential-rotation recipe—including shell-file parsing, canonical no-newline fingerprinting, envelope encryption for long tokens, standalone updater scripts, and cleanup readback—follow `references/worker-database-credential-rotation.md`.

#### Credential fingerprint and SSM serialization pitfalls

- Hash the exact secret bytes on both sides. `printf %s "$token" | sha256sum` is canonical; extracting a line with `sed` and piping it directly to `sha256sum` hashes the trailing newline and can falsely suggest that two equal tokens differ.
- Direct RSA encryption is unsuitable for long database tokens. Use a random symmetric key for the payload and RSA-OAEP/SHA-256 only for that small key.
- `AWS-RunShellScript` commonly starts `/bin/sh`; explicitly invoke a prepared payload under Bash when using `pipefail` or other Bash features. Avoid Python heredocs embedded in semicolon-joined commands—transfer a standalone updater script instead and verify no environment mutation occurred before retrying a failed installer.

### 7. Verify the final projection

After generation succeeds, verify all of:

- central job/request success;
- source and rendition records persisted;
- destination rendition records and URLs populated;
- rendition URL returns the expected HTTP status/content type using the actual viewer request shape; a failing Range probe does not override a successful full image GET;
- GLY/Grid or equivalent viewer requests and renders the rendition.

Treat these as separate acceptance boundaries and report them separately:

1. generation completed;
2. durable rendition exists;
3. public/media URL serves it;
4. destination projection exposes usable rendition metadata to the caller;
5. the authenticated viewer renders the real thumbnail.

A successful worker, durable PNG/WebP objects, or HTTP-200 rendition URLs is not proof of visible Grid acceptance. After a release or auth/projection fix, rerun the narrowest authorized visible-Grid check against the new build and inspect both the bounded folder/catalog response and the rendered tile. If the response omits rendition fields, classify the boundary as projection or authorization before changing media generation.

If viewer authentication or managed-member projection blocks the final render while backend evidence passes, preserve the auth boundary, report visible acceptance as blocked, and route that regression to a separate auth owner rather than weakening access controls. Do not use a successful backend canary to close the UI acceptance gap.

Use the support references `references/deployed-media-pipeline-debugging.md` for the detailed evidence matrix and redacted probe patterns, and `references/bounded-stale-canary-recovery.md` for drift/retry recovery.

Use the support references `references/deployed-media-pipeline-debugging.md` for the detailed evidence matrix and redacted probe patterns, and `references/bounded-stale-canary-recovery.md` for drift/retry recovery.

## Safety and reporting

- Keep credentials, signed URLs, source paths, private document bodies, IDs, and tokens out of logs and handoffs.
- Report facts separately from hypotheses.
- Preserve backups before direct catalog repair.
- Do not claim a fix from a service restart, an operator `ok`, or a scheduled count alone.
- If a canary remains unresolved, report the exact next observable boundary rather than presenting an unverified workflow as successful.
