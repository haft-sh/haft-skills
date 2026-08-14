---
name: haft-auth-and-claim-operations
description: "Operate Haft self-hosted auth and first-owner claim flows: distinguish identity proof from local ownership proof, run bootstrap claim safely, and guide UI/UX decisions for unclaimed public-mode instances."
---

# Haft Auth and Claim Operations

## When to use

Use this skill when working on any of:
- self-hosted Haft auth setup
- public / EC2-like Haft instances that show login but remain unclaimed
- first-owner enrollment / bootstrap claim flows
- OTP succeeds but the app still returns `auth.claim.required`
- deciding between SSH/SSM/CLI vs browser/UI claim for a Haft box
- product design or implementation work around claim, bootstrap, ownership proof, and secure-mode onboarding

## Core model

For a fresh self-hosted/public-mode Haft instance, there are **two different proofs**:

1. **Identity proof** — who the person is
   - Portal identity
   - central email OTP
   - central session / account assertion

2. **Local ownership proof** — who controls this specific box
   - currently: a host-generated one-time bootstrap token
   - future possibilities: local pairing, localhost helper, shell-issued challenge signer

Do not collapse these into one concept.

### Durable rule

**OTP proves identity, not host ownership.**

If OTP verifies successfully but the box is still unclaimed, the correct result is that access still fails closed until a local ownership proof completes first-owner claim.

## Current product/runtime contract

Today, the durable first-owner production path is:

1. operator accesses the host locally / via SSH / via SSM
2. operator generates a one-time bootstrap token on that host
3. token is used once to claim the instance
4. after claim, normal browser sessions / OTP flows work

This is the right current production path for self-hosted Haft. Do not recommend OTP-only first claim for user-owned boxes.

## Canonical operator workflow

### 1. Generate the bootstrap token on the host

```bash
VAULT_ROOT=/srv/haft/default-vault bun run auth:bootstrap
```

Notes:
- The raw token is revealed once.
- Only a hash is persisted.
- Do not paste the token into logs, tickets, or durable notes.

### 2. Claim the instance

```bash
curl -i -X POST http://127.0.0.1:9001/api/auth/bootstrap/claim \
  -H 'content-type: application/json' \
  --data '{
    "bootstrapToken": "<one-time-token>",
    "identity": {
      "provider": "portal",
      "providerSubject": "portal:user:<your-portal-subject>",
      "displayName": "Owner",
      "email": "owner@example.test"
    }
  }'
```

Expected result:
- local claim becomes active
- first owner/admin membership is created
- browser session cookie + CSRF token are issued
- subsequent auth flows can open the box normally

## SSM first-owner claim safety

When an explicitly authorized claim is performed through AWS SSM, treat the SSM execution identity as a security and runtime prerequisite:

- `AWS-RunShellScript` commonly runs as `root`, while Haft systemd services often run as a non-root service account. Discover the unit `User`, `VAULT_ROOT`, and loopback listener before any mutation.
- Never run `haft auth bootstrap` as root against a vault served by another user. Run it as the service user, retain the raw pairing code only in a mode-0600 temporary file, consume it through the loopback claim route, and delete it in a trap. SSM output must contain only redacted/sanitized result fields.
- A read-only preflight must not invoke the bootstrap command: bootstrap issuance mutates auth state.
- Check service state before claiming. If recovery requires restart, prove both loopback and public health/status afterward; a local process being active is not sufficient evidence.
- If an earlier root operation created auth, SQLite lease, or migration artifacts, identify and repair ownership only on those affected paths before restarting. Preserve restrictive modes and recheck catalog/runtime health rather than declaring recovery complete from auth status alone.

See `references/ssm-first-owner-claim-service-user.md` for the safe execution sequence and evidence boundary.

## Diagnose common confusing cases

### Case 1: OTP succeeds, then `auth.claim.required`

#### Symptom

The UI sends an OTP successfully, the user enters it, then gets:

`auth.claim.required: this Haft instance has not been claimed.`

#### Interpretation

This is **not** an OTP failure.

It means:
- identity proof succeeded
- the local instance is still unclaimed
- first-owner bootstrap claim was never completed

#### Correct response

Do not tell the user to retry OTP repeatedly.
Tell them the box needs first-owner claim via local operator proof.

### Case 1b: Public auth says `unclaimed` but the host already has an active claim

#### Symptom

A hosted instance displays `unclaimed · bootstrap` (or an equivalent malformed/untrusted route-gate message), although the operator expects an existing managed claim.

#### Read-only evidence ladder

Do not send an OTP or issue a new bootstrap token first. Establish these facts separately:

1. Query public `GET /api/auth/status` with `Cache-Control: no-cache`.
2. Confirm the hostname resolves to the intended live host before inspecting local state.
3. On that host, inspect the auth document through a **redacted semantic summary**: JSON validity; local claim status; central server/vault/projection status and sources; server↔vault binding; projection expiry; and expected-account membership. Never print the auth document, raw grants, refresh material, or bootstrap tokens.
4. From an authenticated HQ session, inspect managed remote discovery. A discovered target bound to the account is central-control-plane evidence of the central server/vault/grant relationship when direct DB-shell access is unavailable.
5. If the local claim is active but the `central-identity` projection is expired, classify this as **managed projection renewal**, not missing ownership. A public endpoint that collapses all non-active enforcement statuses to `unclaimed/bootstrap` is a UX/diagnostic defect; file a bounded follow-up to distinguish `projection-expired` without exposing private claim metadata.

#### Correct recovery

**Fast path — operator host has no local claim or remotes.** If the orchestrator/workstation `~/.haft/remotes.json` is empty and `haft remote refresh <slug>` fails with `auth.claim.required`, the CLI refresh path is completely blocked. Do not attempt `haft remote enroll` (it requires a real vault context, not temp test vaults). Go directly to SSM server-side refresh on the destination instance:

