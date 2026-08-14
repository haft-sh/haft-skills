---
name: haft-codebase-audit
description: Audit Haft code for boundary, safety, and design risks.
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Haft, TypeScript, Architecture, Security, Audit]
    related_skills: [software-development-lifecycle, systematic-debugging]
---

# Haft Codebase Audit

Audit the Haft TypeScript/Bun repository for concrete risks in architecture, local-first safety boundaries, domain contracts, and changeability. This skill produces evidence-backed findings and prioritized remediation suggestions; it does not make broad rewrites, change product scope, or claim a runtime vulnerability without reproducing or tracing a reachable path. It uses repository evidence and existing Bun checks rather than new audit dependencies.

## When to Use

- “Audit the Haft codebase.”
- “Review Haft architecture or code quality.”
- “Find security or local-first boundary risks in Haft.”
- “Assess whether a Haft change preserves the vault and publishing contracts.”
- “Identify refactoring opportunities without changing behavior.”

## Prerequisites

- Work in a dedicated Haft worktree, never directly in `<haft-repo-root>`.
- Start from the repository's current `AGENTS.md`; it defines active plans, scope, verification, and security gates.
- Use the repository's Bun version and lockfile. Invoke dependency installation only through the `terminal` tool with `bun install` when checks cannot run.
- No credentials are required for a static audit. Do not use production credentials, read vault content unnecessarily, or send email.

## How to Run

1. Use `read_file` on `AGENTS.md`, `docs/security/threat-model.md`, and the relevant product/API contract before judging a boundary.
2. Use `search_files` to map the feature and its tests, then use `read_file` to inspect the narrowest relevant files.
3. Invoke verification through the `terminal` tool from the worktree: `git diff --check`, focused `bun test`, then `bun run typecheck` and `bun run build` when the audit includes a patch or needs baseline confirmation.
4. Report only actionable findings with file/line evidence, affected contract, severity, rationale, and a smallest safe next step.

## Quick Reference

- `read_file`: inspect `AGENTS.md`, contracts, and implementation.
- `search_files`: map domain terms, routes, trust-boundary helpers, and tests.
- `terminal`: run `git diff --check`, `bun test`, `bun run typecheck`, `bun run build`.
- `patch`: make a narrow, approved repair after the audit is accepted.
- `apps/server/src/vault/paths.ts`: path containment and safe resolution authority.
- `apps/server/src/routes/agent.ts`: agent-facing create/get/publish routes.
- `apps/server/src/routes/serve.ts`: vault preview/static serving routes.
- `apps/server/src/routes/reader.ts`: reader API routes.
- `apps/server/src/routes/search.ts`: search API route.
- `.haft/`: private vault state; never serve raw.
- `docs/security/threat-model.md`: required security baseline.

## Procedure

1. **Establish scope and baseline.** Read `AGENTS.md`, `package.json`, the newest governing plan named by `AGENTS.md`, and the relevant contract. State whether the audit covers a route, CLI command, vault operation, reader flow, publishing flow, or the full repository. Complete this step only when the promised product behavior and out-of-scope behaviors are explicit.

2. **Map the execution and ownership path.** Use `search_files` for route paths, CLI subcommands, Zod schemas, domain terms, and tests. Trace input from its trust boundary through validation, policy, filesystem or integration adapter, response, and audit/export state. Complete this step only when each important transition has an owning module and relevant test location.

3. **Audit trust boundaries first.** For user, file, network, remote-import, or agent input, verify validation occurs before use; follow path resolution through `apps/server/src/vault/paths.ts`; and check that `.haft/`, raw private content, secrets, tokens, and audit state cannot enter public/static output. Treat symlinks, traversal, public admin routes, server-side URL fetching, unrestricted filesystem access, and arbitrary uploads as high-risk scope changes. Complete this step only when the reachable boundary and the enforcement point are named.

4. **Audit architecture without ceremony.** Check that route handlers, CLI parsing, framework context, transport payloads, persistence/file shapes, and external clients remain adapters around focused policy. Flag business branching in handlers, use cases that construct volatile infrastructure directly, foreign transport language leaking into core policy, and framework-dependent tests for business rules. Do not demand layers that do not reduce coupling; require the lightest boundary that is enforceable by code or tests.

