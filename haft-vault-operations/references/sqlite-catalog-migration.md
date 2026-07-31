# Haft SQLite catalog migration lesson

## Trigger

Use this when a Haft task touches storage/indexing, large imports, Bhagavatam-scale corpora, manifest behavior, search backend, publish/export state, or remote publishing.

## Product direction

The desired v4 direction is **filesystem-owned, SQLite-indexed**:

- Source files remain authoritative in `content/` and `assets/`.
- SQLite under `.haft/index.sqlite` should become the primary local runtime catalog.
- `.haft/manifest.json` should be treated as derived/debug/compat output, not the runtime backbone.
- Keyword search should move to SQLite FTS5.
- QMD/semantic search remains optional and maps hits back to stable Haft page/chunk IDs.
- Remote publish should upload HTML plus linked generated assets to user-owned S3/R2-compatible storage; base64 image embedding is not the default.
- Publication state belongs in catalog/audit state, not source HTML metadata.

## Important correction from dogfooding

A giant JSON manifest is an MVP shortcut, not the intended long-term architecture. For large imports such as Bhagavatam-scale corpora (roughly 12,000 verse-level units plus purports, citations, assets, and search rows), whole-manifest read/rebuild/update behavior is risky and inefficient.

The older roadmap already pointed toward:

- `Filesystem + SQLite catalog`
- `.haft/index.sqlite`
- SQLite FTS5/vector-capable indexing
- static export to S3/R2

So if current code or docs imply manifest-first as permanent, treat that as architectural drift.

## Operational pattern for storage migration

When leading this class of migration:

1. Freeze autonomous flow first:
   - pause orchestrator/PR-sweep cron jobs
   - park unrelated Ready cards in Scheduled/Blocked with a clear architecture-freeze note
   - leave only the first migration slice Ready
2. Write and commit/push governing docs before dispatching workers:
   - architecture decision doc
   - concrete migration plan
3. File migration cards in dependency order:
   - backup/schema/store
   - rebuild catalog from files
   - reader/app-status routes
   - search FTS
   - agent target resolution
   - publish/export state
   - manifest demotion/docs/tests
4. Keep dependent cards Blocked until prerequisites land.
5. Require the first worker to back up the dogfood vault before mutating `.haft/` storage.

## Boundary

Do not store credentials in the SQLite publish tables. Store only non-secret target metadata and object/public URL facts. Credential handling needs a separate reviewed contract.
