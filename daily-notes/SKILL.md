---
name: daily-notes
description: Use when JP dictates a stream of tasks, ideas, status, or blockers and wants it turned into a durable Daily Notes command-center page in the dev Haft vault.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [daily-notes, task-management, haft, delegation, context]
    related_skills: [hermes-agent, computer-use]
---

# Daily Notes

## Overview
The agent converts the user.s dictated, potentially disjointed thoughts into one living Daily Notes HTML artifact in the dev Haft vault. The page is the durable context and task command center for the day: it makes priorities, owners, blockers, decisions, and verifiable outcomes explicit.

## When to Use
- JP dictates tasks, ideas, project status, reminders, or blockers.
- JP asks for a daily plan, handoff, end-of-day recap, or cross-agent coordination.
- A delegated task needs durable context and a clear completion contract.

Do not use this as a substitute for the Haft Kanban board for development-card state; link or summarize Kanban work here while preserving Kanban as the authoritative development tracker.

## Workflow

1. **Capture and structure the dictation.**
   - Preserve the intent; do not invent missing facts.
   - Create sections for: prior-day carry-forward, today’s priorities, active tasks, blockers/dependencies, delegated work, decisions, friction log, and end-of-day carry-forward.
   - Each actionable item needs an owner, desired outcome, next action, blocker/dependency if any, and completion evidence.
   - Completion: every distinct thought is either represented, explicitly deferred, or identified as needing clarification.

2. **Build the COMPLETE HTML locally before any import.**
   - Do NOT create a starter note and then try to replace its content — the CLI has no in-place content update command, and re-importing triggers collision cascades (clone suffixes like `-2`, `-3`).
   - Write the full, final HTML to a local staging file (e.g. `/tmp/YYYY-MM-DD-daily-notes.html`) in one pass. Include all sections, tasks, and styling.
   - Use `haft daily new --today` ONLY if JP wants the CLI-generated starter structure and you will NOT need to replace it. If you're building custom HTML, skip `daily new` entirely and go straight to import.
   - Keep language scan-friendly and make status visible in both text and color.
   - Completion: the local staging file is valid standalone HTML, names its date and owner, and contains ALL content for this update cycle.

3. **Deliver to Haft, CLI/API-first, single import.**
   - Use the installed `haft` CLI (not `bun src/cli.ts` from a repo checkout).
   - Do **not** open `<dev-hosted-origin>` in a browser for routine creation, retrieval, editing, status, or import; use its web UI only when JP explicitly requests browser interaction.
   - **First import of the day (no existing note):**
     `haft import <staged-file> --target-folder 'Daily Notes' --remote dev --wait --json`
   - **Subsequent updates to the same day's note:**
     `haft import <staged-file> --target-folder 'Daily Notes' --remote dev --wait --on-duplicate overwrite --force --json`
   - **PATH NORMALIZATION WARNING:** The remote normalizes `Daily Notes/` → `daily-notes/`. After the first import, the canonical vault path is `daily-notes/YYYY-MM-DD-daily-notes.html`. If `--on-duplicate overwrite` returns HTTP 409 ("Exact overwrite artifact is missing or removed"), the target path no longer matches the canonical path. Recovery: use `haft query --path-prefix 'daily-notes' --remote dev` to find the actual canonical path, then use `haft move` to consolidate, or accept the clone suffix and archive stale copies.
   - Treat the local file only as ephemeral staging. After a successful import, delete the staging copy unless JP explicitly asks to retain it locally.
   - Capture the returned batch/job ID and vault-relative destination. Note only real CLI/API friction or a requested browser workflow in the friction log.
   - Completion: the command reports a completed remote import with an imported artifact; no local staging copy remains.

4. **Maintain the living page during the day.**
   - When updating, rebuild the COMPLETE HTML locally (not a diff), then re-import with `--on-duplicate overwrite --force`.
   - If overwrite fails (409 or 500), do NOT repeatedly clone. Instead:
     1. `haft query --path-prefix 'daily-notes' --remote dev` to see all copies.
     2. `haft move` stale copies to `daily-notes/archive/` with `--create-destination`.
     3. Accept the surviving copy's path (even with a `-N` suffix) as canonical for the day.
   - Do NOT attempt `haft move` to rename a file to a path that was recently vacated — this can trigger server-side 500 errors.
   - Completion: exactly one active copy exists in `daily-notes/` for the date; stale copies are in `daily-notes/archive/`.

5. **Record product/workflow friction.**
   - Log only real observed friction: authentication obstacles, unclear state, path transformations, missing affordances, failed commands, or handoff gaps.
   - State the observed behavior and the specific product/process improvement it suggests.
   - Completion: every meaningful friction event is captured without exposing credentials or private content.

## Agent Coordination

- The primary agent acts as the daily-notes driver and coordination hub.
- Use the configured inter-agent communication channel for command, status, and unblocking.
- A delegation message must include the desired result, priority, relevant context, requested evidence, and expected reply format.
- Do not report a delegated task complete solely from a message; require operational evidence appropriate to the task.

## Common Pitfalls

1. **Keeping the note only on the Mac.** Remote Haft is the durable system of record; local staging is temporary only.
2. **Mistaking unauthenticated readiness probes for import failure.** Attempt the authorized remote import and report its real result.
3. **Losing a task’s owner or unblocker.** Put owner, dependency, next action, and verification evidence on every task.
4. **Making the page a duplicate Kanban board.** Keep Kanban card state authoritative; Daily Notes carries cross-project context and human-facing priorities.
5. **Logging generic complaints as friction.** Record the actual observed behavior and why it slowed the workflow.
6. **Importing a starter then replacing it.** `haft daily new` creates and imports a starter. If you then build custom HTML and re-import, you get a collision cascade. Build the complete note locally FIRST, import ONCE.
7. **Assuming `--target-folder` casing is preserved.** The remote normalizes `Daily Notes/` → `daily-notes/`. Subsequent `--on-duplicate overwrite` against the original casing returns 409. Always verify the canonical path via `haft query` before overwrite attempts.
8. **Using `bun src/cli.ts` from a repo checkout.** JP requires the user-installed `haft` CLI after `haft update`, not the repo dev entry point.
9. **Retrying failed `haft move` to a recently-vacated path.** The server can 500 when the destination was recently moved away. Accept the surviving copy's path instead of forcing a rename.
10. **Repeatedly cloning on overwrite failure.** Each failed overwrite + fallback clone adds another `-N` suffix. After ONE overwrite failure, switch to the query → archive → accept-survivor recovery path.

## Verification Checklist

- [ ] Daily note has exactly ONE active dated HTML artifact in `daily-notes/` on `dev` Haft.
- [ ] No stale duplicate copies remain in the active folder (check with `haft query --path-prefix 'daily-notes'`).
- [ ] Import result proves the artifact was accepted remotely (batch ID, job state: completed).
- [ ] Local staging copy was removed unless JP asked to retain it.
- [ ] Every active task has an owner, next action, and completion evidence.
- [ ] Current blockers and delegated-agent status are explicit.
- [ ] Observed workflow friction is recorded with an actionable implication.