```bash
# Discover the instance
aws ec2 describe-instances --filters "Name=tag:Name,Values=*dev*" \
  "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].{Id:InstanceId,Name:Tags[?Key==`Name`].Value|[0]}' --output table

# Refresh the projection server-side (runs as the service user)
aws ssm send-command --instance-ids <instance-id> \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["sudo -u haft /srv/haft-dev/app/haft remote refresh default 2>&1"]' \
  --query 'Command.CommandId' --output text

# Check result
aws ssm get-command-invocation --command-id <cmd-id> --instance-id <instance-id> \
  --query 'StandardOutputContent' --output text
# Expected: "Managed projection for default refreshed until <ISO-timestamp>."
```

The projection TTL is ~24 hours. There is no auto-refresh cron on the instance; recurring expiry is expected until one is added. See `references/dev-instance-projection-refresh-ssm.md` for the full procedure and instance paths.

**Standard path — operator host is enrolled.** First discover the active managed vault slug — do not assume it is `default`. The slug is instance-specific (e.g. `gly`, `dev`). The UI error message may suggest `haft remote refresh default` generically; that will fail with `cli-remote.refresh-vault-mismatch` if the actual slug differs. Discover it first:

```bash
sudo -u haft env HOME=/home/haft /srv/haft/app/haft remote list --json 2>&1 | head -c 1000
```

Or read it from the systemd drop-in environment / auth-state. Then use the destination-local managed refresh path with the **actual** vault slug:

```bash
sudo -u haft env HOME=/home/haft HAFT_CENTRAL_JWKS_PATH=<service-jwks-path> \
  haft remote refresh <actual-vault-slug> \
  --vault-root <vault-root> \
  --jwks-path <service-jwks-path> --json
```

- Retain signed-projection verification and fail closed.
- If refresh reports a verifier/schema incompatibility, compare destination embedded build identity with HQ and the intended release. Do **not** edit `auth-state.json`, extend expiry manually, or re-bootstrap the box.
- A version-skewed destination may require a normal fresh immutable patch release before the refresh can validate; do not reuse or retag a partially rolled-out release.
- After successful refresh, verify loopback and public auth status independently, then run a browser-origin OTP admission probe using an invalid email payload. A validation response proves admission without sending mail.

### Case 2: OTP succeeds, claimed instance loops back to login over raw HTTP

#### Symptom

`POST /api/auth/central/otp/verify` returns `ok: true`, `claimed: true`, a `sessionId`, CSRF token, and a human principal, but after reload the UI returns to the auth-required screen. The next `GET /api/app/status` returns `403 route.gate-denied` with `principal: null`, while `GET /api/auth/status` still reports `claimed: true` and active local claim state.

#### Interpretation

This is usually **not** an OTP failure and **not** a claim failure. In `HAFT_MODE=public` / `ec2` / `production`, Haft emits the browser session cookie as `Secure`. If the user is accessing a raw HTTP/IP URL such as `http://<ec2-ip>:9001/`, the browser rejects or refuses to send the `hv_session` cookie, so later app requests have no authenticated principal.

#### Correct response

Verify the `Set-Cookie` warning in browser DevTools and confirm the server runtime mode. Prefer putting the instance behind HTTPS and accessing it via `https://...` while keeping public mode. Use any insecure-cookie override only as a disposable test-only path. See `references/public-mode-http-secure-cookie-login-loop.md`.

### Case 3: Collaborator hits `auth.identity.not-found` on browser login

#### Symptom

An invited collaborator opens a claimed hosted instance (e.g. `https://<gly-hosted-origin>`) and the login screen fails with:

`auth.identity.not-found: no matching local identity exists for this browser login seam.`

They may also report that no OTP email ever arrived, even after resends.

Before changing a mailbox whitelist, compare the exact configured HQ sender with the active exact-email rules. `no-reply@…` and `noreply@…` are distinct addresses. Correlate the hosted request ID through HQ's `email.send.accepted` event, but do not call a queued provider response inbox-delivery proof. Use `references/otp-provider-sender-whitelist-correlation.md` for the read-only evidence sequence and safe reporting boundary.

#### Interpretation

Three independent failures commonly stack here — diagnose them separately, in order:

1. **Identity not enrolled yet.** `auth.identity.not-found` means the local auth document has no identity row matching the browser's `providerSubject`/email. The most common cause is timing: the collaborator tried to log in *before* an owner/admin granted them membership. The error reads like a system bug but is usually "you haven't been added yet."
2. **OTP silently swallowed by HQ rate limiting.** If resends produced no email, check whether every OTP request in the window carried the `otp:rate-lim` challenge prefix (HTTP 200 + `delivery: queued`, no real send). See `references/hosted-central-otp-rate-limit-and-delivery-triage.md` § "Silent-swallow signature."
3. **HQ Turso DB transport failures.** Emails ARE sent (real provider message IDs in HQ logs), challenges ARE written, but the verify transaction cannot read them back due to intermittent Turso connectivity failures. HQ returns `invalid-or-expired-challenge` as a safe fallback — indistinguishable from a genuinely wrong code. The rate limiter may also fire on DB transport failures (returning `otp:rate-limited-redacted` instead of a real challenge). See `references/hq-turso-db-transport-otp-verify-failures.md`.

#### Read-only evidence ladder

1. Confirm the instance is claimed: `curl -s https://<host>/api/auth/status` → `claimed: true`.
2. Read the destination auth document through SSM (do **not** print raw secrets; summarize users/identities/memberships and the last ~10 audit events). Look for:
   - an identity row with `providerSubject`/`email` matching the collaborator;
   - an **active** membership row for that user;
   - the audit timeline: `browser-login-denied` (`auth.identity.not-found`) events vs the `membership-granted` event. If the denials predate the grant, the root cause is enrollment timing, not a defect.
