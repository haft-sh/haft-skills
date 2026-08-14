---
name: haft-release-procedure
description: Use when cutting a Haft release (tag + deploy). Bump version first, tag second, watch the run.
trigger: Cutting a Haft release, tagging a version, deploying to HQ/GLY/dev.
---

# Haft Release Procedure

## Pre-flight

1. `cd <haft-repo-root> && git fetch origin --tags --quiet`
2. Check commits since last tag: `git log --oneline v<last>..origin/master | wc -l`
3. Check current package.json version: `git show origin/master:package.json | grep '"version"'`

## Step 1: Bump version FIRST (critical)

The release gate enforces `tag == package.json version`. Always bump before tagging.

```bash
cd <haft-repo-root>/.worktrees/version-bump-049  # or create fresh worktree
git checkout -b release-<version> origin/master
sed -i 's/"version": "<old>"/"version": "<new>"/' package.json
git add package.json && git commit -m "chore: release v<new>"
git push origin release-<version>
gh pr create --head release-<version> --base master --title "chore: release v<new>" --body "Version bump for release."
gh pr merge <num> --squash --delete-branch
```

This repository does not permit GitHub auto-merge. From a linked worktree, `gh pr merge` may still print a local `master is already used by worktree` error **after the server-side merge succeeds**. Do not retry blindly: verify `gh pr view <num> --json state,mergedAt,mergeCommit,url`, fetch, and confirm `origin/master:package.json` has the new version before tagging.

**Post-merge check ambiguity:** after the server-side merge, `gh pr view --json statusCheckRollup` can show new checks running for the resulting `master` commit (for example cleanup/worktree checks), not the pre-merge PR gate. Treat `state=MERGED`, the recorded `mergeCommit`, and the fetched `origin/master` version as the merge proof; the tag-triggered release workflow is the deployment gate to watch next.

## Step 2: Tag and push

```bash
cd <haft-repo-root>
git fetch origin --quiet
git tag v<new> origin/master
git push origin v<new>
```

## Step 3: Watch the run

```bash
RUN_ID=$(gh run list --workflow=release.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

Use a background watcher with `notify_on_complete=true`.

## Pipeline structure (post-hardening)

- Resolve immutable release commit
- deploy-hq-production / Verify release candidate (typecheck only, NO test suite)
- deploy-hq-production / Publish Haft CLI release binaries
- deploy-hq-production / Build and deploy Haft HQ binary to production
- deploy-gly (after HQ)
- deploy-dev (after HQ)
- Finalize GitHub Release object (after all deployment targets)

## Pitfalls

- **Preflight live config contracts before immutable deployment**: CI/source config tests are not enough when a release changes required environment semantics. Compare the candidate's effective config requirements with the live target's redacted environment presence before tagging when possible. A non-empty feature allowlist, origin list, or enablement flag can activate validation even when provider credentials are absent. Require the production-shaped preflight to cover both the positive configured case and the existing deployed environment shape.
- **If a deployment swaps the new binary but health reports configuration-error, do not blindly rerun the immutable workflow**: record the tag/commit and published-artifact boundary, inspect the exact missing settings, and distinguish startup timing from deterministic config failure. If the service is running the new binary but public health is 503, fix or provision the sanctioned environment contract (or cut a fix-forward release); do not move/reuse the immutable tag or bypass health checks. Verify whether the workflow rolled back before deciding on recovery, and keep downstream targets/finalization skipped until HQ is healthy.
- **Never tag before bumping package.json** — the gate will reject with "Release tag vX must match package.json version vY"
- **Never re-tag a version that partially published to R2** — the immutable manifest pins the commit SHA; a different commit under the same version is rejected. Bump to the next version instead.
- **Runner listener can go deaf** while reporting online/idle. If a run sits queued >5 min with idle runners, restart: `sudo systemctl restart actions.runner.jplew-haft.devspace-haft.service`
- **`gh run view --log-failed` returns empty for SIGTERM'd jobs** — use `gh api repos/jplew/haft/actions/jobs/<id>/logs` and grep instead.
- **Re-running a failed job re-runs ALL steps** including expensive ones. Prefer cancelling and re-triggering fresh.
- **Cache cleanup race**: `reclaim-release-runner-cache.sh` can fail if bun writes concurrently. Already guarded with `|| true` (PR #1345).

## Release-candidate CI gate integrity

A one-line version bump can expose a pre-existing master-level policy failure. Treat that as a real release gate, not as permission to waive CI:

1. Inspect the failed job and identify the exact failing step before retrying or changing the release PR.
2. If `verify:dependency-audit` fails on advisories outside the release diff, do **not** raise the reviewed baseline, bulk-accept unclassified advisories, or bypass the required check merely to tag a release.
3. Create/link one scoped dependency-policy repair owner that classifies actual runtime reachability, upgrades/removes vulnerable dependencies where safe, and leaves only time-bounded, owner-attributed docs/build exceptions.
4. Make the release-bump card genuinely dependency-gated on that repair. Keep the version PR open, but do not merge, tag, publish, or deploy until a fresh required CI run is green.
5. Record separately: local release-bump verification, PR CI outcome, repair owner, and later immutable release/deployment evidence. A failed policy gate is not evidence that the version change caused the advisories.

For the compatible-override, stale-exception, and downward-ratchet sequence, see `references/dependency-audit-release-gate.md`.

## Verification

After success, verify the immutable manifest and its pinned commit (the release artifact names include version and Bun target; do not probe the obsolete unversioned `haft-linux-x64` path):
```bash
curl -fsS "https://releases.<hq-hosted-origin>/releases/v<version>/manifest.json" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["version"], d["build"]["gitCommit"])'
```
Then verify the workflow-created GitHub Release object is non-draft/non-prerelease and targets the same immutable SHA:
```bash
gh release view v<version> --json isDraft,isPrerelease,targetCommitish,url
```
Only use `gh release create` as recovery when the tag workflow succeeded but live evidence proves its finalization step was skipped or interrupted. Then use the artifact URL/path recorded in that manifest for a binary HEAD probe if needed.
