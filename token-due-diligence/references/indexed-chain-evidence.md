# Indexed Chain Evidence

Use when the user provides an indexer, research repository, retained raw archive, or direct database access. Jeetstreet is an optional adapter, not a prerequisite. Keep ordinary RPC/explorer diligence usable when local capabilities are absent.

Read `research-evidence-manifest.md` for token-scoped handoff and claim eligibility. Select the EVM or Solana adapter before interpreting indexed data; the EVM log/receipt mechanics below apply only to EVM.

## Establish capability and authority

1. Read applicable repository instructions, research specifications, schema/migrations, and relevant decoder/ingestion tests. Use `git status --short`, `git rev-parse HEAD`, and `rg` before assuming a clean or current checkout.
2. Distinguish local commit, merged remote commit, deployed image/task revision, and in-flight PRs. Source inspection is not proof of deployed behavior; a merged milestone is not a completed study.
3. Discover the actual storage/query interface from code. Start with existing exact-version retained evidence and offline replay. In a Jeetstreet checkout, useful search roots may include `src/chains/`, `src/evm/`, `src/publicResearch/`, `src/researchCapture/`, `src/db/`, and `docs/`. Verify these paths and schemas in the selected commit; do not hardcode a past table or deployment.
4. Read-only diligence does not authorize migrations, backfill writes, collector changes, new credentials/permissions, paid-plan changes, or deployment. Check existing budgets before remote reads. Do not spin up cloud compute merely because a repository has deployment scripts. If access requires material new infrastructure or authority, report the precise blocker.
5. Never print dotenv contents, connection URLs, private object locators, or credentials. Keep raw private data and operational identifiers out of public reports and reusable skills. Sharing a PR does not automatically authorize publishing its private supporting corpus.

## Separate five evidence layers

| Layer | What successful verification establishes | What it does not establish |
|---|---|---|
| Raw identity | Exact archived bytes, checksum/version, log membership and header binding | Correct ABI interpretation or honest provider |
| Canonical meaning | Reproducible decode under identified source/compiler and registry ancestry | Completeness of the selected universe |
| Coverage | Reconciled identities within explicit chain, contracts, topics, blocks and selection policy | History outside that scope |
| Availability | Original observation/completion clocks plus later evidence availability | Knowledge of repaired data at an earlier decision |
| Scientific qualification | Frozen inputs, cohort policy, outcome horizon and admission gates satisfied | Investment profitability or permission to publish |

A signature authenticates a selected artifact, not historical completeness. Two endpoints are not necessarily independent upstream sources. Record shared-provider dependencies when known.

## Bounded read-only extraction

- Resolve chain, exact target, full pool key/market identifier, event families, deployment/graduation range and upper block/hash first. V4 singleton balances are not individual-pool reserves.
- Inspect indexes and use a bounded query plan; avoid full-chain joins or unbounded scans on production. Use an existing read-only role, transaction-level read-only enforcement and, when needed, one repeatable-read snapshot for related pages.
- Set statement/lock timeouts, row and byte limits, block/time chunk sizes, request/object budgets and a total deadline. Keep snapshots short: long-lived read transactions also impose operational cost. Persist private snapshot/cutoff identity, SQL and parameters, paging boundaries, extraction times and counts.
- A row cap is truncation unless proven otherwise. Use stable unique keyset pagination or subdivide an overflowing range. Record failed/unqueried ranges; never treat an empty timeout result as zero events.
- For a declared availability cutoff, select the latest eligible revision per logical event before filtering active/reverted status; otherwise an older active row can be resurrected. Bind canonical headers and applicable reorg displacements separately. Stable ordering includes unique identity/revision ties. A sampled set of active revision-1 rows does not qualify the query for general reuse. Do not keep a production transaction open while a model reads pages; prefer a bounded immutable export.
- Prefer verified raw archive reads before new provider calls. For RPC fallback, retain exact chain-ID/header requests and responses, paginate bounded log ranges, and check provider caps. Spot-check early/late boundaries and successful receipts; absence from one RPC query is not proof that a capped provider returned all history.
- Temporary query credentials must remain read-only. Any diagnostic resources explicitly authorized for this task must be tracked to terminal state; do not stop pre-existing collection.
- Retain actual approval references and independently inspectable terminal observations privately; a script literal such as `taskStopped: true` does not authenticate completion. Do not retroactively invent missing receipts. Jeetstreet-specific access and cumulative paid-provider rules are in `research-operations.md`.

## Reconcile identities, then bodies

Freeze the selection before calculating trading/holder statistics. Compare canonical log identities using chain ID, block hash, transaction hash and log index, with address/topic/pool filters. Also compare block number and raw payloads. Deduplicate redeliveries without hiding conflicting bodies. A reorg is not an ordinary missing event: reconcile canonical headers, removal status and event revisions explicitly.

For Solana, use cluster/signature/instruction-location identities and retained slot/block context as described in `solana.md`; reconcile top-level/inner instructions and account balance bodies rather than manufacturing EVM log fields.

Report at least:

- Requested inclusive range and canonical end pin, observed first/last event, event-family and market filters.
- Raw/index row counts before deduplication and unique active identities after revision selection.
- Matched, raw-only, index-only, duplicate and conflicting identities; counts by block and event family.
- Raw and indexed body comparison coverage separately, including decoder source identity and sign/orientation checks.
- Retrieval/snapshot times, known gaps, failed ranges and what is deferred.

Equal counts can conceal one missing plus one extra event. Matching identities do not validate `side`, amounts, fee accounting or ownership. Current market-registry membership and healthy live ingestion do not prove launch history. Check the launch transaction, next-block acquisition, graduation, pool registration and initial liquidity independently: discovery can arrive after the first tradable events.

For missing ancestry, locate all bounded unresolved dependency groups before repeating one-parent-at-a-time capture. Verify exact archived launch/registration membership and headers, then replay chronologically from an empty or independently proven registry. Current descriptors can locate candidates but cannot substitute for historical raw provenance. Missing/corrupt discoveries must not seed later interpretations.

## Corrections and research validity

A decoder defect is a data-quality finding, not a token exploit finding. Demonstrate it with a successful receipt and meaningful regression for both directions/currency orders. Quantify affected selection scope without claiming every downstream table is audited.

Corrected canonical bodies generally change hashes while raw event identity stays fixed. Preserve original receipts, hashes, decoder/code identity and observation clocks. Keep mismatch checks fail-closed. A repair needs explicit correction lineage, new derived hashes/availability, affected-consumer inventory, bounded replay and before/after reconciliation. Do not overwrite signed/frozen artifacts, silently reinterpret old hashes, or backdate newly acquired headers. Fixing code, deploying it, rewriting history and requalifying a study are separate actions and approvals.

Do not infer success probabilities from an in-flight research spec or a provenance milestone. Require the study's complete inclusion policy, launch/post-graduation coverage, censored failures, point-in-time availability, outcome maturity, fees and executable-size assumptions. Otherwise provide descriptive bounded evidence and leave predictive claims unresolved.
