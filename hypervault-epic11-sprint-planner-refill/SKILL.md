---
name: hypervault-epic11-sprint-planner-refill
description: Refill the Hypervault EPIC 11 queue for up to four concurrent workers by promoting dependency-safe scheduled cards, separating executable reserve from visual trackers, and seeding new worktree-backed runway cards with explicit branch/workspace metadata.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Hypervault EPIC 11 sprint planner refill

## When to use

Use for the slow-cadence Hypervault planner cron when EPIC 11 is the live lane and the board needs more executable Ready or Scheduled runway.

## Rules

1. Read live `stats`, `ready`, `scheduled`, `running`, and `review` first.
2. Count executable cards separately from visual trackers like `[EPIC ...]` and `[PHASE ...]`.
3. Treat `ready < 3` as thin and `ready <= 1` as urgent refill.
4. First unblock dependency-safe EPIC 11 scheduled cards before inventing new work.
5. Re-read live board state after **every** unblock, create, or schedule step.
6. Pre-seed every new executable card with:
   - `workspace_kind=worktree`
   - repo-root anchor `workspace_path=<hypervault-repo-root>`
   - explicit `branch_name`
   - expectation that Hermes will materialize the checkout under `<hypervault-repo-root>/.worktrees/<task-id>`
7. Keep at least 4 executable Ready cards and at least 4 executable Scheduled-reserve cards when docs support it.

## Audit-followup cleanup-lane refill pattern

When the live Hypervault lane has pivoted from older EPIC 11 tracker work to the 2026-06-26 professional-code-audit cleanup lane, do **not** keep refilling from visual EPIC/PHASE tracker cards by inertia.