3. For "no email arrived," grep the service journal for `auth.otp.requested` events and inspect `challengeIdPrefix`. All `otp:rate-lim` ⇒ rate-limited, nothing sent; a normal prefix ⇒ a real send (check spam/promotions).
4. For "code invalid/expired" despite correct entry: check HQ journald for `admission-control.dependency` events with `failureClass: "db-transport"`. Correlate timestamps with verify denials. If every verify denial coincides with a DB transport recovery event, the Turso connection is the root cause — not the user's code. See `references/hq-turso-db-transport-otp-verify-failures.md`.

#### Correct response

- If the identity/membership is missing: have an owner/admin grant access first (managed invite, or the break-glass local membership seam in `references/manual-local-collaborator-access.md`), then retry login.
- If rate-limited: stop retrying, wait for the bucket to reset, confirm with one direct HQ probe returning a real challenge prefix, then have the user request a fresh code.
- If DB transport failures: the problem is HQ infrastructure, not the user. Check Turso instance health, connection limits, and network path from the HQ EC2 instance. A service restart may clear stale connections. The user's codes are valid — they just can't be verified until the DB stabilizes.
- Do not re-bootstrap, edit `auth-state.json` by hand, or treat this as a claim failure.

#### GLY instance access path

SSH to GLY does not work from the orchestrator host (no key / connection timeouts). Use AWS SSM:

```bash
# Instance: i-0ef8f3e99090b9a7d, region ca-west-1, service haft-gly.service
# Vault auth state: /srv/haft-vault/default/.haft/private/auth-state.json
aws ssm send-command --region ca-west-1 \
  --instance-ids i-0ef8f3e99090b9a7d \
  --document-name AWS-RunShellScript \
  --parameters '{"commands":["cat /srv/haft-vault/default/.haft/private/auth-state.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print(json.dumps({k:d.get(k) for k in [\\\"users\\\",\\\"identities\\\",\\\"memberships\\\",\\\"claim\\\"]}, indent=2))\""]}' \
  --query 'Command.CommandId' --output text
# then: aws ssm get-command-invocation --region ca-west-1 --command-id <id> --instance-id i-0ef8f3e99090b9a7d --query 'StandardOutputContent' --output text
# Service logs: journalctl -u haft-gly.service --since "<ts>" --no-pager
```

Discover the instance ID fresh if stale: `aws ec2 describe-instances --region ca-west-1 --filters "Name=tag:Name,Values=*gly*"`.

## Hosted central OTP failures before claim diagnosis

If a claimed HTTPS hosted instance fails immediately after **Send login code** with `auth.central-otp.unavailable`, first distinguish a central policy rejection from an email-delivery outage. The local route currently collapses any non-OK upstream OTP-request result into this generic `502` error.

- Verify local health, claimed state, and HQ reachability separately. They do not prove browser-origin authorization.
- Probe HQ with `Origin: https://<host>` and an **invalid** email payload—this cannot initiate provider delivery:
  ```bash
  curl -i -X POST https://<hq-hosted-origin>/api/v1/auth/otp/request \
    -H 'Origin: https://<host>' \
    -H 'Content-Type: application/json' \
    --data '{"email":"not-an-email"}'
  ```
  `403 origin-not-allowed` proves the origin is absent; `400 invalid-otp-request` proves origin admission succeeded without testing delivery.
- Do not retry the user's address or diagnose SES/Resend first when the direct HQ result is `origin-not-allowed`.
- For an explicitly authorized immediate production repair: back up the locked-down HQ environment file, add the exact canonical HTTPS origin (never wildcards, suffixes, or HTTP), restart `haft-hq.service`, then verify service health and the origin probe changes from 403 to 400.
- Treat preserving a safe upstream policy code instead of flattening it into `unavailable` as a product-quality follow-up.

### When the origin fix works but `auth.central-otp.unavailable` remains

Do not stop after proving that the origin probe changed from `403 origin-not-allowed` to `400 invalid-otp-request`. That proves only the browser-origin gate. Continue with a syntactically valid, non-deliverable reserved address such as `diagnostic.invalid@example.invalid` from the hosted instance itself; never use a real person's address for this diagnostic:

1. Call HQ directly with the hosted origin and malformed email; expect `400 invalid-otp-request`.
2. Call HQ directly with the reserved valid-format email; capture the real upstream status/body.
3. Call the local hosted OTP route with the same reserved address; compare it with HQ.
4. If HQ reports `Unsupported central database schema version: N` while the local host reports generic `502 auth.central-otp.unavailable`, inspect live HQ binary/schema compatibility. A service restart only restarts the currently installed binary; it does not deploy a compatible one.
5. Compare the live binary's supported `centralDatabaseSchemaVersion`, the database schema version, intended deploy SHA, and on-host binary freshness. Prefer redeploying a previously verified binary that supports the existing schema over opportunistically advancing the database again during incident repair.

See `references/hosted-central-otp-schema-drift.md` for the probe sequence and remediation decision tree.

### When reserved-address success does not match the browser

A reserved valid-format address proving HTTP 200 `delivery: queued` is not complete evidence for a real login request. The browser may still be hitting HQ admission throttling or an account/provider-specific failure that the local route flattens into the same generic 502.

- Correlate the local `X-Haft-Request-Id` through the hosted Caddy log and HQ Caddy log; inspect the real upstream status before changing infrastructure.
- Treat HQ HTTP 429 as throttling, not central unavailability. The hosted route should eventually map it to a dedicated local 429 with bounded `Retry-After` guidance.
- Remember that HQ's global `otp-auth` bucket may key all server-to-server calls from one hosted instance to the same relay egress IP. Do not blindly raise/remove limits or trust public forwarding headers.
- Invalid and reserved probes can consume admission capacity. After cooldown, make at most one explicitly authorized real request, verify HTTP 200 `delivery: queued`, and let the user use the newest code.
- If application telemetry delivery is stale, bounded Caddy access logs still provide request path, status, request ID, duration, origin, and source IP without request bodies.

