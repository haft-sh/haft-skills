---
name: haft-artifact-catalog-reconciliation
description: Use when a Haft vault shows duplicate artifacts, a yellow question-mark (missing) row, or an irreconcilable file the UI can't move/delete. Diagnose catalog records, soft-remove orphans safely, and refresh the viewing surface.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, operations, catalog, artifacts, reconciliation, duplicates]
    related_skills: [haft-vault-operations, haft-import-operations, haft-operator-health-checks]
---

# Haft Artifact Catalog Reconciliation

## When to use

Use this when an operator reports any of:

- "There are two versions of the same file and I can't reconcile them."
- A file row shows a **yellow question-mark icon** in the vault sidebar.
- Dragging a file into a folder is a **silent no-op**, or delete/move "does nothing."
- A file appears in the tree but has no readable backing.

This is a **catalog-state reconciliation** task, distinct from importing a file
(`haft-import-operations`) or editing one document (`haft-agent-session-operations`).

## Core model: how duplicates form

The same on-disk content can be ingested through **more than one path** — e.g. a
CLI import into `scripts/foo.md` AND a page-indexing pass at vault root `foo.md`.
Each path mints its own `artifact_id`. When one copy later loses its local backing,
`reconcileArtifactLocalAbsence` flips that record to `storage_state='missing'` with
`source_ref=NULL` — an **unrecoverable zombie**. It still renders in the tree (with
the question-mark icon) but has no bytes to move, preview, or delete cleanly.

The tree projection hash-collapses same-`content_hash` records (`tree.ts`), so a
third live duplicate can be **invisible in the tree yet still a live catalog row**.
Always reconcile against the **catalog**, not the rendered tree.

### storage_state taxonomy

| state | meaning |
|---|---|
| `local-only` | bytes on disk, no remote backing — normal healthy local file |
| `mirrored` | local + remote backing |
| `remote-only` | remote backing, no local bytes |
| `stale` | backing present but out of date |
| `missing` | **no local backing AND `source_ref=NULL`** — the zombie; question-mark icon |
| `removed` | soft-deleted; excluded from browser queries |

The question-mark icon is `storageState === "missing"` rendered as `FileQuestion`.

## Diagnostic workflow

1. Query the catalog `artifacts` table by `logical_path`/`title` fragment. List
   `artifact_id, kind, title, logical_path, storage_state, source_ref, content_hash,
   revision, indexed_at, updated_at`.
2. Group by `content_hash`. Records sharing a hash are the duplicate family.
3. Pick the **canonical** record: the one with real backing (`storage_state` in
   `local-only`/`mirrored`, non-null `source_ref`, file present on disk). Confirm it
   is the one the user's URL / reader route points to.
4. Everything else in the family is an orphan candidate. Check `artifact_aliases`
   (handles, slugs, legacy-page-id) and `artifact_events` before removing, so you
   know what references the record.

See `references/duplicate-taxonomy-and-access.md` for the exact catalog location,
the dev-instance access pattern, and the `bun:sqlite` query recipe.

## Remediation: revision-guarded soft-remove

Never hard-`DELETE` catalog rows. Replicate `removeArtifactWithRevision` semantics
exactly so the audit trail and revision guard stay intact:

```sql
UPDATE artifacts
SET storage_state = 'removed',
    updated_at = $now,
    removed_at = $now,
    revision = revision + 1
WHERE artifact_id = $id
  AND revision = $expectedRevision      -- guard against concurrent change
  AND storage_state <> 'removed';
```

Then append an `artifact_events` row: `event_type='removal'`, an `actor` naming the
operator/cleanup, and `before_json`/`after_json` snapshots. Verify `changes === 1`
per row; if a revision mismatches, re-read and retry rather than forcing.

## Refresh the viewing surface (do not skip)

There are **two** tree endpoints with different freshness semantics:

- `GET /api/vault/tree` — computes the tree **live** from the catalog. Already
  correct after a catalog edit (it excludes `removed` records).
- `GET /api/vault/tree/children` — the paginated sidebar source. Reads a
  **materialized explorer projection** (`explorer.sqlite`) that does **not**
  self-heal. It stays stale until an explicit refresh.

**You cannot claim the UI is clean until the projection is refreshed.** The blessed
refresh path is `haft index rebuild` (it reconciles the catalog and refreshes the
explorer projection). Do not hand-edit `explorer.sqlite`.

## Pitfalls

1. **`haft index rebuild` can be non-idempotent on vaults with thumbnail-backed
   assets** — it fails with `UNIQUE constraint failed: assets.path`. The rebuild's
   `DELETE FROM assets ... AND NOT EXISTS (thumbnail)` retains thumb-backed rows,
   then the manifest re-insert assigns the same `path` to a new content-derived
   `asset_id`, colliding on `path TEXT NOT NULL UNIQUE`. This blocks the projection
   refresh (and all future rebuilds on that vault). Verify the data is intact first
   (assets on disk, hashes match) — the data is usually fine; the rebuild is not
   idempotent. Prefer a surgical projection refresh, or fix the rebuild, over
   hand-editing. See the reference for the verification query.
2. **Reconcile against the catalog, not the tree.** Hash-collapse hides live dupes.
3. **A move/delete no-op is a symptom of `missing` state**, not a UI bug. The row
   has `capabilities.move` gated off because there is no writable backing.
4. **Selection collision hides Delete for live duplicates.** When two live records
   share the same `logical_path` (both `local-only` or `mirrored`), the frontend
   selection model keys on `logicalPath` (via `selectionPathForTarget` in
   `VaultBrowserTree.tsx`). Clicking one row selects both → `multiple=true` →
   `canDelete` is false → no Delete button in the context menu. The user sees
   "clicking one selects the other" and "can't right-click to delete." This is
   distinct from the `missing`-state no-op: both rows are healthy, the bug is
   identity collision. Fix: dedup the catalog (this skill) AND file the frontend
   selection-identity fix (key on `treeId`/`artifactId`, not `logicalPath`).
4. **Don't conflate the live tree endpoint being correct with the UI being correct.**
   The paginated projection is what the sidebar actually renders.

## Filing the code fix

The durable product bug is the **ingest dedup gap**: same-content-hash content
ingested via two paths forks into separate records instead of merging, and the
losing fork decays into a `missing` zombie. When this recurs, file a scoped ticket:
reconcile-on-ingest should detect an existing record by `content_hash` + logical
path and merge rather than fork. Also file the rebuild-idempotency bug separately if
you hit pitfall #1 — it is reproducible and blocks operator workflows.

## Verification checklist

- [ ] Duplicate family identified by `content_hash` from the catalog (not the tree)
- [ ] Canonical record confirmed against the user's URL / on-disk backing
- [ ] Orphans soft-removed with revision guard + `removal` audit events
- [ ] Explorer projection refreshed (or a documented reason it is blocked)
- [ ] UI verified clean in the paginated sidebar, not just the live tree endpoint
- [ ] Recurring root cause filed as a scoped ticket (ingest dedup; rebuild idempotency)
