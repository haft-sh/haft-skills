---
name: haft-import-operations
description: Use when importing files into Haft or testing the CLI-managed remote import path; covers route selection, the shortest reliable dev-import workflow, verification, and managed-vs-manual failure classification.
version: 2.2.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, import, upload, multipart, media, documents, html]
    related_skills: [haft-vault-operations, software-development-lifecycle]
---

# Haft Import Operations

## Overview

Use this when the user already has content and wants it added to Haft, or when you need to test the product import path end to end.

This is the detailed import playbook. `haft-vault-operations` should route here once you know the task is actually an import problem, instead of repeating the import commands itself.

This skill covers two distinct operational lanes:
1. **local vault import** through Haft product routes
2. **remote destination import** through the installed `haft` CLI

Keep them separate. A successful local vault import does not prove the managed remote path works.

The routine remote-import default on this host is **import first**. An existing host wallet and central target are consumed by the import itself, so do not spend a round trip on auth or remote discovery before attempting a normal import:

```bash
# Ensure haft is in PATH
haft import /absolute/path/to/file.md --remote dev --wait --json
```

A successful result already returns the batch/job/path/hash facts needed to prove the write. Run `haft whoami --json` and `haft remotes list --json` only after an import failure, or when gathering formal managed-path/release evidence.

## When to Use

Use for:
- importing documents or assets into a local Haft vault
- deciding between document, media, browser, and exact-file placement paths
- testing CLI remote import dogfood on the dev destination
- teaching another agent the shortest reliable remote-import workflow on this host
- verifying whether a managed path failure is auth, discovery, status, or import related

Do not use for:
- broad product-surface routing before you know whether the task is import, artifact creation, or another Haft seam
- arbitrary server-side URL fetching
- direct canonical-checkout edits as a substitute for product behavior
- claiming remote-import success from login alone

## Route Selection

| Input | Preferred path |
|---|---|
| generic Markdown or HTML where normalization is acceptable | `POST /api/import/documents/upload` |
| authored/publish-ready Haft HTML that must remain byte-for-byte unchanged | place under `<vault-root>/content/` then rebuild index |
| image / PDF / audio / video / binary asset | `POST /api/import/media` |
| trusted remote HTML already fetched by the browser | `POST /api/import/remote-html/browser` |
| remote destination import to another Haft instance | installed `haft` CLI |

## Exact-file placement rule

For a finished Haft HTML artifact the user expects to preserve unchanged:
1. determine the active vault
2. place the file under `<vault-root>/content/`
3. rebuild the index
4. verify file size/hash and resulting page metadata

Do **not** push these through generic normalization if byte-for-byte preservation matters.

## Local Product Import Verification

After any local import:
1. verify the API response shape
2. record returned paths / identifiers
3. verify the index/reader sees the result
4. if user-visible, verify the frontend can open it

Do not stop at "upload returned 200".

## Installed CLI Remote Import Path

For host-level dogfooding, prefer the installed CLI:

```bash
# Ensure haft is in PATH
haft version --json
```

### Critical HOME distinction
In a Hermes profile session, the default `HOME` may be profile-scoped, for example:
- `<profile-home>`

But the real host/operator wallet may live under:
- `~/.haft`

When testing managed remote import, verify which home you are exercising.

### Fast path: single existing file → dev remote

Use this when the task is simply "import this file into dev." Start with the operation the user asked for; do not preflight an already-established wallet or target.

```bash
# Ensure haft is in PATH
FILE=/absolute/path/to/file.md
haft import "$FILE" --remote dev --wait --json
```

Why this is the current best default:
- Setting `HOME` to the operator user home uses the real host/operator wallet instead of the profile-scoped home.
- `haft import ... --wait --json` is the decisive proof because it exercises wallet lookup, target-bound grant exchange, destination verification, actual write, and indexing in one command.
- a successful JSON result contains the batch/job/path/hash facts; extra `whoami` or `remotes list` calls add no operational value.
- an absolute file path avoids cwd-dependent mistakes when other agents are dropped into different shells.

### Optional failure diagnostic: `remote status`

Use this only after an import failure when `whoami` and `remotes list` do not provide enough human-readable readiness/reachability explanation:

```bash
# Ensure haft is in PATH
haft remote status dev --json
```

Important interpretation:
- `remote status` is useful for readiness diagnosis.
- It is **not** stronger proof than a completed `haft import --remote dev --wait --json`.
- On this host, `remote status` may report public reachability as `403 failed` while separately showing HQ-projected delegated readiness as verified. That is not itself an import failure.

### Failure-first diagnostic path

Only enter this path after `haft import ... --remote dev --wait --json` fails. Keep the failed import output: it is the primary classifier. Then inspect the host wallet and central target:

```bash
# Ensure haft is in PATH
haft whoami --json
haft remotes list --json
```

