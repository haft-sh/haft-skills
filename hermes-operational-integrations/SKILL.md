---
name: hermes-operational-integrations
description: "Use when operating Hermes-adjacent infrastructure integrations: Kanban orchestration/worker flows, native MCP servers/tools, webhook subscriptions, shared gateway access control, s6 container supervision, and Codex runtime configuration."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, devops, kanban, mcp, webhooks, gateway, s6, codex]
    related_skills: [hermes-agent]
---

# Hermes Operational Integrations

## Overview

This umbrella covers Hermes operational integrations that are not ordinary coding tasks: Kanban-based multi-agent work routing, MCP tool registration, event-driven webhook subscriptions, shared messaging gateway access controls, s6 container supervision, and Codex runtime wiring. Load the main `hermes-agent` skill for general Hermes usage; use this skill when the task concerns the operational plumbing around Hermes deployments or integrations.

## When to Use

- Decomposing work through a Hermes Kanban board or acting as a Kanban worker.
- Connecting native MCP servers and registering their tools.
- Creating or debugging webhook subscriptions that trigger agent runs.
- Configuring shared messaging profiles, group-only access, or collaborator gateway controls.
- Modifying/debugging the Hermes Docker s6-overlay supervision tree.
- Troubleshooting Codex runtime workspace, profile, `CODEX_HOME`, sandbox, or app-server behavior.
- Debugging Hermes runtime provider/fallback credential routing, especially cron/gateway jobs that fail differently than interactive sessions.
- Checking whether a gateway `/background` task is still running, completed, or was interrupted.
- Answering "which auth key/account is Hermes using right now?" without exposing secrets.
- Self-hosting Honcho as a local Hermes memory provider and wiring profile-local Honcho config.

## Router

| Need | Route |
| --- | --- |
| Split a goal into cards and workers | Kanban orchestrator |
| Execute/claim/report a specific board card | Kanban worker |
| Add external tools via stdio/HTTP | Native MCP |
| Event-driven runs from outside systems | Webhook subscriptions |
| Shared Telegram/Discord/etc. gateway access | Shared gateway access control |
| Docker service supervision and startup | s6 container supervision |
| Codex app-server/runtime config | Codex runtime configuration |
| Cron/gateway fallback auth behaves differently than interactive chat | Runtime provider credential resolution |
| Check whether a `/background` task is still alive | Gateway background-task liveness |
| Need to identify which account/key Hermes would use right now | Active credential identification |
| Move Hermes kanban/profile state from one host to another | Hermes host migration |
| Run Honcho locally for Hermes memory | Honcho self-hosted memory provider |
| Give Hermes an Inkbox mailbox/phone identity and verify email flow | Inkbox identity + gateway wiring |

## Kanban Orchestration

Use Kanban orchestration for multi-worker decomposition, not for simple tasks a single agent can finish directly. Sketch dependencies first, create bite-sized cards, assign/route to workers, and keep the orchestrator from doing worker implementation. The orchestrator owns decomposition, dependency management, and final integration.

## Kanban Worker Pattern

Workers should claim only cards they can identify by returned IDs or exact board state. Respect tenant/workspace isolation. Good worker summaries include what changed, verification evidence, blockers, and machine-readable metadata useful to the orchestrator.

## Native MCP

For MCP integrations, identify transport first: stdio command/args or HTTP URL. Register tools only after verifying the server starts and exposes expected capabilities. Keep MCP config minimal and avoid leaking credentials in command strings or logs.

## Headless OAuth MCP Authorization

For an OAuth-protected HTTP MCP server on a headless Hermes host, register and authorize it as two deliberate stages:

1. Add the server with its explicit OAuth mode and run the command in a PTY so the interactive browser/callback prompt remains alive.
2. Give the account owner the printed authorization URL. If the provider redirects to `127.0.0.1` on the headless host, their browser may not load the callback page; they should copy the full redirect URL (or its `code` and `state`) from the address bar into the waiting Hermes prompt.
3. Treat that callback as a short-lived credential: do not echo it, write it to tickets, or leave it in shell history.
4. Smoke-test tool discovery after authorization. If the current agent session was already running, open a new session after the server connects; tool schemas are fixed for the life of a session.
5. MCP OAuth authorizes the operator integration only. It does not replace application runtime secrets, which must remain in their approved service secret store.

## Webhook Subscriptions

Use webhook subscriptions when external events should trigger autonomous agent runs. Configure endpoint/auth, create the subscription, verify with a test event, and document delivery semantics. For recurring polling or time-based triggers, use cron jobs instead.

## Gateway Background-Task Liveness

When a user asks whether a `/background` task is still running, treat the `bg_*` id as the primary key and inspect task-tagged profile logs plus the actual gateway process. Background agent work is gateway-owned and may not appear in terminal process registries. Classify the task as running, completed, interrupted, or uncertain from timestamps, model/tool activity, gateway PID continuity, and worktree state; do not launch a duplicate writer into the same worktree on ambiguous evidence. See `references/gateway-background-task-liveness.md`.

