---
name: hypervault-artifact-planning-and-publication
description: Plan, prepare, and publish Hypervault/Haft HTML planning artifacts safely, including privacy-lint-aware wording and active-vault publication flow.
---

# Hypervault / Haft Artifact Planning and Publication

## When to use

Use this when working on Hypervault/Haft planning docs, roadmap artifacts, implementation-plan HTML files, or any authored artifact that is meant to be published through Hypervault's local export pipeline.

Typical triggers:
- drafting a new epic or roadmap HTML doc
- copying a repo doc into the active Hypervault vault for publication
- publishing a plan to a canonical site URL
- debugging why a planning artifact fails Hypervault publication or privacy lint

## Core workflow

1. Write the planning artifact in repo space first if needed.
2. Copy the final publishable source into the active vault under a stable content path such as `content/plans/...`.
3. Ensure the artifact's metadata visibility is publishable (`unlisted` or `public`, not `private`).
4. Rebuild the vault index before publishing so the page ID is present in the reader/catalog.
5. Publish through the real Hypervault route or helper, not by inventing output files manually.
6. Verify the returned canonical URL and fetch the URL to confirm it resolves.

## Important product rule

For Hypervault/Haft planning artifacts, **local files remain the source of truth**. Publication is a derived export workflow. Do not treat local SQLite files or cache state as the source artifact to upload or synchronize.

## Style preservation: authored HTML needs a valid profile (CRITICAL)

Haft's import normalizer **strips all styling and rebuilds uploaded HTML as plain text blocks** unless the document carries a valid `haft-html-profile-v0` profile. This is the #1 cause of "my CSS disappeared after import." With a valid profile the document is preserved **byte-for-byte**; without one, every `<style>` is lost.

Whenever you author a styled Haft HTML document (daily notes, planning artifacts, demo docs) that will be imported, you MUST:

1. Include the full set of valid `haft:*` meta tags (profile, page-id, slug, description, visibility, content-type, created-at, updated-at, script-policy, source-kind, source-label).
2. Include at least one `data-haft-block-id` attribute and one `<section>` with both `id` and `data-haft-section`.
3. Avoid blocked content: `<script>`/`<iframe>`/`<form>`/`<link>`/`<base>`, `on*` handlers, `javascript:` URLs, `expression()`, and external fonts/CDN links (use system font stacks).
4. **Verify preservation** by comparing the import response `sha256` to the local file's `sha256sum`. A match means styles survived; a mismatch means normalization stripped them.

Start from `templates/styled-daily-note.html` — a known-good profiled document verified to import byte-for-byte with full CSS. Full tag/structure/pattern requirements and the blocked-content list are in `references/haft-import-style-preservation.md`.

Note: re-importing a styled (profile-preserved) doc with `--on-duplicate overwrite` may return a 409 identity mismatch (tracked product gap); the fallback is `--on-duplicate clone`. Check current behavior before assuming — see the reference file.

## Privacy-lint pitfall for planning docs

Hypervault's publication privacy lint can flag planning-doc wording as secret-like even when no real secrets are present. In authored planning artifacts intended for publication, avoid or neutralize words that look like raw secret material in titles, descriptions, and repeated body text when they are not necessary for the published audience.

Common risky wording:
- `credential` / `credentials`
- `secret` / `secrets`
- `key` / `keys`
- repeated secret-handling phrases in headings, metadata, citations, or chunk titles

Prefer safer public wording when the exact low-level term is not required:
- `remote access setup`
- `setup details`
- `bring your own remote target`
- `object path` / `path prefix`

This is especially relevant for published plan docs whose repeated headings or table labels get chunked and linted many times.

## Publication checklist

- Source file is inside the active vault content tree.
- `hv:visibility` is not `private`.
- Title and metadata do not contain unnecessary secret-like phrasing.
- Index rebuild completed after copying or editing.
- Publish route returned success.
- Canonical URL resolves with HTTP 200.

## Failure recovery

If publish fails on privacy lint:
1. Read the lint issue paths carefully.
2. Check title, metadata description, and repeated section headings first.
3. Replace unnecessary secret-like wording with neutral public wording.
4. Rebuild index again.
5. Re-run publish and verify the URL.

If remote publish fails with `Page is not a validated HTML profile artifact` even though the reader can resolve the page, check for rebrand-era metadata drift before blaming the artifact. In particular, inspect the source HTML `hv:profile` literal and compare it to the current publish-side profile constant. Legacy `hypervault-html-profile-v0` source can be indexed/readable while publish validation expects `haft-html-profile-v0`; see `references/remote-publish-legacy-profile-mismatch.md` for the reproduction and ticket guidance.

## Additional authored-artifact pattern

When the user asks for a talk track, pitch, or demo script and then wants it stored and published from Haft, keep the content authored for **the product being demoed** rather than drifting into the underlying infrastructure. For Haft hackathon demos specifically:

- make **Haft** the protagonist of the script
- treat Hermes, NVIDIA, and Stripe as enabling layers
- then convert the final script into an HTML artifact and publish it through the real Haft routes

Important compatibility note from live publication work: the product name may be Haft, but the current `create_html` route still expects the profile literal `hypervault-html-profile-v0`. Do not invent a renamed profile string without checking the live contract first.

See `references/haft-demo-script-publication.md` for the exact create/publish route sequence and response fields.

## References

- See `references/privacy-lint-wording-pitfall.md` for the condensed session-specific pattern that motivated this skill.
- See `references/haft-demo-script-publication.md` for the create_html → publish_remote_package pattern for storing and publishing a generated Haft demo-script artifact.
- See `references/remote-publish-legacy-profile-mismatch.md` for diagnosing indexed/readable planning artifacts that remote publish rejects because raw source profile metadata still uses the legacy Hypervault literal.
- See `references/haft-import-style-preservation.md` for the full `haft-html-profile-v0` tag/structure requirements, blocked-content list, and sha256 verification recipe that keep authored CSS from being stripped on import. Starter: `templates/styled-daily-note.html`.
