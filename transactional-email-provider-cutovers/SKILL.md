---
name: transactional-email-provider-cutovers
description: Safely cut over Haft/HQ-style transactional email providers in production with runtime verification, bounded smoke tests, and rollback.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Transactional Email Provider Cutovers

Use when switching a production app between transactional email providers (for example SES → Resend), especially when auth/OTP delivery is on the critical path.

## Why this exists
Provider cutovers fail in misleading ways when config, deployed code, DNS verification, and API-key scope drift apart. This skill forces a verify-first, fail-closed workflow so the agent does not leave production pointed at a provider that cannot actually send mail.

## Trigger conditions
Use this skill when:
- a merged PR adds a new email provider path, but production still needs config/DNS rollout;
- OTP, invite, or auth mail must keep working during the transition;
- the provider requires sender-domain verification (DKIM/SPF/return-path);
- the service environment and deployed runtime may be out of sync.

## Core procedure

1. **Verify the live runtime before touching config.**
   - Confirm the production host is actually running the merged commit that added the new provider path.
   - Inspect the deployed checkout for provider-specific code markers if needed.
   - Do not trust the merge state alone; a host can lag the repo by many commits.

2. **Inspect the current production env in a redacted way.**
   - Confirm the exact env file path used by the service.
   - Check presence of the current provider vars, the new provider vars, and the sender address.
   - Record the allowed browser origins before running request-level smoke tests.

3. **Check provider prerequisites before enabling the new path.**
   - Confirm the sender address/domain the service will use.
   - Confirm the new provider key exists and is suitable for the needed operations.
   - If the key is send-only, assume it may not be able to list domains or return verification records.
   - Check public DNS for existing SPF/DKIM/DMARC/return-path state.

4. **Back up the production env before any change.**
   - Copy the env file to a timestamped backup on the host.
   - Apply the new provider vars only after the backup exists.

5. **Restart and verify service health separately from mail delivery.**
   - Restart the service.
   - Expect a possible short restart race where an immediate loopback health probe fails once before the service is actually up.
   - Re-check health after a short retry window before concluding the restart failed.

6. **Run a bounded live smoke test against the real app route.**
   - Use an actually allowed `Origin`, not a guessed one.
   - For Haft HQ, inspect `HAFT_HQ_ALLOWED_ORIGINS` first and use one of those origins.
   - Capture HTTP status, response code, request ID, and delivery status.

7. **Inspect provider-mode evidence from logs.**
   - Verify the app log shows the expected `deliveryMode` for the new provider.
   - If the API returns success but logs still show the old provider, treat that as proof the runtime or selection logic is still on the old path.

8. **If delivery fails, get the provider’s exact rejection reason out-of-band if possible.**
   - The app may intentionally log only bounded status/code data.
   - Reproduce a direct provider API probe with the same key + from-address to obtain the human-readable rejection message.
   - Common durable causes: unverified domain, insufficient key scope, sender identity mismatch.

9. **Separate provider acceptance from final delivery.**
   - A successful send API response with a provider message ID proves provider acceptance/queueing, not inbox arrival.
   - Record the exact provider message ID only if the runtime or an authorized provider read surface exposes it. If logs intentionally retain only a redacted prefix, state that limitation plainly; do not reconstruct or claim the full ID.
   - Probe provider read access non-destructively before promising trace evidence. Send-only Resend keys can submit mail yet return `401 restricted_api_key` for `/emails` and `/domains`; such a key cannot establish delivered, bounced, suppressed, or domain-verification state.
   - For an inbox-delivery incident, use the provider dashboard or a narrowly scoped read-capable operator credential to retrieve the message event sequence. Do not replace a deployed send-only key without explicit approval.

10. **Rollback immediately if the new provider cannot send.**
   - Restore the previous env backup.
   - Restart the service.
   - Re-run the bounded smoke test to confirm the prior path is working again.
   - Do not leave production pointed at a provider path that returns auth-mail failures.

## Haft HQ-specific notes
- The live sender address may already be correct even when the provider cutover is not. Verify, do not assume.
- `deliveryMode` in HQ OTP logs is strong evidence because it comes from the active sender implementation.
- For request-level smoke tests, `Origin` must be one of the configured allowed origins. A wrong origin produces a misleading `origin-not-allowed` failure unrelated to mail delivery.
- A send-only Resend key can be enough for live send attempts but not enough to query domain-verification state or fetch DNS setup records.
- If Resend returns HTTP 403, expect domain-verification or scope issues; verify by direct API probe if safe.

## Pitfalls
- **Merged PR != deployed runtime.** Always compare host SHA against the repo SHA before reasoning about provider behavior.
- **Config-only cutover can mislead.** Setting provider env vars on an old runtime does not prove the new provider path is live.
- **Immediate post-restart curl can be a false negative.** Retry briefly before declaring the restart broken.
- **Wrong browser origin masks email progress.** Fix CORS/origin first, then evaluate provider behavior.
- **Do not leave production degraded.** If the provider rejects live sends, revert promptly.

## Verification checklist
- Production host SHA matches the expected merged commit.
- Service health is green after restart.
- Env presence matches the intended provider state.
- Live request uses a configured allowed origin.
- Response status/code recorded.
- Logs confirm the expected `deliveryMode`.
- If failure: provider status/code captured, direct provider error reason captured, rollback completed.
- Post-rollback or post-cutover smoke verified.

## What to hand back to the user
Report these separately:
1. **What changed live** (host deploy, env changes, restarts).
2. **What was verified** (SHA, health, allowed origin, request IDs, log evidence).
3. **What blocked full cutover** (for example, unverified domain).
4. **Whether production was left on the new provider or reverted safely**.
5. **Exact remaining operator action** (for example, add Resend verification DNS records for the sender domain).
