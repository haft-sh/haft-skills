---
name: evm-token-due-diligence
description: "Rigorous evidence-bounded diligence on exact EVM tokens."
license: MIT
metadata:
  version: "0.2.0"
  author: Agent Chud (@AgentChud), Hermes Agent
---

# EVM Token Due Diligence

Rigorous, evidence-bounded diligence on an exact EVM token and its economic system. Investigates privileged actor control, liquidity custody, sellability, supply concentration, launch integrity, fee flows, reward rights, and external dependencies. Not a price predictor, trading bot, generic scanner score, or substitute for a full protocol exploit audit.

## When to Use

- User asks about a specific EVM token's safety, risks, or economic structure
- Questions about mint authority, upgradeability, seizure rights, or blacklist controls
- Liquidity lock status, LP principal removal risk, or side-pool exposure
- Sellability, exit depth, or executable size for a holder
- Supply concentration, launch allocation, or insider cohort tracking
- Fee flows, treasury composition, or reward redeemability
- Due diligence before purchase, position sizing, or exposure decisions

Don't use for: price prediction, trading signals, generic safety scores without chain/address binding, or full protocol exploit audits (route those to a separate audit workflow).

## Prerequisites

- An EVM RPC endpoint (public or private) reachable from the terminal
- `cast` (Foundry), or an equivalent ABI-capable library such as ethers, for read-only RPC and decoding
- Block explorer access (Etherscan, Blockscout, or chain-specific) for source verification and discovery
- No private keys, seed phrases, or signing capability required — this skill operates read-only
- Optional: an authorized local indexer/research repository and retained chain evidence. Discover its current capabilities; do not assume complete history or permission to deploy/backfill.

## Operating Modes

1. **Focused answer** — investigate the requested question and necessary dependencies only. A question about whether a vault balance came from LP fees gets a reconciled fee-origin answer without expanding into a full audit.
2. **Broad diligence** — screen all core risk surfaces, deepen only where evidence triggers further work, produce a layered conclusion.
3. **Formal report** — complete and reconcile evidence first, then generate the requested report and visuals. Do not repeat research just to format it.

## Quick Reference

- Pin state: `cast block latest --rpc-url <rpc>` → block number, hash, timestamp
- Identity check: verify chain ID from RPC; resolve name/symbol/decimals/supply from the target contract
- Runtime: `cast code <addr> --block <pin> --rpc-url <rpc>` → hash; resolve proxies, implementations, beacons, upgrade authority
- Architecture pass: identify every contract/key that can change balances, restrict transfers, remove principal, upgrade, collect fees, allocate rewards
- Batch reads: cache by chain/address/block/query; deduplicate identical runtimes by code hash
- Evidence ledger: finding ID, proposition, chain, address, pin/tx, artifact/query, decoding basis, confidence, alternatives, coverage, staleness conditions
- Keep secrets out of commands and artifacts where possible; use environment-based RPC configuration and redact credentials before sharing.

## Procedure

1. **Build the target packet** — requested/observed chain/address, name/symbol/decimals/supply, block pin + header, runtime hash + proxy/implementation info, deployment/launch tx, candidate pools/contracts, user's decision question, scope, materiality rules, known limitations.
2. **Verify chain identity** — `cast chain-id --rpc-url <rpc>`; confirm the target address resolves to the expected metadata. Never substitute a same-symbol token.
3. **Architecture pass** — identify every contract or key that can change balances, restrict transfers, remove principal, upgrade behavior, collect fees, allocate rewards, or enforce claimed utility. Prioritize checks that can change the conclusion.
   If an indexer or research repository is in scope, first read `references/indexed-chain-evidence.md`. Separate source/code identity, retained raw evidence, canonical interpretation, historical coverage, and scientific/publication eligibility.
4. **Screen core risk surfaces** — work through the 8 risk surfaces (see `references/core-risk-surfaces.md`). Deepen only where evidence triggers further work.
5. **Reconcile evidence** — opening balance + inflows + adjustments = outflows + closing balance + bounded unexplained delta. Account for wraps, burns, bridge legs, gas, reverts.
   Verify material decoded trade directions against raw receipts before using side-based metrics. Read `references/execution-and-utility.md` for launch routing, hook fees, source reconstruction, and claimed buyback checks.
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

## Verification

- Confirm the finding-to-evidence ledger covers every material claim with chain, address, pin, and decoding basis.
- Validate any broad-diligence report against the target-integrity manifest: chain/address consistency, metadata consistency, block pins, scope-address provenance, and no-signing declarations.
- For a machine-checkable evidence packet, follow `references/validation.md` and run `python3 scripts/validate_report.py <manifest.json>`. It checks captured bytes/header bindings, not economic truth, RPC honesty, or completeness. Existing reports must be explicitly adapted; do not manufacture missing evidence to satisfy the schema.

## References

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