Use this sequence:
1. Re-read live `ready`, `scheduled`, `running`, and `review` first.
2. Count executable cards separately from visual trackers.
3. If Ready is below the four-worker target and an existing dependency-safe scheduled executable card already exists, unblock that card before creating anything new.
4. If Scheduled is numerically non-empty but most of it is visual trackers, report the executable reserve explicitly and do not count tracker-only runway as healthy depth.
5. After promoting the existing scheduled executable, seed deeper Scheduled reserve directly from the audit's large-module and browser-smoke recommendations.
6. If Ready has already fallen below the floor (for example Ready=2) and Scheduled contains only visual trackers, restore depth in one pass: add enough dependency-safe executable audit cards to bring Ready back to 4 immediately, then park the next 4 executable follow-ons in Scheduled so the board exits the pass with both a claimable buffer and real reserve.
7. Before finalizing new audit cards, verify every named test file or script against the live repo rather than trusting drafted card text. Prefer a broad authoritative inventory such as `search_files(pattern="*.test.ts", target="files", path="tests")` and then choose the nearest live focused suite; do not leave cards pointing at nonexistent focused tests.
8. If Ready contains an off-lane planning/recommendation card or another item that is not genuinely worker-ready (for example missing `branch_name` on a worktree card), move it out of Ready before counting queue depth. Do not let a non-claimable planning card mask a real refill defect.
9. Apply the same rule to assigned follow-up cards that are not clean claimable code runway yet. If a Ready card is already assigned, lacks worker-neutral branch metadata, or belongs to a different lane (for example an image-generation follow-up or planning-only slice), park it back in `scheduled` with a short queue-hygiene note before you measure executable Ready depth.
10. Keep the new reserve cards in `scheduled` unless one is immediately needed to restore the Ready floor.
11. When restoring Ready from an already-`scheduled` executable card, use `hermes kanban unblock <task-id> --reason ...` rather than `promote`. In current Hermes CLI behavior, `promote` only applies to `todo`/`blocked`; it will refuse a `scheduled` card. Treat `unblock` as the standard scheduled→ready refill move and re-read live board state immediately after.
12. If live `scheduled` contains only visual trackers and Ready has already fallen to one executable card, do not waste time hunting for stale referenced card numbers from older refill notes. Treat executable Scheduled reserve as zero and seed a fresh batch in one pass: restore Ready to four claimable cards, then park at least four additional executable follow-ons in Scheduled.
13. If Ready is empty and the most relevant non-done card is a broad bug/debug intake or lane umbrella with concrete findings already recorded in comments, do not simply promote that intake back to Ready. Keep the intake parked as tracking context, extract the verified findings into 2–3 bounded executable cards, and make those the claim path instead. Prefer one card per independently-fixable seam (for example request-contract mismatch, redacted status/readiness projection drift, and sanitized provider-error surfacing) so the board gains real low-collision runway rather than a vague "debug this whole area" placeholder.
14. When splitting a broad intake into executable runway, prefer the newest dated doc referenced by the live card comments or current lane over older roadmap text alone. Example pattern: a newly added guardrails/demo doc can be the right source slice for the concrete child cards even when the older master roadmap still describes the broader product lane.
15. After that split, leave at least one follow-on child in `scheduled` if the fixes touch the same route/UI surface and would otherwise collide in Ready. Count only the new executable children toward runway depth; the original intake/umbrella card remains context, not reserve.
14. When creating that fresh batch from the audit lane, derive candidate slices from the live repo rather than historical card IDs alone: sanity-check current hotspot modules (for example line counts / residual dense helper clusters) and confirm the focused verification files actually exist before writing the new card bodies.
15. Before assuming an older audit recommendation still needs new queue depth, re-measure the current hotspot files directly. In Hypervault, `wc -l` across the previously-audited files is a fast sanity check: if `apps/web/src/App.tsx`, `apps/server/src/agent/publish.ts`, or `apps/server/src/routes/document-upload*.ts` have already shrunk materially, stop seeding more cards against them by inertia and move the reserve to the live large modules instead.
16. Current audit-lane recalibration example: if `publish.ts` is already thin again, `App.tsx` is no longer monolithic, and `document-upload-commit.ts` / `document-upload-planning.ts` are small, the next reserve should shift toward still-large modules such as `html-profile.ts`, `local-graph.ts`, `lineage.ts`, or `reader.ts` rather than reopening already-drained audit themes.
17. Live-board race nuance: workers can claim newly-created Ready cards during the same planner pass. After every create/schedule/unblock batch, re-read `running`, `ready`, and `scheduled` again before finalizing. If the Ready floor was restored briefly but active workers immediately consumed that runway, use existing scheduled executable cards first to restore the target Ready depth in the same pass rather than reporting stale counts from a pre-claim snapshot.
18. Rename-drift checkout nuance: the Hypervault board/repo can keep historical names in cards, repo URL, and stored worktree metadata while the live checkout directory on the host has already been renamed (for example `haft`). If `<hypervault-repo-root>` is missing, do not stop at the first path failure. Reconcile by reading the live repo's `AGENTS.md` rename note and checking `git rev-parse --show-toplevel` in the actual checkout, then continue planning against that live repo for docs/tests/file verification.
19. Repo-anchor precedence under rename drift: when the cron prompt, older cards, or historical docs still mention `<hypervault-repo-root>` but the live repo `AGENTS.md` explicitly promotes a new canonical repo/worktree root (for example `<haft-repo-root>` and `<haft-repo-root>/.worktrees/<task-id>`), treat the live `AGENTS.md` guidance as the current board doctrine for newly seeded executable cards. Seed new worktree cards with the live repo-root anchor and branch metadata that current workers can actually claim. Do not keep stamping newly created runway with the stale legacy anchor just because older scheduled cards still carry it.
20. Legacy-anchor reserve hygiene: after a rename migration, older scheduled cards may still be executable in title/body but carry stale `workspace_path` metadata pointing at the historical root. Do not count those cards as healthy reserve until they are reconciled to the current repo-root anchor or otherwise intentionally retired. It is acceptable to leave them parked during the refill pass while you seed fresh Ready/Scheduled runway with clean current metadata; just report that the legacy-anchor cards were excluded from reserve counts.