Use this only if those results do not explain the failure and you need a human-readable readiness/reachability distinction:

```bash
haft remote status dev --json
```

Check profile-scoped `HOME` only when the worker may have used it accidentally; do not make it routine diagnostic ceremony. After repair, retry the original import command exactly once and report its JSON result.

## Managed path vs manual fallback

### Managed path (preferred)
For a normal established session, import first:
```bash
# Ensure haft is in PATH
haft import /absolute/path/to/file.md --remote dev --wait --json
```

If that command reports missing or expired credentials, authenticate or refresh, then retry the import directly. Run `haft whoami --json`, `haft remotes list --json`, or `haft remote status dev --json` only to classify a failed import or to collect formal managed-path evidence.

The normal path should **not** require `HAFT_DEV_REMOTE_TOKEN`.

### Manual fallback (explicit break-glass only)
Use only when central discovery / grant exchange is unavailable and the task explicitly accepts fallback semantics:
```bash
# Ensure haft is in PATH
haft remote add dev --url https://dev.haft.sh --token-env HAFT_DEV_REMOTE_TOKEN
haft remotes list --json
haft remote status dev --json
haft import /absolute/path/to/file.md --remote dev --wait --json
```

When using this path:
- say it is manual fallback, not managed-path proof
- do not print token values
- do not put token material in comments, docs, PRs, fixtures, or shell history

## Post–Epic 20 live blocker map

Use these to classify failures accurately.

### `cli-auth.missing-credentials`
Meaning:
- the CLI home being exercised has no wallet

Typical recovery:
- determine whether you are in profile-home or host-home context
- run `haft auth login`

### `invalid-central-session` / `cli-auth.refresh-expired`
Meaning:
- wallet exists, but the session/refresh material is stale

Typical recovery:
- complete a fresh login with OTP

### `cli-remote.central-discovery-unreachable`
Meaning:
- login may be valid, but HQ remote-target discovery failed before `dev` could be resolved
- debug this as discovery/transport/response parsing, not as a generic auth failure

Important:
- this is **not** the same as missing credentials
- this is **not** proof that `dev` is absent by entitlement
- discovery can fail even when `whoami` is healthy

### Public-route `403` after a healthy import
Meaning:
- you are probing a private/read-protected destination surface without destination credentials

Typical recovery:
- report the successful import separately from the unauthenticated reader/UI check
- use an authenticated destination lane if the user explicitly wants UI proof

## Verification for managed-path proof

A real managed-path success requires more than login. Prefer this evidence order:
1. `haft whoami --json` authenticated under the intended `HOME`
2. `haft remotes list --json` shows the expected `dev` target and readiness/operations
3. `haft import ... --remote dev --wait --json` returns bounded identifiers and file facts
4. capture the returned `batchId`, `jobId`, `vaultPath`, `size`, `sha256`, and `indexed` result
5. if the user needs destination UI proof, verify that in an authenticated destination lane

Do **not** require a separate `remote status` success before importing if `remotes list` already shows the target and you only need to perform the import.

Do **not** treat an unauthenticated `403` from a public reader or status probe as contradiction of a successful import. That is a different seam.

## Common Pitfalls

1. **Treating `HAFT_DEV_REMOTE_TOKEN` as normal-path configuration**
   - It is fallback only.

2. **Ignoring the `HOME` distinction**
   - Profile home and host home can tell different truths.

3. **Equating successful OTP login with successful managed import**
   - Login is only one seam.

4. **Blurring local vault import and remote destination import**
   - They prove different things.

5. **Claiming unknown-remote means product entitlement is definitely wrong**
   - If discovery failed upstream, unknown-remote may be a downstream symptom.

6. **Using a relative path for the import file in an unknown shell cwd**
   - Prefer an absolute path unless the calling shell's cwd is explicitly controlled.

7. **Omitting `--wait --json` on remote imports**
   - Without them you lose the best machine-readable proof and may stop before the job outcome is final.

8. **Treating unauthenticated `403` on dev as import failure**
   - Public route gating and import success are separate seams.

9. **Running `remote status` as mandatory ceremony before every import**
   - Use it when you need diagnosis, not when the simple import path already proves success.

## Verification Checklist

- [ ] Correct route chosen for local import type
- [ ] Exact-file placement used when byte-preservation mattered
- [ ] For CLI remote tests, both `PATH` and relevant `HOME` reality checked
- [ ] Fast path attempted first for simple dev imports: `import --remote dev --wait --json`; auth/discovery commands ran only after failure or for formal evidence
- [ ] `HAFT_DEV_REMOTE_TOKEN` treated as break-glass only
- [ ] Remote success claims backed by returned `batchId`/`jobId`/`vaultPath`/`sha256`/`indexed`
- [ ] Any `remote status` or public-route `403` interpreted separately from import success
- [ ] Failure classified to the correct seam: credentials, refresh, discovery, status, import, or route gating