---
name: GitHub Project Board Reconciler
description: Automatically reconcile GitHub Project v2 board item states with actual issue/PR status to prevent drift.

---

## Overview

This skill implements an automated reconciler for GitHub Project v2 boards to maintain accurate stage transitions (Ready → In Progress → Review → Done) based on actual PR/issue state.

## When to Use

- Before or after Night Shift work sessions
- Periodically in cron jobs (e.g., daily)
- When human reports board inconsistencies

## Objectives

- Ensure the project board reflects reality
- Clean up stale items that have drifted into wrong stages
- Maintain canonical workflow discipline

## Methodology

1. Query the Project v2 for all items with fields: Stage, Priority, Status, Issue number
2. For each item, verify expected state and transition if necessary:
   - **Stage = Ready**: Issue must be Open and have no open PR linked. If open PR exists → In Progress. If issue closed → Done.
   - **Stage = In Progress**: Must have an open PR. If no PR → Ready.
   - **Stage = Review**: Must have open PR. If PR merged → Done. If PR closed without merge → Ready or In Progress.
   - **Stage = Done**: Issue must be Closed. If still Open → appropriate stage based on PR linkage.
3. Optionally, close issues automatically when PRs merge with "Closes #N" syntax.
4. Report a summary of all changes.

## Tools

- GitHub GraphQL API (preferred)
- `gh` CLI (alternative)
- Scriptable in TypeScript/Bun

## Tips

- Make the script idempotent (running twice should produce no further changes)
- Include a `--dry-run` mode by default for safety
- Log every state transition with issue number and reason
- Consider ignoring items with a special tag (e.g., `keep-in-stage`) if manual override is needed

## Example Implementation

File: `scripts/reconcile-project-board.ts`

```typescript
// Use GraphQL to query ProjectItems and Issues
// Use mutations to update the item's single-select field (Stage)
// Integrate into Night Shift: run at start and end of each session
```

## References

- [GitHub GraphQL Documentation](https://docs.github.com/en/graphql)
- Project v2 field update patterns
