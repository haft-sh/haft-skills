# Linked assets vs self-contained HTML in Haft

Use this note when reasoning about review boards, renderable local HTML artifacts, and future public-share/export behavior.

## Product direction

- For Haft-local artifacts, **linked assets are the default**.
- Do **not** default to embedding images as `data:` / base64 blobs inside stored HTML.
- A self-contained single-file HTML artifact is an optional portability mode, not the normal storage or render target for Haft.

## Why linked assets are preferred

- Smaller HTML files
- Better diffs and easier inspection/editing
- Reuse of Haft asset records and allowlists
- Clearer separation between document source and asset source
- Better fit for deterministic publish/export manifests and stale detection
- Avoids duplicating large binary payloads into source HTML

## Public/share direction

If Haft later supports user-facing public sharing beyond local static export preview:

- Preferred model: upload the generated HTML and generated asset copies separately to **user-owned R2/S3**.
- Do **not** solve public sharing by embedding all images as base64 into the HTML.
- Reuse deterministic generated asset paths/naming rather than source filenames.

## State tracking

Track publication state in Haft's **private registry/audit state** under `.haft/`, not by mutating source HTML and not by introducing a database as the source of truth for publication state.

Track enough facts to answer:
- which local export was generated
- which remote objects/URLs were uploaded
- whether the remote copy matches the local generated export
- whether unpublish/tombstone has removed or superseded a remote copy

## Design warning

Current publish contracts are intentionally scoped to local static export, so R2/S3 publishing is a **future publish target/profile**, not a tiny implementation detail. It needs explicit handling for credentials, upload state, remote drift, and unpublish semantics.
