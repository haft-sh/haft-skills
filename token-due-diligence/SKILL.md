---
name: token-due-diligence
description: "Evidence-bounded risk and investment due diligence on exact EVM and Solana tokens, including indexed-chain research."
license: MIT
metadata:
  version: "0.4.0"
  author: Agent Chud (@AgentChud), Hermes Agent
---

# Token Due Diligence

Rigorous, evidence-bounded diligence on an exact EVM contract or Solana mint and its economic system. Investigates privileged actor control, liquidity custody, sellability, supply concentration, launch integrity, fee flows, reward rights, and external dependencies. Not a price predictor, trading bot, generic scanner score, or substitute for a full protocol exploit audit.

## When to Use

- User asks about a specific EVM or Solana token's safety, investment risks, or economic structure
- Questions about mint authority, upgradeability, seizure rights, or blacklist controls
- Liquidity lock status, LP principal removal risk, or side-pool exposure
- Sellability, exit depth, or executable size for a holder
- Supply concentration, launch allocation, or insider cohort tracking
- Fee flows, treasury composition, or reward redeemability
- Due diligence before purchase, position sizing, or exposure decisions

Don't use for: price prediction, trading signals, generic safety scores without chain/address binding, or full protocol exploit audits (route those to a separate audit workflow).

## Prerequisites

- For direct chain checks: a chain-appropriate read-only RPC endpoint and decoding tools; EVM can use `cast` or an ABI-capable library, Solana needs account/instruction decoding
- Chain-appropriate explorer access for source verification and discovery
- No private keys, seed phrases, or signing capability required — this skill operates read-only
- Optional: an authorized local indexer/research repository and retained chain evidence. Discover its current capabilities; do not assume complete history or permission to deploy/backfill.
- If the user requests cursory research or excludes RPC/indexer reads, honor that scope. Report unchecked chain controls and coverage as unresolved; tools are not a prerequisite to a bounded desk-research answer.

## Chain Routing

Read `references/evidence-rules.md` for every investigation. For EVM, use the block/runtime checks below and `references/execution-and-utility.md` when execution or utility is material. For Solana, read `references/solana.md` before chain queries or interpreting indexed data; EVM receipts, address normalization, proxy checks and the EVM validator are not substitutes. Use separate chain-specific packets for cross-chain dependencies.

## Operating Modes

1. **Focused answer** — investigate the requested question and necessary dependencies only. A question about whether a vault balance came from LP fees gets a reconciled fee-origin answer without expanding into a full audit.
2. **Broad diligence** — screen all core risk surfaces, deepen only where evidence triggers further work, produce a layered conclusion.
3. **Formal report** — complete and reconcile evidence first, then generate the requested report and visuals. Do not repeat research just to format it.

For a Jeetstreet formal report or migration-era revision, read `references/research-operations.md` and `references/report-publication.md`. They cover current capability discovery, operational authorization, the report envelope, score eligibility, and private/public release boundaries. A draft or merged specification does not establish a deployed service.

## Quick Reference

The `cast` commands below are EVM-only. Solana identity, state context and instruction checks are in its adapter.

- Pin state: `cast block latest --rpc-url <rpc>` → block number, hash, timestamp
- Identity check: verify chain ID from RPC; resolve name/symbol/decimals/supply from the target contract
- Runtime: `cast code <addr> --block <pin> --rpc-url <rpc>` → hash; resolve proxies, implementations, beacons, upgrade authority
- Architecture pass: identify every contract/key that can change balances, restrict transfers, remove principal, upgrade, collect fees, allocate rewards
- Batch reads: cache by chain/address/block/query; deduplicate identical runtimes by code hash
- Evidence ledger: finding ID, proposition, chain, address, pin/tx, artifact/query, decoding basis, confidence, alternatives, coverage, staleness conditions
- Keep secrets out of commands and artifacts where possible; use environment-based RPC configuration and redact credentials before sharing.

## Procedure

1. **Build the target packet** — requested/observed chain and contract/mint, metadata/raw supply, block pin or Solana commitment/context slots, code/program/authority identity, deployment/launch transaction, candidate markets, user's decision question, scope and known limitations.
2. **Verify chain identity** — EVM: RPC chain ID and exact contract; Solana: cluster genesis identity and exact case-sensitive mint. Confirm target metadata without substituting a same-symbol token.
3. **Architecture pass** — identify every contract or key that can change balances, restrict transfers, remove principal, upgrade behavior, collect fees, allocate rewards, or enforce claimed utility. Prioritize checks that can change the conclusion.
   If an indexer or research repository is in scope, first read `references/indexed-chain-evidence.md` and `references/research-evidence-manifest.md`. Before fresh acquisition, discover actual capabilities and check reusable exact-target exports and retained raw evidence; record gaps and authorization for new reads. Separate source/code identity, retained raw evidence, canonical interpretation, historical coverage, and scientific/publication eligibility. Check the adapter's actual chain support before using it.
