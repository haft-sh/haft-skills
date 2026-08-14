---
name: haft-cli-auth-and-remotes
description: "Operate Haft CLI authentication lifecycle and remote target registration: OTP login, credential wallet, token classes, remote add/status, and diagnostic recovery."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [haft, cli, auth, remotes, otp, credentials]
    related_skills: [haft-import-operations, haft-vault-operations, self-hosted-instance-auth-claiming]
---

# Haft CLI Auth & Remotes

## When to Use

Any session that touches:
- `haft auth login` / `haft auth refresh`
- `haft remotes list` / `haft remote add` / `haft remote status`
- remote publish-target inspection/configuration through an authenticated CLI
- delegated-grant authorization for remote configuration writes
- Token expiry diagnostics (`central-access-expired`, `central-no-targets`)
- Credential wallet inspection

## Style Preference: Pragmatic Troubleshooting

The user expects a **direct, pragmatic approach** when faced with authentication or grant-sync obstacles:

- **Prefer live workarounds** over theoretical explanations when the managed path is broken.
- **Actively try fallback steps** (e.g., manual remote registration, SSM instance reset) immediately upon encountering stale claims.
- **When Epic 20 sync isn't wired** and `central-no-targets` persists, treat manual fallback as the legitimate immediate path, not as a failure.

Key signals:
- Phrases like **"do whatever works"** mean skip architectural analysis, jump to actionable steps that yield a working state, document the gap separately.
- **Clock-aware**: Central sessions expire in ~30 min; OTP challenges expire in ~5 min. Sequence work so you complete tasks before token expiry.
- **Focus on outcome**: A registered remote (even if manual) is better than an empty `remotes list`.

Thus, when diagnosing auth/remote discovery:
1. Verify the quickest‑path fix (manual `remote add` with available tokens)
2. If that fails due to stale/confused instance claim, reset instance auth via SSM
3. Accept that Epic 20 sync gap may remain — that's a product issue, not a blocker for delivering a minimally working remote registration

## User Preference: Pragmatic Over Perfect

When user says "do whatever works", immediately:
- Skip architectural analysis of sync gaps
- Accept manual fallback paths without commenting on product issues
- Focus on achieving working state rather than fixing underlying sync wiring
- Document gaps separately from execution path

## Two-Step OTP Login

Login is always two commands.

### Self-serve OTP retrieval for Codex / DevSpace workers

When a ChatGPT / Codex worker is blocked waiting for a human to relay an OTP, prefer direct mailbox inspection through the shared Inkbox identity instead of pausing the lane.

Haft-specific note: OTPs for `<operator-email>` may be forwarded into the read-only `<read-only-canary-address>` operational inbox. For Haft login flows, inspect that inbox first before asking JP to relay a code manually. Treat the forwarded OTP message as read-only input only — never reply, forward, or turn it into a conversational email thread.

Bootstrap once:

```bash
export PATH="<local-bin>:$PATH"
# Keep nounset off only while loading this profile's environment: a shell
# already running with `set -u` can reject valid provider setup expansions.
set +u; set -a; source <hermes-home>/profiles/orchestrator/.env; set +a; set -u
command -v inkbox
command -v haft
```

If that environment file is not needed by the installed Inkbox CLI, prefer the existing authenticated CLI configuration rather than sourcing it.

Read path:

```bash
inkbox email unread -i haft --direction inbound --limit 10 --json
inkbox email list -i haft --direction inbound --limit 20 --json
inkbox email get -i haft <message-id> --json
```

Rules:
- OTP emails are **read-only inputs**. Do not reply.
- Prefer `unread` / `list` before `get`; fetching an inbound message with `inkbox email get` marks it read.
- Match the message timestamp to the active challenge window so you do not consume an older code.
- Extract the OTP, complete `haft auth login --challenge-id ... --code ...`, then immediately verify with `haft whoami --json` and continue the blocked operation in the same fresh auth window.
- If `whoami` succeeds but `remotes list` or `remote status` still fails, classify that as discovery / remote-resolution work, not an OTP failure.
- When the OTP email itself is the current inbound Hermes/Inkbox chat context, treat that message body as the source of truth and relay the code directly if needed; do **not** search old sessions first and do **not** reply to the no-reply sender.
- If the user needs the code on another device/channel, use an approved non-email relay path (for example Home/Telegram delivery) rather than turning the OTP email into a reply thread.

See `references/codex-self-serve-otp-via-inkbox.md` for the shell-ready workflow and extraction pattern.

