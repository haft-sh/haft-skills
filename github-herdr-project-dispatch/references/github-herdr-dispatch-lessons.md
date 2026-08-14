# GitHub/Herdr Dispatch Lessons

## Validated preflight

- Create a fresh Herdr workspace and tab/pane; do not split an existing active workspace when the human needs readable full-screen review.
- Use `herdr pane split` only for ordinary local work. For issue dispatch, prefer a new workspace/session API when available.
- Rename the pane and Hermes session to `github-issue-<id>`; verify the live terminal title and Herdr agent identity by pane ID.
- Check the worker's actual `gh auth status` and project access before claiming. The controller shell can have `project` scope while the worker context does not.
- Never run `gh auth refresh` or device/browser authorization from a noninteractive worker. Stop before claim if required scope is absent.

## Lifecycle

When explicitly delegated to the worker: inspect issue/project, claim the issue, move Ready → In Progress, perform bounded work, then move In Progress → Review with a sanitized evidence comment. Do not move Done or merge without approval. Independently verify the assignee, project status, comment, worktree, PRs, and checks.

## Provider and token telemetry

Attempt the requested provider/model once. If MOA/provider routing fails before tool execution, record the failure and use an authorized fallback only if needed. Do not blindly resubmit. Report provider/model attempted, fallback, wasted round trips, and whether any side effect occurred.

## Browser acceptance

Separate local contract/test evidence from authenticated visual evidence. A backend rendition or projection test does not prove that the live Grid displays a thumbnail. A worker may move to Review with a clearly stated browser-session blocker, but the issue is not Done.

## Incident pattern from issue 1636

The worker successfully claimed `haft-sh/haft#1636`, transitioned it Ready → In Progress → Review, ran 65 projection/media tests plus 18 derivative/reconciliation tests, and made no code changes. Final visual verification was blocked because no authorized Gly browser session was available. The issue remained in Review with sanitized evidence.