4. **Screen core risk surfaces** — work through the 8 risk surfaces (see `references/core-risk-surfaces.md`). Deepen only where evidence triggers further work.
5. **Reconcile evidence** — opening balance + inflows + adjustments = outflows + closing balance + bounded unexplained delta. Account for wraps, burns, bridge legs, gas, reverts.
   Verify material decoded trade directions against raw successful execution and balance flows before using side-based metrics. Apply the selected chain adapter to launch routing, fees and claimed buybacks.
6. **Write the verdict** — lead with a direct conditional answer to the user's actual question. Rate each risk surface separately. Use bounded language. Maintain a finding-to-evidence ledger.

## Pitfalls

- "No owner" and "renounced" are claims to investigate, not conclusions about the whole system.
- A locked canonical position does not establish that all liquidity is locked, that price is supported, or that liquidity will remain in range.
- Historical execution proves execution at that historical state. Quotes and previews do not prove a realized exit.
- A wallet reaching zero does not prove a cash-out. Router transfers alone do not prove a sale.
- A vault balance is not necessarily available backing. A synthetic reward is not necessarily redeemable.
- RPC timeouts, pruning, rate limits, DNS failures, and unavailable APIs are coverage limitations, not token findings.
- Decompiler output is not verified source. Claim executable equivalence only when compilation and byte comparison close meaningful differences.
- Fresh ingestion, a signed artifact, matching counts, or a current registry entry does not establish complete launch/swap/liquidity history.
- Uniswap v3 and v4 do not share a swap-delta sign convention. Pool deltas, hook-adjusted wallet output, router callers, and beneficial owners are different facts.
- Token metadata linking a website does not authenticate project endorsement. Pending fee claims and configured buyback rules do not prove executed token purchases.
- Selector lookup is a candidate signature, not proof of privileged behavior. Distinguish a reverted call, empty return, encoded zero and RPC failure; missing familiar selectors/proxy slots do not prove all control paths absent.
- Cross-check a project's token, fee, status, utility and audit disclosures. Report contradictory terms with source/time attribution; do not replace disclosure review with on-chain depth.

## Verification

- Confirm the finding-to-evidence ledger covers every material claim with chain, address, pin, and decoding basis.
- Validate any broad-diligence report against the target-integrity checklist: chain/target consistency, metadata, chain-appropriate state context, scope provenance and no-signing declarations.
- For an **EVM-only** machine-checkable packet, follow `references/validation.md` and run `python3 scripts/validate_report.py <manifest.json>`. It checks captured bytes/header bindings, not economic truth, RPC honesty, or completeness. Solana uses the manual adapter checklist; no Solana packet validator is included. Do not fabricate evidence or coerce Solana into the EVM schema.
- When relying on derived histories/metrics, run a separate offline verifier that recomputes page/body equality, calculations and material semantic checks from retained inputs—not saved success flags. Preserve unknowns when inputs are missing. Report/PR summaries and site cards must obey the same evidence bounds.

## References

- `references/research-operations.md` — Jeetstreet migration, capability discovery, retained-first operations and budgets
- `references/report-publication.md` — report revisions, A–H score eligibility, release privacy and approval
- `references/solana.md` — Solana identity/context, authorities, instruction flows, holder and liquidity checks
- `references/research-evidence-manifest.md` — token-scoped research handoff, claim eligibility and publication lineage
- `references/evidence-rules.md` — non-negotiable evidence rules
- `references/core-risk-surfaces.md` — the 8 core risk surfaces (A-H)
- `references/workflow.md` — efficient workflow and parallel-agent guidance
- `references/output-standard.md` — output formatting and bounded language
- `references/triggered-deep-investigations.md` — conditional deep-dive tracks
- `references/attribution-discipline.md` — neutral attribution rules
- `references/validation.md` — validation requirements and synthetic test cases
- `references/behavioral-examples.md` — behavioral edge-case examples
- `references/indexed-chain-evidence.md` — optional Jeetstreet/indexer adapter, bounded queries, raw/index reconciliation, historical correction
- `references/execution-and-utility.md` — receipt truth, routed cohorts, integer fee accounting, operational utility and runtime reconstruction
