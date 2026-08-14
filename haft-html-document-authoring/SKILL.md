---
name: haft-html-document-authoring
description: Use when creating, styling, or updating Haft HTML documents (daily notes, plans, artifacts). Covers profile byte-preservation, rich-media embedding, broken in-place update seams + the working workaround, and the haft daily workflow.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, html, authoring, styling, rich-media, daily-notes, import, update]
    related_skills: [haft-vault-operations, haft-import-operations, haft-agent-session-operations, haft-document-retrieval]
---

# Haft HTML Document Authoring

## Overview

Use this skill when JP asks to **create, restyle, or edit the content of** a Haft HTML document — daily notes, implementation plans, design docs, review boards. It captures the mechanics that decide whether your styling and images actually survive import, and the (currently broken) in-place update paths plus the workaround that works.

This is about **authoring content**. For the transport/import seam itself load `haft-import-operations`; for choosing a product seam load `haft-vault-operations`; for conversational edits via AgentSession load `haft-agent-session-operations`.

> Repo-shared `haft-ops` skills live in an externally-owned, read-only directory — autonomous `patch`/`write_file` to them is refused. Durable authoring knowledge lives here (profile-owned) instead; hand edits to the repo skills to JP.

## The two rules that decide everything

1. **Styling survives only with a valid profile.** On import, Haft preserves HTML **byte-for-byte** if it carries a valid `haft-html-profile-v0` profile; otherwise it rebuilds the doc as plain text blocks and **strips every `<style>` block**. Verify: imported `sha256` == local file `sha256`.
2. **Images survive only WITHOUT a profile.** A profile doc cannot display images (reader view shows text chunks only; the preview iframe can't resolve relative `assets/` and its CSP blocks `data:`). The only working image path is a **non-profile** doc with embedded `data:` image URIs — Haft stores an original-source snapshot and serves it intact.

So the first decision for any document is:

| Document type | Profile? | Why |
|---|---|---|
| Text-only, styled | **Yes** (valid profile) | CSS preserved byte-for-byte |
| Contains images | **No** (non-profile) | embedded `data:` images render via original-source snapshot |

Do not add a profile to an image-bearing doc — it forces reader view and breaks the images.

## Creating a styled daily note (the common case)

1. Build the HTML with a valid profile (requirements in `references/html-styling-and-rich-media.md`). A ready starter is `templates/daily-note.html`.
2. Import: `HOME=<dev-host-home> haft import /abs/path.html --remote dev --on-duplicate clone --wait --json`.
3. Verify byte-preservation: imported `sha256` must equal `sha256sum` of the local file.
4. Confirm resolution: `HOME=<dev-host-home> haft query '<title>' --remote dev --json` → slug + contentHash.

JP's daily notes live under `daily-notes/` with pattern `{date}-daily-notes.html`. Daily Notes are now **configured** on dev (path prefix `daily-notes/`), so `haft daily show/status/new --remote dev` resolve them. See `references/haft-daily-workflow.md`.

## Updating an existing document in place — currently broken

All three native update seams fail on a managed remote (see `references/in-place-update-seams.md` for evidence + root causes):

- `--on-duplicate overwrite` → **HTTP 409** identity mismatch once the target is profile-preserved (also fails with `--target-folder`).
- `haft move` → **HTTP 403** grant-denied, even a plain rename.
- AgentSession `turn --runner hermes` → no production runner binding.

**The workaround that works:** re-import the edited file with `--on-duplicate clone`. Because a profile doc's own `haft:slug` meta drives placement, setting the slug to the original's location makes Haft place the new version at the **canonical slug** and rename the original to a hash-suffixed backup (e.g. `...-6c280b2cc541`). Nothing is lost; the styled version owns the clean URL. The backups can be consolidated once the move/delete fix lands (tracked on the board).

Never present a failed overwrite as success — always check the returned `collision`/`vaultPath`/`slug`.

### Operational log append workflow

For maintained Haft documents such as an agent-friction or code-smell log, treat an append as an **existing-document edit**, not as a new import:

1. Resolve the exact durable page handle with `haft query`, then retrieve bounded current text with `haft get`.
2. Start one managed AgentSession using that handle, issue a minimal append/replace instruction, then inspect preview and diff before a revision-guarded Apply.
3. If the runner is unavailable or its installation is invalid, verify that no draft revision changed and discard the session. Do **not** replace the log through import/overwrite or direct patching.
4. Record the bounded runner diagnostic and file/reuse a runner-installation or capability-repair card when the defect materially blocks the maintenance workflow. Keep the proposed entry for the next safe edit; do not claim the remote log was updated.

This keeps the long-lived log authoritative and prevents a runner/tooling failure from creating duplicate or diverging log documents.

## Rich media (images + click-to-enlarge)

For image-bearing docs (plans, mockup showcases):
- Build as **non-profile** HTML with embedded `data:` WebP images (compress with PIL, cap ~900px wide, quality ~72).
- Click-to-blow-up must be **JavaScript-free** (sandbox blocks all JS): use a CSS `:target` lightbox driven by internal anchor links.
- Full recipe, the CSP/validator constraints, and image-prep code: `references/html-styling-and-rich-media.md`.

## Design bar

JP asks for these to look genuinely designed, not templated — strong type hierarchy, a real palette, living details (hover states, reveals), and content that reflects the actual note/plan. Match the effort to the artifact: a daily note gets a crafted masthead and sections; a plan gets navigation, tables, and callouts. Use system font stacks (external font `<link>` is blocked).

## Pitfalls

1. **Importing styled HTML without a profile** → reader shows bare text, all CSS gone. Always add a valid profile for styled text docs.
2. **Adding a profile to an image doc** → forces reader view, images never render.
3. **Using external URLs / `file://` / CDN fonts** → rejected by the validator or blocked by CSP.
4. **Trusting `--on-duplicate overwrite` on a profile doc** → 409; use the clone workaround.
5. **Assuming `data:` images are blocked everywhere** → they're rejected by the *profile validator* but are exactly what non-profile rich docs rely on.
6. **Forgetting `HOME=<dev-host-home>`** → profile-scoped home has a different wallet than the host operator wallet.

## Checklist

- [ ] Decided profile vs non-profile from the "two rules" table
- [ ] Profile docs: valid profile meta + ≥1 block-id + ≥1 section; sha matches after import
- [ ] Image docs: non-profile, embedded `data:` WebP, `:target` lightbox, no JS
- [ ] Used `--on-duplicate clone` for updates (not the broken overwrite)
- [ ] Verified via returned `sha256`/`slug`/`contentHash`, not just "import ok"
- [ ] Daily notes use the `daily-notes/` prefix + `{date}-daily-notes.html` pattern