Concrete queue-hygiene example from a live audit-followup refill:
- `HV-560` appeared in Ready but was an assigned image-generation follow-up with `workspace_kind=worktree` and no `branch_name`
- correct planner action was to move it back to `scheduled` so it stopped inflating executable Ready depth
- after that correction, unblock existing dependency-safe audit cards first (`HV-569`, then `HV-575`) before seeding deeper reserve
- then add any missing Scheduled runway only after the real Ready count is restored

Concrete example from a live refill:
- Ready sat at 3 executable cards
- Review held `HV-550`
- Scheduled contained only one executable (`HV-553`) plus visual trackers
- Correct action: unblock `HV-553`, then seed deeper Scheduled reserve with `HV-555` through `HV-558` covering publish helper seams, document-upload normalization seams, SourceEditorPanel presentational seams, and a post-`HV-550` App.tsx subtree extraction

Reference: `references/hypervault-audit-followup-four-worker-refill-example.md`
Additional example: `references/hypervault-audit-followup-thin-ready-with-offlane-planning-card-example.md`
Ready-hygiene reference: `references/hypervault-ready-hygiene-before-refill.md`
Tracker-to-runway example: `references/hypervault-new-lane-planning-runway-from-trackers-example.md`
Reference: `references/hypervault-epic12-production-mode-refill-from-empty-ready.md`
Additional reference: `references/hypervault-epic12-ready1-with-mixed-scheduled-reserve-example.md`

## EPIC 12 production-mode refill pattern

When the live lane has shifted from older cleanup or tracker-only work into the production server mode program, do not keep counting EPIC/PHASE trackers as reserve and do not strand execution behind them.

Use this sequence:
1. Re-read live `stats`, `ready`, `running`, `review`, and `scheduled` first.
2. If `ready=0` or otherwise below the normal floor and Scheduled is mostly visual EPIC/PHASE cards, treat executable reserve as thin even if Scheduled looks numerically healthy.
3. Prefer small dependency-safe implementation slices from the production plan before broad infra follow-ons. Good first Ready choices are Phase 5 documentation/runbook slices and tightly bounded Phase 0 verification slices when the repo already has supporting templates/scripts/tests.
4. Before writing card text, verify the live repo already contains the anchors you plan to cite: deploy templates, smoke/backup scripts, and exact focused tests. Do not create cards that point at imaginary deployment files or stale test names.
5. For Phase 5, split the runway into worker-sized slices instead of one broad hardening blob. A good early ladder is:
   - deployment template pack + environment inventory
   - backup / restore / rollback runbooks
   - production smoke CLI go/no-go tightening
6. For Phase 0, a good bounded follow-on is focused EC2/public exposure verification for docs and operator/admin denial rather than broad deployment work.
7. If an EPIC 12 child automation lane already exists only as tracker/spec material, seed the first executable reserve card at the route-family / fail-closed policy seam before the full ingest implementation card. Keep the broad ingest implementation parked until the policy/principal/service-token groundwork exists.
8. Keep Ready limited to low-collision cards when workers are already active on adjacent EPIC 12 slices; park deeper reserve in Scheduled.
9. Re-read every newly created worktree card and confirm `status`, `assignee=null`, repo-root `workspace_path`, and non-null `branch_name` before counting it.
10. When Scheduled includes a mix of executable worktree cards and scratch/future placeholders, count only the executable worktree cards as real reserve. Scratch cards can stay parked, but they do not satisfy external-worker runway depth.

Concrete live refill example:
- Ready had fallen to `0` while Running held two unrelated queue items and Review held several EPIC 12 cards.
- Scheduled looked full numerically but was mostly `[EPIC 12]` / `[PHASE ...]` trackers plus one future automation implementation card.
- Correct refill was to add two claimable Ready cards:
  - `HV-630` deployment template pack + environment inventory
  - `HV-631` backup/restore/rollback runbooks
- Then add deeper Scheduled reserve:
  - `HV-632` production smoke go/no-go CLI tightening
  - `HV-633` EC2/public exposure verification
  - `HV-634` automation route family + fail-closed policy seam
- Each new card used `workspace_kind=worktree`, `workspace_path=<hypervault-repo-root>`, explicit worker-neutral branch names, and unassigned status.

