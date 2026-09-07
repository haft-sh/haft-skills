# Behavioral Examples

## Frozen replay with incorrect semantics

A frozen export reproduces every stored event hash, but independent raw receipt decoding shows inverted buy/sell directions. Treat reproducibility and semantic validity separately. Preserve the legacy artifact; require corrected decoder fixtures and successor lineage before using direction-based metrics. Do not weaken hash checks to accept silently changed bodies.

## Retrospective launch attribution

A mint transfer precedes the launch event within one verified transaction. A replay can attribute it after discovering the token, with that later availability. It cannot claim the token was known before discovery, borrow a later transaction's registry, or imply missing indexed rows were backfilled.

## Solana sample and context limits

A provider returns 20 largest token accounts, several owned by one authority, at a later slot than the supply read. Report a sampled account/owner analysis with context drift, not a complete holder census or a single pinned snapshot. Resolve program ownership separately from token-account owner authority. Do not lowercase mints or pass them through the EVM validator.

## Research support on the wrong chain

A research export supports only Robinhood event identities, while the requested mint is on Solana. Reuse the evidence standards, not the decoder/schema. Discover a compatible Solana adapter or leave indexed coverage unresolved; the existence of a whole-chain indexing project is not proof of target coverage.

## Cursory scope without fresh chain reads

The user asks for desk research only on a chain without local coverage. Use permitted public evidence, time-label claims and explicitly leave untested controls and executable depth unresolved. Do not provision infrastructure or issue RPC queries merely to satisfy the broad-diligence checklist.

## Indexed history with a convincing count

An index and raw RPC each return the same number of trades. One early swap is missing from the index and a duplicate/different-fork event fills the count. Reconcile exact active identities and headers; do not declare completeness from totals. Then check bodies: perfectly matching identities can still carry reversed trade sides.

## Configured revenue without execution

A project's docs promise fee-funded purchases. Pending escrow exists, but the treasury token binding and swap route are unset. Report deployed components and pending claims separately from unexecuted purchases. Affiliation remains unresolved without authenticated exact-address evidence; do not jump to a counterfeit allegation.

These examples illustrate edge cases the skill must handle correctly.

## 1. Locked Canonical Liquidity with Removable Side Liquidity

A token locks its primary Uniswap v3 position for 2 years on a reputable locker. However, a second pool exists on a lesser-known DEX with no lock, containing 30% of total liquidity. The side pool has no removal restrictions.

Verdict: The canonical lock is real but incomplete. Report side-pool removal risk separately. Do not claim "all liquidity is locked."

## 2. Fixed Supply with Severe Holder-Sized Exit Degradation

Token has a hard-capped 1M supply, no mint function. But 70% of supply sits in 3 wallets that have never sold. The remaining 30% trades in a pool with $400 total liquidity. A holder of 10,000 tokens (1% of supply) attempting to sell would face >90% price impact.

Verdict: Fixed supply does not guarantee sellable. Report token controls separately from sellability. "No mint" is not "exitable."

## 3. Upgradeable Reward Layer Surrounding an Immutable Token

The base ERC-20 is immutable — no mint, no pause, no upgrade. But a staking contract routes rewards from an upgradeable fee distributor proxy. The proxy admin is a 2-of-3 multisig with no timelock.

Verdict: The token itself is frozen, but the reward layer is mutable. Report token controls and reward custody separately. Immutable core + upgradeable periphery = mixed verdict.

## 4. Launch Wallets Selling and Rebuying for New Recipients

Three wallets that received from the deployer send all tokens to a DEX router, then receive fresh tokens from a new wallet funded by the same bridge. Net effect: supply appears redistributed. But the deployer's wallet still controls the fee collector.

Verdict: Treat as market-mediated redistribution unless common control is proven. Do not call it a "cash-out" without cost basis evidence. Track fee collector separately.

## 5. A Vault Holding Synthetic Claims Without a Proven Underlying Exit

A vault contract holds 100,000 "wrapped reward tokens" issued by the protocol. The wrapper has no redeem function, no burn path, and no migration router. The tokens trade at $0.001 on a thin pool.

Verdict: Vault balance ≠ available backing. Report inventory vs. redeemability separately. Do not treat synthetic claims as underlying assets.

## 6. An RPC Failure That Must Remain a Coverage Limitation

During a broad diligence run, the archive node times out on historical Transfer logs for a 3-month-old contract. The investigation needs those logs to answer a launch-cohort question.

Verdict: Report "Unknown because historical state was unavailable." Do not skip the check silently and present other findings as if the check passed. Record the coverage limitation in the evidence ledger.
