---
name: haft-agent-api
description: Use when creating Haft HTML artifacts through the agent API and verifying that the resulting artifact resolves through the correct reader, preview, or canonical product seam.
version: 2.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, agent-api, create-html, reader, canonical-path, slug]
    related_skills: [haft-vault-operations, haft-agent-session-operations, software-development-lifecycle]
---

# Haft Agent API

## Overview

Use this when the task is to create a new Haft artifact from structured JSON rather than importing an existing file.

Primary route:

```http
POST /api/agent/create_html
Content-Type: application/json
```

The operational lesson after recent Haft work is simple: artifact creation is only successful when the created artifact is discoverable through the **right downstream seam**, not merely when the POST returns success.

## When to Use

Use for:
- agent-generated HTML artifacts
- synthetic or transformed HTML pages that should become first-class Haft artifacts
- validating slug, page ID, canonical path, and downstream resolution

Do not use for:
- uploading an existing file from disk
- generic document/media import
- editing an existing document through a draft/review/Apply lifecycle; load `haft-agent-session-operations`
- claiming visual success from reader-only verification when rendered preview is the real requirement

## Expected Response Evidence

A successful create should return bounded identifiers such as:
- `pageId`
- `slug`
- `sourcePath`
- `canonicalPath`

Record them. They are part of the contract.

## Verification Workflow

1. Check HTTP status and JSON success shape.
2. Record `pageId`, `slug`, `sourcePath`, and `canonicalPath`.
3. Verify reader/index resolution when the artifact is meant to behave like a document.
4. Verify rendered preview when the artifact is meant to behave like standalone HTML.
5. If canonical routing matters, verify the actual canonical path, not just the app shell.

## Reader Verification

Typical lookup:
```http
GET /api/reader/pages/by-slug?slug=<slug>
```

Use this to confirm:
- the artifact is indexed
- the expected slug resolves
- reader data exists

## Preview / Render Verification

Do not conflate these surfaces:
- app shell loads
- artifact record resolves
- backing preview/render route resolves actual HTML

A real failure class in Haft is:
- shell page loads
- artifact metadata exists
- preview/render seam returns 404 / not found / wrong content

When the user expects a visually rendered HTML artifact, verify the render/preview surface explicitly.

## Canonical Path Expectations

If `canonicalPath` is returned, treat it as part of the acceptance contract.

Verification should distinguish between:
- root app availability
- artifact deep-link availability

## Provenance Expectations

Keep enough provenance to explain:
- what source/prompt/transform produced the artifact
- what identifiers were returned
- what downstream seam proved it was usable

## Common Pitfalls

1. **Using `create_html` for existing-file upload**
   - use an import route instead unless transformation is the point.

2. **Stopping at creation success**
   - a created record is not enough; verify discovery/resolution.

3. **Handing back reader resolution when the real ask was rendered HTML**
   - reader and preview are not interchangeable.

4. **Checking only the shell URL**
   - verify the actual artifact seam behind it.

## Verification Checklist

- [ ] POST succeeded with bounded identifiers
- [ ] `pageId` / `slug` / `canonicalPath` recorded
- [ ] Reader lookup verified when document behavior is expected
- [ ] Preview/render seam verified when visual HTML behavior is expected
- [ ] Canonical deep-link checked when in scope
- [ ] Success claim matches the actual downstream surface the user needed
