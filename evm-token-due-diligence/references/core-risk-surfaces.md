# Core Risk Surfaces

Screen all 8 surfaces. Deepen only where evidence triggers further work. Prioritize checks that can change the conclusion — do not apply monetary materiality thresholds to discovery of mint, upgrade, seizure, transfer restriction, arbitrary-call, or LP-removal authority.

## A. Token Code and Control

Inspect minting, burning, rebasing, balance rewrites, seizure, pause, blacklist, whitelist, taxes, exemptions, cooldowns, transaction limits, trading gates, external calls, delegatecall, and upgrade paths.

Resolve current owners, roles, multisig thresholds, timelocks, and who can change them. Distinguish what current code permits from what an administrator could introduce by replacing it.

"No owner" and "renounced" are claims to investigate, not conclusions about the whole system.

## B. Liquidity Custody

Identify each material pool by exact address or complete pool key.

For v3/v4 positions, resolve position manager, NFT/position ID, tick range, liquidity, owner, approvals, operators, and locker or hook authority.

Inspect withdrawal, decrease-liquidity, burn-position, rescue, arbitrary-call, approval, upgrade, and transfer paths.

Separate canonical liquidity from side pools. Declare discovery sources, searched ranges, and coverage limits.

A locked canonical position does not establish that all liquidity is locked, that price is supported, or that liquidity will remain in range.

For Uniswap v4, record currency ordering, fee, tick spacing, hook, and derived PoolId. Never treat the singleton PoolManager's token balance as one pool's reserves.

## C. Sellability and Executable Depth

Find a successful historical sell when available and obtain current pinned read-only quotes at a small size and relevant holder-sized amounts.

Report route, input, quote asset, expected output, fees, per-unit degradation, and failure reasons. Distinguish price impact, slippage tolerance, gas, spot price, and executable depth.

Historical execution proves execution at that historical state. Quotes and previews do not prove a realized exit.

For a decisive simulated sale or redemption, require a successful receipt plus the intended underlying-asset balance delta, with route and costs explained. A returned success flag or emitted event alone is insufficient.

## D. Supply and Concentration

Reconcile supply and material balances using methods appropriate to the token's accounting.

Classify pool custody, protocol custody, lockers, treasuries, burn addresses, creator allocations, and investor-like balances separately. State concentration denominators and exclusions.

Keep raw assets, rebasing units, synthetic claims, bond/NFT shares, LP shares, custody, total supply, and circulating float distinct.

Use full Transfer replay when discrepancies or historical questions justify it. Account for tokens whose balances change without ordinary Transfer events.

## E. Launch Integrity

Decode launch parameters, allocations, fee exemptions, direct buy recipients, funding, deterministic addresses, deployment sequence, and early transfers or sales.

Distinguish automatic launch-platform behavior from manually supplied exceptions. Verify the exact factory version and deployed behavior.

Define any investigated wallet cohort before measuring it: inclusion rule, time bounds, sources, exclusions, and coverage.

Track initial allocation, transfers, sales, rebuys, downstream inventory, proceeds, fees, and retained assets. A wallet reaching zero does not prove a cash-out.

Prove sales from successful execution and pool/curve mechanics; router transfers alone are insufficient.

For Pons-style launches, inspect the direct curve buy recipient and applicable tax treatment rather than assuming the transaction sender received the benefit.

## F. Fees, Treasury, and Proceeds

Map fee basis, denomination, splits, escrow, claim authority, recipients, configurable routes, and subsequent use.

Separate a percentage of gross trade value from a percentage of a fee bucket. Separate current configuration from historically realized rates.

Reconcile each relevant asset:
opening balance + inflows + explained adjustments = outflows + closing balance + explicitly bounded unexplained delta.

Account for wraps, burns, bridge legs, gas, and reverted transactions correctly. Do not double-count transformations.

For bridge tracing, match source execution, identifiers, destination chain, recipient, delivered amount, and destination evidence.

Stop exact attribution at commingling. An exchange deposit does not prove a sale, fiat withdrawal, or final beneficiary.

## G. Rewards, Vaults, Backing, and Redemption

Separate inventory from holder liabilities and promises from enforceable rights.

Identify who can claim, the actual asset received, conversion units, fees, timing, caps, approvals, admin dependencies, and exit route.

A vault balance is not necessarily available backing. A synthetic reward is not necessarily redeemable for an underlying asset.

For "did these holdings come from LP fees?", reconcile balances and transfers to receipt-level fee collections and forwarding. Distinguish vault holdings, pool inventory, and unclaimed fees.

For distributions, test conservation, entitlement rules, cumulative caps, duplicate payments, unpaid amounts, retained inventory, and processing liveness when material.

Do not assume distributed amounts must be less than purchases if prefunding, donations, carryover, or minting exist.

## H. Utility, Dependencies, and Development

Determine whether advertised utility is live, token-linked, and enforceable.

Inspect material external assets, oracles, bridges, APIs, keepers, lending systems, collateral, and redemption dependencies.

Assess source correspondence, reproducible builds, tests, audit scope, release controls, governance, disclosure accuracy, and actual operating behavior.

Polished marketing, copied templates, and awkward code do not establish safety, fraud, or AI authorship.
