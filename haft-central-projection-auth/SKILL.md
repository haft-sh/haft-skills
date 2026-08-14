---
name: haft-central-projection-auth
description: Work on Haft HQ central projections, destination-readable vault-access grants, and collaborator-sensitive authorization without regressing owner/admin visibility or downstream projection consumers.
---

# Haft central projection auth

Use this when changing any of the following in Haft:
- `apps/hq/src/projection-v1.ts`
- `apps/server/src/central-projection-v1.ts`
- destination auth that consumes `vaultAccessGrants`
- collaborator-sensitive routes that authorize from central projection state
- tests that verify signed HQ projections or Epic 20/Epic 21 grant behavior

## Goal

Keep the central projection useful as a destination-readable auth artifact:
- owner/team-admin projections must carry enough grant detail to authorize collaborator-sensitive destination routes
- collaborator/member projections must remain scoped to self-visible grants only
- downstream tests and projection consumers must stay aligned with the full `vaultAccessGrants` schema, not a partial older shape

## Workflow

1. Read both the HQ issuer and the shared projection contract before editing.
   - `apps/hq/src/projection-v1.ts`
   - `apps/server/src/central-projection-v1.ts`
2. Check how destination auth maps projected grants into local membership/authorization inputs.
3. Inspect at least these tests before changing behavior:
   - `tests/central-projection-v1.test.ts`
   - `tests/hq-remote-grant-exchange.test.ts`
   - `tests/epic20-invitations-vault-access-grants.test.ts`
4. Decide subject visibility by relationship, not just by account id.
   - `owner` / `team-admin`: include all explicit grants for the bound vault so destination routes can reason about collaborators
   - `team-member` / `none`: include only grants bound to the requesting account
5. If you expand `vaultAccessGrants` fields, update every expectation that compares the grant payload directly.
6. Re-run targeted tests first, then broader repo verification.

## Required grant-shape invariants

Projected `vaultAccessGrants` are not just central records. They are destination-readable auth inputs and must carry:
- `source`
- `sourceLabel`
- `localRoles`
- `localCapabilities`
- `localRouteFamilies`
- `localPathPrefixes`
- `canManageMembers`

Synthetic owner/team grants and explicit collaborator grants should both satisfy the same shared schema, even when their semantics differ.

## Central invitation cleanup safety

For operator-requested cleanup of duplicate collaborator invitations, treat the central invitation table and the vault-access-grant table as separate lifecycles:

1. Establish the current authoritative HQ database/service target before reading or mutating anything. Historical instance IDs, deployment notes, or local checkouts are not proof of the live production data source.
2. Identify the complete scope from live data: normalized email, team ID, and—when collaborator invites are vault-bound—the vault claim ID, inviter, role, and invitation status. If the scope or current operator path cannot be established, stop and request the current procedure rather than guessing.
3. Inspect and record all matching invitation rows before mutation. Only rows that are currently `pending` and match the normalized email and verified scope are eligible; never delete accepted, revoked, expired, historical, or active grant rows.
4. Preserve one canonical pending invitation, preferably the newest non-expired record with intact lifecycle metadata. Cancel redundant rows through the existing invitation lifecycle (`revoked` with timestamps/audit), not hard deletion, and do not alter entitlements or grant authorization.
5. Re-read the central owner/member projection after mutation and verify exactly one pending invitation remains for the scope. Report only non-secret identifiers and statuses.

The create path's read-then-insert reuse logic is not by itself a concurrency-safe uniqueness guarantee. Track prevention work separately: a partial unique constraint/index for active pending invitations where the product scope permits it, plus an idempotent create path that handles uniqueness conflicts and preserves the canonical lifecycle record.

## Pitfalls

### Do not always filter explicit grants by `subject.accountId`
That breaks owner/admin projections for collaborator-sensitive routes because the projection can no longer describe collaborator grants that the owner/admin is allowed to manage.

Instead, branch on relationship:
- owner/admin subjects get vault-wide explicit grants for the bound vault
- member/none subjects get self-only explicit grants

### Expect test fallout outside the immediate Epic slice
A change to projection grant shape or visibility often breaks:
- central projection contract tests
- Epic 20 invitation/grant tests
- remote grant exchange tests

Treat that as normal cross-surface fallout, not unrelated noise.

### Use explicit type narrowing in this repo's tests
For discriminated results that TypeScript does not narrow cleanly here, prefer checks like:
- `if (result.ok !== true) throw ...`

This avoids fragile access to error-only fields such as `result.code` in branches that TS still considers union-typed.

## Verification

Start with targeted checks:
- `bun test tests/central-projection-v1.test.ts`
- `bun test tests/hq-remote-grant-exchange.test.ts`
- `bun test tests/epic20-invitations-vault-access-grants.test.ts`

Then run broader gates:
- `bun run typecheck`
- `bun run build`
- `git diff --check`

## References

- `references/owner-admin-projection-visibility.md` — session notes on the owner/admin explicit-grant visibility fix, schema fallout, and the test updates that usually accompany this class of change.
