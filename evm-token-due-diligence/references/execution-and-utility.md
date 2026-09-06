# Execution, Attribution and Operational Utility

Use these checks when launch routing, AMM hooks, fee-funded utility, or inherited contract source is material. They supplement the core risk surfaces, not replace them.

## Receipt-level economic truth

Bind the exact venue implementation and pool key, currency ordering, decimals and signed integer widths. For normal opposite-signed swaps, v3 positive target delta means input to the pool (sell); v4 positive target delta means target output (buy). Do not infer the convention from a generic field name or copied decoder. Verify the emitting implementation and successful receipt flows. In v4, pool Swap amounts may precede hook adjustments; the caller's final settlement and recipient output can differ.

For material samples, retain the transaction, success status, raw logs, block/header binding and, where needed, trace. Join swaps to ERC20 transfers, native value, wraps, fee legs and recipient changes. Event sender may be a router; it is not automatically the payer, recipient, investor or beneficial owner. Zero, one-sided, fee-only and unexpected same-sign deltas need an explicit unclassified policy; do not manufacture a buy/sell or silently count them as organic volume.

Use integer raw units for balances, fees, deltas and cost reconciliation. Match the contract's order of operations and rounding: subtracting individually truncated fees can differ from truncating the retained percentage. Keep gross pool output, net recipient output, protocol-internal conversions and paired route volume distinct. A zero ERC20 transfer tax does not mean a zero venue/hook fee.

## Reproducible launch cohorts

1. Freeze seed addresses from exact launch/acquisition receipts, chronology, inclusion/exclusion rules, maximum traversal and end pin before summarizing the cohort.
2. Inspect atomic next-block acquisition and graduation, not only the creator's initial purchase.
3. Track later direct transfers and market-mediated sell/rebuy routing under separately declared rules. To add a routed recipient, demonstrate payer tokens, sale output, fees, rebuy input and final recipient in the same transaction or otherwise proven connected path.
4. Compare gross route turnover with total venue turnover only under a common range and event policy. Paired turnover is not fresh net inflow.
5. Replay Transfer supply accounting through the pin; reconcile mint/burn behavior and selected cohort balances against pinned getters. State whether every address, only material addresses, or only aggregate supply was cross-checked. Rebase/nonstandard tokens require their own balance model.
6. Identify protocol custody by function and authority. Code presence alone is insufficient: account delegation (including EIP-7702) is not proof of protocol custody. Avoid adding nominal NFT/singleton balances to unrelated pool liquidity.

Report this as a rule-linked recipient/flow cohort unless independent evidence establishes ownership. Original wallets reaching zero after reinvestment are not necessarily cashing out. A consolidated ending balance is not a cost basis or profit calculation. Include unresolved routes, downstream descendants, fees, gas and cross-chain legs in limitations.

## Prove the claimed economic mechanism end to end

Treat token affiliation and mechanism operation as separate questions. Launcher-supplied website/social metadata is a lead, not authentication. Seek an exact-address announcement from an authenticated project channel and agreement with current treasury/registry token bindings. An unset binding is evidence of incomplete configuration, not sufficient proof of counterfeiting.

Follow the actual path:

`trade fee → fee escrow → recipient/splitter → configured route + cap → successful work/buyback receipt → asset balance change or burn`

At the common pin inspect recipient overrides/timelocks, pending claims, inventories by asset, route addresses, token binding, spending caps, operator permissions, work counters/epochs and successful execution receipts. Pending escrow, internal accounting credits and configured percentages are not executed revenue or purchases. Zero counters support a scoped liveness finding only when the counter's code semantics and history are verified.

Review control outside the ERC20: mutable routes, emergency withdrawals and delays, arbitrary calls, upgradeability, custody, owner EOA/multisig threshold, and whether holders have redemption rights. A purchase into an owner-controlled treasury is not a burn, dividend or pro-rata backing. A registry's unique ticker string is not legal equity, price tracking, market-wide exclusivity or proof of demand.

State what would change the thesis: authenticated binding, operational routes, repeated successful work cycles with reconciled balances and persistent independent activity. Do not value a promised flow as current holder revenue.

## Reconstruct source carefully

If the target has no direct verified source, inspect verified factory/deployment compiler inputs and exact pinned source commits before deeper decompilation. Rebuild using exact compiler version, optimizer/via-IR/EVM settings, libraries and metadata configuration. Patch only compiler-declared immutable references with independently resolved values; retain that map and getter/storage evidence. Preserve input/output, runtime bytes and hash, tool versions and comparison procedure.

Distinguish full runtime equality, metadata-excluded executable equality, unresolved differences and merely similar source. Do not ignore compiler/settings differences or call decompiler output verified. Review surrounding upgrade/fee/custody contracts even when the ERC20 itself reproduces exactly.

## Value exits in the actual output asset

Separate supply-times-spot FDV, any justified circulating-supply estimate, total LP value and quote-side inventory. Disclose locked/surplus denominator adjustments; they do not automatically establish circulating market cap. With concentrated liquidity, inspect active tick ranges and other positions; a permanent lock does not guarantee depth at every price.

Pin read-only quotes for disclosed token quantities across meaningful position sizes, with the actual route/hook and fee configuration. Retain raw input and ETH/stablecoin output, quote basis and gas exclusions. Time-label external USD conversion separately from the chain pin. Do not call a current-dollar translation historical USD turnover.

Compare with independent pool math where valid; do not apply full-range math to concentrated multi-position liquidity. Quotes are not completed sales, optimal routing or a promise of future fills. Distinguish isolated quotes from sequential liquidation and explicitly label cohort-wide stress scenarios.
