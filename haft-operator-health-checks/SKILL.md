---
name: haft-operator-health-checks
description: "Run evidence-backed Haft operator health checks: prove which environments are current, distinguish deploy intent from live runtime truth, inspect remote readiness, and escalate observability gaps into board work."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, operations, observability, health-checks, deployments, remotes]
    related_skills: [haft-cli-auth-and-remotes, haft-orchestrator-workflows]
---

# Haft Operator Health Checks

## When to use

Use this when JP asks questions like:

- "What's the state of our system?"
- "What's the health of our system?"
- "Is HQ / dev / gly on the latest binary?"
- "Anything out of the ordinary?"

This skill is for **operator truth**, not code review or PR triage.

## What the answer must cover

Every health report should try to answer all of these:

1. Is `<hq-hosted-origin>` / HQ up, and is it on the latest intended binary?
2. Is `dev.wheretoaccess.com` up, and is it on the latest intended binary?
3. Is `<gly-hosted-origin>` up, and is it on the latest intended binary?
4. Were there recent deploy issues?
5. Is anything degraded, stale, blocked, or unprovable from the current operator surfaces?
6. Is there a human review surface for incoming items/messages?

## Core principle: separate deploy truth from runtime truth

Never treat a successful deploy workflow as sufficient proof that the environment is current.

You must distinguish:

- **Deploy truth** — what GitHub Actions most recently tried to deploy
- **Runtime truth** — what the live environment says it is actually running
- **Remote-readiness truth** — whether managed/central remote status is healthy enough to trust for operator workflows

### Current canonical surfaces

- **HQ runtime truth:** `https://<hq-hosted-origin>/api/v1/health`
- **Deploy truth:** recent `Deploy HQ production` and `Deploy dev` GitHub Actions runs
- **Remote-readiness truth:** `haft remotes list --json`, `haft remote status <slug> --json`
- **Human review surface:** Inbox Capture UI at `#/inbox`
- **Operator overview:** CloudWatch dashboard `Haft-Operations` when AWS access is available

## Release trigger gate (required before diagnosing drift)

A merge to `master` is **not** a Haft runtime deployment by itself. Before declaring a just-merged fix deployed, inspect the release version, tags, and `Release` workflow:

1. Read `package.json` at `origin/master` and record its semver version and SHA.
2. Compare it with the latest reachable `vX.Y.Z` tag.
3. Inspect recent `Release` runs. If there is no run for the matching new tag, no all-service rollout has started.
4. Probe HQ, Gly, and dev build-bearing health endpoints and compare their embedded SHA to `origin/master`.

The normal production action is to push a **new immutable matching semantic tag** (for example `v0.1.8` for `package.json` `0.1.8`). This triggers the ordered release workflow: it resolves one exact commit, deploys HQ first, then deploys Gly and dev in parallel using that same SHA. Do not manually dispatch a new `master` build under an already-published version merely to make a merged fix live; that can corrupt release identity and CLI publication provenance.

A manual `workflow_dispatch` remains a bounded break-glass or rollback path, preferably against a previously published immutable tag. It is not evidence that merge-driven deployment is enabled.

## Standard workflow

### 1) Check latest deploy intent

Inspect recent deploy workflows and capture the latest intended SHA per environment.

Minimum set:
- `Deploy HQ production`
- `Deploy dev`
- any gly-specific deploy workflow if one exists

Report both the **latest successful deploy** and the **latest failed deploy** if the failure is recent enough to affect operator confidence.

### 2) Check HQ live runtime truth

Call the public HQ health endpoint and compare `build.commit` / `build.shortCommit` to the intended HQ deploy SHA.

Interpretation:
- match = HQ current
- mismatch = stale or drifted
- endpoint down / invalid = HQ unhealthy regardless of deploy green

### 3) Check dev and gly runtime truth

Do not assume dev or gly have the same build-bearing public health surface as HQ.

For each environment:
- check public reachability
- check any available authenticated/public status endpoint
- check `haft remote status <slug> --json`
- state plainly whether you have **actual runtime build proof** or only **deploy intent / reachability**

If you cannot prove the live build commit for dev or gly, say so explicitly. Do not blur that into a healthy/current claim.

## Remote-status interpretation rules

`haft remote status` can improve operator visibility even when it does not prove runtime build freshness.