Login is always two commands:

```bash
# 1. Request OTP (sends email)
bun src/cli.ts auth login --email <operator-email>
# → Challenge: otp:<uuid>
# → Expires: ~5 min window

# 2. Verify with code from email
bun src/cli.ts auth login --email <operator-email> \
  --challenge-id otp:<uuid> --code <6-digit-code>
# → Logged in. Session expires: ~30 min from login.
```

Session is short-lived (~30 min). Plan accordingly — don't login early then do unrelated work.

## Reader URLs versus browser artifact routes

For CLI retrieval, distinguish a canonical Haft Reader URL from a browser-only SPA artifact route.

- `haft get` accepts its documented Reader page/slug URLs and durable handles such as `haft://artifact/<artifact-id>`.
- A link shaped `https://<host>/#/artifact/<artifact-id>` is a frontend route, not a Reader route; do not claim it is retrievable by `haft get` just because it opens in the browser.
- For remote AgentSession work, preserve the canonical `readerUrl` emitted by a successful start/attach/status/preview/diff/turn receipt. It is the handoff URL for later `haft get` retrieval. If only an artifact UI route is available, use the artifact ID or durable handle for targeting and obtain the canonical Reader URL from a current session receipt.

When a reader URL is supplied, run the installed CLI against the intended remote with the deliberate host `HOME` context and record the actual result before filing implementation work from the document. Do not infer document contents from the URL shape.

## Credential Wallet Location

Depends on effective `HOME`:

| Context | Wallet path |
|---|---|
| Hermes orchestrator session | `~/.hermes/profiles/orchestrator/home/.haft/cli-credentials.json` |
| Host-level bare shell | `<dev-host-home>/.haft/cli-credentials.json` |

When debugging, check which wallet you're actually reading.

## Token Classes (Critical Distinction)

| Prefix | Scope | Issued by | Valid for |
|---|---|---|---|
| `hv_central-session_*` | HQ (<hq-hosted-origin>) only | `haft auth login` OTP | HQ API, grant discovery |
| Instance-level token | One remote instance | Instance admin/claim | That instance's routes |

**A central session token CANNOT authenticate to a remote Haft instance.** Using one as a remote credential will register locally (bookkeeping) but produce 403 `route.gate-denied` on `remote status` or any instance API call.

## Registering a Remote

`haft remote add` requires exactly one credential source flag.

### Use `--token-env` (always prefer this in Hermes)

```bash
HAFT_DEV_TOKEN="<token>" bun src/cli.ts remote add dev \
  --url https://dev.wheretoaccess.com --token-env HAFT_DEV_TOKEN
```

### Do NOT use `--token-stdin` in Hermes sessions

Piping to stdin triggers the Hermes safety system (blocks as potentially destructive action). Always use `--token-env` with inline env var assignment instead.

## Remote registry is not remote publish-target configuration

When a user asks to “configure a remote,” first separate workstation-local remote registration from mutation of the destination vault:

- `haft remote add/status/remove` and `haft remotes list` operate on this machine’s remote registry and reachability/import relationship.
- `haft remote enroll` and pairing establish managed destination identity and claims.
- The destination vault’s R2/S3 publishing target is a separate admin-write surface. Do not imply that `remote add` configures it.

Before suggesting syntax, inspect the installed `haft --help` and `haft remote --help`; CLI capabilities change. If there is no verified CLI wrapper, direct the user to the authenticated **Settings → Remote publish target → Configure BYO target** flow rather than inventing a command or bearer-token `curl` recipe.

For a future managed CLI wrapper, keep authentication and authorization distinct:

1. The central CLI session proves identity to HQ; never forward it directly to the destination.
2. Exchange it for a short-lived grant bound to the selected server/vault and configuration operation.
3. Require owner/admin configuration authority—normally the live equivalent of `admin.config.write`. Ordinary `artifact.publish` permission is insufficient because this write stores provider credentials and changes where vault data can be uploaded.
4. Keep raw central-session rejection, cross-target denial, expiry checks, and bounded audit behavior intact.
5. Accept provider credentials through environment references or another non-argv secret source, and return only redacted status.

A preferred command family is `haft remote publish-target show|set <slug>`, which remains distinct from artifact publishing and default auto-publish policy mutation.

See:
- `references/remote-registry-vs-publish-target-configuration.md` for the control-plane distinction, live capability-check procedure, underlying app routes, and safe answer pattern.
- `references/remote-publish-target-cli-authorization.md` for the delegated-grant design, secret handling, failure behavior, and verification matrix.