5. **Audit Haft domain language and contracts.** Confirm that local-first ownership, vault roots, manifests, import jobs, artifact visibility, publish audit, remote destinations, and agent tools use stable meanings at their boundaries. Flag overloaded terms, primitive flags that carry rules, duplicate schema/validation knowledge, and external payloads that define internal semantics. Prefer a clear domain concept or boundary translation over shared ambiguous objects.

6. **Audit changeability and implementation quality.** Identify concrete friction: one change requiring unrelated edits, duplicated validation/mapping, shallow pass-through modules, temporal setup contracts, mixed phases, long routines, hidden side effects, unclear errors, or untestable construction. For unclear or weakly tested behavior, require characterization or a narrow observation seam before proposing semantic change. Prefer a small behavior-preserving refactor; stop before speculative abstractions or rewrites.

7. **Audit the safety net.** Locate focused `bun:test` coverage and examine normal, boundary, invalid-input, and contract cases. Verify that risky policy can be tested without a real network, framework runtime, or production vault where practical, while retaining integration tests for true seams. Run the smallest relevant test command through `terminal`; expand to `bun run test`, `bun run typecheck`, and `bun run build` only when audit scope or a proposed patch warrants it. Record exact commands and real results.

8. **Write the findings in priority order.** Each finding must include: severity (`critical`, `high`, `medium`, or `low`); evidence as `path:line`; the affected Haft contract; the reachable failure or maintenance cost; why the current test suite does or does not protect it; and the smallest safe remediation plus a verification command. Label unverified hypotheses as hypotheses. Complete only when every finding is independently actionable and no finding is based on style preference alone.

## Codex Worker Variant

When this audit must be given to a ChatGPT/Codex worker, create a matching native Codex skill under `~/.codex/skills/haft-codebase-audit/`. Use only `name` and a trigger-rich `description` in its frontmatter, write imperative shell-worker instructions instead of Hermes tool framing, include `agents/openai.yaml`, and validate it with the installed Codex skill creator's `quick_validate.py`. Preserve the same evidence standard: severity, `path:line`, affected contract, impact, test protection, smallest remediation, and exact verification.

## Namespace and product-rename migrations

When auditing a rename that touches persisted HTML, exports, themes, handles, or credentials, do not treat every old prefix as one replace-all problem. First classify each occurrence by contract durability and security impact. Persisted document syntax can usually use dual-read/canonical-write; durable handles require aliases; credential prefixes require a separate security-protocol migration; historical evidence should normally remain historical.

For document syntax, require one shared compatibility authority, canonical-only writers, legacy-only reader support, explicit full-document canonicalization, and rejection of a document carrying both aliases for the same semantic field. Never let duplicated meta tags silently resolve by insertion order, especially for visibility, script policy, or other policy-bearing values. Trace validation, normalizers, writers, indexers, editors, patch selectors, privacy/presentation stripping, publishing, and active contracts before calling the migration safe.

See `references/namespace-compatibility-migrations.md` for the migration matrix and compatibility test checklist.

## Pitfalls

- Do not treat a generic TypeScript smell as a Haft defect without connecting it to a local-first, security, domain, testability, or changeability consequence.
- Do not infer public exposure or a vulnerability from a filename; trace the active route, configuration, and enforcement code.
- Do not recommend database-backed storage, public deployment, public admin routes, arbitrary upload handling, server-side URL fetching, or unrestricted filesystem tools unless the task explicitly changes Haft scope.
- Do not confuse a refactor with a behavior change. Separate structural remediation, policy changes, and test changes so review remains trustworthy.
- Do not demand full DDD or Clean Architecture patterns for simple CRUD or glue code. Prefer the smallest boundary that protects an important invariant or volatile dependency.
- Do not run broad builds repeatedly or treat passing CI as evidence that a contract was inspected. Use focused evidence first.
- Do not expose vault documents, `.haft/` state, credentials, cookies, tokens, or raw private content in the audit report.

## Verification

Invoke through the `terminal` tool from the Haft worktree:

```bash
git diff --check && bun run typecheck
```

The audit is ready to hand off only when the command passes (or its baseline failure is recorded), every finding has file/line evidence and a contract impact, and no claim exceeds the traced evidence.