See `references/hosted-central-otp-rate-limit-and-delivery-triage.md` for the correlation workflow, shared-relay-IP trap, and product follow-up contract.

### Design guidance: dynamic managed origin registry

A deployment-file allowlist is a valid bootstrap trust root, but it is poor day-to-day control-plane design for centrally managed hosted instances because every legitimate origin requires remote filesystem mutation and an HQ restart. Prefer a central, audited, **claim-bound browser-origin registry** for normal operation:

- store exact canonical HTTPS origin, `server_claim_id`/`vault_claim_id`, team, status, timestamps, and audit actor;
- activate an origin only after central owner/admin authority **and** cryptographic proof that it belongs to the claimed instance; custom domains also require DNS or HTTPS challenge proof;
- automatically revoke the origin on claim revocation or transfer;
- allow short-lived cache reads, but fail closed for browser-origin admission when authoritative registry state is unavailable;
- retain only a minimal static bootstrap/break-glass policy in deployment configuration.

The registry is browser-origin/CSRF posture, not authorization. Keep central sessions, signed claims/projections, scoped grants, and local route enforcement as the actual authorization boundaries; requests without an `Origin` header may be legitimate service-to-service calls and require those stronger controls.

See `references/hosted-central-otp-origin-policy-debugging.md` for read-only probes, expected response shapes, and the safe remediation sequence. See `references/dynamic-claimed-browser-origin-registry.md` for the claim-bound dynamic replacement design.

### Managed-enrollment runtime recovery after deploy

When repairing a legacy bootstrap claim after an HQ/destination release, distinguish **release deployment**, **managed-origin activation**, **local central projection**, and **browser-shaped OTP delivery**. Do not report login recovery from health/status alone. A command-line OTP request must include the exact HTTPS `Origin` header to represent browser behavior; without it, `auth.central-origin.missing` is expected.

**Classify where the OTP request stops before touching email infrastructure.** If the destination route itself returns `auth.central-origin.managed-origin.claim-inactive` and logs `browser-origin.local-proxy-mismatch`, the request never reached HQ or the email provider. Do not inspect the inbox, retry the user's address, or diagnose SES/Resend. Instead, inspect the destination auth-state claim sources, redacted enrollment journals, and HQ's exact origin→vault→server binding using the read-only evidence ladder in `references/durable-host-enrollment-origin-conflict.md`. An active local-bootstrap claim can truthfully report `claimed/login` while managed browser OTP remains unavailable.

**First prove that the hostname reaches the host you are repairing.** Resolve the canonical FQDN, map its IP to the live instance/load balancer, inspect lifecycle tags and active service, and make a public no-cache auth-status request. A service name, `hostRole` log, historic deployment variable, or a successful loopback probe is not evidence of current FQDN ownership. Never claim or enroll a host tagged temporary/E2E merely because DNS currently reaches it; do not repoint DNS to a candidate until TLS/SNI, virtual-host routing, health, and public auth status pass. Re-check the public FQDN after every repair. See `references/live-origin-identity-before-claim-recovery.md`.

If enrollment fails writing a JWKS path under `/etc`, remember that atomic replacement needs parent-directory write permission. Move the JWKS to a service-user-writable path allowed by systemd `ReadWritePaths`, update a late drop-in, restart, and resume the existing journal. Clear deprecated `HAFT_REMOTE_*` compatibility bindings when the destination should use managed local-host identity. If HQ assigns a collision suffix (`<slug>-2`) rather than the requested target slug, stop and reconcile the central target binding through a supported operation; do not force journal state or treat it as a harmless label mismatch. For durable replacement at the same hostname, distinguish a local claim from central browser-origin ownership: a partial server claim can leave the host recoverable while HQ correctly rejects the old active vault origin.

A later fixed release does not automatically repair central rows created by an earlier partial recovery. Compare journal and deploy timestamps, require the idempotent recovery path to supersede stale same-origin claims transactionally, and derive `VAULT_ROOT`, Central JWKS, service, and binary paths from the active runtime before any retry. When a repair is dispatched from a workflow branch but deploys a tag, remember that the deploy checkout replaces branch-only helper files; use a second sparse checkout of `github.ref` into a separate path. See `references/partial-managed-enrollment-convergence-and-ops-dispatch.md` for the regression contract, fail-closed repair sequence, and constrained GitHub Actions/SSM pattern. See `references/managed-enrollment-runtime-recovery.md` and `references/durable-host-enrollment-origin-conflict.md` for the broader evidence hierarchy, constrained local-identity repair, and escalation boundary.

For workstation-pairing recovery on Haft `0.1.22`, keep two operational pitfalls explicit until the transfer-intent follow-up lands. First, the workstation's `$HOME/.haft` directory must be owned by the operator and mode `0700`; a group-writable directory causes journal creation to fail closed with a generic malformed/unsafe-journal error even when the invitation is valid. Second, when the destination-issued invitation carries `recover-reinstall` or `transfer-owner`, pass the same value explicitly on both consume and resume commands (for example `--transfer recover-reinstall`). In `0.1.22`, omitting it can mint the HQ assertion with parsed intent `none`, reach `destination-pairing-ready`, and then force invitation reissue at claim. Transfer pairing files only through an encrypted channel, keep them mode `0600`, delete transfer copies after consumption, and verify completion with exactly one ready central target plus a real bounded canary import—not status or health alone.

## Product guidance

### Best near-term product direction

Keep the current security boundary but improve the UX:

