---
name: remote-media-artifact-operations
description: "Use for remote Haft media artifact publishing."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, remote, media, artifact, publish, ingest, r2]
    related_skills: [haft-remote-media-operations, haft-remote-publish-operations]
---

# Remote Media Artifact Operations

Use this class-level skill when a user asks to publish, mirror, or register an existing media artifact on a remote Haft target, especially when the source is already cataloged and the user wants a remote-only result without writing original bytes into the local vault.

## Core distinction

Remote capability, route availability, and input compatibility are separate facts:

1. The remote may advertise `automation.media.ingest` and `artifact.publish`.
2. The media-ingest route may accept only caller-owned `contentBase64` or a `remote-only` asset containing `sourceUrl`, size, SHA-256, filename, and MIME.
3. A counterpart-publish route may accept an asset/vault-file subject, but still resolve and read a local vault path.
4. A browser artifact handle such as `artifact-...` may not be accepted by either route.

Never infer that a capability advertisement means an existing catalog artifact handle can be published.

## Required workflow

1. Verify the installed CLI version and inspect the current command/API help before mutating anything.
2. Verify the intended remote is authenticated, ready, and advertises the required operation. Keep credential values redacted.
3. Resolve the supplied artifact handle through an authenticated catalog/read surface. Distinguish a browser SPA route (`https://host/#/artifact/...`) from a durable CLI/API handle.
4. Inspect the actual input contract for the supported media-ingest and counterpart-publish routes. Check whether it accepts:
   - an existing artifact ID/handle;
   - a remote source URL plus metadata;
   - caller-owned bytes; or
   - a local vault path.
5. If the route does not accept the supplied artifact handle, stop. Do not guess a source URL from the browser route, filename, object key, public media host, or artifact ID. Report the exact contract mismatch.
6. Do not substitute a local download/re-import when the user requires a remote-only/catalog-preserving operation. That changes provenance and violates the requested storage semantics.
7. If a compatible operation exists, use one idempotency key and preserve provenance fields: source artifact handle, original filename, and destination remote slug. Mutate only the explicitly authorized artifact.

## Verification after a successful operation

Verify all of these separately:

- HTTP response status and bounded operation result;
- destination catalog artifact row and destination artifact ID/handle;
- `storage_state=remote-only` when supported;
- canonical `source_url` or public media URL;
- MIME, size, and hash where available;
- source/original filename and provenance metadata;
- no original bytes were written into the local vault;
- public URL returns the expected HTTP status and content type;
- browser visibility is checked separately from catalog existence.

A successful catalog write does not prove the current browser tree or Recently Imported projection will show a catalog-only remote-only artifact. Report that as a separate surface result.

## Safe blocker report

When no compatible handle-based operation exists, report:

- remote readiness and advertised capabilities;
- the exact accepted input shapes discovered;
- why the supplied artifact handle cannot be passed safely;
- that no mutation was performed;
- that no URL was guessed and no local original was written; and
- the smallest product seam needed: an artifact-handle-to-remote-counterpart/media-ingest operation that reads the existing catalog source, preserves provenance, verifies the remote object, and updates the destination catalog without materializing original bytes locally.

Do not report a public URL, destination ID, or catalog state change unless the operation and postconditions were actually verified.

## Security and provenance boundaries

- Never print provider credentials, service tokens, signed URLs, raw private source URLs, cookies, or private media bytes.
- Do not use a central session token as a destination instance credential.
- Do not broaden grants or change publish-target configuration to compensate for an input-contract mismatch.
- Do not create unrelated tickets, modify source files, or alter other assets when the user authorizes one media operation only.

## Known route-shape pattern

The normalized automation media-ingest contract commonly looks like:

- `asset.storageMode=local` with filename, MIME, and base64 bytes; or
- `asset.storageMode=remote-only` with filename, MIME, source URL, size, SHA-256, and bounded metadata.

A remote counterpart contract may use `subject.kind=asset` or `vault-file`, but if its implementation reads a local absolute vault file before uploading, it is not a valid remote-only path for a catalog-only source. Treat this as an honest capability gap rather than bypassing it with a guessed URL.

See `references/catalog-handle-publish-contract.md` for concrete route-shape evidence and the safe stop condition.

## Relationship to other skills

This skill complements, and partially overlaps with the protected/external Haft skills `haft-remote-media-operations` and `haft-remote-publish-operations`. Those skills remain the more detailed source for their respective workflows; this profile-owned skill captures the cross-route artifact-handle compatibility check and the fail-closed reporting pattern.
