# Haft ready-buffer seeds

Use this when the `haft` board's Ready column drops below roughly 4 claimable cards and the current active phase does not provide enough dependency-safe work.

## Phase 6 editing fallback seeds

These are contract-backed, worker-sized implementation slices that fit the repo's existing local-first boundaries and usually make good Ready-buffer replenishment candidates.

### HV-345 — Internal link autocomplete API and editor insertion helper
- Source: `docs/internal-link-autocomplete-contract.md`
- Why it is safe: owner-local only, bounded route/UI scope, no remote lookup, no public-surface expansion.
- Suggested verification:
  - `git diff --check`
  - `bun test tests/link-autocomplete.test.ts`
  - `bun test tests/editor-link-autocomplete-route.test.ts`
  - `bun test tests/reader-editor.test.ts`
  - `bun run typecheck`
  - `bun run build`

### HV-346 — Editable properties inspector routes and page-local UI refresh
- Source: `docs/editable-properties-inspector-contract.md`
- Why it is safe: page-local metadata edit flow, snapshot + validate + rebuild pattern already matches core Haft assumptions.
- Suggested verification:
  - `git diff --check`
  - focused editable-properties test(s)
  - `bun test tests/reader-web.test.ts`
  - `bun run typecheck`
  - `bun run build`

### HV-347 — Block move operations helper, owner-local route, and conservative editor controls
- Source: `docs/block-move-operations-contract.md`
- Why it is safe: owner-local only, deterministic source-owned ordering, bounded UI controls instead of broad drag-and-drop.
- Suggested verification:
  - `git diff --check`
  - `bun test tests/block-move-operations.test.ts`
  - `bun test tests/phase-6-editing-smoke.test.ts`
  - `bun run typecheck`
  - `bun run build`

### HV-350 — Owner-local version snapshot history route and restore boundary first slice
- Source: `docs/version-snapshots-history-restore-contract.md`
- Why it is safe: planning/spec only, tightly bounded to owner-local history/restore seams, and avoids new public/runtime exposure in the card itself.
- Suggested verification:
  - `git diff --check`

## Selection rule

Prefer cards that:
1. already have an accepted contract or implementation-plan doc,
2. stay within owner-local editing/search/read-model boundaries,
3. can land in one PR with focused tests,
4. do not introduce deployment/auth/public-surface risk,
5. are large enough to be meaningful worker slices rather than 5-minute microcards.

## Anti-pattern

Do not pad the Ready queue with vague placeholders, dependency-unsafe implementation cards, or cards that silently reopen archived remote-fetch / URL-import work.