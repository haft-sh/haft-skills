# Behavioral Examples

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
