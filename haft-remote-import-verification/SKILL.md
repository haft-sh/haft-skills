---
name: haft-remote-import-verification
description: Verify Haft remote imports end to end by separating CLI import success, destination file presence, destination route-gating, and UI projections such as Recently Imported.
version: 1.2.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, import, remote, verification, ui, recent-artifacts]
    related_skills: [haft-cli-auth-and-remotes, haft-import-operations, haft-vault-operations]
---

# Haft Remote Import Verification

## When to Use

Use this after a Haft CLI remote import when the user cares about what appears on the destination instance, especially:
- whether the file actually landed on the remote vault
- whether the UI can see it
- whether **Recently Imported** reflects it
- whether a mismatch is an import failure or a destination projection/UI bug

## Core distinction

Treat these as separate seams:
0. **Managed readiness seam** — before upload, does HQ discovery expose exactly one authoritative target for the requested slug, with readiness `ready` and `allowedOperations` containing `import`?
1. **CLI import seam** — did `haft import ... --remote <slug> --wait --json` complete successfully?
2. **Destination file seam** — does the destination's authenticated file listing include the imported path?
3. **Destination recent-feed seam** — does the vault-tree / recent-artifacts projection that powers `Recently Imported` include it?

Do not collapse all four into a single yes/no result. `remote status`, public health, TLS, or browser login prove reachability or a separate auth seam; they do not prove delegated-import readiness. A requested slug plus a collision-suffixed target, `status`-only operations, `projection-expired`, or `destination-verifier-not-ready` means the import is blocked before upload. Do not substitute the suffixed target or a manual remote unless the user explicitly authorizes a bypass; repair managed enrollment convergence first.

When the source is also being persisted as a repository decision/feasibility memo, follow `references/repo-backed-discussion-memo-dev-import.md`. It covers worktree/PR persistence, importing the merged canonical bytes, the installed CLI's nested JSON envelope, hash equality, and safe `--on-duplicate skip` verification without accidental clone duplicates. For an explicit **spec → PR → Dev import** handoff where the Dev artifact intentionally precedes merge, also use `references/repo-spec-pr-dev-import-handoff.md`; it requires exact branch-file hashing and clear non-canonical labeling. When a changed revision must replace an existing remote path, use `references/remote-import-overwrite-collision-handling.md`; an explicit overwrite can return an identity-mismatch 409, and a cloned fallback must be reported as a distinct artifact rather than an update.

## Verification order

0. Run `haft remotes list --json` and require exactly one canonical target for the requested slug, readiness `ready`, and `allowedOperations` containing `import`. Stop before creating a canary if this gate fails.
1. Run the remote import with `--wait --json` and capture:
   - remote slug
   - job or batch id
   - destination vault path
   - file size / hash when returned
2. Verify the destination file listing contains the imported artifact.
3. If the user expects a UI confirmation, verify the authenticated destination UI surface separately.
4. For `Recently Imported`, check the destination recent-artifacts projection, not just the file listing.

## Interpretation matrix

| CLI import | Destination file listing | Recently Imported | Correct conclusion |
|---|---|---|---|
| success | present | present | import and UI are both working |
| success | present | missing | import worked; recent-feed / UI projection is stale or wrong |
| success | missing | missing | import result needs deeper investigation |
| failure | absent | absent | import failed or was rejected before commit |
| failure (`commit-failed` 409) | committed-but-unindexed (query `no-match`) | absent | upload committed and files preserved, but destination vault index/catalog rebuild failed — server-side fault, not operator config |

The last row is a distinct class, not "rejected before commit": the bytes landed and are preserved on the destination, but they are invisible to `query` and readers until the destination's index rebuild is repaired. See `references/commit-failed-index-rebuild-outage.md` for the diagnostic signature and the anti-retry rule.

## Common pitfall

A destination can successfully store the imported file while the `Recently Imported` section remains stale. In that case:
- report the import as successful
- report the `Recently Imported` mismatch as a separate bug
- avoid telling the user the import failed just because the recent-feed UI is wrong

## Practical checks