## Clean-host managed recovery activation

A `recover-reinstall` enrollment can legitimately stop at `remote-enrollment.activation-required` after it stages public JWKS and before it writes local host identity. Configure central grants and JWKS in the **destination service**, restart it, and prove bounded localhost health. The CLI performs its own runtime verifier preflight as well, so invoke the resumed CLI with the same enabled verifier configuration; do not assume systemd environment automatically reaches the CLI process.

For a clean host with no local identity yet, use only the documented, journal-derived compatibility verifier binding during this narrow activation window. Never copy the retired host identity or manually edit HQ claims. After success, remove the temporary compatibility binding and verify the service resolves grants through the newly installed local-host identity.

If recovery instead reaches `remote-enrollment.target-slug-mismatch`, do not retry under the historical source slug. Treat it as an atomic target-convergence product defect: recovery must expose the replacement slug while ordinary enrollment remains strict. See [clean-host recovery activation and target-slug convergence](references/clean-host-recovery-enrollment-activation-and-target-slug.md).

## Managed browser OTP identity resolution

When a managed instance sends and verifies central email OTP but returns `auth.identity.not-found` after verification, diagnose the local identity provider before retrying OTP. Managed enrollment commonly projects approved people as `portal` identities keyed by central account ID; an older central-email login seam may look only for a `local-email` identity keyed by email. Confirm this with provider/count-only host diagnostics; never print local auth state, identity subjects, emails, assertions, or session records.

Do not repair this by manually seeding auth-state JSON or creating a local-email owner after an OTP. The product must resolve the verified assertion's existing `portal` account identity first, retain `local-email` as a compatibility fallback for locally claimed hosts, and never auto-provision identity or membership from OTP alone. Use the focused reproduction, security boundaries, and test matrix in [managed central OTP identity resolution](references/managed-central-otp-identity-resolution.md).

## Diagnostic Codes & Recovery

| Code | Meaning | Recovery |
|---|---|---|
| `cli-remote.central-access-expired` | Wallet exists, session expired | Try `haft auth refresh`; if refresh says it did not return a usable access handle, immediately do fresh two-step `auth login` instead of retrying refresh |
| `cli-remote.central-no-targets` | HQ has no grant rows for this identity | Confirm instance claimed/granted in HQ, or manual `remote add` fallback |
| `route.gate-denied` (403 on remote) | Token class mismatch, invalid principal, missing delegated grant projection, or status check without destination credential | First verify the configured credential source is present; then distinguish central-token-as-instance-token from an instance grant/principal sync gap |

## Verification Order

### Routine remote delivery: import first

When the user asks to upload an already-host-visible artifact to an established target, run the import first:

```bash
export PATH="<local-bin>:$PATH"
HOME=<dev-host-home> haft import /absolute/path/to/file --remote dev --wait --json
```

A successful result is the decisive proof: it exercises wallet lookup, central target resolution, target-bound grant exchange, destination verification, and the write. Do **not** spend routine calls on `whoami`, `remotes list`, or `remote status` first. Use those only after a failed import to classify the failure, or when collecting formal managed-path/release evidence.

### Formal auth/discovery evidence

After auth, verify incrementally:

1. `bun src/cli.ts remotes list` — confirms wallet is readable and discovery runs
   - Treat the output as two separate signals: **manual registry rows** may appear even when **managed HQ discovery** returns `central-no-targets`.
   - If a row's credential is `env:<NAME>`, check that environment variable is actually set before interpreting status failures.
   - If a slug shows as `manual*`, remove the manual override before diagnosing the managed path. A manual `dev` remote can mask the central-discovered `dev` target and turn a central-path investigation into a misleading manual-credential failure.
2. `bun src/cli.ts remote status <slug>` — confirms instance reachability AND token validity only when the configured destination credential is present.
   - If the env credential is missing, status may fall back to bounded public `/api/app/status` reachability and report HTTP 403; that proves the instance is reachable but does **not** prove the instance token is invalid.
3. `bun src/cli.ts import ./artifact.html --remote <slug> --wait --json` — proves the managed import path only if it succeeds without an instance service-token env var.
4. If managed import fails with `source=central` + `route.gate-denied` + `malformed or untrusted`, separate the likely causes before blaming the destination token:
   - destination verifier / projection gap on the instance
   - HQ runtime not actually using the intended central DB/token config
   - central DB reachable and migrated but still empty of account / identity / claim / grant rows
   See `references/central-empty-db-and-breakglass-import.md`.
