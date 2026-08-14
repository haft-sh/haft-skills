---
name: dev-host-disk-reclamation
description: Use when reclaiming disk on the Hermes/Haft dev host.
---

# Dev Host Disk Reclamation

Use when JP asks to check disk space, clean up stale worktrees, or "reclaim some
room" on the dev host (`<dev-host-home>`, the EC2 box running Hermes + Haft + DevSpace).
This is recurring maintenance: worktrees accumulate fast because every Haft task
worktree carries its own `node_modules` (~550 MB each) and test runs litter `/tmp`.

## Stance

Audit first, present a tiered plan, then execute zero-risk tiers immediately and
cross-reference the board before touching worktrees. Never delete worktrees whose
tasks are still active. Report concrete GB reclaimed, not vague "freed up space."

## Procedure

1. **Top-level disk.** `df -h /` for the headline (size/used/avail/use%).
2. **Find big consumers.** `du -sh --max-depth=0 <dir>` per top-level dir.
   PITFALL: plain `du -sh <dev-host-home>/Sites/*` and `du` on `haft/.worktrees` or
   `/tmp` WILL time out (30s–180s). Use `--max-depth=0` on one dir at a time, and
   SAMPLE a few entries to extrapolate rather than measuring everything.
3. **Enumerate worktrees.** Use `git worktree list --porcelain` from the main repo.
   A detached HEAD is only a triage signal, never deletion authority: it may be a
   recent DevSpace session or a still-needed verification checkout. Pair it with
   directory recency, working-tree cleanliness, active-process evidence, and the
   live board state before considering removal.
4. **Cross-reference against the board** before pruning task worktrees — see below.
5. **Inspect Docker before source worktrees.** Run `docker system df`. If it
   reports reclaimable unused images or build cache, run `docker image prune -a -f`
   and `docker builder prune -a -f`: these retain active containers and volumes,
   but future builds may need to pull/rebuild images. Never run a volume prune
   without an explicit volume-deletion approval.
   For Haft's Dockerized CI runners, inspect stopped containers separately:
   `docker ps -a`, `docker inspect`, and `docker compose ls --all`. A stopped
   runner can retain multi-GB writable layers even when its image is only a few
   GB. Remove only clearly stale stopped CI runner containers, then remove their
   unused reproducible images if the checked-in Compose/Dockerfiles can rebuild
   them. Preserve persistent `_work` volumes unless JP explicitly authorizes
   volume deletion; report their size and dangling status instead.
   After any CI runner image/container cleanup, verify the runner provisioning
   contract before relying on CI: the shared `haft-ci-host-lock` volume must
   contain a regular readable/writable `heavy.lock` for the container `runner`
   UID/GID, and both build/browser runner containers must be healthy and online.
   After cleanup, re-measure rather than trusting deletion totals: run `df -h /`,
   `docker system df`, and a bounded scan of cache targets. Package managers or
   active services may recreate a cache during the cleanup pass, so remove only
   the recreated cache path on a final, targeted pass and then take the final
   `df` reading. Report both explicit reclaim totals and net before/after disk
   change; they can differ because of concurrent writes and filesystem accounting.
   Do not interpret a dirty canonical checkout as cleanup residue unless the
   pre-cleanup and post-cleanup Git status prove this operation changed it.
6. **Prune stale `/tmp` artifacts narrowly.** Before deletion, inspect
   `/proc/*/{cwd,fd}` for live references. Limit removal to known generated
   CI/test prefixes plus an age threshold, and skip any directory for which
   `git -C <path> rev-parse --is-inside-work-tree` succeeds. `/tmp` can contain
   registered Git worktrees, so a broad `/tmp/haft-*` deletion is unsafe.
7. **Present a tiered plan** (zero-risk caches/tmp first, worktrees last) and
   execute. Run bulk deletion in the BACKGROUND with `notify_on_complete=true`;
   removing ~100 worktrees at 550 MB each exceeds the 300s execute_code limit and
   even the 600s foreground cap.

## Fast bounded inspection mode (no deletion)

When JP asks for a quick read-only inventory, avoid a per-worktree recursive size
walk. Run each shallow root scan independently so one expensive root cannot hide
the other:

```bash
df -h /
timeout 180 du -xhd1 <dev-host-home>/.devspace/worktrees
timeout 180 du -xhd1 <haft-repo-root>/.worktrees
git -C <haft-repo-root> worktree list --porcelain
```

- A large worktree root can still exceed a bounded `du -xhd1` scan. Report partial
  output and the missing total honestly; do not immediately retry with a deep scan.
- Identify current entries with directory `mtime` and attached branch information.
  When needed, inspect `/proc/*/cwd` for processes rooted inside a worktree; no
  match is supporting evidence only, not a substitute for board and clean-tree
  checks.
- Report scanned roots, largest observed entries, recency/attachment caveats, and
  whether anything was removed.

## Board cross-reference (the high-value step)

Haft worktree directories are named after their task IDs (`t_XXXXXXXX`, or a
human slug for older/manual cards). So pruning is a join between
`os.listdir(<repo>/.worktrees)` and the board's task table.

CRITICAL: the real board DBs live at `~/.hermes/kanban/boards/<slug>/kanban.db`,
NOT the default `~/.hermes/kanban.db` (that one holds only a stray archived task
and will mislead you). The `tasks` table has NO `board` column — board is encoded
in the DB file path. Columns include `id, title, status, branch_name`.

`sqlite3` CLI is NOT installed on this host (exit 127) — query via python:

