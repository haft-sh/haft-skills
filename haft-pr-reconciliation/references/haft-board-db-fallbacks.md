# Haft board DB fallbacks

Use these only when the Hermes Kanban CLI leaves the board in an inconsistent state after a real PR handoff or merge.

Always use the live Hermes venv Python on this host — currently `python3` — and `from hermes_cli import kanban_db` for both reads and writes. Prefer `kanban_db.connect(board='haft')` over opening a guessed SQLite file path directly; it keeps you on the same schema/view the CLI is using.

## 1) Close a lingering run after the worker already moved the card to `review`

Symptom:
- task status is `review`
- PR handoff comment exists
- `current_run_id` is still set / run still shows active

Pattern:
- load `python3`
- import `hermes_cli.kanban_db`
- inside `write_txn`:
  - verify the task is already `review`
  - call `kanban_db._end_run(...)` with outcome/status like `reclaimed`
  - insert a durable `task_events` status row so audit history shows the reconciliation

Use summary text like:
- `review status already set; orchestrator reconciled lingering run metadata after PR handoff`

## 2) Mark a just-merged review card done when `hermes kanban complete` refuses it

Symptom:
- PR is merged and merge commit is confirmed
- task is still `review`
- `hermes kanban complete <task>` prints something like `unknown id or terminal state`

Recommended sequence:
1. add a board comment first with PR URL, merge SHA, and exact verification evidence so the audit trail is visible even if the CLI completion path is broken
2. run the DB fallback
3. re-run `hermes kanban --board haft show <task-id>` and confirm the card now reports `status: done`, `completed:` timestamp, and a populated `Result:` block

DB update requirements:
- set `status='done'`
- set `completed_at=<unix timestamp>`
- set `result=<merge summary with PR URL + commit + verification>`
- clear `claim_lock`, `claim_expires`, `worker_pid`, `current_run_id`
- insert a `task_events` row with `kind='status'` and payload `{"status":"done"}`

Working pattern:
```python
import json, sys, time
sys.path.insert(0, '<hermes-agent-path>')
from hermes_cli import kanban_db

TASK_ID = 't_...'
BOARD = 'haft'
result = {
  'summary': 'Merged PR #... (HV-...).',
  'pr_url': 'https://github.com/<github-org>/haft/pull/...',
  'merge_commit': '<sha>',
  'verification': [
    'GitHub Actions CI: bun test · typecheck · build (success)',
    'git diff --check HEAD~1..HEAD (pass)',
    'bun test tests/health.test.ts (pass)',
  ],
}

conn = kanban_db.connect(board=BOARD)
try:
    now = int(time.time())
    with kanban_db.write_txn(conn):
        prev = conn.execute(
            'SELECT status,current_run_id FROM tasks WHERE id=?',
            (TASK_ID,),
        ).fetchone()
        if prev is None:
            raise SystemExit('unknown task')

        conn.execute(
            "UPDATE tasks SET status='done', completed_at=?, result=?, claim_lock=NULL, claim_expires=NULL, worker_pid=NULL, current_run_id=NULL WHERE id=?",
            (now, json.dumps(result, separators=(',', ':')), TASK_ID),
        )
        conn.execute(
            "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) VALUES (?, ?, 'status', ?, ?)",
            (TASK_ID, None, json.dumps({'status': 'done'}), now),
        )
finally:
    conn.close()
```

Do not leave the card in `review` just because the CLI rejected the transition.

## 3) Archive done cards older than 48 hours

In this environment, `hermes kanban archive` takes explicit task ids; it does not accept an age threshold.

Pattern:
1. query the board DB for `done` tasks with `completed_at < now - 48h`
2. archive the returned ids explicitly via `hermes kanban --board haft archive <task-id...>`

Working query pattern:
```python
import sys, time
sys.path.insert(0, '<hermes-agent-path>')
from hermes_cli import kanban_db

conn = kanban_db.connect(board='haft')
try:
    rows = conn.execute(
        "SELECT id, title, completed_at FROM tasks WHERE status='done' AND completed_at IS NOT NULL AND completed_at < ? ORDER BY completed_at ASC",
        (int(time.time()) - 48 * 3600,),
    ).fetchall()
    for row in rows:
        print(row['id'], row['title'], row['completed_at'])
finally:
    conn.close()
```

Then archive each returned id with the CLI so the UI stays clean.

## 4) PR/card mapping queries against the live board schema

When you need to map an open PR to a Haft card and the CLI cannot do it directly, query the board DB — but do it against the live schema, not guessed columns.

Observed durable pitfall:
- the live `tasks` table uses `body`, not `description`
- ad hoc queries that assume `description` fail with `sqlite3.OperationalError: no such column: description`

Safe sequence:
1. inspect the schema first with `PRAGMA table_info(tasks)`
2. search `title` + `body` for HV ids, PR provenance, or key phrases
3. only widen to broader keyword matching if exact provenance is absent

Working pattern:
```python
import sys
sys.path.insert(0, '<hermes-agent-path>')
from hermes_cli import kanban_db

conn = kanban_db.connect(board='haft')
try:
    for row in conn.execute('PRAGMA table_info(tasks)'):
        print(dict(row))

    rows = conn.execute(
        'SELECT id, status, title, body FROM tasks'
    ).fetchall()
    needle = 'hv-341'
    for row in rows:
        text = ((row['title'] or '') + '\n' + (row['body'] or '')).lower()
        if needle in text:
            print(row['id'], row['status'], row['title'])
finally:
    conn.close()
```

If exact provenance is still missing after that search, keep the PR blocked rather than forcing an implied mapping from a completed or only vaguely related card.

## 5) Cleanup order after merge

After merge confirmation and card completion:
1. remove the worktree
2. delete the local branch
3. `git fetch --prune origin`
4. verify the worktree paths are actually gone

## 6) Reporting rule

When the DB fallback was required, say so plainly in the reconciliation report and include why the CLI path was bypassed. Future runs should treat this as an environment quirk to work around, not as a reason to skip board completion.