- if `claimState.status === unclaimed`, show a **Claim this Haft box** flow
- step 1: sign in / verify identity
- step 2: provide local bootstrap proof
- step 3: finalize first-owner claim

That is **UI-assisted claim**, not **OTP-only claim**.

### Best current recommendation

For real deployments, recommend:
- SSH / SSM / local shell for issuing the bootstrap token
- browser UI only as a helper for entering identity and optionally entering the one-time token

### What not to recommend

Do **not** recommend treating verified email alone as enough to claim a self-hosted instance. Inbox control is weaker than host control and breaks the intended fail-closed ownership model.

## Reset broken claims when Epic 20 sync is missing

When a remote Haft instance (e.g., `dev.wheretoaccess.com`) has a stale claim that predates Epic 20 sync and blocks CLI remote-target discovery, follow this pattern to reset and reclaim fresh.

**Symptom**: `haft remotes list` returns empty (`central-no-targets`) despite recent OTP login; remote status returns HTTP 403; `POST /api/v1/vault-access-grants` fails with `vault-claim-not-found` because the local claim hasn't synced to HQ's projection.

**Root cause**: Historical claims may lack central projection sync — the Epic 20 grant‑exchange path hasn't wired the dev instance's `serverClaimId` to HQ's `central_vault_access_grants`.

**Workflow**:

1. **Locate the instance**
   Find EC2 instance ID (`i-…`) via AWS Console or `aws ec2 describe-instances` filter on public IP.

2. **SSM in and backup auth state**
   ```bash
   aws ssm send-command \
     --instance-ids i-0f5e0799f02f1768d \
     --document-name AWS-RunShellScript \
     --parameters 'commands=["systemctl stop haft-dev.service", \
                           "cp /home/haft/.haft/vaults/default/.haft/private/auth-state.json /home/haft/.haft/vaults/default/.haft/private/auth-state.json.bak.$(date +%s)", \
                           "rm /home/haft/.haft/vaults/default/.haft/private/auth-state.json", \
                           "systemctl start haft-dev.service"]'
   ```

3. **Generate fresh bootstrap token**
   ```bash
   aws ssm send-command \
     --instance-ids i-0f5e0799f02f1768d \
     --document-name AWS-RunShellScript \
     --parameters 'commands=["cd /srv/haft-dev/app && sudo -u haft bun scripts/haft-auth-bootstrap-token.ts /home/haft/.haft/vaults/default"]'
   ```

4. **Complete fresh claim via local API**
   Use the raw `bootstrapToken` revealed once:
   ```bash
   curl -X POST https://dev.wheretoaccess.com/api/auth/bootstrap/claim \
     -H "Content-Type: application/json" \
     -d '{
       "bootstrapToken": "hvclaim_...",
       "identity": {
         "provider": "local-email",
         "email": "owner@example.com",
         "displayName": "Owner"
       }
     }'
   ```

5. **Capture fresh claim IDs**
   Extract `serverClaimId` (e.g., `srvclaim:…`) and `vaultClaimId` from the returned auth state.

