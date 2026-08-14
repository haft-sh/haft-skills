---
name: haft-ready-worktree-cards
description: "Create and validate claimable Haft Ready external-worker worktree cards without broken assignee/branch/workspace metadata."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, kanban, worktree, orchestration, external-workers]
---

# Haft Ready Worktree Cards

## When to use
Use this when creating, backfilling, or validating **Haft** Kanban cards that should enter the **Ready** lane as claimable external-worker worktree tasks.

This is specifically for the pre-claim board state that external shell workers depend on.

## Goal
Ensure a Haft Ready worktree card is *actually claimable* before it reaches workers, so the board does not advertise broken runway.

## Canonical helper
Use the guarded helper instead of ad hoc DB edits and instead of raw `kanban_create` for Haft Ready external-worker worktree cards:

```bash
python3 <shared-scripts-root>/haft_ready_worktree_card.py create \
  --title "<title>" \
  --body-file /tmp/body.md \
  --priority 95 \
  --branch-name <bare-slug>
```

Validate an existing Ready card with:

```bash
python3 <shared-scripts-root>/haft_ready_worktree_card.py validate <task_id>
```

To create a dependency-gated child in one atomic step, add `--parents` (repeatable or comma-separated). The card is created in `todo` and auto-promotes to `ready` when all parents are done; parent ids must already exist on the board:

```bash
python3 <shared-scripts-root>/haft_ready_worktree_card.py create \
  --title "<child slice>" \
  --body-file /tmp/body.md \
  --branch-name <bare-slug> \
  --parents <parent_id_a>,<parent_id_b>
```

For GitHub-issue intake, follow `references/github-issue-to-ready-card.md`: inspect the live issue, deduplicate against the live board, preserve source context and acceptance criteria, add external-worker PR/test handoff requirements, and separate implementation from post-merge production/operator verification before helper creation and validation.

## Relevance before shape

The helper proves metadata shape; it does **not** prove that the work is still unresolved. Before creating a card or when auditing Ready:

1. compare the full acceptance criteria with current `origin/master` and recent merged PRs;
2. for incident/deploy cards, check whether a later immutable release already proved the repair even if the original failed run remains red;
3. remove completed operator/scratch gates from Ready—they are not external-worker capacity;
4. keep partially delivered cards only when the remaining acceptance scope is concrete and current;
5. immediately before helper creation, re-list Ready and search the board for the failing run, PR, release SHA, and surface keywords; another session may have created the same incident card while this intake was being drafted. For historical duplicate checks through the Hermes CLI, use `hermes kanban --board haft list --archived --json`; `list` does not accept a generic `--all` flag, and omitting `--archived` can hide a prior merged, retired, or superseded owner;
6. if concurrent intake still creates a duplicate, retain the earlier or richer evidence-backed card as canonical, add a cross-link comment on the duplicate, and move the duplicate out of Ready before any worker can claim it. Never leave competing implementations claimable.
7. re-read Ready after the audit because an external worker may claim a legitimate card concurrently.

A validation failure showing `running`, a non-null assignee, and a materialized `.worktrees/<task-id>` path usually means the card was claimed correctly. Do not “repair” it back to Ready.

## Release-gate reconciliation for evidence-backed rollouts

For a production rollout whose upstream certification/evidence card is terminal `done`, do **not** infer activation is approved or its dependent rollout card is claimable. `done` can truthfully mean only that evidence was recorded.

Before promoting or unblocking a rollout:

1. Retrieve the newest authoritative state report and separately verify the deployed build/release identity and public endpoint behavior.
2. Record distinct facts in a concise reconciliation comment: certification outcome, deployed release presence, runtime gate state, quality/relevance status, canary/rollback status, and any human approval still required.
3. Convert newly discovered executable preconditions into worker-neutral helper-created cards and add them as real rollout parents. This keeps dependency state from advertising false readiness.
   - Do this in the same reconciliation pass: draft a narrowly scoped preparation card, helper-create and validate it, link it as a real parent of the activation card, and leave a concise comment naming the new owner and remaining activation gate.
   - Do not leave a concrete prerequisite only in rollout-card prose. If it requires a PR, release handoff, deployment preparation, or an evidence run, it needs a card and dependency edge.
   - Distinguish **release preparation** from **activation**: preparation may produce a disabled-by-default release and operator handoff; activation, canaries, and rollback remain a separate approval-gated rollout step.
   - A worker statement that a deployment is already live is not completion evidence by itself. Independently query the public runtime's health/build identity and the relevant disabled-state/keyword contract; only then complete the deployment card. If that verification succeeds with routing still disabled, retain the activation safety boundary but normalize its blocker to `needs_input` with the exact activation approval required, rather than leaving a stale `capability` block.
4. Keep policy choices (for example released upstream dependency vs an explicitly pinned reviewed build) as an exact operator decision in the rollout comment; do not bury them in a completed evidence card.
   - When the only remaining block is operator approval, surface it proactively in the reconciliation result with exact copy-paste approval text. Do not make the operator rediscover it from historical comments or infer redundant target choices when there is only one live target.
5. Preserve historical failure comments, but add one dated supersession comment when later bounded evidence resolves them. Never rewrite history or treat an earlier failure as live truth.

Use a release contract that separates lifecycle from eligibility: `evidenceRecorded`, `certificationOutcome`, `activationEligible`, `blockers`, `evidenceRef`, and `verifiedAt`. Promotion automation must consume the eligibility/gate facts, not merely whether parent cards are `done`.

If a still-relevant safety/reliability card points to a closed-unmerged PR or obsolete integration base, do not reopen it blindly. Leave a supersession comment with live PR/ancestry evidence, create a fresh helper-backed card against the current integration branch, and link that replacement as a rollout parent.

## Ready-lane invariants
A Haft external-worker worktree card only counts as true Ready runway when all of these are true in the **live board row**:

- `assignee = null`
- `status = ready`
- `workspace_kind = worktree`
- `workspace_path = <haft-repo-root>`
- `branch_name` is non-empty
- the row passes post-write re-read verification

If any one of these is missing, the card is an orchestrator defect, not worker error.

## Branch naming rule
For Haft, branch metadata should be a **bare worker-neutral slug** such as:

- `epic-20-implementation-plan`
- `resend-transactional-email-integration`
- `spec-local-admin-entitlements`

Do **not** prefix Haft Ready-card branch metadata with `jplew/`.

## User hard rule
JP treats broken Ready metadata as an orchestrator failure, not a worker problem. Do not ask the user to remind you about null assignees, branch names, or workspace anchors. The helper path is mandatory specifically so Haft Ready cards are born correct without manual repair.

### Intake precedence: Kanban first
For Haft implementation intake, default to **Haft Kanban tickets first**. GitHub issues are a backup path only for workers or environments that do not have board access. See `references/kanban-first-intake.md`.

When JP says "file an issue" for Haft work, assume he means a Kanban ticket unless he explicitly says GitHub issue. If the task should be external-worker claimable now, use the helper path immediately. If a GitHub issue was opened by mistake for a board-native task, close it with a short reconciliation note and recreate the same acceptance criteria, screenshot evidence, and worker instructions on the Haft board.

#### Cross-repository deduplication before creation
For an intake request that names a repository outside Haft, deduplicate against **open** board cards using the repository identity plus the defect signature and evidence (affected resource/API, error, CI run, or handoff title). A shared credential-free handoff URL is not sufficient identity: unrelated cards may cite the same operational page. Inspect all nonterminal statuses, including triage, scheduled, blocked, review, running, todo, and ready; do not rely on Ready/Todo alone. If the normal board listing cannot search bodies, use a read-only query against the board-scoped database at `<hermes-home>/kanban/boards/haft/kanban.db`, never the legacy/global database, and compare the candidate card's repository, scope, and cited evidence manually. If an equivalent open card exists, return its ID and do not create a duplicate. Otherwise create exactly one helper-backed Ready card with null assignee, repo-root workspace, and a bare worker-neutral branch.

Record the deduplication result in the intake response: candidate IDs inspected, why related cards are equivalent or excluded, and whether creation occurred. Keep credential values and private document bodies out of both the search output and the card body.

## Audit/spec-to-ticket decomposition
When turning a repository audit or implementation plan into multiple externally claimable cards:

1. Read the source from the live checkout and record its immutable baseline commit in every card.
2. Build a surface-ownership map before creating cards; merge overlapping slices or serialize them with real parent links. Do not expose colliding cards in Ready.
3. Keep the first wave to 2–3 independent cards. Create later slices with `--parents` so they land in intentional `todo` until prerequisites are Done.
4. Put concrete acceptance criteria, likely files/tests, security non-goals, and Review handoff requirements in each body. Separate implementation from deployment/live acceptance.
5. Re-read every created card and validate every one; report the Ready wave and dependency-gated backlog separately.

## Creation sequence
1. Draft the task body in a temp markdown file.
2. Run the helper `create` command with a bare branch slug.
3. Confirm the tool output shows:
   - `status: ready`
   - `assignee: null`
   - repo-root workspace path
   - expected branch name
4. If the card cites a screenshot, recording, or other supplied evidence, attach the actual file before handoff. Follow [Kanban evidence attachments](references/kanban-evidence-attachments.md); a chat-upload path or body-only reference is not durable worker evidence. Reconcile the card body against the live attachment list: every filename described as attached must appear in `kanban_attachments` and in the re-read worker context. If an upload is unavailable, revise the body to name exactly which evidence is attached and which remains transient chat context.
5. Re-read the card, confirm its worker context lists every cited attachment, then validate the unchanged Ready invariants before handing it to workers.

## Visual UI issue intake

When JP provides an annotated screenshot for a UI ticket, use `references/visual-ui-intake.md` before helper creation. It covers durable evidence attachment, source/history inspection to distinguish a missing entry point from a missing feature, and screenshot-derived acceptance criteria.

### Copyable metadata controls

For a request to expose an existing internal identifier, token, URL, or path with a copy affordance:

1. Trace the selected-view data model and name the existing canonical field in the card; do not assume a new identifier scheme or backend work is needed.
2. Search the app for an established copy control first. When it already provides clipboard fallback, copied-state feedback, and accessible labeling, require its reuse rather than a second copy implementation.
3. Keep the value display-only unless an edit contract is explicitly requested; it must not enter editable-property forms or patch payloads.
4. Make same-row placement, keyboard-accessible `Copy <value label>` naming, and narrow-layout behavior concrete acceptance criteria.

For a control that looks absent or blank in a themed view, inspect both the rendered component and its base/theme CSS before scoping the card. Record whether the control already has an accessible name and working interaction but loses its visible icon, label, border, or surface contrast. Frame that as a narrowly bounded styling/discoverability repair; do not accidentally request a duplicate control or rewrite the underlying interaction.

### Explorer / Grid navigation regressions

For a report where switching Viewer/Grid or selecting an Explorer folder produces an artifact-unavailable, 404, or blank canvas state, transcribe the **full visible hash route** from the screenshot before scoping the ticket. Then trace the route builder, the top-bar mode-toggle target derivation, and the Explorer folder-click/context-menu handlers together.

- Distinguish a **folder context** route from an **artifact selection** route. A selected directory must not be serialized as `focus` or `selection` unless it is a real artifact under the documented selection contract.
- State the expected recursive browse behavior explicitly when the user asks to see nested descendants; do not assume a folder Grid means only direct children.
- Require transition coverage, not merely route parsing: Viewer → selected folder → Grid; Grid → Viewer → Grid; and the folder context-menu/open-in-Grid path. Include a nested fixture and assert both the canonical route and rendered descendants.
- Preserve valid multi-artifact selection, keyboard/range/toggle semantics, bounded folder loading, route validation, and authorization. Do not prescribe an unbounded Browser fallback just to make the Grid populate.
- Attach the screenshot as durable Kanban evidence and name the attachment plus the observed hash route in the card body.