5. If the user's real goal is urgent operator delivery rather than proving the product seam, use host-side direct placement as an explicitly labeled break-glass fallback: copy the finished Haft HTML into the destination vault `content/` tree, rebuild the destination index, verify resulting file size/hash, and report clearly that this bypassed managed import and does not prove Epic 20 success.

If step 2 returns 403 while a destination credential is definitely supplied, the token class is likely wrong. If step 3 returns central-source 403 but direct service-token import works, do not call managed import fixed; wire destination `centralGrantVerifier`/JWKS trust. If central discovery succeeds but the destination still rejects `source=central` as malformed/untrusted, check whether central claims/grants are actually present in the active central DB and whether HQ runtime is fully cut over to that DB.
## Managed Path vs Manual Fallback

**Managed (preferred):** Login → HQ discovers granted remotes automatically → `remotes list` shows them.

**Manual fallback (break-glass):** When HQ grant exchange is unavailable:
```bash
HAFT_DEV_TOKEN="<instance-token>" bun src/cli.ts remote add dev \
  --url https://dev.wheretoaccess.com --token-env HAFT_DEV_TOKEN
```

When using manual fallback:
- State clearly it is fallback, not managed-path proof
- See `references/remotes-list-manual-vs-managed-discovery.md` for the diagnostic pattern where a manual row appears but HQ still reports `central-no-targets`.
- See `references/central-empty-db-and-breakglass-import.md` for the pattern where central discovery works but grants/projections/runtime cutover are still insufficient, and for the host-side direct-placement fallback when delivery matters more than proving the managed seam.
Do not print token values in comments, docs, or shell history.
## CLI Update / Installer Transport Recovery

Treat `haft update` as a release-download path, distinct from CLI authentication, remote discovery, and destination reachability.

### Fast diagnosis

Run:

```bash
haft update --check
```

If a normal update reaches `Downloading Haft <version> for <os>/<arch>...` and curl then exits with code `28`, release manifest lookup and installer discovery succeeded. The archive transfer exceeded the installer's download budget; do **not** misdiagnose this as a PATH, version, central-session, remote, or vault problem.

### Safe immediate recovery

Increase the installer transfer budget while preserving its normal extract-then-atomic-replace behavior:

```bash
HAFT_DOWNLOAD_MAX_TIME=900 haft update
```

For interruption-prone networks, use the immutable versioned release manifest as the source of truth for the matching OS/architecture archive URL and `sha256`. Download into a temporary location using bounded retries and HTTP range resume only when the host advertises byte-range support, verify the checksum before extraction, and replace the user-local binary only after successful extraction. Never overwrite an existing `haft` binary with a partial or unverified archive.

### Product follow-up classification

A fixed global archive timeout with no retry/resume is an installer-resilience product gap when valid releases routinely transfer most bytes before curl times out. File a narrow implementation card covering bounded retry, archive resume, checksum verification, and preservation of atomic installation. Do not alter release hosting merely to work around one client network path.

## Daily Notes with requested initial content

Use the installed CLI's Daily Notes lane when a user asks to create a dated note.

1. Run `haft daily status --json` or `haft daily new --json` against the intended `HOME`/target. If it returns `daily-notes.not-configured`, the vault needs a reviewed data-only `dailyNotes` configuration before a strict Daily Note can be created.
2. `haft daily new` creates only the standard empty HTML starter; it accepts no body/content argument. For a new note that must include user-specified tasks, build a complete Daily Notes HTML or Markdown document using the exact configured date filename and import it into the configured path with `haft import <absolute-file> --target-folder <folder> --wait --json`.
3. Import folder labels may normalize (for example `Daily Notes` to `daily-notes`). Confirm the returned `vaultPath` matches the configured path pattern, then verify with `haft daily show --today --format summary --json`.
4. `haft daily status` parses a conservative Markdown-oriented projection. It may not classify an HTML-rendered checkbox even when `daily show` correctly proves the note content and strict resolver are working.

Never call a generic timestamped import a Daily Note: the configured filename pattern is the resolver contract.

## Tool Loop Warning Avoidance

When terminal commands fail repeatedly, Hermes shows "tool loop warning". Prevent this by:
- Diagnosing before retrying: run diagnostic commands (pwd, ls, etc.) to understand environment mismatch
- Use absolute paths when relative paths fail
- Check if working directory is correct: compare `pwd` with expected workspace
- For command failures due to wrong CLI flags, check help before retrying

## Live Managed-Enrollment Probes

### Send the browser `Origin` header