## Shared Gateway Access Control

For collaborator access, prefer group-scoped access with owner DM retained and unauthorized direct DMs blocked. Discover the actual platform/chat IDs rather than relying on names. Do not reconstruct secrets from redacted output; read the real config file only when needed and permitted.

## s6 Container Supervision

For Hermes Docker supervision, understand whether the image uses s6 as PID 1 and whether Hermes itself is the main program or supervised service. Modify service directories carefully, preserve executable bits, and verify startup logs after changes.

## Codex Runtime Configuration

For Codex runtime issues, distinguish app-server working directory, `terminal.cwd`, `CODEX_HOME`, profile config, and sandbox permissions. Workspace access problems often require checking user namespaces/bubblewrap and the runtime's effective root, not just passing a different CLI `-C` argument.

## Active Credential Identification

When the user asks which auth key/account Hermes is using, inspect the live profile's config and credential store before answering. Do not infer from a random environment variable dump: Hermes may be using profile-scoped OAuth credentials from `auth.json`, not an env key.

Recommended sequence:
1. Read the active profile identity (`HERMES_HOME` if present, otherwise the target profile path) and inspect that profile's `config.yaml` for `model.default`, `model.provider`, `fallback_providers`, and any `credential_pool_strategies` override.
2. Inspect the same profile's `auth.json` credential pool for the resolved provider. For `openai-codex`, the decisive data is usually under `credential_pool.openai-codex`, not `.env`.
3. Report only safe identifiers: provider, account label, credential id, priority/order, base URL, status, and a short fingerprint if needed. Never print raw tokens or full secrets.
4. If you need to know which entry Hermes would pick right now, use the Hermes venv/runtime to load the pool and call a non-destructive selector such as `peek()` rather than guessing from JSON order alone.
5. Distinguish model auth from tool auth. A session can use Codex OAuth for model calls while tools independently use `INKBOX_API_KEY`, `CLOUDFLARE_API_TOKEN`, etc.

Pitfalls:
- The wrapper `~/.local/bin/hermes` may exec a profile-local venv binary; if a direct `python3` import fails, rerun the inspection with the Hermes venv interpreter rather than concluding the pool is unreadable.
- `least_used` / round-robin credential-pool strategies can reorder or rotate entries; "first entry in auth.json" is not proof of the active credential.
- `current()` can be empty if nothing has selected a credential in-process yet. Prefer `peek()` for "what would Hermes use now?" and make the hypothetical nature explicit.

See `references/active-credential-identification.md` for the exact inspection pattern and safe reporting shape.

## Runtime Provider Credential Resolution

When cron/gateway jobs fail with provider auth errors that interactive chat does not reproduce, distinguish process environment from Hermes `.env`/credential-pool state. A key can be configured and visible to `hermes auth list` while a runtime resolver still sends an empty key if it only checks `os.getenv(...)`. For OpenRouter-style `401 Missing Authentication header`, first verify whether runtime resolution is attaching a non-empty `api_key` before assuming the key is invalid. See `references/runtime-provider-credential-resolution.md` for the diagnostic and fix pattern. For the adjacent "which account/key is active right now?" question, use `references/active-credential-identification.md`.

## Hermes Host Migration

When moving Hermes operational state to a new machine, stage a curated migration payload instead of cloning the entire `~/.hermes/` tree blindly. Preserve the kanban database/boards plus the target profile's functional config/auth/memory/skills/cron state first; exclude bulky runtime/session databases, caches, logs, checkpoints, LSP directories, archived skill backups, and transient lock/PID files unless the user explicitly asks for full runtime continuity. If direct `scp` is unavailable but command-style remote execution exists (for example AWS SSM), chunked base64 transfer into a staging directory on the target host is a valid fallback. Keep the payload outside the live `~/.hermes/` tree until the operator manually reconciles it, and after migration pick one canonical host for live kanban writes/dispatching. See `references/hermes-kanban-profile-host-migration.md`.

## Honcho Self-Hosted Memory Provider

When moving Hermes from Honcho Cloud/API-key mode to a local Honcho instance, verify three layers separately: the Honcho service stack (API, Postgres/pgvector, Redis, deriver), the Hermes runtime dependency (`honcho-ai` installed in the active Hermes venv), and the profile-local `$HERMES_HOME/honcho.json` host mapping. `memory.provider: honcho` only selects the provider; it does not prove the local server, SDK, host key, or LLM-backed derivation is ready. Use `hermes honcho status` to discover the actual resolved host key (for profiles this may be normalized, e.g. `hermes_orchestrator`) before writing host blocks. See `references/honcho-self-hosted-memory-setup.md`.

