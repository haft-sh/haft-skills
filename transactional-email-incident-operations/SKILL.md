---
name: transactional-email-incident-operations
description: Use when triaging hosted OTP or invite email incidents.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [email, otp, invitations, incident-response, hosted-auth]
---

# Transactional Email Incident Operations

## Purpose

Use for evidence-backed investigation and recovery of hosted authentication-email or collaborator-invitation incidents: missing OTPs, invite delivery reports, provider acceptance ambiguity, invitation-acceptance failures, and operator handoffs.

Keep three facts separate:

1. **Application acceptance** — the hosted app/HQ accepted the request.
2. **Provider acceptance** — SES/Resend accepted the message for delivery.
3. **Mailbox delivery and authentication completion** — the intended mailbox received the message and the recipient completed the right identity/invitation flow.

A `200` response or `delivery: queued` proves only an earlier layer. Never report mailbox delivery or successful login without direct evidence.

## Safety and privacy boundary

- Treat OTPs, browser cookies, bearer tokens, invitation acceptance tokens/hashes, raw provider IDs, and database DSNs/auth tokens as secrets. Never put them in chat, tickets, logs, or handoffs.
- Use redacted, semantic DB/journal queries. Output status, timestamps, provider mode, bounded error codes, and hashes/prefixes only where the product already authorizes them.
- Do not use a real collaborator address for diagnostics. A controlled inbox owned by the operator is appropriate only with explicit authorization for a real OTP send.
- Operational inboxes may be read-only by policy. Send a reply only when the current user explicitly authorizes outbound email; then reply in the source thread and verify the send receipt.
- Do not mutate central invitations/grants directly in storage when a supported API or UI action exists.

## Evidence-first workflow

### 1. Read the report, but do not rely on a message subject alone

Retrieve the named sender/contact and inspect the message body and thread. Some inbox ingestion paths can retain a subject while losing the substantive body. If so, label the report details as unavailable and correlate only bounded facts: sender, subject, timestamp, thread, and live request/audit evidence.

### 2. Prove runtime identity and basic health

Before changing anything:

- resolve the intended public hostname to its current host;
- check public auth status with `Cache-Control: no-cache`;
- discover the target instance fresh rather than assuming historic instance IDs;
- inspect the service state through the approved host-control plane (for example, SSM), including active user and service state.

A claimed/healthy instance is not evidence that browser-origin OTP or invitation acceptance works.

### 3. Correlate the invitation request

For a reported collaborator invite, correlate the destination request with HQ evidence using timestamp/request ID. Retrieve a privacy-safe audit summary containing:

- invitation status and expiry;
- resend count / last-sent time;
- provider mode and `queued` versus `failed` status;
- provider code/status/retryability on failure;
- whether the invited identity is verified and whether its grant is bound.

Do not output the recipient address, acceptance material, or full provider message ID.

Interpretation:

- **pending + queued + no verified identity/grant binding**: invite creation succeeded; the user still needs the central acceptance flow.
- **failed**: classify by provider code/status before retrying. Preserve the one existing invitation/grant; do not create duplicates.
- **accepted + grant not projected/bound**: investigate projection refresh and destination authorization separately from email delivery.

### 4. Use a controlled browser-shaped OTP canary when authorized

A real canary must use the same hosted browser transport as the user:

1. POST the hosted OTP request route with the exact canonical HTTPS `Origin` header.
2. Confirm an actual (non-rate-limit-placeholder) challenge and `delivery: queued` response.
3. Poll only the controlled inbox for a new matching OTP message after the test start time.
4. Extract the code only in process memory; never print it.
5. POST verification through the same hosted route and origin.
6. Report only HTTP status, safe error code, and whether a session cookie was issued.

A canary recipient that is not a collaborator may correctly reach HQ verification but receive local `auth.identity.not-found`. Classify that as proof of request/delivery/HQ verification, **not** as a GLY/destination-login failure.

Avoid repeated requests: hosted relays may share a global rate-limit bucket. One clean request is better evidence than retries.

### 5. Give the right retry handoff

For a pending collaborator invite, the correct order is normally:

1. Open the newest invitation email at the invited address.
2. Follow the invitation acceptance link.
3. Complete central sign-in there with the same address and only the newest OTP.
4. Accept the invitation.
5. Return to the hosted destination and request a new code there.

Do not tell an unaccepted collaborator to begin by logging directly into the destination: local `auth.identity.not-found` can be correct before invitation acceptance and projection binding.

The handoff should include the exact next action, expiration/retry limit if known, and a request for the exact on-screen error plus time if it fails. Do not include secret links, codes, or tokens.

### 6. Verify the destination-local completion boundary separately

HQ acceptance, provider acceptance, inbox delivery, and HQ OTP verification can all succeed while the hosted destination fails creating or persisting its local browser session. Treat that as a separate destination-local boundary, not as an email-delivery failure.

1. For one authorized controlled canary, correlate safe HQ request/verification records and separately inspect the destination response.
2. If HQ logs verification/session issuance as successful but the destination returns an opaque `500`, classify the defect as local session/projection/persistence work. Do not relabel the code invalid or claim provider delivery failed.
3. Contain the user-facing failure with a stable retryable error and redacted structured event at the destination boundary; add a regression test that first reproduces the opaque failure.
4. This containment is not proof the state-store root cause is fixed. Preserve a separate investigation path for the destination runtime.
5. Never reuse a consumed code. Every full-flow test needs one fresh challenge and its matching fresh controlled-inbox message; keep codes, cookies, and session handles only in process memory.

### 7. Handle observability gaps as product work

If an application audit retains only `queued`/`failed` and provider mode while discarding a safe bounded provider correlation identifier, it cannot distinguish provider acceptance from later delivery. Capture this as a scoped observability issue, not as a claim that email was delivered.

A good remediation preserves privacy while adding:

- structured success/failure event;
- provider mode, bounded error code/status, retryability;
- redacted provider-message prefix on acceptance;
- explicit idempotent resend semantics; and
- documented boundary between provider acceptance and mailbox delivery.

Before filing, search the live board for an existing nonterminal card and add fresh evidence there instead of creating a duplicate.

## Verification checklist

- [ ] Source report/body availability recorded truthfully.
- [ ] Target hostname and live service confirmed.
- [ ] Invitation/audit state summarized without PII or secret material.
- [ ] Browser-shaped canary used only when authorized.
- [ ] Controlled inbox receipt and HQ verification independently confirmed.
- [ ] Destination-local response/session issuance checked separately; no opaque 500 is mistaken for an email or OTP-code failure.
- [ ] Local identity/grant outcome classified separately from OTP delivery.
- [ ] A sender handoff was sent only with explicit authorization, and send receipt verified.
- [ ] Existing observability work was discovered and updated rather than duplicated.
