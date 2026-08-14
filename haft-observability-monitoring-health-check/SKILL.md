---
name: haft-observability-monitoring-health-check
description: "Reusable Haft operator health-check workflow: prove whether HQ/dev/gly are up, whether each is running the latest intended binary, whether deploys are failing, what human review surfaces exist, and what anomalies need action."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, observability, monitoring, health-check, operations, deploys]
    related_skills: [haft-cli-auth-and-remotes, haft-orchestrator-workflows]
---

# Haft Observability Monitoring Health Check

## When to use

Use when JP asks variants of:

- "What's the state of our system?"
- "What's the health of our system?"
- "Is HQ/dev/gly on the latest binary?"
- "Were there recent deployment issues?"
- "Is there anything out of the ordinary?"

## Goal

Produce an operator report that distinguishes **deploy intent** from **runtime truth**.

The deliverable must answer, with evidence:

1. Is `<hq-hosted-origin>` / HQ current?
2. Is `dev.wheretoaccess.com` current?
3. Is `<gly-hosted-origin>` current?
4. Were there recent deploy failures?
5. Is anything degraded, stale, or inconsistent?
6. What human review surface exists besides alerting?

## Core rule: do not infer runtime freshness from deploy success alone

A green deploy run is not enough. Always separate:

- **deploy truth** — what GitHub Actions most recently tried or claims to have deployed
- **runtime truth** — what the live service says it is actually running
- **remote readiness truth** — whether central remote discovery / projection / verifier state is healthy

Use these exact labels in reasoning and reporting when needed.

## Required evidence sources

### 1) Deploy truth

Inspect recent deploy workflows in GitHub Actions, at minimum:

- `Deploy HQ production`
- `Deploy dev`
- any gly/e2e deploy workflow if active

Capture:

- workflow name
- SHA
- success/failure
- run URL
- failure step/class if red

### 2) Runtime truth

Check live health/build surfaces.

Canonical known endpoints:

- HQ: `https://<hq-hosted-origin>/api/v1/health`
- dev: `https://dev.wheretoaccess.com/health`
- gly: `https://<gly-hosted-origin>/health`

Interpretation:

- if live `build.commit` matches intended SHA -> current
- if older -> stale
- if endpoint is down/5xx -> unhealthy
- if the endpoint responds but only proves reachability/runtime class (for example `{ok, app, runtime}` without build identity) -> freshness is **unknown**, not assumed current

### 3) Remote readiness truth

Use Haft CLI after authenticating:

- `haft remotes list --json`
- `haft remote status dev --json`
- `haft remote status gly --json`

This does **not** prove binary freshness, but it does reveal central readiness problems that matter operationally.

Important classifications:

- `projection-expired` / `projection-stale` -> discovery exists but target readiness is degraded; fail closed
- `verifier-not-ready` / readiness unknown -> destination verifier path is not healthy enough to trust delegated readiness

Report these as operator-health problems even when the site still responds publicly.

### Browser AgentSession rollout evidence

When Dev/Gly dogfooding includes remote AgentSession review, treat a healthy CLI session or a server-side preview response as **insufficient**. Verify the public browser Reader actually attaches the supplied session and renders its review/diff controls without a feature-disabled fallback warning.

A service can report `HAFT_AGENT_SESSION_REVIEW=preview` while the browser still resolves disabled because its deployed JavaScript was not given a safe public rollout value. In that case, inspect browser configuration delivery separately; do not blame grants, session state, or the user's browser and do not prescribe a local-storage override as the deployment fix. Require both browser-build and service-runtime rollout configuration on every dogfood target.

See `references/browser-agentsession-rollout-verification.md` for the live proof sequence and diagnosis.

## OTP workflow for remote-status checks

If `haft auth refresh` fails, immediately do a fresh `haft auth login` flow.

For this user, Haft OTP emails for `<operator-email>` may be forwarded into the read-only `<read-only-canary-address>` inbox. In that case:

1. request the OTP challenge
2. read the forwarded OTP from `<read-only-canary-address>`
3. complete `haft auth login --challenge-id ... --code ...`
4. verify with `haft whoami --json`
5. continue with `remote status` in the same auth window

Rules:

- Reading forwarded OTP mail is allowed for explicitly authorized login flows.
- `<read-only-canary-address>` remains strictly **read-only**.
- Never reply to OTP emails.
- Ignore `mailer-daemon` bounce noise as non-authoritative unless it changes the actual login outcome.

## Deploy-lifecycle CloudWatch emission checks

Deploy workflows can emit `started` and `completed` lifecycle records to `/haft/ci/deploy`. These steps may intentionally be non-blocking (`continue-on-error: true`), so a green deploy does **not** prove lifecycle records were written.

When an emitter reports `deploy-observability.log-stream-create-failed:254`:

1. Classify it as an **observability gap**, not proof that the binary deployment failed.
2. Verify deploy truth and live embedded build SHA independently before reporting runtime state.
3. Inspect the AWS CLI error. The runner's least-privilege writer policy needs only `logs:CreateLogStream` and `logs:PutLogEvents`, scoped to `arn:aws:logs:<region>:<account>:log-group:/haft/ci/deploy:log-stream:*` (substitute the configured group if it differs).
4. Do not broaden the role to `logs:*`, and do not require `logs:Describe*` simply to emit records. Provision the log group separately.
5. State plainly that lifecycle records for the affected run are missing; do not treat a later runtime check as a retroactive CloudWatch lifecycle record.

## Human operator surfaces

When asked whether observability is alert-only, distinguish between:

### Ops surfaces

- CloudWatch dashboard / alarms / canaries
- public health endpoints
- deploy runs and logs

### Review surfaces

- product Inbox Capture UI (`#/inbox`) for human review of captured incoming items

State clearly that Inbox Capture is the human review surface; it is not the same thing as alerting.

## Required report shape

Use a compact table:

| Environment | Intended SHA | Live SHA | Runtime | Recent deploys | Notes |
|---|---|---|---|---|---|

Then summarize anomalies only.

## Classification rules

For each environment, classify as one of:

- **current**
- **stale**
- **unhealthy**
- **unknown**

Use **unknown** when runtime build truth is missing. Do not overstate confidence.

## Escalation rule

If HQ freshness is provable but dev/gly freshness is not, treat that as an operator-health gap worth filing on the Haft Kanban board. The issue should explicitly call out:

- inability to prove runtime freshness for dev/gly
- any degraded remote readiness (`projection-expired`, `verifier-not-ready`)
- need for a build-bearing operator surface comparable to HQ `/api/v1/health`

## Pitfalls

- Do not say dev/gly are current just because the most recent deploy succeeded.
- Do not treat `remote status` as proof of live binary version.
- Do not ignore a stale gly projection just because the public site responds.
- Do not ask the user for an OTP before checking the forwarded Haft inbox path.
- Do not treat bounce messages or mailer-daemon noise as a reason to abandon the OTP path if the forwarded OTP email is present.