When retiring Bedrock/LiteLLM in favor of ChatGPT-account Codex OAuth, treat text generation and embeddings as separate migration dependencies. Honcho cannot consume the Codex Responses backend or its OAuth token as a drop-in Chat Completions plus embeddings provider. Use a dedicated-refresh-token protocol adapter for text, choose a separate embedding path, rebuild all stored vectors, and only then remove the old services. See `references/honcho-codex-oauth-provider-migration.md`.

## Inkbox Identity + Gateway Wiring

Use this route when Hermes needs its own mailbox/phone identity for CI alerts, OTP capture, or inbound human email.

Recommended sequence:
1. Install and enable the plugin first: `hermes plugins install inkbox-ai/hermes-agent-plugin --enable`.
2. Run `hermes inkbox setup` from the target Hermes profile and complete the prompts interactively. The wizard can install the Inkbox SDK into the Hermes Python environment, validate the API key, bind the existing identity, and mint the required signing key.
3. Run `hermes inkbox doctor` and verify `ok: true`, correct identity handle, and the expected mailbox.
4. Smoke-test the mailbox with a real send/receive loop, not just setup output. Send one outbound message, then verify inbound mail by listing or reading messages through the Inkbox CLI/API.
5. If you also install the standalone Inkbox CLI on Linux and global npm install would require root, prefer a user-local prefix install (for example `npm install -g --prefix ~/.local @inkbox/cli`) instead of escalating privileges.
6. If Hermes gateway is already running, restart it from a separate shell after enabling the plugin. Do not attempt `hermes gateway restart` from inside the running gateway process; that path self-terminates before completing.
7. When debugging live Inkbox email behavior, verify which codebase actually owns the adapter before patching. The running gateway can load a profile-scoped plugin from `~/.hermes/profiles/<name>/plugins/inkbox/` even when the upstream dev checkout under `~/Sites/hermes/hermes-agent-dev` does not contain the offending code. Search the active profile plugin tree first, patch the live adapter there when appropriate, and then verify the gateway PID/start time changed after restart so you know the running process picked up the fix.

Persist identity details in the profile-local Hermes files, not ad hoc notes: put `INKBOX_API_KEY` in the active profile `.env`, ensure `.env` is gitignored, and add a short identity stanza to the profile persona/instructions so future sessions know the handle, mailbox, and base URL. See `references/inkbox-hermes-identity-setup.md` and `references/inkbox-automated-email-reply-guard.md`.

## Hermes Config Inspection Before Claiming a Provider Reset

When a user reports that Hermes "changed my default provider/model" or "started using a paid API key," inspect the live profile config before concluding that the primary model was overwritten.

Use this read order:
1. Check `model.default`, `model.provider`, and `model.base_url` first. This is the primary chat model.
2. Then check `fallback_providers`. A paid fallback here can explain surprise spend even when the primary model is still correct.
3. Then check `auxiliary.*.provider` / `auxiliary.*.base_url`. Values like `provider: auto` in auxiliary sections are not the same as the main chat provider.
4. Inspect the profile-scoped `auth.json` credential pool. If the profile still has OpenRouter credentials, fallback traffic can still bill even if the user expected Codex to be the only paid path.
5. Compare timestamps and any available snapshots, but do not claim a specific process rewrote the file unless there is direct evidence.

Default recommendation when the user wants "never spend on fallback": remove `fallback_providers` from the target profile config and remove the corresponding paid-provider credentials from that same profile's `auth.json`/auth store so runtime fallback cannot silently route there.

See `references/hermes-config-provider-reset-triage.md` for the exact triage and hardening pattern.

## Common Pitfalls

1. **Using Kanban for trivial tasks.** The board pays off only when decomposition/parallelism/ownership matter.
2. **Claiming cards by guessed IDs.** Capture returned IDs or query board state.
3. **Registering MCP without a smoke test.** Verify server startup and tool discovery.
4. **Weak gateway ACLs.** Names are not stable identifiers; use platform IDs.
5. **Confusing Codex cwd layers.** App-server cwd and agent terminal cwd are different concerns.
6. **Misreading provider 401s.** `401 Missing Authentication header` means the request likely had no Authorization header; first inspect runtime credential resolution/key length before assuming the API key itself is invalid.
7. **Treating Inkbox setup as complete before a real mail loop.** The wizard and doctor can pass while forwarding rules or human reply flow are still unverified.
8. **Restarting the gateway from inside itself.** Run Inkbox plugin restarts from a separate shell/process.
9. **Assuming pgvector reconciliation rebuilds every Honcho vector.** In pgvector-only mode, verify document embeddings separately; pending message rows and document rows can follow different code paths.
10. **Misdiagnosing QMD's native backend from an inline Node probe.** `node --input-type=module` propagates into forked compatibility checks; use a real `.mjs` smoke-test file before patching `node-llama-cpp`.

## Verification Checklist

- [ ] Operational route selected from the table.
- [ ] Current config/state inspected before changes.
- [ ] Secrets handled without logging or reconstruction from redacted text.
- [ ] Integration smoke test or service log verification completed.
- [ ] User-facing summary includes exact IDs/paths/statuses where relevant.
