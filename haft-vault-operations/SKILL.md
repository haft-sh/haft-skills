---
name: haft-vault-operations
description: Use when deciding which Haft product seam to use; this thin routing skill points to the narrower import, artifact, and reconciliation skills and defines minimal verification.
version: 2.3.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, operations, routing, imports, artifacts]
    related_skills: [haft-import-operations, haft-agent-session-operations, software-development-lifecycle]
---

# Haft Vault Operations

## Overview

This is the umbrella skill for **operating Haft itself**.

Load it first when you need to answer:
- which Haft product seam matches this task?
- which narrower skill should I load next?
- what downstream surface should I verify before claiming success?

This skill is intentionally thin. It should help you choose a lane, then hand off to the narrower skill that owns the detailed procedure.

If the task is **"import this existing file into Haft"** or **"import this file into dev"**, stop here and load `haft-import-operations`. That skill is the source of truth for the CLI recipes, fallback rules, and import-specific failure taxonomy.

## Portability Rule

- Repo-local skills should describe durable Haft behavior, not one operator's private setup.
- Mention host-specific realities only when they change the behavior class, for example profile-home versus host-home wallet separation.
- Keep secrets, personal tokens, and one-machine-only setup habits out of this skill.

## When to Use

Use for:
- routing a task to the correct Haft product seam
- distinguishing local import, exact-file placement, artifact creation, browser-mediated remote HTML capture, and installed-CLI remote dogfood
- deciding which narrower skill owns the detailed steps
- setting the minimum verification bar for the chosen lane

Do not use for:
- detailed existing-file import procedures once you already know the task is an import
- source-code planning or PR sweeps
- direct DB/file manipulation when a real product seam exists

## Load the Narrower Skill

| Task | Skill |
|---|---|
| import an existing file into Haft or a remote destination | `haft-import-operations` |
| create a structured HTML artifact through the API | `haft-agent-api` |
| conversationally edit one existing local or remote document through a draft and explicit Apply | `haft-agent-session-operations` |
| reconcile PRs and queue state | `haft-pr-reconciliation` |

## Current Core Seams

### App readiness
```http
GET /api/app/status
```
Use before local write operations.

### Document import
```http
POST /api/import/documents/upload
```
For generic Markdown or HTML where normalization is acceptable.

### Media import
```http
POST /api/import/media
```
For images, PDFs, audio, video, and other approved assets.

### Browser-mediated remote HTML import
```http
POST /api/import/remote-html/browser
```
For browser-fetched bytes plus provenance, not generic backend URL fetching.

### Agent-created HTML artifact
```http
POST /api/agent/create_html
```
For structured artifact creation, not existing-file upload.

### Installed CLI path
```bash
haft
```
For host/operator dogfooding, especially remote destination import flows.

## Route Selection Shortcut

| Goal | Path |
|---|---|
| generic document import | document upload |
| binary asset import | media upload |
| browser-fetched remote HTML bytes | remote-html/browser |
| structured generated HTML artifact | agent create_html |
| exact finished Haft HTML artifact | direct vault placement + rebuild |
| remote destination import to dev or another instance | installed CLI, then load `haft-import-operations` |
| remote conversational edit of one existing document | installed CLI, then load `haft-agent-session-operations` |

## Operating Rules

### 1. Prefer product seams over raw manipulation
If a normal product API or CLI path exists, use it before reaching for:
- direct vault writes
- SQLite inspection
- ad hoc filesystem surgery

Exception:
- a finished Haft HTML artifact that must remain byte-for-byte unchanged may be placed directly in vault `content/` plus index rebuild

### 2. Distinguish local vault work from remote dogfood
Local import success does not prove the managed remote path.

### 3. Distinguish route selection from detailed procedure
Use this skill to pick the seam. Once the seam is clear, move to the narrower skill instead of restating its full recipe here.

### 4. Verify the viewing surface the user actually wants
For HTML artifacts, distinguish:
- reader/index/document view
- rendered standalone HTML view
- Haft-shell embedded preview
- remote-import transport proof versus authenticated destination UI proof

Do not hand back a reader link and imply it is equivalent to rendered HTML.

### 5. Respect CLI home context when doing host dogfood
If the task leaves browser/local seams and enters installed-CLI dogfood, deliberately choose the intended `HOME`. On this host, profile-home and host-home can tell different truths. Load `haft-import-operations` for remote import or `haft-agent-session-operations` for one-document conversational editing.

## Minimal Verification Standard

After any write or create action, verify at least one downstream surface:
- returned metadata
- index or reader resolution
- actual rendered or preview route
- remote destination visibility when that is the task

A request succeeding is not enough.

For remote CLI imports, record at minimum:
- target slug
- `batchId`
- `jobId`
- destination `vaultPath`
- file `sha256`
- `indexed` result

For the exact CLI commands and how to interpret status failures or public-route `403` results, load `haft-import-operations`.

## Common Pitfalls

1. **Using this umbrella skill as if it were the full import playbook**
   - Once you know the task is an import, load `haft-import-operations` and stop duplicating commands from memory.

2. **Using the wrong seam**
   - Existing-file import, generated artifact creation, exact-file placement, and remote destination import are different lanes.

3. **Skipping downstream verification**
   - A shell or API success is not the same as artifact, preview, or import success.

4. **Using a public route probe as the sole proof for remote import success**
   - Public-route gating and import transport are different seams.

5. **Using raw DB or filesystem inspection for routine operator questions**
   - If the product should answer it, treat missing seams as a product gap instead of normalizing the workaround.

## Verification Checklist

- [ ] Correct narrow Haft skill loaded for the chosen seam
- [ ] Chosen path matches the real task: import, exact-file placement, artifact, or CLI dogfood
- [ ] Product seam used before fallback manipulation
- [ ] Detailed procedure delegated to the narrower skill when applicable
- [ ] Verification matched the user-facing or downstream seam that actually matters