```python
import sqlite3, os
conn = sqlite3.connect(os.path.expanduser('~/.hermes/kanban/boards/haft/kanban.db'))
cur = conn.cursor()
cur.execute("SELECT id FROM tasks WHERE status IN ('done','archived')")
done = {r[0] for r in cur.fetchall()}
prunable = [d for d in os.listdir('<haft-repo-root>/.worktrees') if d in done]
```

Prune only `done`/`archived`. Keep `running`, `ready`, `blocked`, `triage`,
`scheduled`. Worktrees with NO matching task (orphan slugs) usually have unmerged
branches — surface them to JP for a decision rather than auto-deleting.

Remove with `git worktree remove --force <path>` run from the MAIN repo root
(`<haft-repo-root>`), not from inside the worktree.

### Terminal-state race and external-worktree guard

- Take the board snapshot immediately before deletion, then re-check it after
  the first bulk-removal pass. Review cards can become `done` while deletion is
  running; perform a second pass until no eligible registered task worktrees
  remain.
- Restrict automatic removal to paths under
  `<haft-repo-root>/.worktrees/<task-id>` whose board status is exactly
  `done` or `archived`, whose `git status --porcelain` is empty, and whose path is
  not the CWD of a live process. Keep `ready`, `running`, `review`, `blocked`,
  `triage`, `todo`, and `scheduled` worktrees.
- `git worktree list` may include sibling DevSpace worktrees under
  `<dev-host-home>/.devspace/worktrees/haft-*`. Their hash-like names are not
  reliably board-mappable, so do not bulk-delete them just because they attach
  to the Haft repository. Audit branch, detached state, and working-tree status
  separately; surface unmapped worktrees for an explicit decision.
- If JP explicitly authorizes disposal of the DevSpace set, remove only
  registered worktrees that are clean and have no live-process CWD. Re-check
  `git status --porcelain` immediately before each `git worktree remove --force`;
  skip and report dirty or active paths rather than silently discarding work.
  Treat the observed `du` totals as logical tree size and the before/after `df`
  delta as the actual reclaimed-space evidence.
- Legacy or release worktrees under `.worktrees/` without a task-id mapping are
  also report-only until explicitly approved.

## Hermes state.db reclamation

The orchestrator profile's `state.db` is often the single largest consumer on disk
(7+ GB). It holds all session transcripts. Pruning old sessions reclaims logical
space but does NOT shrink the file — you must VACUUM afterward.

### Procedure

1. **Check current state.** `hermes sessions stats` reports total sessions,
   messages, and the database's logical size (what it would be after VACUUM).
   Compare with `ls -lh ~/.hermes/profiles/orchestrator/state.db` for the
   physical file size. The gap between them is reclaimable space.

2. **Prune old sessions.** Use `hermes sessions prune` with age filters:
   ```bash
   hermes sessions prune --older-than 30 --yes   # start conservative
   hermes sessions prune --older-than 14 --yes   # then more aggressive
   hermes sessions prune --older-than 7 --yes    # if still needed
   ```
   Each pass removes sessions and their messages. Re-run `hermes sessions stats`
   after each pass to see the new logical size.

3. **Free enough space for VACUUM.** SQLite VACUUM creates a temporary copy of
   the database, so it needs roughly 2x the post-prune DB size in free disk
   space. If disk is critically full (< 2 GB free), clean other targets first
   (nested profile home/, caches, /tmp, old logs) before attempting VACUUM —
   it will fail with "database or disk is full" otherwise.

4. **Run VACUUM in background.** On a multi-GB database, VACUUM takes 10+
   minutes. Use `terminal(background=true, notify_on_complete=true)`:
   ```python
   python3 -c "
   import sqlite3, time
   db = '<hermes-home>/profiles/orchestrator/state.db'
   start = time.time()
   conn = sqlite3.connect(db)
   conn.execute('VACUUM')
   conn.close()
   print(f'VACUUM complete in {time.time()-start:.1f}s')
   "
   ```
   Do NOT attempt foreground VACUUM — it will hit the 600s timeout.

5. **Verify.** After VACUUM completes, `ls -lh state.db` should match the
   logical size from `hermes sessions stats`. Run `df -h /` for final disk
   reading.

### Nested profile home/ directory

The orchestrator profile contains a `home/` subdirectory
(`~/.hermes/profiles/orchestrator/home/`) that is a nested copy of `<dev-host-home>`.
It accumulates stale tool caches: `.cargo` (878 MB), `.rustup` (726 MB), `.bun`
(522 MB), `.haft` (194 MB), `.local` (133 MB), `.codex` (94 MB), `.cua-driver`
(81 MB). These are duplicates of the real toolchains in `<dev-host-home>` and can
be safely removed:
```bash
rm -rf ~/.hermes/profiles/orchestrator/home/.cargo
rm -rf ~/.hermes/profiles/orchestrator/home/.rustup
rm -rf ~/.hermes/profiles/orchestrator/home/.bun
rm -rf ~/.hermes/profiles/orchestrator/home/.haft
rm -rf ~/.hermes/profiles/orchestrator/home/.local
rm -rf ~/.hermes/profiles/orchestrator/home/.codex
rm -rf ~/.hermes/profiles/orchestrator/home/.cua-driver
```
This typically reclaims 2+ GB. The `home/.hermes/` subdirectory is small and
contains profile-specific config — leave it alone.

See `references/this-host-layout.md` for exact paths, sizes, and board locations.
See `references/ci-runner-provisioning.md` for the Dockerized Haft CI runner lock, secret, UID/GID, label, and post-rebuild verification contract.