Second concrete EPIC 12 refill example:
- Ready sat at `3`, Running was `0`, and Review was `0`, so the board was not empty but the four-worker claimable buffer was still thin.
- Existing Scheduled reserve already contained a clean executable Phase 2 card with worktree metadata (`HV-PROD Phase 2 authenticated principal propagation and audit actor attribution`).
- Correct first move was to `unblock` that existing executable card into Ready instead of creating a fourth Ready card from scratch.
- After restoring Ready to `4`, the next reserve should come from the latest live Phase 4 / Phase 5 repo anchors rather than more tracker cards: admin dashboard overview/provider hardening, production smoke/operator-pack drift guard, and backup/restore/rollback evidence-contract alignment.
- Before creating those reserve cards, verify the exact live anchors exist in the repo: `tests/admin-dashboard-route.test.ts`, `tests/production-smoke-script.test.ts`, `tests/catalog-store.test.ts`, `docs/2026-06-29-production-deployment-operator-pack.md`, `docs/2026-06-30-production-backup-restore-rollback-runbooks.md`, and the checked-in `deploy/` templates.
- Park those new cards back in Scheduled immediately after create, then re-read Ready and Scheduled again; the board counts after the mutation, not the planner's intent, are authoritative.

## Late-audit seam targeting refinement

When the audit-followup lane has already landed the first large-file splits, do not keep creating follow-on cards against the old top-level filename by inertia. Re-check where the remaining complexity actually lives, then seed the next card against that live seam.

Current Hypervault examples:
- After `HV-575`, `apps/server/src/routes/document-upload.ts` became thin route wiring. The next real cleanup surface moved into `apps/server/src/routes/document-upload-commit.ts`, especially `planSingleDocumentImport()` and adjacent normalization/collision/write-planning helpers. New runway should target that helper module, not keep pretending the route file is still the hotspot.
- After `HV-579` becomes the publish bookkeeping split, the next publish follow-on should usually target the remaining pure planning/assembly work in `apps/server/src/agent/publish.ts` — request normalization, target validation, payload/manifest assembly, privacy-lint input shaping, and dry-run response preparation — while keeping commit-side audit/registry/catalog effects out of scope.

Planner rule:
1. Before creating the next audit cleanup card, sanity-check the current hotspot file/function rather than copying the previous card title pattern.
2. If earlier refactors moved most logic into a helper module, name the new card after that helper module and specific residual seam.
3. Keep the verification set aligned with the same contract surface; expand only when the new helper seam truly widens coverage.

## Proven refill pattern

When the lane is on durable handles / resolver modes / command delegation:

### Promote first
- HV-437 publish-preflight resolver mode
- HV-438 plugin-handoff resolver mode
- HV-441 direct-route vs command parity coverage

### Then seed next runway
- `agent.move_block` durable-handle targeting
- `agent.document_patch` durable-handle targeting
- `agent.unpublish` durable-handle targeting
- publish-preflight consumer integration
- plugin-handoff consumer integration

### Post-handle refill pattern when Ready is thin and Scheduled contains only visual trackers
If the active review queue already contains the remaining typed-route handle cards and Scheduled reserve is tracker-only, keep EPIC 11 moving by seeding the next concrete worker-sized read-model and command-registry slices directly from the dated roadmap/contracts.

For a later live-board example where `ready` hit zero while Scheduled still held only local-graph follow-ons, and the refill widened the queue with `HV-457` through `HV-461` (preview resolver + effectful command delegation runway), see `references/hypervault-epic11-preview-resolver-and-effectful-delegation-refill-example.md`.

Put into **Ready** first:
- compare-context link projections on owner-local comparison descriptor/candidate read models
- owner-local tag page API route backed by manifest/properties projection
- shared command descriptor registry for palette + agent discovery metadata

Keep in **Scheduled** behind those Ready cards:
- reader tag-route links + owner-local tag page view (after tag-page API route)
- bounded current-page local-graph neighborhood route
- reader local-graph panel/view (after local-graph route)
- owner-local command discovery route (after shared descriptor registry)

