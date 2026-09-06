---
name: evm-token-due-diligence
description: "Rigorous evidence-bounded diligence on exact EVM tokens."
version: 0.1.0
author: Agent Chud (@AgentChud), Hermes Agent
license: MIT
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
- `cast` (Foundry) for RPC calls, calldata encoding, decoding
- Block explorer access (Etherscan, Blockscout, or chain-specific) for source verification and discovery
- No private keys, seed phrases, or signing capability required — this skill operates read-only

## Operating Modes

1. **Focused answer** — investigate the requested question and necessary dependencies only. A question about whether a vault balance came from LP fees gets a reconciled fee-origin answer without expanding into a full audit.
2. **Broad diligence** — screen all core risk surfaces, deepen only where evidence triggers further work, produce a layered conclusion.
3. **Formal report** — complete and reconcile evidence first, then generate the requested report and visuals. Do not repeat research just to format it.

## Quick Reference

- Pin state: `cast block latest --rpc-url <rpc>` → block number, hash, timestamp
- Identity check: verify chain ID from RPC; resolve name/symbol/decimals/supply from the target contract
- Runtime: `cast code <addr> --rpc-url <rpc>` → hash; resolve proxies, implementations, beacons, upgrade authority
- Architecture pass: identify every contract/key that can change balances, restrict transfers, remove principal, upgrade, collect fees, allocate rewards
- Batch reads: cache by chain/address/block/query; deduplicate identical runtimes by code hash
- Evidence ledger: finding ID, proposition, chain, address, pin/tx, artifact/query, decoding basis, confidence, alternatives, coverage, staleness conditions

## Procedure

1. **Build the target packet** — requested/observed chain/address, name/symbol/decimals/supply, block pin + header, runtime hash + proxy/implementation info, deployment/launch tx, candidate pools/contracts, user's decision question, scope, materiality rules, known limitations.
2. **Verify chain identity** — `cast chain-id --rpc-url <rpc>`; confirm the target address resolves to the expected metadata. Never substitute a same-symbol token.
3. **Architecture pass** — identify every contract or key that can change balances, restrict transfers, remove principal, upgrade behavior, collect fees, allocate rewards, or enforce claimed utility. Prioritize checks that can change the conclusion.
4. **Screen core risk surfaces** — work through the 8 risk surfaces (see `references/core-risk-surfaces.md`). Deepen only where evidence triggers further work.
5. **Reconcile evidence** — opening balance + inflows + adjustments = outflows + closing balance + bounded unexplained delta. Account for wraps, burns, bridge legs, gas, reverts.
6. **Write the verdict** — lead with a direct conditional answer to the user's actual question. Rate each risk surface separately. Use bounded language. Maintain a finding-to-evidence ledger.

## Pitfalls

- "No owner" and "renounced" are claims to investigate, not conclusions about the whole system.
- A locked canonical position does not establish that all liquidity is locked, that price is supported, or that liquidity will remain in range.
- Historical execution proves execution at that historical state. Quotes and previews do not prove a realized exit.
- A wallet reaching zero does not prove a cash-out. Router transfers alone do not prove a sale.
- A vault balance is not necessarily available backing. A synthetic reward is not necessarily redeemable.
- RPC timeouts, pruning, rate limits, DNS failures, and unavailable APIs are coverage limitations, not token findings.
- Decompiler output is not verified source. Claim executable equivalence only when compilation and byte comparison close meaningful differences.

## Verification

- Confirm the finding-to-evidence ledger covers every material claim with chain, address, pin, and decoding basis.
- Validate any broad-diligence report against the target-integrity manifest: chain/address consistency, metadata consistency, block pins, scope-address provenance, and no-signing declarations.

## References

- `references/evidence-rules.md` — non-negotiable evidence rules
- `references/core-risk-surfaces.md` — the 8 core risk surfaces (A-H)
- `references/workflow.md` — efficient workflow and parallel-agent guidance
- `references/output-standard.md` — output formatting and bounded language
- `references/triggered-deep-investigations.md` — conditional deep-dive tracks
- `references/attribution-discipline.md` — neutral attribution rules
- `references/validation.md` — validation requirements and synthetic test cases
- `references/behavioral-examples.md` — behavioral edge-case examples
