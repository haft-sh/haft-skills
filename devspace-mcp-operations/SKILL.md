---
name: devspace-mcp-operations
description: Operate and verify a self-hosted DevSpace MCP runtime, including native ChatGPT artifact handoff and safe workspace materialization.
version: 1.0.0
---

# DevSpace MCP Operations

## Use when

- Updating or deploying a self-hosted DevSpace MCP runtime.
- Debugging ChatGPT native generated/attached file handoff.
- Adding or reviewing artifact staging and workspace materialization behavior.
- Reconciling DevSpace pull-request review feedback with a live runtime.

## Native artifact workflow

Expose one intent-level tool by default:

```text
ChatGPT native file reference
  -> materialize_artifact
  -> explicit verified file in an already-open approved workspace
```

- `materialize_artifact` accepts the connector-authorized native object, existing workspace ID, **relative** destination, explicit conflict mode (`error`, `rename`, or `replace`), and optional expected SHA-256.
- The private store may remain a transitional server-side implementation detail: validate/stream/hash → stage internally → workspace materialize → delete internal record in `finally`.
- Return only relative workspace path, basename, MIME hint, size, SHA-256, conflict mode, and rename status. Never expose artifact IDs, host paths, signed URLs, native IDs, TTLs, pinning, or lifecycle controls.
- Do not substitute model-authored base64 or arbitrary shell downloads for a native MCP file value; do not make the user babysit browser materialization.

## Download-origin trust policy

Generated-file URLs are short-lived download origins; they are not the DevSpace storage destination.

1. Accept `files.oaiusercontent.com` plus the constrained regional OpenAI Blob-account family `oaisdmntpr<region>.blob.core.windows.net`, where `<region>` is lowercase alphanumeric.
2. Do **not** permit generic `*.blob.core.windows.net` or arbitrary Azure accounts.
3. Require HTTPS, reject credentials/non-default ports/fragments, and manually revalidate every redirect against the same policy.
4. Never expose signed URL paths/query strings, opaque native file IDs, or file bytes in logs, tool results, PR bodies, or tickets.

## Workspace-copy safety requirements

- Owner-scope artifact lookup before opening the source.
- Resolve destination through the existing workspace registry; preserve workspace-root containment.
- Reject path escapes, symlinked parents, symlinked destinations, and non-regular destinations for replacement.
- Write through a private no-follow temporary file; verify size and SHA-256 before promotion and after materialization.
- `error` preserves an existing entry; `rename` chooses an unused deterministic sibling; `replace` accepts only an existing regular non-symlink file and must retain/restore a temporary backup if post-placement validation fails.
- Clean internal staging in `finally`; cleanup failure must not change a successful materialization result.
- Cover single-tool registration and result redaction, internal-record cleanup, `error`, `rename`, `replace`, path escape, symlink-parent, and symlink-destination behavior in tests.

## PR-to-runtime deployment procedure

1. Inspect the current checkout, branch/commit, service unit, and latest PR inline comments before changing anything.
2. Turn the newly observed native reference or security condition into a failing focused test first.
3. Apply the minimal implementation and run focused tests, then canonical checks: `npm test`, typecheck, build, and `git diff --check`.
4. Review the full diff; commit and push the actual PR-head ref. Re-read the GitHub PR head SHA because it can lag immediately after a push.
5. Update the PR body and reply to active inline review threads with the resulting commit SHA. Treat historical/resolved bot comments as context, not new work.
6. Restart the systemd service only after the runtime checkout has built successfully. Verify the new PID/start time, an expected unauthenticated OAuth `401` from the public MCP endpoint, and compiled feature markers in `dist`.
7. A local unit/adapter smoke proves only the DevSpace side. Request or run a fresh ChatGPT connector canary in a new chat/reconnected connector before claiming native end-to-end success.

## Reporting

State separately:

- **Verified locally:** tests, typecheck/build, compiled markers, service health.
- **Verified externally:** an actual ChatGPT-generated/attached file staged and copied into a workspace.
- **Pending external action:** a new ChatGPT chat or connector refresh if the client caches old tool schemas.

## Reference

- `references/devspace-native-artifact-runtime.md` — host layout, validation probes, and review checklist.
- `references/version-and-auth-identity-probes.md` — version-scheme truth table (Haft tags vs DevSpace package vs MCP date-string protocol vs Codex CLI), auth-mode probes, and the honest-mismatch response pattern when a quoted version/key matches no live scheme.