The central browser OTP routes resolve the destination's managed origin before accepting the incoming browser origin. A raw `curl` without `Origin` can return `auth.central-origin.missing` even when the destination claim is healthy; that is not an enrollment failure. For a real admission probe, include the exact canonical HTTPS origin:

```bash
curl --fail --silent --show-error \
  -X POST https://<dev-hosted-origin>/api/auth/central/otp/request \
  -H 'Origin: https://<dev-hosted-origin>' \
  -H 'Content-Type: application/json' \
  -H 'Cache-Control: no-cache' \
  --data '{"email":"<authorized email>"}'
```

A `200` proves browser-OTP **admission** only. Completing a real login still requires verifying the current OTP through the authorized read-only inbox flow.

### Do not accidentally turn an argv array into a no-op

For sensitive host-side enrollment runs, capture output without printing credentials or assertions. In Bash, this is wrong because it assigns the array expansion instead of executing it:

```bash
output="${cmd[@]}" # no command runs
```

Execute the array and capture its bounded outcome in a private log instead:

```bash
log=$(mktemp); chmod 600 "$log"
if "${cmd[@]}" >"$log" 2>&1; then
  echo 'enrollment=completed'
else
  echo 'enrollment=failed' # extract only a bounded error code if needed
fi
rm -f "$log"
```

Before reporting recovery success, verify postconditions without exposing identifiers: journal completion/cleanup, managed credential and local-host-identity presence, no-cache `/api/auth/status`, and a browser-origin OTP request.

## CLI Flag Corrections

Common incorrect flag patterns seen in debugging:
- **Wrong**: `import file file.html --to dev` → `--to` not valid
- **Correct**: `import file file.html --remote dev`

- **Wrong**: `import file file.html --dry-run` → `--dry-run` not supported
- **Correct**: Omit `--dry-run` entirely

- **Wrong**: `import file file.html --no-publish` → `--no-publish` not valid
- **Correct**: Use without publish flag

When testing import syntax, check help first:
```bash
bun src/cli.ts import file --help

## Epic 20 Sync Verification

When Epic 20 sync is claimed complete but dev instance still rejects connections:

1. **Check dev instance principal store** via SSM:
   ```bash
   aws ssm send-command --instance-ids <dev_instance_id> --document-name "AWS-RunShellScript" \
     --parameters 'commands=["sudo -u haft ls -la /home/haft/.haft/vaults/default/.haft/private/"]'

   # Expected files:
   # - auth-state.json           (auth state)
   # - principals.json           (Epic 20 sync result - MUST exist)
   # - service-tokens.json       (optional, may be empty)
   # - remote-publish-target.json
   ```

   Current dev store reality (2026-07-06):
   - ✅ `auth-state.json` exists
   - ❌ `principals.json` missing → Epic 20 sync not deployed
   - ⚠️ `service-tokens.json` exists but 0 bytes → empty, can seed
   - ✅ `remote-publish-target.json` exists

2. **Error Pattern → Root Cause**:
   - `auth.service-token.malformed` → Token parsing failed
   - → **Check**: `principals.json` missing (Epic 20 not deployed to dev)
   - → **Check**: `service-tokens.json` empty (0 bytes) → manual service tokens not seeded

3. **Epic 20 Gap Analysis Pattern**:
   - ✅ **Central sync complete**: HQ has grant exchange APIs
   - ❓ **Instance sync status**: Check instance's `principals.json`
   - ❌ **Dev gap**: Sync may target prod-like instances only, not dev
   - 🔁 **Retry logic**: Restarting service doesn't help; needs sync deployment

4. **SSM Store Inspection Pattern**:
   ```bash
   # Quick directory check
   aws ssm send-command --instance-ids <dev_instance_id> \
     --document-name "AWS-RunShellScript" \
     --parameters 'commands=["sudo -u haft ls -la /home/haft/.haft/vaults/default/.haft/private/"]'

   # Check principals.json existence and size
   aws ssm send-command --instance-ids <dev_instance_id> \
     --document-name "AWS-RunShellScript" \
     --parameters 'commands=["sudo -u haft test -f /home/haft/.haft/vaults/default/.haft/private/principals.json && sudo -u haft wc -c /home/haft/.haft/vaults/default/.haft/private/principals.json || echo 'missing'"]'

   # View service-tokens.json content
   aws ssm send-command --instance-ids <dev_instance_id> \
     --document-name "AWS-RunShellScript" \
     --parameters 'commands=["sudo -u haft jq . /home/haft/.haft/vaults/default/.haft/private/service-tokens.json 2>/dev/null || echo 'empty/invalid'"]'
   ```

5. **SSM Heredoc Limitation**: When seeding stores via SSM, heredocs with embedded JSON often fail due to shell escaping. Better options:
   - Use Python script on dev to generate JSON: `sudo -u haft python3 << 'EOF' ... EOF'`
   - Copy pre-made JSON via simpler command
   - Use base64 encoding: `echo '<base64>' | base64 -d > /tmp/file.json`
   - Or accept wait for sync rollout