### Image / media preview sizing and fit regressions

For a report that an image or media asset renders as a tiny, blurry, or cropped strip inside a large empty stage (rather than the complete asset fit to the reader), trace **four** things before writing the card:

0. **Prior-fix code-path verification** — when a merged PR claims to have fixed the same symptom, inspect its diff (`git show <sha> --stat` + file diffs) to confirm it modified the **same component and CSS path the user is actually seeing**. Haft has parallel image-preview code paths: `RemoteArtifactPreview.tsx` (remote artifact click-to-zoom dialog, `.remote-artifact-image-*` CSS classes) and `AssetImagePreview` inside `DocumentCanvas.tsx` (main canvas inline viewer, `.asset-preview-image-*` CSS classes). A fix to one does not fix the other. Identify which path the screenshot shows (check the breadcrumb, URL hash route, and surrounding UI chrome) and verify the prior PR touched that path. If it didn't, the card body must state explicitly: "PR #N fixed component X; the reported clipping is in component Y — a different code path."
1. **Preview URL selection** — find where the inline preview picks its `src`. A common defect is `thumbnailUrl ?? fullSizeUrl`: the inline viewer shows only the derivative thumbnail when one exists. Check the thumbnail generation pipeline's max dimensions (e.g. a ≤96×96 derivative) — a tiny source upscaled into a large stage is the blurry-strip signature. The fix is usually "thumbnail as fast first-paint placeholder, full-size as the final render," not "make the thumbnail bigger."
2. **Fit-to-stage sizing** — inspect the stage container and the media element together. A stage with `overflow:hidden` + fixed `min-height` and an image that only has `max-width/max-height + object-fit:contain` but no sizing that fits it to the stage will render small sources at natural size and can mask content taller than the stage box.
3. **Deployed-bundle confirmation** — fetch the live CSS/JS from the deployed hostname and compare against source (see the deployment-drift-repair skill's `references/client-side-bundle-forensics.md`). This distinguishes deploy drift from an inherent design defect before scoping the fix.

Use vision analysis of the screenshot to confirm the symptom shape (cropped band vs complete, sharp vs blurry, fraction of stage occupied) — this is decisive evidence for whether the cause is a crop, an undersized source, or a missing fit contract.

Acceptance criteria must require: the complete asset (never cropped) fit to the available stage with padding on all axes; a sharp full-size final render; no stage clipping/masking; portrait/landscape/square coverage; and before/after visual evidence on the deployed surface after deploy. Do not let the worker change the thumbnail generation pipeline unless it is the proven root cause.

Watch for a **secondary identity desync** in the same screenshot (e.g. the route's artifactId names one file but the details panel and rendered content show a different file/dimensions). If present, instruct the worker to verify the served record against the route while they have local auth, and file a follow-up card if it is a real stale-identity bug — do not fold it into the rendering fix's scope.

### Rendered document / iframe sizing regressions

For a rendered-view report that shows a document in a shallow strip, blank stage, or clipped frame, trace the **entire owning grid/flex sizing chain** before writing the card. Do not label it merely an iframe defect: `height: 100%`, `min-height: 0`, and `1fr` only work as intended when an ancestor establishes a definite available height. Record the rendered component, shell/frame selectors, and suspected missing height contract as *likely* surfaces, while requiring the worker to confirm the chain.

Acceptance criteria must distinguish the stage from artifact content:
- preview fills the available space beneath the shell header/toolbar;
- long content scrolls inside the stage without clipping;
- desktop and narrow/mobile layouts remain usable; and
- sandbox, referrer policy, view routing, and adjacent reader/source/editor modes remain unchanged.

Do not prescribe a fixed pixel height as the generic fix. Require focused layout regression proof (browser/computed-layout coverage where possible; otherwise a narrow structural/style-policy guard plus visual evidence). See `references/rendered-preview-height-regression-intake.md`.

## Global projection vs. bounded Explorer intake

When a Vault Browser sidebar or summary section is expected to represent a **global** artifact set (for example, Recents), establish whether it is instead derived from the currently materialized Explorer snapshot before filing work:

1. Trace the rendered section's input through its view-model builder to the client/server projection. A helper that sorts `snapshot.nodesById`, loaded tree nodes, or a paged folder response proves only a local-cache view—not global coverage.
2. State the precise mismatch in the card: global user promise versus bounded data source. Cite the renderer, the derivation helper, and the loaded-snapshot field rather than attributing the omission to a particular creation path without evidence.
3. Require a dedicated bounded canonical catalog/index query or equivalent global projection. Do not solve global Recents by eagerly loading the whole Explorer tree or weakening scoped folder APIs.
4. Enumerate all creation/index entry points in acceptance criteria: local/CLI import, remote import, Daily Notes, New/template creation, agent-created artifacts, and other indexed paths. Require fixtures whose eligible entries are intentionally absent from the loaded Explorer snapshot.
5. Require authoritative timestamp ordering and deterministic ties. Treat provenance as conditional: display compact labels only when canonical metadata supports a truthful source classification; specify a neutral/absent fallback rather than inventing provenance.
6. Preserve direct artifact/folder navigation, ownership/authorization boundaries, result limits, and existing bounded Explorer loading. Require both projection/API coverage and UI regression coverage.

## Explorer deletion and configured-root intake

For a report that deleting a Tree Explorer folder apparently succeeds but the folder remains or reappears:

1. Trace the browser delete action through the tree mutation route and the post-delete reconciliation/scaffold path before calling the folder protected. A mutation route may permit a configured root while a later scaffold initializer recreates it.
2. Separate **configured user-visible roots** (for example content/assets) from internal/generated paths (hidden metadata, exports, manifests). The card must never weaken protections on internal/generated paths merely to make configured roots less surprising.
3. State one truthful product contract: either an empty configured root can remain absent and is recreated lazily by the next operation requiring it, or it is a permanent invariant and the UI blocks/refuses deletion with explanatory copy. Never accept a silent-success-then-reappear outcome.
4. Require fixture coverage for empty configured roots, ordinary nested-folder deletion, and the next create/import operation after deletion when lazy recreation is allowed.

For a report that deleting an artifact resets Tree Explorer location:

1. Trace artifact and folder delete flows separately; they can have different client callbacks and mutation receipts even when launched from the same context menu.
2. Inspect expansion state, sidebar scroll preservation, selection reconciliation, and post-mutation focus together. A retained `scrollTop` alone is insufficient when refresh clears selection or focus.
3. Require Finder-like deterministic continuity after a successful single-item delete: next sibling in the same visible order, otherwise previous sibling, otherwise parent folder. Do not select a descendant of a deleted folder or leave the parent while a sibling exists.
4. Require browser coverage using a scrolled nested folder and assert expansion, visible location, keyboard focus, ARIA selection, and failed-delete non-mutation. Preserve multi-select/range/toggle, virtualization, lazy loading, stale-tree handling, and authorization.

## Deployed-regression reconciliation

When a user reports that merged work is absent or broken on a deployed hostname, distinguish a stale rollout from a shipped functional gap before filing the card:

1. inspect the cited PR/merge and current `origin/master`;
2. verify the deployed build fingerprint against the release commit that should contain it;
3. trace the user-visible path end-to-end — selection/input → route → collection filter → rendered projection — rather than treating helper/unit-test presence as proof of reachability;
4. trace asynchronous projections (for example import → queued derivative → worker → catalog/API → UI) separately from their queue-creation code; a queued job is not proof that it executes;
5. if the actual vault/catalog requires authorization, preserve the route gate and state the record-level fact as unknown. Require an authorized, bounded audit and repair path in the card rather than weakening access or inventing a result.

Record the resulting classification and exact evidence in the card body. For tightly coupled Explorer/grid/thumbnail repairs, one large coherent card is appropriate only when the selection model, route/context model, browse projection, and derivative lifecycle must change together; otherwise keep independent work separate.

## Source-plan freshness

Before drafting card bodies, verify the cited plan or audit exists in the canonical checkout **or** in live `origin/master` history. A canonical checkout can be clean yet behind `origin/master`; do not treat a missing local plan file as absent work when its commit is reachable remotely.

- If the source exists only on `origin/master`, fetch without modifying the canonical checkout, inspect the exact blob (for example `git show origin/master:<path>`), and record the path plus immutable source commit in each card body. Do this even when `canonical:check` reports clean/OK: that establishes local integrity but can coexist with an upstream-stale checkout.
- Do not fast-forward a clean-but-behind canonical checkout merely to read a plan during intake; ground the board in the fetched remote commit instead. If the plan's own stated baseline predates the fetched plan commit, cite the fetched commit as the ticket source of truth.
- Tell workers to start from the selected integration base before implementation so the referenced source is present in their worktree. Default to `origin/master`; when JP explicitly directs a shared integration branch, create or verify that remote branch from the immutable plan commit first, cite the branch and SHA in every card, and require workers to branch/rebase from `origin/<integration-branch>` with PR base `<integration-branch>`.
- Before replacing a broad predecessor card with a dependency ladder, inspect its live row. For a terminal predecessor, leave an explicit supersession comment and do not attempt a state mutation; reconcile an active/claimable predecessor out of the runnable queue before exposing overlapping slices.
- When a user supplies a plan path absent from both the canonical checkout and `origin/master`, search fetched refs for the exact path and resolve its source branch plus immutable commit. Cite that source in every card, but keep implementation PRs based on `origin/master` unless the user explicitly selects the plan branch as the integration base. A documentation-review branch is not an implicit code-integration branch.
- Keep the first Ready wave to 2–3 independent cards. Combine tightly coupled remediation, such as a shared persistence primitive with its first migrations, rather than creating colliding worker lanes.

### Priority reprioritization safety

When a user asks to elevate a new epic and demote an existing family of cards:

1. Snapshot the live board and resolve the exact target **task IDs** before any mutation. Use title, branch, and live status to identify the old family; do not use a broad body-text match as the mutation selector, because new cards often cite the old project in non-goals or dependency context.
2. Set the new epic's Ready and dependency-gated cards to the board's established maximum priority, preserving dependency status. A Todo child may share the epic priority without becoming claimable.
3. Demote only the captured nonterminal target IDs. Preserve active claims/status; priority is scheduling policy, not permission to reclaim or interrupt work.
4. Immediately re-read the board and assert: every new epic ID retained the requested priority; every intended old-family ID is below it; and the highest open priority is the requested value. Repair an accidental over-broad mutation before reporting success.

This keeps reprioritization auditable and prevents a keyword in a new card body from silently demoting that same card.
- Before creating cards from a document's suggested-ticket list, build a surface-ownership map: every mutable file, CI workflow, test manifest, or policy rule must have one owning card in the initial backlog. If two suggested tickets overlap, either merge them or move the overlapping surface into exactly one card and name that exclusion in the other card's non-goals. Do not expose overlapping cards in Ready merely because the audit listed them separately.
- When JP asks to turn a complete audit or plan into tickets, seed the entire remediation backlog in the same intake pass. A narrow Ready wave is not a complete backlog.
- **Staged convergence-audit exception:** when the source audit explicitly directs an iterative rollout (for example, “start with one small high-confidence family” and re-evaluate after real-app proof), create only that bounded, independent first family as Ready. Do not turn investigation rows or later behavioral migrations into claimable placeholders merely to satisfy backlog completeness. State in the intake result which findings are intentionally deferred and why; create the next bounded wave only after the specified proof or a fresh decision.
- For a sequential plan, helper-create every slice so each has valid external-worker metadata, then immediately add real parent links so only the first unblocked slice remains `ready` and downstream slices fall to `todo` with `assignee=null`, `workspace_kind=worktree`, repo-root workspace, and branch metadata preserved.
- After linking dependent slices, add a short reconciliation comment to each child explaining that live `todo` status is intentional and authoritative despite the helper's creation-time Ready comment.
- Park independent later work in `scheduled` so the PR-sweep worker can promote it when capacity is available. **Helper lifecycle limitation:** `haft_ready_worktree_card.py create` currently births independent cards in `ready` only; it has no initial-status flag. For a complete staged backlog, create and validate the card first, then immediately run `hermes kanban --board haft schedule <task-id> '<wave/capacity reason>'`. Treat the short Ready interval as an intake transaction: do not report the card as dispatchable until the schedule command succeeds and a board re-read confirms `scheduled`. Do not fake a dependency merely to park independent work. For sequential work, create the external-worker card with this helper, add real parent links immediately afterward, and confirm it lands in `todo` until its parents are done.
- Do not create later sequential slices merely to fill Ready; seed them only when dependencies and claimability can be represented truthfully.
- Finish the intake with a live board re-read that reports the whole plan's Ready, Scheduled, Todo, and blocked counts. For SQLite spot checks, read the board-scoped DB (for Haft: `<hermes-home>/kanban/boards/haft/kanban.db`), not the legacy/global `<hermes-home>/kanban.db`, or newly created helper cards may appear missing. Never describe only the first Ready wave as the complete plan.

### Audit follow-up visibility gates

When an audit says to prove a small initial wave before dispatching higher-risk or less-certain rows, do not leave the remainder implicit in chat history. Create one helper-backed, unassigned worktree **dispatch-gate** card and immediately attach the initial-wave cards as real parents. Its live status must become `todo`, which is intentional even though the helper's pre-link validation expects `ready`.

The gate body must distinguish:

- **sequenced candidates**: items that need evidence from the initial wave but no product decision yet;
- **investigations**: items that need a focused interaction/contract-parity check before implementation; and
- **true decision points**: only cases where preserving established semantics would require a product trade-off.

Name the exact parent cards, source audit commit, remaining surfaces, non-goals, and the required post-parent outcome: inspect merged evidence, deduplicate against live source/board, map mutable-surface ownership, then create collision-free worker-ready child cards. Add a reconciliation comment that live `todo` is authoritative and the historical helper-created Ready comment is pre-link history. This keeps deferred scope durable without falsely advertising it as immediately claimable work.

## CI rescue for an unrelated failure on a source-card PR

When a Review-card PR fails a deterministic CI check that is demonstrably **outside its diff**, preserve the source card as the owner of its intended work and create one independent helper-backed repair lane:

1. Verify the live PR head SHA, run/job URL, failing assertion, retry outcome, and browser/server error signature from raw logs. Treat diagnostic-artifact upload failures (including quota exhaustion) as secondary unless they are the failing test step.
2. Compare the PR file list/diff with the failure surface. State the separation concretely in the source-card comment; do not merely call it unrelated.
3. Search the live board by the failure surface, run ID, and key stack/function name before creating anything; reuse a current repair owner if one exists.
4. If no owner exists, helper-create one unassigned Ready worktree card on a new worker-neutral branch. Scope it to the root failure plus regression proof; explicitly prohibit drive-by changes to the source PR's feature area.
5. Add a compact source-card comment naming the failing SHA/run/job, first failing assertion, repair-card ID/branch, and merge stop. Keep the source card in Review when the board does not support an honest review→blocked transition; the red required check is the live merge gate.
6. Require a green fresh pull-request run on the repaired head before the source PR is considered mergeable. The repair card must stop in Review; do not self-merge either branch.

This pattern separates failure ownership without falsely treating a CI regression as a defect in the feature under review.

## CI rescue for a direct-user PR with no source card

A PR can explicitly declare `Board/card ID: direct user request (no Kanban card)` and later fail CI. That does not remove the need for a durable repair owner.

1. Verify the alert against live GitHub evidence first: canonical run URL, current PR head SHA, latest attempt conclusion, failed job/step, and whether the PR has already advanced.
2. Search the live board by PR number, run URL/ID, and failure surface before creating anything; reuse an existing current repair card if one owns the same defect.
3. If no owner exists and the run is still red, helper-create **one** unassigned Ready repair card. State `source card: none` and cite the PR/run/SHA in its body.
4. When the fix must land in an existing PR, first check whether that source branch is already registered to its source Review card. If it is, the helper will reject duplicate branch metadata with `branch_name already exists on another task: <branch>`. Two paths depending on whether a source card exists:
   - **Source card exists (preferred):** find the existing card (query the board DB by `branch_name` if `hermes kanban list` grep misses it), check its live status, and add a CI-failure evidence comment directly to that card. Do **not** create a new card — the existing card already owns the branch and the PR. This is the correct action when the card is in `review`, `running`, or any active state.
   - **No source card exists:** create the repair with a unique worker-neutral **coordination branch**, state both branches in the body, and require the worker to fetch/check out, commit, and normally push the existing source branch without force-pushing. The coordination branch must not become a duplicate PR.
   If the source branch is not already registered to any card, it may be used directly.
5. Keep scope to the exact live failure surface. For policy failures, prohibit baselines, exemptions, disabling the check, or unrelated behavior changes unless the evidence shows a separate defect.
6. Require a fresh `pull_request` run on the post-repair SHA, then hand off the existing PR for review rather than marking the repair Done or self-merging.

## Security-sensitive remote-write cards

When filing a Haft card that adds a remote mutation capability (especially delegated grants, agent write, vault edits, or remote CLI/API access), do the minimal contract audit before helper creation:

1. Trace the destination route, its route classification/required capability, the shared delegated-grant operation enum, HQ target-operation projection/exchange, and the installed CLI surface.
2. Record the live target capability gap as evidence, but do not encode a transient access failure as a permanent product claim.
3. Lock the card to a distinct, least-privilege operation. Do **not** solve a narrow remote edit need by granting the whole `agent.write` family: endpoint-level operation checks must prevent that grant from reaching unrelated agent commands, creation, publish/unpublish, sessions, or arbitrary vault writes.
4. Require target-bound short-lived grants only; the destination must never receive a central session/refresh credential, and no bearer, raw HTML body, or private path may enter stdout, JSON, audit records, journals, fixtures, PR text, or Kanban comments.
5. Require preview-versus-commit semantics, stale-hash enforcement, replay/unknown-outcome reconciliation, existing atomic snapshot/validation/index behavior, and denied-case coverage. Keep public/CORS/browser-write expansion and production dogfood mutations out of the implementation card unless separately authorized.
6. Include the relevant `docs/security/threat-model.md` checklist and require a focused security review in the PR. Do not claim an older broad security audit is globally closed solely because local hardening exists.

For this class of tightly coupled cross-cutting contract change, one large worktree card is preferable to splitting HQ policy, destination authorization, and CLI support into concurrent cards that could create an unsafe partial state.

## Splitting coupled remediation into independently-claimable cards

When one incident exposes two separable concerns — most commonly a **root-cause fix** plus an **error-visibility / observability / diagnostics** gap that made the incident hard to triage — file them as **two** helper-created Ready cards rather than folding both into one body or one acceptance-criteria list.

- Give each card its own worker-neutral branch slug, scope, and acceptance criteria. The root-cause card owns the fix; the visibility card owns surfacing the underlying error (or a safe bounded projection / stable error code) to operators.
- Cross-link them with **reciprocal `kanban_comment`s** (A names B, B names A), **not** a parent/child `parents=[...]` dependency, when the two can be worked in parallel. A dependency gate serializes work that need not be serial; reciprocal comments preserve discoverability while keeping both cards independently claimable in Ready.
- Use a real parent link only when one card genuinely cannot be evidenced or implemented without the other's output.
- State the relationship and parallelizability explicitly in each card body so a cold-start worker knows the sibling exists and how it bounds scope.

This keeps each card reviewable on its own merits and lets two workers proceed without a false ordering. It is the decomposition counterpart to "Large coherent implementation cards" below: split when the concerns are separable, combine only when splitting would create collisions or unsafe partial states.

## Large coherent implementation cards

JP may explicitly prefer the largest safe slice rather than a ladder of small cards. When that happens, create one Ready card for the full coherent implementation boundary instead of mechanically splitting by subsystem.

A large card is still bounded:

1. Cite the merged/source spec path, source PR or commit, and require workers to start from current `origin/master`.
2. State the architecture decisions that are already locked so the worker does not reopen product/security choices.
3. Enumerate the expected implementation surfaces, test matrix, verification gates, and PR handoff requirements.
4. Separate implementation from live operations. A large auth/infra card may deliver migration/backfill tooling and a rollout runbook while explicitly forbidding production backfill, environment mutation, deployment, or destructive dogfood proof until a separately reviewed operator action.
5. Name deferred features and non-goals so “large” does not become unbounded scope.
6. Keep the card unassigned and helper-created in Ready with one worker-neutral branch; validate it after creation and re-read the live body/metadata.
7. In the handoff, require one PR against the documented base, exact verification results, known risks, and a stop in Review rather than self-merge or self-completion.

Use a large card only when the surfaces are tightly coupled enough that splitting would create transaction/schema/API collisions or partial unsafe states. For independent workstreams, keep using a small Ready wave and dependency-gated follow-ons.

## Validation semantics
`validate` is for **pre-claim / Ready-state** troubleshooting.

### Newly linked dependent cards

Prefer creating dependency-gated children directly with `--parents`, which lands them in `todo` atomically with their edges already verified. For cards created that way, `validate` derives the expected status from live parent state: it accepts `todo` while any parent is open and `ready` once every parent is `done`. The helper reports the parent IDs, so no reconciliation comment about a stale "Ready" creation comment is needed.

The legacy serial pattern (create a structurally valid Ready row, then attach a parent link afterward) is still supported for cards whose parents do not exist yet at creation time. For that path:

1. create the parent card;
2. create one child with the helper and immediately add its real parent link;
3. re-read the child and confirm the live status became `todo` while `assignee=null`, `workspace_kind=worktree`, repo-root workspace, and branch metadata remain intact;
4. if `validate` now reports only `status is 'todo', expected 'ready'`, treat that as the expected dependency gate—not a broken card (note: `validate` auto-detects parent links and will instead report `ok: true` with the parents listed, so this manual interpretation is only for edge cases);
5. add a reconciliation comment when the helper's historical creation comment says “Ready,” explicitly stating that live `todo` status is intentional and authoritative;
6. run helper validation again only after the parent completes and the child promotes to live `ready`.

Do not force a dependency-gated child back to Ready merely to satisfy the validator.

Once a worker claims a card, normal live state changes mean it should no longer satisfy the Ready invariant:
- `status` becomes `running`
- `assignee` becomes non-null
- `workspace_path` materializes under `.worktrees/<task-id>`

So a failed validation on a claimed card is not automatically a bug. First check whether the card is still supposed to be in the Ready lane.

If JP intentionally wants Hermes dispatcher pickup instead of external ChatGPT/DevSpace pickup, it is valid to reassign a previously claimable card to a real Hermes profile such as `orchestrator`. That intentionally breaks the external-worker `assignee=null` invariant; use broader Kanban/orchestrator procedures to dry-run and dispatch it rather than treating helper validation failure as a defect.

## Pitfalls
- **Helper-only intake:** Create every Haft external-worker Ready worktree ticket with `<shared-scripts-root>/haft_ready_worktree_card.py create`; never substitute raw `kanban_create` as a shortcut. In particular, native `kanban_create` requires a named assignee and has no `branch_name` input, so it cannot produce a valid unassigned Haft Ready worktree card. The helper seeds the null assignee, repo-root worktree anchor, bare branch slug, and Ready state together.
- **`kanban_create` with an unknown assignee silently rots:** the dispatcher SILENTLY DROPS a card whose `assignee` is not a real Hermes profile — the card sits in `ready` forever, never dispatched, with no error surfaced to the creator. There is no validation warning at creation time. Before ever using `kanban_create` for a dispatched card, confirm the assignee exists (`hermes profile list`). For Haft external-worker cards this is moot because the helper uses `assignee=null` (workers self-claim), but if you reach for `kanban_create` for a Hermes-dispatched card and invent a profile name like `devspace-worker`, the card will look healthy on the board and never run. If you discover such a card, archive it and recreate via the correct path rather than leaving a dead-but-visible card in the queue.
- **Malformed pre-claim card recovery:** Repair the existing card **in place**; do not create a duplicate merely because `assignee`, `branch_name`, or workspace metadata is wrong. Before returning it to Ready, clear `assignee` to null, seed a bare worker-neutral `branch_name`, restore `workspace_kind=worktree` and the repo-root `workspace_path`, clear stale claim/run state as appropriate, add a reconciliation comment, then run helper `validate` and re-read the card. Recreate only when the original card itself is irreparably wrong (for example, its scope/body or dependency graph must be replaced), not as a shortcut for metadata repair.

  A raw `kanban_create` cannot produce a valid unassigned Haft Ready worktree card because it requires a named assignee and does not accept `branch_name`; treat that as an intake/orchestrator defect. If the board CLI has no metadata-repair command, use the board's documented transactional DB fallback only after identifying the board-scoped database and exact task row. Update the existing row atomically, clear stale `current_run_id`/claim/block fields, append an auditable reconciliation event or comment, and immediately prove the result with the helper plus a live board re-read. When the body cites an implementation branch already in progress, choose a distinct bare worker-neutral coordination branch for the card metadata so the card does not collide with the implementation branch's ownership.
- Do not create Haft Ready worktree cards with a named assignee unless JP explicitly wants that. Default is unassigned/null until worker claim.
- Do not use `.worktrees/<task-id>` as the Ready-lane workspace anchor; use the repo root `<haft-repo-root>`.
- Do not treat a historical blocker comment as stronger than the live `status`.
- Do not count a Ready card as healthy just because it is visible in Ready; verify branch/workspace/assignee metadata.
- When invoking the helper through a shell, quote ticket titles and user-provided CLI examples with **single quotes**. Backticks inside double-quoted titles become shell command substitutions, which can corrupt the card title and run an unintended local command. After creation, re-read the live card and verify its exact title as well as its body and Ready metadata. If an accidental card is created before anyone claims it, archive/delete it and recreate it cleanly rather than leaving a malformed duplicate in the queue.
- **Body prose vs. helper metadata drift:** after creation, confirm any metadata the body *describes* (branch name, workspace, base branch) matches what the helper actually *stored*. If they diverge, add a reconciliation comment naming the live value rather than leaving a contradiction for the worker. This bites most on non-standard cards (e.g. integration-branch sync cards) where the body explains an override.

## Priority positioning for new epics

When JP says "lower priority than X cards" or "below Y on the board":

1. List the live board and find the reference family's actual priority values. Do not guess from memory — priorities shift.
2. Choose a priority number strictly below the reference family's minimum. A gap of 10 is conventional (e.g. BBT at 40 → new epic at 30).
3. Apply the same priority to all cards in the new epic. Dependency gating (not priority) controls execution order within the epic.
4. Verify in the post-creation board re-read that the new cards sit below the reference family and above any unrelated lower-priority work.

This is distinct from "Priority reprioritization safety" above, which covers elevating a new epic *and* demoting an existing family. This section is for the simpler case: position new cards relative to an existing family without mutating the existing family.

## Dependency-gated epic ladders

When turning an implementation plan into a full external-worker ladder, use `references/dependency-gated-epic-seeding.md`. Keep only the independent first wave in Ready; helper-create cards with valid worktree metadata, keep later dependent slices in Todo with real parent links, and validate each card when it enters Ready.

### Spec-document decomposition

When the source is a spec with explicit slices, phases, or migration steps, use the spec's own structure as the card boundaries. Do not invent a different decomposition. Each card body should cite the spec path and the specific sections it implements, so a cold-start worker can read only the relevant parts.

### Requested Jira-like ticket prefixes

When JP asks for Jira-like identifiers, make the prefix part of every **card title**, not merely the body or branch name. Use one stable zero-padded series for the whole intake, for example `PERF-000 — Measurement baseline`, then `PERF-001 — ...`.

- Reserve `-000` for an explicit shared measurement/foundation card only when the source requires evidence before behavior changes; otherwise start at `-001`.
- Keep the semantic package title after the prefix. Do not substitute opaque task IDs for the requested human-readable key.
- Use the same prefix family in branch slugs and dependency/handoff prose so workers can scan the board and graph reliably.
- Allocate the prefix once per source plan before helper creation (for example `DND-01` through `DND-07` for one Finder drag/drop ladder). Do not reuse a family across unrelated plans, and do not leave a later slice without a prefix merely because the user named the convention on an earlier intake.
- The helper validates worktree metadata, not human-facing keys: post-write verification must also confirm the exact prefixed title, branch slug, and parent links match the intended ladder.
- Preserve the external-worker metadata rules: the prefix is a naming convention, not a reason to create a parallel issue tracker or duplicate card.

### Batch creation and linking

The helper now accepts `--parents`, so dependency wiring is a **single atomic step** per card — no separate `kanban_link` pass required:

```bash
python3 <shared-scripts-root>/haft_ready_worktree_card.py create \
  --title "<child slice>" \
  --body-file /tmp/body.md \
  --branch-name <bare-slug> \
  --parents <parent_id>          # repeat the flag, or comma-separate: t_aaa,t_bbb
```

Semantics of `--parents`:
- Every parent id must already exist on the board (the helper validates and fails closed with `parent task not found: <id>` otherwise).
- A card with parents is created directly in `todo` (not `ready`) and auto-promotes to `ready` when all parents reach `done`. All other claimability invariants (null assignee, repo-root worktree, bare branch) still apply and are post-verified.
- The parent edges are inserted into `task_links` in the same transaction as the card, and the helper post-verifies the links landed.
- `validate <task_id>` recognizes a parent-gated `todo` card as legitimate (it no longer flags `status is 'todo', expected 'ready'` when `task_links` rows exist) and reports the card's `parents` list.

Use `--parents` whenever you know the parent ids at creation time — it is the preferred path for multi-card fan-out from a spec. The legacy `kanban_link` second pass is still valid and is the fallback when parent cards do not exist yet at creation time, or when wiring edges onto cards created before `--parents` existed. `kanban_link` auto-demotes a `ready` child to `todo` when a parent link is added, so no card stays falsely claimable either way. Still re-read every card after creation/linking to confirm the expected status transitions.

### Preserve declared parallelism and fan-in

When a reviewed spec declares multiple independent foundation slices followed by an integration slice, seed the complete ladder in one pass:

1. helper-create each independent foundation as an unassigned Ready worktree card (normally 2–3 cards in the initial wave);
2. helper-create the integration card, then attach **every** declared parent link immediately so its live state becomes Todo;
3. helper-create downstream proof/release cards and link them serially to the integration card;
4. re-read every card to confirm linking preserved its unassigned worktree metadata, and comment that Todo is intentional.

Do not serialize independent foundations merely for board simplicity when the plan explicitly permits separate worktrees. Conversely, do not release an integration or remote-transport card until all resolver, authorization, and local-contract parents are Done. This preserves collision-free parallel implementation without exposing an unsafe partial workflow.

### Post-merge / DB-fallback promotion pitfall

If review-card completion used a DB fallback instead of the normal Kanban completion path, do not assume dependency promotion fired. Re-read the child task and its `task_links`: if every parent row is `done` but the child remains `todo`, add a reconciliation comment, advance the child to `ready`, and immediately run `haft_ready_worktree_card.py validate <task_id>`. Only report it as external-worker runway after the helper returns `ok: true` with `assignee=null`, `workspace_kind=worktree`, repo-root workspace, and non-empty branch.

## Promoting worker-created cards to Ready

External workers (e.g. ChatGPT DevSpace) sometimes create follow-up cards with `assignee=devspace-worker` (or another named profile) instead of `null`. These cards are **not externally claimable** even if they have valid worktree/branch metadata. When JP asks to promote such cards:

1. **Unassign all candidates**: `hermes kanban --board haft assign <task_id> none` for each card. This clears the assignee to `null`.
2. **Validate each card** with `haft_ready_worktree_card.py validate <task_id>`. The only remaining issue should be `status is 'todo', expected 'ready'` — everything else (null assignee, worktree kind, repo-root anchor, bare branch) should already pass if the worker pre-seeded metadata.
3. **Concurrency-safety analysis** (see below) before promoting more than one card.
4. **Promote selectively**: `hermes kanban --board haft promote <task_id> --force` for each safe card. Use `--force` when the card is parent-gated by a non-done parent (e.g. an audit card still in Review).
5. **Leave sequencing comments** on held-back cards explaining why they are not promoted and what must happen first.
6. **Re-validate** promoted cards to confirm `ok: true` with all invariants.

### Concurrency-safety analysis before batch promotion

When multiple cards from the same audit or decomposition touch overlapping source files, promoting all of them to Ready simultaneously guarantees merge collisions between parallel external workers. Before promoting:

1. **Map the file-overlap surface**: for each card, list the core files it will edit (from the card body's evidence section and acceptance criteria).
2. **Identify collision clusters**: cards that edit the same file (especially the same function or transaction) cannot run concurrently.
3. **Identify dependency chains**: a card that explicitly says "coordinate with X" or "reuse X's shared primitive" depends on X merging first.
4. **Promote only the independent set**: cards with zero file overlap and no declared dependencies on each other or on in-flight Review cards.
5. **Document the sequencing plan** in comments on held-back cards: what must merge first, what order to promote later, and which cards must serialize against each other.

Example from a reconciliation-integrity audit: five follow-up cards all touched `index-rebuild.ts` or the reconciliation/lease core. Only two were safe to promote concurrently — one isolated to `legacy-split-root-migration-executor.ts` and one whose core change was in a separable `index-rebuild-catalog-mutations.ts` surface. The other three were held with explicit serialization comments.

### CLI quirks for promote/assign

- `hermes kanban promote <id> --force` works. Do **not** pass a positional `reason` argument — the parser rejects it as an unrecognized top-level arg despite `--help` listing it. Do **not** combine with `--json` — it also breaks argparse. Put the audit-trail reason in a `kanban_comment` instead.
- `hermes kanban assign <id> none` clears the assignee. This is the correct way to make a worker-created card externally claimable.

## Integration-branch sync / catch-up cards

When a long-lived integration branch (e.g. `bbt`) drifts behind `master` and JP wants it caught up behind review, the deliverable lands on the **integration branch**, not `master` — an inversion of the standard worktree flow. Use `references/integration-branch-catchup-cards.md` for the pre-flight git analysis (divergence counts, merge base, the both-sides overlap-file surface, open-PR check), the working-branch override (branch FROM the integration branch, PR targets it, `branch_name` metadata is only a coordination slug), the hard rules (never touch/rebase/force-push `master` or the shared branch, never edit the canonical checkout, preserve both sides of every conflict), the verification gate, and the review-gated handoff. Keep the card review-gated: the worker hands off to Review and a human merges.

## Relationship to broader orchestration skills
This skill is the Haft-specific guardrail for external-worker Ready-lane card creation. Use broader Kanban/orchestrator skills for review flow, PR reconciliation, and queue management; use this one when the question is specifically whether a Haft worktree card is safe to hand to workers.