This keeps the queue aligned with roadmap phase-8 relationships/reader niceties and phase-9 command-delegation runway without inventing a new epic or parking workers behind review-only work.

### Duplicate/residual Ready cleanup before refill
Before counting Ready capacity or promoting follow-ons, check whether any apparent Ready card is already implemented on `master` under an older card/PR and only reappeared as residual runway. If so:
- verify the older implementing card/PR/merge commit really covers the scope
- add a reconciliation comment naming the superseding card/PR
- move the residual card out of Ready immediately (complete it as already implemented on master)
- only then refill from the next dependency-safe EPIC 11 card

Concrete EPIC 11 example from live board maintenance:
- `HV-447` was a residual duplicate of already-merged `HV-332` (compare context links)
- after removing `HV-447`, the next dependency-safe follow-on to unblock was `HV-450`
- to restore depth, a good replacement Ready card was a bounded compare-context status route, while deeper Scheduled reserve could extend local-graph asset nodes/edges and citation nodes/edges

Use this pattern whenever a stale/refilled Ready card would otherwise make the queue look healthier than it really is.

### Scheduled-reserve metadata reconciliation before counting runway
Before treating an existing `scheduled` executable card as real reserve, inspect whether it already carries claimable worktree metadata:
- `workspace_kind=worktree`
- repo-root anchor `workspace_path=<hypervault-repo-root>`
- worker-neutral `branch_name`

If an older scheduled executable card is still `scratch`, has no branch, or is otherwise missing claim-time metadata, reconcile the stored metadata first instead of counting it as healthy reserve. Then re-read the live card and column counts.

Concrete Hypervault cleanup-lane example from a planner refill:
- `HV-514` was still a valid scheduled product slice, but it was parked as `scratch` with no branch metadata
- before counting it toward executable reserve, update it to `workspace_kind=worktree`, `workspace_path=<hypervault-repo-root>`, and a worker-neutral branch such as `agent/hv-514-remote-publish-credentials`
- only after the metadata fix should it count as executable Scheduled runway

This avoids overstating queue health with cards that look scheduled on paper but would create worker reconciliation churn at claim time.

