# Artifact operations roadmap v5 and htmx guidance

Use this reference when planning or ticketing Haft work around artifact generation, management, review, editing, publishing, or verification.

## Durable product lesson

Haft should be treated as an **artifact operations system**, not just a vault or HTML reader. The core loop is:

```text
Capture → Normalize → Relate → Edit → Preview → Publish → Verify → Handoff
```

The product should manage artifact intent. A file is not only its MIME type; it may be a draft, locked visual reference, generated asset, review target, published public object, mirrored remote asset, verification artifact, or plugin event source.

## Roadmap/document pattern

When a session produces a major product-plan rewrite:

1. Save a durable HTML document under `content/plans/` with Haft HTML-profile metadata.
2. Preserve any product suggestions as a separate named document when the user asks, instead of burying them only in chat.
3. Mark older roadmap docs as superseded rather than deleting them.
4. If the user wants a public link, upload the HTML doc to a stable R2 key under `shared/plans/` and verify the public body contains current-revision markers.
5. Propagate the new roadmap pointer into relevant Kanban/task context only as an integration concern; do not make Kanban a core product assumption.

Example artifacts from the v5 session:

```text
content/plans/cliphouse-suggestions.html
content/plans/haft-roadmap-v5.html
https://media.wheretoaccess.com/shared/plans/haft-roadmap-v5.html
```

## v5 implementation lane shape

After the SQLite catalog migration, the natural v5 lane is:

1. artifact registry + storage state + handle resolver
2. Make Durable capture flow
3. artifact collections + reference locks
4. semantic document patch API
5. render/check verification pipeline
6. remote publish/mirror workflow
7. desktop app shell against locked references
8. mobile browse/reader shell against locked references
9. plugin/event seam for integrations
10. end-to-end artifact operations vertical slice

The storage migration should still come first: filesystem source of truth plus SQLite catalog; manifest JSON becomes derived/debug/compat output.

## htmx / Carson Gross ecosystem assessment

htmx is useful as **vocabulary and inspiration**, not automatically as the app framework.

Useful semantics to borrow for persistent document patch APIs:

- `innerHTML`
- `outerHTML`
- `beforebegin`
- `afterbegin`
- `beforeend`
- `afterend`
- `delete`
- `none`
- `hx-target`
- `hx-select`
- out-of-band swap ideas

Important boundary:

- htmx modifies the **browser DOM** after HTTP responses.
- htmx does **not** persist documents to disk by itself.
- Haft must own persistence: parse source document, validate target section/block, snapshot, mutate the file or catalog-backed source, update SQLite, and return preview/evidence.

Recommended API framing:

```json
POST /api/documents/:id/patches
{
  "target": { "sectionId": "visual-direction-lock" },
  "operation": "insertAdjacentHTML",
  "position": "afterend",
  "html": "<section id=...>...</section>",
  "expectedHash": "...",
  "preview": true
}
```

## Kanban/plugin boundary

JP explicitly considers Kanban workflow specific to his agent setup. In Haft product planning:

- Core should emit artifact/document events and support handles.
- Kanban, agent dispatch, notification, and CI-like workflows should consume those events through plugins/integrations.
- Do not make Kanban central architecture or a primary product primitive.

## Ticketing pitfalls

- Do not dispatch app-shell work before locked visual references are captured in durable docs.
- Do not file downstream v5 implementation tickets as Ready while the storage backbone is still migrating. Parent-gate them behind the relevant SQLite/catalog cards.
- When creating many tickets programmatically, verify returned task IDs and dependency links. If parent IDs were not captured, audit the graph before telling the user the lane is safe.
- Ready queue should contain only intentionally dispatchable cards; downstream roadmap tickets can sit in `todo` with parent links until promoted/unblocked.