6. **Decision Tree for Pragmatic "Do Whatever Works"**:
   ```
   Dev instance rejects import → Check principals.json existence
     ├── ✅ Exists, nonzero → Token mismatch or other auth issue
     ├── ❌ Missing → Epic 20 sync not rolled out to this instance
     │    ├── Can wait → Log sync gap, create follow-up card
     │    └── Need usable connection now → Switch to prod instance (if sync complete there)
     └── Empty/0 bytes → Manual seed required or instance misconfigured
   ```

7. **Epic 20 vs dev instance mismatch**: Sync complete ≠ deployed to all instances. Common pattern: Completed centrally but not deployed to dev/testing instances.

8. **Status Verification**: Use central session token as credential for local registration, but verify dev can accept:
   ```bash
   # Will register locally (bookkeeping), but 403 on actual dev calls
   HAFT_DEV_TOKEN="hv_central-session_..." bun src/cli.ts remote add dev --token-env HAFT_DEV_TOKEN --url https://dev.wheretoaccess.com
   HAFT_DEV_TOKEN="hv_central-session_..." bun src/cli.ts remote status dev
   # Returns: "Remote dev: HTTP 403 (failed)" → principal store mismatch
   ```

## Pitfalls

1. **`--token-stdin` blocked in Hermes** — always `--token-env`.
2. **Central token ≠ instance token** — registration succeeds (local bookkeeping) but remote calls fail 403.
3. **Session expiry is ~30 min** — don't start long work between login and remote operations.
4. **Profile HOME vs host HOME** — different wallets, different auth state.
5. **Epic 20 sync gap** — the normal managed path `remotes list` depends on central sync of server/vault claims to HQ's `central_vault_access_grants`. This sync often isn't wired yet, leaving `remotes list` returning empty `targets` after successful login.
   - **Diagnostic**: `central-no-targets` even after fresh claim and valid central session.
   - **Resolution**: Manual fallback `remote add` with an instance-level token (if available), or SSM into the dev host to directly inspect/reset the local auth state.
6. **Resetting stale claim on dev hosts** — If an instance's claim is stale (pre-Epic 20) and gating everything behind auth with 403 while HQ grants are missing, reset the instance to unclaimed via SSM:
   ```bash
   aws ssm send-command --instance-ids <dev_instance_id> --document-name "AWS-RunShellScript" \
     --parameters 'commands=[
       "systemctl stop haft-dev.service",\
       "cp /home/haft/.haft/vaults/default/.haft/private/auth-state.json /home/haft/.haft/vaults/default/.haft/private/auth-state.json.bak.$(date +%s)",\
       "rm /home/haft/.haft/vaults/default/.haft/private/auth-state.json",\
       "systemctl start haft-dev.service",\
       "cd /srv/haft-dev/app && sudo -u haft bun scripts/haft-auth-bootstrap-token.ts /home/haft/.haft/vaults/default"
     ]'
   ```
   Then reclaim via browser or the claim endpoint with the fresh bootstrap token. This fixes the deadlock but still leaves Epic 20 sync unwired — you'll still be in manual-fallback lane.
7. **HQ deploy can rotate delegated-grant signing keys** — A freshly deployed HQ may issue grants that an otherwise-ready destination rejects with `route.gate-denied`; inspect the destination's `.haft/private/central-delegated-grants/audit.json`. If the bounded code is `auth.central-grant.bad-signature`, refresh the destination projection/JWKS and restart the destination service before retrying. Run the refresh on the destination host using the vault's local slug (often `default`, not the workstation remote alias such as `gly`):
   ```bash
   sudo -u haft env HOME=/home/haft /path/to/haft remote refresh default \
     --vault-root /home/haft/.haft/vaults/default \
     --jwks-path /home/haft/.haft/central-jwks.json \
     --force --json
   systemctl restart <haft-destination-service>
   ```
   Verify recovery with `haft remote publish-target show <remote-alias> --json` before retrying a mutation.