### Seeding discipline for this pattern
- use `create --json` plus idempotency keys for planner-created runway cards so reruns stay deduplicated
- pre-seed every executable card with exact worktree path + explicit branch before it ever reaches Ready
- add parent links only between real executable predecessors/successors (for example tag-page API -> tag-page view, descriptor registry -> discovery route)
- after **every** create and every schedule step, re-read live counts because `create` lands in `ready` first and the board state, not planner intent, is authoritative
- important live-board nuance: the JSON object returned by `hermes kanban create ... --json` is only the immediate post-create snapshot. If your script schedules or otherwise mutates the card right after creation, that emitted JSON can still say `status: ready` even though the live card is already `scheduled`. Never report or branch on the returned create payload alone; re-query the card or the affected column afterward.
- do **not** hardcode or pre-assume task ids when creating several planner cards in one shell pass. Capture the real id from each `create --json` result (or immediately re-query by title/idempotency key) before `schedule`, `comment`, or `link` calls. An `unknown task` schedule failure can strand newly created executable cards in `ready` and silently overfill the queue.
- safer shell pattern: after each `create --json`, parse the returned JSON immediately into a shell variable (for example with `python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'`) and issue the matching `schedule`/`comment` call **before** creating the next card. Do not reuse guessed ids or rely on later manual transcription from stdout once several create payloads have scrolled by.
- Hermes CLI nuance: `hermes kanban show <task_id> --json` returns a wrapper object with the live card under the `task` key, not a bare task object. When re-checking status after a create/schedule step, read `json["task"]["status"]` (and sibling fields like `branch_name` / `workspace_path`) rather than assuming top-level keys.
- recovery rule: if a create→schedule step fails partway through, stop the batch, re-read live `ready` and `scheduled`, identify the actual ids of the newly created cards, reconcile their intended status immediately, and only then continue seeding more runway. Do not leave accidental extra Ready cards in place and proceed as if the planned counts already hold.
- current Hypervault-host behavior: `hermes kanban create --workspace worktree:<hypervault-repo-root> --branch ...` records the repo-root anchor as the card's stored `workspace_path`, not the literal `.worktrees/<task-id>` materialized path. Treat that as normal for repo-root-anchor seeding unless the operator explicitly asks for the literal per-task path in stored metadata; in that special case, plan a separate metadata-reconciliation step instead of assuming `create` wrote the final literal path for you.
- when scripting card creation, pass the body through a single-quoted heredoc, temp file, or other shell-safe transport if it contains backticks/code spans. Do **not** interpolate a Markdown body with backticks inside a double-quoted shell string: command substitution can silently strip tool names like ``agent.publish`` from the stored card text.
- Hermes CLI create syntax is easy to misremember during planner passes: `hermes kanban create` takes the card title as a **positional argument** and supports `--body`, but not `--title` or `--body-file`. If you want file-backed authoring, write the Markdown to a temp file and pass `--body "$(cat file)"` (or equivalent safe shell capture), then immediately parse the returned JSON for the real task id before any follow-on `schedule` or `comment` call.
- before finalizing new card bodies, confirm that every verification path/script you name actually exists in the live repo. Audit-derived card text can drift toward stale filenames (for example imaginary `browser-smoke.test.ts` or `document-upload-route.test.ts` paths) even when the intended coverage is real; replace them with the nearest live commands such as `bun run test:e2e:smoke`, `tests/document-upload-api.test.ts`, or `tests/document-upload-response.test.ts` before reporting the lane as seeded.
- Hermes CLI discovery syntax is easy to misremember during planner passes: use `hermes kanban stats` for column counts, and use `hermes kanban list --status <status> --json` for machine-readable column reads. Do **not** call a nonexistent `hermes kanban status` subcommand or shorthand like `list ready --json`.
- Hermes CLI scheduling syntax is positional: use `hermes kanban --board hypervault schedule <task_id> "<reason>"`, not `schedule <task_id> --reason ...`. If you use the wrong form after a create, the new card stays stranded in `ready`; immediately re-read live `ready`/`scheduled`, move the card to its intended column, and only then continue the refill pass.
- Live-board dependency nuance: unblocking a `scheduled` card with unmet parents can land it in `todo`, not `ready`, and a later `promote` may refuse unless you `--force` past those parent dependencies. Do not force-push such a card into Ready just to hit counts. Re-read `todo` immediately after the unblock, treat the dependency gate as authoritative, and seed a different dependency-safe Ready card while leaving the gated card in reserve until its parent really lands.
- Create-time dependency nuance: a newly created card with `--parent` can also land in `todo` immediately instead of the usual post-create `ready` state. When seeding dependent reserve this way, do not trust the create payload alone; re-check live `todo`/`scheduled`, then move the card to `scheduled` explicitly if it is meant to be reserve. Finish the pass by confirming there are no stranded executable `todo` cards accidentally created by parent-gated reserve seeding.
- Visual-tracker parent nuance: if an implementation card is intentionally attached to an `[EPIC ...]`, `[PHASE ...]`, or other tracker-only parent for lineage, Hermes may still gate the child into `todo` as if the parent were a real dependency. In that case, verify the parent is truly visual-only, then reconcile immediately: `promote --force` the child into its intended executable state (`ready` for immediate runway or `scheduled` for reserve), add a short queue-hygiene comment explaining that the parent is tracker-only, and only then continue counting Ready depth. Do not leave a claimable worktree card stranded in `todo` just because the tracker link exists.

## Card body shape

Each new card should include:
- planning lane/phase note
- source slices listing exact docs
- narrow scope bullets
- acceptance bullets
- verification commands

## Safety checks

- Do not count visual trackers toward executable reserve.
- Do not move dependency-unsafe cards into Ready just to hit counts.
- If the current docs do not support another concrete slice, report the lane as exhausted instead of fabricating broad epics.
