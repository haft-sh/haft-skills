# Haft EPIC 11 handle/relationship runway seeds

Use this when the Haft board needs executable EPIC 11 refill cards and the existing Scheduled lane has degraded into visual `[EPIC]` / `[PHASE]` trackers only.

## Refill pattern

1. Re-read live board state first.
   - Count executable `Ready` only.
   - Count executable `Scheduled` reserve only.
   - Ignore visual tracker cards in both counts.
2. Inspect adjacent active history before inventing new slices.
   - Check the current `running` cards in the lane.
   - Scan recently `done` cards for the same EPIC/phase so you do not recreate already-landed work with a new HV id.
3. Extend the next unresolved seam from planning docs plus live code/tests.
   - For the compact-handle lane, look for mixed grammar leftovers (`hv:` vs `hv://` vs `@collection:`).
   - Prefer concrete follow-ons such as projection normalization, alias support, resolver expansion, and regression coverage over vague tracker cards.
4. End the sweep with both:
   - about 4 executable `Ready` cards for immediate workers
   - about 4 executable `Scheduled` cards as deeper reserve
5. Seed worktree metadata on every executable card.
   - `workspace_kind=worktree`
   - `workspace_path=<repo-root>`
   - worker-neutral `branch_name`

## Proven card shape used successfully

Immediate Ready buffer:
- normalize operation-event/plugin-adjacent page/asset/chunk handles onto compact `hv:` syntax
- normalize reader/search/public-safe relationship projections onto compact `hv:` handles
- add compact `hv:collection` aliases alongside existing `@collection` handles
- add mixed-handle regression coverage for compact `hv:` vs legacy `hv://` and `@collection` forms

Scheduled reserve behind that buffer:
- resolve compact `hv:collection` handles through owner-local collection summaries
- resolve compact `hv:lock` handles through bounded reference-lock summaries
- project compact collection/lock handles into command and plugin discovery metadata
- add end-to-end alias-canonicalization coverage for collection and lock handoff surfaces

## Why this pattern works

- It stays inside EPIC 11 instead of jumping lanes.
- It uses already-merged planning contracts as the source of truth.
- It avoids duplicate work by checking recent done/running cards first.
- It leaves a real worker queue, not just tracker noise.

## Pitfalls

- Do not report raw Scheduled count as runway if it is mostly trackers.
- Do not seed cards from docs alone without checking whether equivalent slices already landed.
- Do not preseed worker identity into branch names.
- Do not leave all newly created cards in Ready; schedule the deeper reserve in the same sweep.
