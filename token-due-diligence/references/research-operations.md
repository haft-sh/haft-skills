# Jeetstreet research operations during migration

Use for Jeetstreet-supported token reports, revisions, or evidence-service access. This is a maintained adapter, not a claim that all planned APIs exist. Keep ordinary bounded RPC/desk research usable when the service is absent.

## Discover reality before choosing a workflow

The authoritative repositories are:

- `haft-sh/jeetstreet`: collectors, canonical decoding, retained archives and private evidence-plane contracts/gateway.
- `haft-sh/jeetstreet-research`: research jobs/budgets, report schemas/rubric, review/publication and frontend.
- `haft-sh/haft-skills`: this portable skill. Runtime copies should be synchronized from an identified canonical revision, not independently maintained.

Read applicable repo instructions, status, current README/specs, released schemas and deployment/capability receipts. Local folders may be absent; use authorized GitHub read access to inspect the repo. Useful read-only discovery:

```bash
gh repo view haft-sh/jeetstreet-research --json defaultBranchRef
gh api 'repos/haft-sh/jeetstreet-research/git/trees/main?recursive=1' --jq '.tree[].path'
gh pr view 174 --repo haft-sh/jeetstreet --json state,headRefOid
```

Record exact inspected revisions. A source branch, passing tests, merged contract or README is not a live endpoint, deployed decoder, repaired history, complete target capture or editorial approval. Do not probe invented `/v1` URLs merely because a spec lists them. Discover the deployed base URL/authentication and compatible schema from operator-owned configuration or ask for the missing access.

Migration snapshot **2026-09-08**, to be rechecked rather than treated as permanent configuration: the new research repo's default branch contained README/.gitignore only. Its README specifies a private sole-superadmin initial service, exact-report-version user approval, a USD 100/month operating envelope, separate QuickNode/Birdeye credit accounting, retained PostgreSQL/S3 first, and public/x402 access last. These are scope constraints, **not a per-job spending grant or evidence of deployment**. Check remaining shared budget and authorized provider scope before calls.

Design references: [platform PR 174](https://github.com/haft-sh/jeetstreet/pull/174), [research repo](https://github.com/haft-sh/jeetstreet-research), and the current `docs/20260908-research-program-platform-reconciliation-spec.md` in Jeetstreet. The latter narrows public exposure to reviewed reports/approved assets; private underlying data does not become public because a report is public. Recheck implementation and approved policy, not just the original proposal.

## Evidence acquisition and authorization

1. Resolve exact chain/network/contract or case-sensitive mint and requested depth. Use the deployed capability/preflight interface when available; otherwise inspect a compatible existing export and bounded local capability record.
2. Prefer a qualified exact-target packet, then target inventory, then authorized retained S3/raw objects. Check cutoff, history gaps, launch/graduation ancestry, decoder/revision status, private access and permitted model-provider egress. Reuse bytes only when their claim scope matches.
3. Record **Existing internal data checked before external acquisition**: inventory/export IDs, selection, coverage, missing ranges and why fresh requests are necessary. If access is unavailable, say so; do not claim the archive is empty or exhausted.
4. Use fresh RPC only within the agreed scope. Before paid QuickNode, Helius, Birdeye or another metered source, obtain/reuse an explicit grant identifying provider/account scope, methods, target/range, maximum requests/credits/cost, and deadline. Key availability, a monthly ceiling, DB-read permission and a public-RPC failure are not authorization.
5. Account cumulatively across failed attempts, retries, resumed runs and concurrent workers. Keep provider credit units distinct from cash and reserve uncertain costs conservatively. Stop at a grant boundary; no silent provider, plan, backfill, stream or compute escalation.

An approved internal gateway should expose typed bounded operations, not SQL credentials or arbitrary provider URLs. Use request-scoped capabilities bound to principal/job/target/cutoff/export/artifacts, byte/method limits and expiry. Knowing another export ID grants no access. Keep credentials out of model text and public artifacts; private evidence access does not automatically permit sending all rows to any model vendor.

Legacy fallback: inspect `src/publicResearch/inventoryCli.ts` before using
`bun run --cwd packages/research-runtime research:public:inventory --request REQUEST.json --output INVENTORY.json`.
At the reviewed baseline it requires an explicit authorized `PUBLIC_RESEARCH_INVENTORY_DATABASE_URL`, remote TLS, a range of at most 5,000 blocks and count limits. It is registry-frame private metadata, **not a complete token holder/history export**. Prefer a smaller existing token export. Never expose DB networking or launch ECS to make it work without explicit separate approval; AWS credentials alone do not confer network reachability or compute authority.

For direct approved extraction use `indexed-chain-evidence.md`: SELECT-only role, short read-only transactions, query-plan/row/byte/time bounds, latest-revision and canonical-header qualification, stable pagination and exact archive versions. Preserve `unsupported`, `not_captured`, `not_decoded`, `access_unavailable`, `not_queried`, `partial` and `quarantined` as different outcomes. An error is never a verified-empty success.

## Destination and stopping rules

New research findings belong to the research system as its implementation becomes available; proposed storage is research PostgreSQL for state/lineage and S3 for artifact bytes, not a new raw corpus in either Git repo. Do not implement storage or migrate objects during a diligence request. If the service/importer is unavailable, retain an authorized local candidate and report the handoff gap, or use the legacy PR destination **when specifically requested**. No cross-repo `.env`, writes to collector tables, or automatic bulk corpus copying.

A token report and a population market study are distinct report kinds. An available token packet cannot establish an unbiased cohort, survival rate or peer rank. Preserve cohort qualification when including comparisons; otherwise leave rank unavailable.

Completing a draft does not authorize publication, social posting, paid requests, or closing competing PRs. Follow the exact requested mutation. A canonical selection does not authenticate a missing historical receipt or refresh an old chain pin.