Important interpretations learned from this session:

- `projection-stale` / `projection-expired` on a remote (for example gly) means the central remote is discovered but its central projection is stale enough that delegated operations must fail closed.
- `verifier-not-ready` / readiness `unknown` (for example dev) means the target exists in central discovery, but delegated verifier readiness is not healthy enough to trust.
- These states are **operator-health issues** even when the domain itself still responds publicly.
- They do **not** prove which binary is running.

## OTP-assisted remote diagnostics

If CLI auth is expired and a fresh OTP is needed:

- request a fresh `haft auth login --email ...` challenge
- check the read-only `<read-only-canary-address>` inbox for the forwarded OTP message
- the forwarded message may still show `to: <operator-email>`; that does **not** invalidate it
- extract the OTP from the forwarded message and complete login
- immediately run `haft whoami --json`, then `haft remotes list --json` and `haft remote status ... --json`

Treat OTP mail as read-only input only. Never reply.

## What counts as a complete answer

A good answer includes a table like:

| Environment | Intended SHA | Live SHA / proof | State | Notes |
|---|---|---|---|---|
| HQ | ... | `/api/v1/health` commit ... | current / stale / down | ... |
| dev | ... | deploy success only / runtime build proof / unknown | current / unknown / degraded | ... |
| gly | ... | remote readiness only / runtime build proof / unknown | current / unknown / degraded | ... |

Then summarize:
- what is definitely current
- what is definitely broken
- what is merely unproven

## Required style for JP

JP wants the answer in operator language:
- lead with the conclusion
- call out what is **proven** vs **assumed** vs **unknown**
- do not say "healthy" when runtime freshness is unproven
- if a deploy succeeded but runtime build truth is missing, say exactly that
- if a visibility gap blocks confident health checks, treat that as a real issue, not a footnote

## When to file a Kanban card

Create or update a board task when any of these are true:

- dev or gly freshness cannot be proven from operator-visible surfaces
- a remote is stuck in `projection-stale`, `projection-expired`, `verifier-not-ready`, or similar degraded readiness
- the only available evidence is deploy intent and public reachability, but not live build truth
- the user explicitly says this should be prioritized

Good card framing:
- prove runtime freshness for the affected environments
- identify the missing operator surface if proof is impossible today
- diagnose the failing layer behind degraded remote readiness
- leave a future operator with a reusable path instead of another one-off answer

## SSM-based vault repair (when UI and API are both blocked)

When the UI cannot perform an operation (duplicate rows, broken selection,
missing context-menu items) and the API is auth-gated even on localhost, the
operator path is direct DB manipulation via SSM on the EC2 instance.

See `references/dev-instance-ssm-vault-repair.md` for:
- dev instance topology (instance ID, DB paths, service name)
- SSM + bun:sqlite query and mutation recipes
- duplicate artifact detection query
- pitfalls (catalog.sqlite is empty, revision must be bumped, restart required)

This is a break-glass path. File a ticket for the systemic fix whenever the
root cause is a product bug, not operator error.

## Explorer projection outage recovery

When Gly's authenticated Explorer reports that its projection is unavailable,
rebuild the authoritative vault catalog, restart the Gly service, and verify
the derived `explorer.sqlite` projection through aggregate-only state before
asking the user to retry. A public `403 route.gate-denied` from the private
tree route is an expected anonymous control response, not proof of failure.
See `references/gly-explorer-projection-recovery.md` for the exact bounded
recovery and verification procedure. If the supported index-rebuild command
does not itself restore or report Explorer-projection readiness, treat that as
a product-contract bug rather than normalizing the restart workaround.

## Pitfalls

- **Do not equate successful deploy with current runtime.** This was the main operator gap in this session.
- **Do not overclaim on gly/dev.** Reachability plus central remote discovery is not runtime build proof.
- **Do not stop at expired auth.** Re-auth using the forwarded OTP workflow, then continue the diagnosis.
- **Do not bury observability gaps.** If HQ can prove its build but dev/gly cannot, that is itself a reportable health issue.

## Suggested follow-up artifacts

If this workflow uncovers a persistent gap, add a board card or a reference note with:
- exact failing readiness code
- latest intended SHA
- any public endpoint results
- what operator surface is missing