6. **Create vault‑access grant via HQ (if projection sync is live)**
   Use the section above ([HQ Admin API endpoint for vault-access grants](#hq-admin-api-endpoint-for-vault-access-grants)).
   ```bash
   curl -H "Authorization: Bearer $ACCESS_HANDLE" \
     -H "Content-Type: application/json" \
     -d '{
       "vaultClaimId": "vaultclaim:…",
       "email": "owner@example.com",
       "role": "admin",
       "capabilities": ["secure", "publish"],
       "routeFamilies": ["private-read", "automation"],
       "pathPrefixes": [""],
       "apiOrigin": "https://dev.wheretoaccess.com"
     }' \
     https://<hq-hosted-origin>/api/v1/vault-access-grants
   ```

**Note**: If `POST /api/v1/vault-access-grants` still returns `vault-claim-not-found`, the Epic 20 projection sync may not be wired yet; in that case:

- The managed path (`haft remotes list`) will stay empty until Epic 20 ships.
- Manual `haft remote add <slug> --url … --token-env <ENV>` works for remote registration.

**But** even after fresh claim, `remote status` may fail with HTTP 403 because the dev instance gates `/api/app/status` behind auth that central session token doesn't satisfy.

**Fallback: manual service‑token creation**

If `POST /api/auth/service-tokens` gate‑denied (central projection missing), you can write a local service token directly to the dev host's `.haft/private/service-tokens.json` via SSM.

**Steps:**

1. Generate a service token on the dev host via Python/SSM:
```bash
aws ssm send-command \
  --instance-ids i-… \
  --document-name AWS-RunShellScript \
  --parameters 'commands=[\"sudo -u haft tee /home/haft/.haft/vaults/default/.haft/private/service-tokens.json <<'\''EOF'\''\\n{\\\"profile\\\": \\\"haft.scoped-service-token-store.v0\\\", \\\"principals\\\": [...], \\\"tokens\\\": [...], \\\"auditEvents\\\": [...}\\nEOF\"]'
```

2. Use the token as `--token-env ENV` credential:
```bash
HAFT_DEV_TOKEN=\"hvst_<instance-service-token-material>\" \
bun src/cli.ts remote status dev
```

**Key signal**: Current service-token bearer material uses the `hvst_` prefix. If `remote status dev` returns **403** but shows `Reachability: checked public /api/app/status without destination credentials`, the status command did not send destination credentials; verify token acceptance with a direct authenticated endpoint or an actual import.

**Pitfall**: Writing the store file requires correct ownership (`chown haft:haft` on the parent directory) and valid JSON."

## Break-glass local collaborator access

When a claimed hosted instance needs immediate access for a known collaborator before managed invitations are complete, use the destination-local membership seam rather than pretending the unfinished central invite flow is ready. Keep the distinction explicit: a local `local-email` identity plus active vault membership enables destination login, but does not create a central invitation, acceptance record, or portable grant.

Follow `references/manual-local-collaborator-access.md` for the backup, idempotent mutation, atomic write, restart, OTP-origin/provider verification, rollback, and post-login checks. Prefer the authenticated member API; direct file mutation is an explicitly authorized break-glass path only.

## Managed owner and collaborator browser projection

Keep authorization roles separate during managed browser login and session bootstrap:

- claimed owners use local claim/team membership and must bypass central-vault-grant lookup, regardless of whether the browser identity provider is `local-email` or `portal`;
- non-owner managed collaborators must be projected from an active central grant matching the account, email, and vault claim;
- after projection, verify the browser session is rebound to the projected portal identity and that the local membership retains the target vault and usable vault scopes/path prefixes;
- do not alter OTP or invitation delivery to fix a `grant-missing` or `route.gate-denied` projection failure.

Use `references/managed-browser-owner-collaborator-projection.md` for the predicate trace and regression contract.

### Managed owner denied as a missing grant

When a claimed owner receives `managed-member-projection.grant-missing` after successful central OTP verification, do not assume the owner lacks a central vault grant. First compare the managed claim vault with the claimed owner's local membership vault and scope. The owner bypass is conditional: the identity must be the claim owner, the asserted central account must match the claim account, and there must be an active membership whose `vault` and `vaultScopes[].vault` match `claim.vaultClaim.vault`. A stale legacy membership such as `default` on a claim for `gly` makes the owner look like a non-owner managed member; projection then correctly requires a central grant and fails closed when none is present.

Read-only evidence should establish separately that OTP request/verify succeeded at HQ, GLY is claimed with an active managed projection, and the exact claim vault, account binding, owner membership vault/scope, and projection failure stage. Repair local managed enrollment/membership through a supported reconciliation path. Do not add a central grant merely to mask a stale owner membership, and do not edit `auth-state.json` by hand unless an explicitly authorized break-glass procedure requires it. See `references/managed-owner-grant-missing.md`.

If no supported reconciliation command exists and the operator explicitly authorizes break-glass repair, use a guarded SSM procedure: stop the destination service; make a mode-0600, service-owned backup; require an active `central-identity` claim, exactly one active owner membership, and a target vault from `claim.vaultClaim.vault`; atomically retarget only that owner membership's `vault` and `vaultScopes` to the claim vault while preserving roles/capabilities; append a bounded audit event without secrets; restore service ownership/mode; restart; and verify service activity, public `/api/auth/status`, public health/build, and the resulting owner membership summary. Never report login recovery from service health alone—the browser OTP canary must be rerun after the repair.

For future incidents, expose this predicate as a structured decision rather than a boolean: distinguish `claimed-owner`, `claimed-owner-membership-mismatch`, `managed-member`, and `identity-not-found`. Map the mismatch to a safe actionable browser error while keeping real collaborator `grant-missing` failures fail-closed. This prevents a stale owner membership from being misreported as a missing central grant and preserves the authorization boundary. See `references/managed-owner-reconciliation-cli.md` for the bounded follow-up CLI contract and regression matrix.

## Browser-session duration and cookie-identity changes

Treat local browser sessions as distinct from both OTP challenges and central credentials:

- The local browser-session expiry and cookie `Max-Age` must be derived from the same issued expiry. Verify both, and determine whether expiry is fixed or sliding before recommending a duration change.
- A central access handle/refresh credential can rotate independently; it does **not** automatically extend the local browser session unless code explicitly does so.
- When a user asks to make one hosted surface (for example a dev/dogfood hostname) stay signed in longer, do not silently change the global default. Prefer an explicit, bounded per-runtime/per-deployment TTL seam; keep production-like defaults unchanged unless the user asks for a global policy change.
- Renaming a cookie is an authentication cutover decision, not merely branding. Inventory the canonical name constant, issuance/clearing/parsing paths, source tests, operator documentation, and generated build artifacts. State the compatibility cost explicitly.
- For a small controlled audience, a clean cutover is usually preferable: issue/read only the new cookie name and do not migrate or accept the legacy name. Existing sessions then require one re-login after deployment; legacy cookies expire naturally. Preserve `HttpOnly`, `SameSite`, `Path`, `Secure`, CSRF behavior, and server-side session validation.
- Add regression coverage for the default TTL, the targeted override, canonical cookie issuance and `Max-Age`, and rejection of a legacy-cookie-only request. Verify the deployed hostname's `Set-Cookie` header after rollout without exposing its cookie value.

## Implementation surfaces to inspect

When verifying or modifying this behavior, inspect at least:
- `scripts/haft-auth-bootstrap-token.ts`
- `docs/2026-06-30-epic13-self-hosted-auth-operator-runbook.md`
- `apps/server/src/routes/auth.ts`
- `apps/server/src/auth/human-sessions.ts`
- `apps/web/src/app-shell/OnboardingStateScreen.tsx`

## Pitfalls

- Do not describe the bootstrap-token path as merely a rare recovery path when the box is still unclaimed; under the current model it is the **required first-owner enrollment path**.
- Do not confuse **login failure** with **claim-state failure**.
- Do not weaken the model by proposing public first-login auto-claim for self-hosted/public-mode boxes.
- Public/EC2/production-like browser login must use HTTPS. These runtimes mark `hv_session` as `Secure`; over a raw `http://<ip>:9001` URL the OTP/claim response can return `ok: true` and create a server-side session, but the browser will reject/withhold the cookie, so follow-up `/api/app/status` sees `principal: null` and loops back to login. Put the instance behind DNS + Caddy/TLS (for example `https://<gly-hosted-origin>`) before dogfooding browser auth.
- Do not leak raw bootstrap tokens into logs, issue bodies, comments, or stored artifacts.
- The `projection-expired` UI message suggests `haft remote refresh default` as a generic example. The actual vault slug is instance-specific (e.g. `gly`). Always discover the real slug via `haft remote list --json` or systemd environment before running refresh; a slug mismatch fails closed with `cli-remote.refresh-vault-mismatch` and wastes an SSM round-trip.

## Verification checklist

- Confirm whether the instance claim state is `unclaimed`, `active`, or `revoked`.
- If unclaimed, confirm the user/operator has local host access or an equivalent trusted operator path.
- Verify the bootstrap token is generated locally and revealed once.
- Verify first-owner claim activates local claim state and creates owner/admin membership.
- Verify post-claim browser session / CSRF issuance works.
- If reviewing UI, make sure unclaimed-state messaging distinguishes identity proof from ownership proof.
- For temporary/public EC2 test instances, separately report: local claim state, HQ central server/vault claim rows, HQ vault-access grant rows for the exact target origin, and account-level entitlement rows. A local claim does not imply HQ projection, and entitlements do not imply a target-specific grant. See `references/temporary-instance-claim-vs-hq-entitlements.md`.

## Regression handoff and board reconciliation

A completed rollout or benchmark card is historical evidence, not proof that a host remains claimed. Recheck the live public auth-status endpoint immediately before any authenticated acceptance rerun.

If live auth is `unclaimed` / `bootstrap` while the predecessor card is terminal:

1. Do not force the terminal card back to active or claim the benchmark is unblocked.
2. Create a narrowly scoped operational successor for claim restoration plus the blocked acceptance rerun.
3. Keep it blocked until both proofs exist: a host-local short-lived pairing proof and verified human browser identity. Never synthesize an identity or transmit pairing material through tickets, issue comments, logs, or email.
4. Record sanitized live facts only: auth state, health/build identity, trusted public origin, and host reachability.
5. After the claim, verify browser bootstrap separately before the benchmark. Runtime health alone is insufficient.

This preserves the two-proof boundary and prevents stale Done state from masking a renewed prerequisite.

### Extended: Historical claim-to-discovery mismatch debugging

When a local instance shows as claimed (`haft doctor` returns `claimState.status: "active"`) but remote-targets discovery returns empty, follow this layered verification:

**Symptoms**: `haft remotes list` returns zero targets despite active local claim and central session.

**Root cause pattern**: Historical claims (pre-Epic 20/central entitlement projection) may not have automatic grant creation in the central `vault_access_grants` table.

**Debugging layers**:
1. **Local auth**: `haft whoami --json` → verify active central session
2. **Session refresh**: If remote-targets returns `invalid-central-session`, refresh CLI session with `haft auth login`
3. **Route availability**: `curl -H "Authorization: Bearer <accessHandle>" https://<hq-hosted-origin>/api/v1/remote-targets` → confirm endpoint deployed (404 vs 401 vs 200 with empty `targets`)
4. **Local claim metadata**: Extract `serverClaimId` and `vaultClaimId` from `haft doctor --json`

### HQ Admin API endpoint for vault-access grants

**Always prefer the documented API over raw SQL** — HQ provides a validated endpoint for creating missing grants.

**Endpoint**: `POST /api/v1/vault-access-grants`

**Required headers**:
- `Authorization: Bearer <central-access-handle>`
- `Content-Type: application/json`

**Schema (TypeScript/Zod)**:
```typescript
{
  vaultClaimId: string,           // must exist in central_vault_claims
  accountId?: string,             // central_accounts.account_id
  email?: string,                 // email_normalized
  role: "admin" | "editor" | "viewer",  // defaults to "viewer"
  capabilities: Array<"publish" | "secure" | "team" | "custom-domain" | "service-token-admin">,  // default ["secure"]
  routeFamilies: Array<string>,   // regex ^[a-z0-9][a-z0-9._:-]*$i, default ["private-read"]
  pathPrefixes: Array<string>,    // default [""]
  apiOrigin: string,              // target vault API origin
  expiresAt?: string             // ISO date string
}
```

**Default valid payload**:
```json
{
  "vaultClaimId": "vaultclaim:...",
  "accountId": "acct:...",
  "role": "admin",
  "capabilities": ["secure"],
  "routeFamilies": ["private-read"],
  "pathPrefixes": [""],
  "apiOrigin": "https://example.com"
}
```

**Common errors**:
- `invalid-vault-access-grant-request`: Schema validation failed (invalid capability, routeFamily format)
- `vault-claim-not-found`: `vaultClaimId` doesn't exist in HQ (vault not yet synced via projection)
- `invalid-central-session`: Token expired — use `haft auth login` to refresh
- `account-not-found`: `accountId` doesn't match central_accounts

**Pre-flight checklist**:
1. Ensure vault claim exists in HQ projection (may require projection sync after remote instance setup)
2. Ensure you have admin privileges on the team owning the vault claim
3. Verify central session is active (`$HOME/.haft/cli-credentials.json` contains valid `accessHandle`)

**Example curl**:
```bash
ACCESS_TOKEN=$(jq -r .central.accessHandle ~/.haft/cli-credentials.json)
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vaultClaimId": "vaultclaim:...",
    "accountId": "acct:...",
    "role": "admin",
    "capabilities": ["secure"],
    "routeFamilies": ["private-read"],
    "pathPrefixes": ["/api/v1"],
    "apiOrigin": "https://example.com"
  }' \
  https://<hq-hosted-origin>/api/v1/vault-access-grants
```

5. **Central DB verification** (when HQ SQLite accessible):
   - Account exists in `central_accounts` for authenticated identity
   - Server claim exists in `central_server_claims`
   - Vault claim exists in `central_vault_claims` with matching `server_claim_id`
   - Check `central_vault_access_grants` for grants linking `subject_account_id`/email to `vault_claim_id`
6. **Manual repair options**:
   - Use HQ route `POST /api/v1/account/grant` (if admin session available)
   - Direct DB fix via production HQ instance access:
     - **SSM access** (EC2 production HQ):
       ```bash
       # Find HQ database path via environment
       # NOTE: live HQ prod instance is i-0506a9354ace6c77f (ca-west-1) as of 2026-07-29.
       # Discover fresh via: gh variable list --repo jplew/haft | grep HAFT_HQ_PROD_INSTANCE_ID
       aws ssm send-command --region ca-west-1 \
         --instance-ids i-0506a9354ace6c77f \
         --document-name AWS-RunShellScript \
         --parameters commands='["set -eu", "grep -E \"^(HAFT_HQ_DATABASE_DSN|BUN_SQLITE_PATH|DBSQLITE)\" /etc/haft-hq.env || echo \"no env var found\""]'
       ```
     - **SQLite insertion pattern**:
       ```python
       # Using current central_vault_access_grants schema from our session
       grant_data = {
           "grant_id": "grant:e7d9679c623c4091a0",  # prefixed with "grant:" + random hex
           "vault_claim_id": "vaultclaim:ea712cd4b8444476a89bb9e6ffa944e8",
           "subject_account_id": "acct:bf80da62-0b84-4f94-9b80-f55c9d2f1635",
           "email_normalized": "<operator-email>",
           "role": "admin",
           "status": "active",
           "target_api_origin": "https://hypervault.canedo.me",
           "capabilities_json": "{\"canPublish\": true}",
           "route_families_json": "[\"*\"]",
           "path_prefixes_json": "[\"/api/v1\"]",
           "created_at": "2026-07-06T04:49:32.267348Z",
           "updated_at": "2026-07-06T04:49:32.267354Z"
       }
       ```
   - Restart HQ service (`systemctl restart haft-hq.service`) after DB changes if using in-memory session mapping

**Key credentials locations**:
- CLI central session tokens: `~/.haft/cli-credentials.json` (contains `accessHandle`, `refreshHandle`)
- HQ environment: `/etc/haft-hq.env` (production), `.env.production` (app root)
- Production HQ instance: `i-0506a9354ace6c77f` (ca-west-1 region) — discover fresh via `gh variable list --repo jplew/haft | grep HAFT_HQ_PROD_INSTANCE_ID`; the older `i-085957aeb58cda332` is stale.

**Pitfalls**:
- HQ database path may not be in `/etc/haft-hq.env` for production; check app root `.env.production` or `.env.production.local`
- Central session tokens expire (~30 minutes); refresh with `haft auth login`
- Insert `OR IGNORE` to avoid duplicate grant errors
- Verify grants count after insertion: `SELECT count(*) FROM central_vault_access_grants WHERE vault_claim_id = ? AND subject_account_id = ?`

## References

- `docs/2026-06-30-epic13-self-hosted-auth-operator-runbook.md`
- `scripts/haft-auth-bootstrap-token.ts`
- `apps/server/src/routes/auth.ts`
- `apps/server/src/auth/human-sessions.ts`
- `apps/web/src/app-shell/OnboardingStateScreen.tsx`

**Linked in‑skill references** (use `skill_view(name, file_path)`):
- `references/epic20-sync-gap-remote-status-fails.md` — remote‑status 403 patterns
- `references/hq-vault-access-grant-endpoint.md` — HQ grant endpoint schema
- `references/service-token-direct-fallbacks.md` — manual service‑token injection when `POST /api/auth/service-tokens` gate‑denied
- `references/hq-managed-discovery-repair-blockers.md` — repairing `haft remotes list` managed discovery when HQ lacks central claim/grant rows, including the ephemeral `HAFT_HQ_SESSION_MATERIAL` blocker
- `references/hq-persistent-db-and-manual-central-grant-repair.md` — break-glass repair for HQ persistent DB wiring plus manual central server/vault claim and grant seeding when managed discovery returns no targets
- `references/central-managed-remote-repair-2026-07-06.md` — session-specific repair notes for HQ persistent DB/session material, account-ID reset after durable DB cutover, central grant seeding, and destination verifier separation
- `references/hq-central-identity-turso-clean-cutover.md` — planning guidance for moving HQ central identity/grant/entitlement state from EC2-local SQLite to Turso/libSQL with a clean wipe/reseed stance when JP accepts data reset
- `references/hq-turso-runtime-cutover-verification.md` — live post-cutover verification/repair checklist: query Turso via the HQ adapter, distinguish empty schema from usable authorization, confirm HQ passes `HAFT_HQ_DATABASE_AUTH_TOKEN`, handle libSQL `PRAGMA user_version` limits, and classify deploy-run ref-lock failures separately from DB health
- `references/central-grant-dogfood-triage.md` — managed remote import triage for central-discovered `dev`: separate account grants, destination JWKS staleness (`auth.central-grant.bad-signature`), delegated capability mapping, and CLI/server strict-schema drift.
- `references/manual-local-collaborator-access.md` — explicitly authorized destination-local admin/member grant before managed invites ship: backup, atomic file mutation fallback, OTP readiness, verification, and rollback.
- `references/hosted-central-otp-rate-limit-and-delivery-triage.md` — correlate request and verify failures across hosted/HQ logs and privacy-safe challenge state; diagnose stale OTP autofill, mapped 429s, shared relay buckets, and silent `noop` observability regressions.
- `references/hq-turso-db-transport-otp-verify-failures.md` — emails sent but verify returns `invalid-or-expired-challenge`: intermittent Turso transport failures on HQ break the verify transaction; correlation, rate-limiter interaction, and remediation.
- `references/legacy-local-claim-managed-enrollment-recovery.md` — recover hosted-browser OTP denial caused by a legacy `local-bootstrap` claim; managed enrollment, journal privacy, and HQ vault-claim-500 resume triage.