- Use the same authenticated destination session for the file-list and vault-tree checks when possible.
- If the destination file listing shows the artifact path, name, size, MIME, and modified time, treat that as strong proof the remote commit happened.
- If the CLI import response itself already returns `batchId`, `jobId`, destination `vaultPath`, file `sha256`, and `indexed: true`, treat that as the strongest proof available from the CLI lane even before you have authenticated destination UI access.
- If a follow-up reader or page lookup returns unauthenticated `403 route.gate-denied`, classify that separately as destination route gating. Do not let it overwrite a successful import conclusion.
- If the recent feed still shows older items or obviously stale timestamps, classify the bug at the recent-feed/catalog projection layer.

## Output pattern

State three facts separately:
- **Import result:** success/failure with job or batch id
- **Destination storage result:** whether the file is present in the destination listing, or whether CLI-lane proof (`vaultPath`/`sha256`/`indexed`) is the strongest evidence currently available
- **UI/result-surface status:** whether `Recently Imported` reflects it, or whether route gating prevented UI proof

## Pitfalls

1. **Using `Recently Imported` as the only verifier**
   - That can misclassify a projection bug as an import failure.
2. **Stopping at CLI success without capturing the returned facts**
   - Save the job/batch/path/hash/indexed evidence; it may be the strongest proof available from the current lane.
3. **Checking an unauthenticated destination route**
   - Private destination routes may 403 without proving anything about the import result.
4. **Letting route gating overwrite a successful import conclusion**
   - Report route gating as a separate verification limit, not as contradiction of the import response.
5. **Retrying a deterministic `commit-failed` (409) in a loop**
   - When the upload commits but the destination index rebuild fails, the error is deterministic and will not self-clear. Retrying the identical import only adds more preserved-but-unindexed copies to dedupe later. Diagnose once, escalate to the operator, and retry only after they confirm the destination's index rebuild is healthy. There is no operator-side remote rebuild seam — `haft index rebuild` only targets the local active vault.

6. **Treating a queryable page as proof that exact overwrite can resolve its artifact**
   - `haft query` and `haft daily show` can resolve a `pages` projection while exact overwrite independently requires a unique, non-removed artifact-registry record with matching logical path and source reference. For `Exact overwrite artifact is missing or removed`, preserve the existing copies, capture the page ID/source path/content hash from `daily show`, and report a page-to-artifact reconciliation failure rather than a missing-file claim.
   - Do not use clone or move as a speculative repair. File implementation work requiring bounded structured diagnostics (path/page/artifact/revision/hash and one safe next command) plus a disposable-fixture, idempotent recovery test that proves one active canonical path and unchanged Reader identity.

7. **Honor a late scope reversal before continuing a mutation**
   - An out-of-band user message is a current instruction, not historical tool text. If it narrows a previously authorized mutation to read-only diagnosis, stop ticket creation, source edits, deploys, service restarts, catalog changes, and asset writes immediately.
   - Preserve the evidence already gathered, then report observed facts, the exact gate/policy blocker, ranked safe remediation options, verification commands, and rollback planning. Do not resume the superseded mutation unless a later explicit instruction re-authorizes it.

8. **Distinguish malformed probes from valid route-gate evidence**
   - Probe an authenticated/private route with a syntactically valid request body before classifying it as disabled or unregistered. A no-body or malformed POST may produce a route-null/public-runtime diagnostic; a valid JSON request can reveal the actual route class, family, and authorization gate.
   - Compare route classification, runtime support, route-policy capability, central-grant route mapping, and vault scope separately. A target advertising an operation/capability is not proof that the specific route is mapped into central-grant authorization.

## Verification checklist

- [ ] HQ discovery exposes exactly one canonical target for the requested slug
- [ ] Target readiness is `ready` and `allowedOperations` contains `import`
- [ ] No collision-suffixed duplicate or status-only target is being used as a workaround
- [ ] CLI import run with `--wait --json`
- [ ] Job/batch id captured
- [ ] Destination path confirmed
- [ ] CLI-lane proof captured (`vaultPath`, `sha256`, `indexed`) even if destination UI auth is unavailable
- [ ] Destination file listing checked when an authenticated destination lane exists
- [ ] `Recently Imported` verified separately when requested
- [ ] Any `403 route.gate-denied` reported as a separate route-gating seam
- [ ] A `commit-failed` (409) classified as committed-but-unindexed, NOT retried in a loop, and escalated as a server-side index-rebuild fault
- [ ] Import-vs-projection conclusion stated explicitly
