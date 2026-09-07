# Solana Adapter

Use for exact Solana mints. Shared economic risk surfaces still apply; EVM tooling and packet validation do not. For current protocol details, verify the relevant official RPC/token-program documentation rather than assuming a decoder supports every extension or transaction version.

## Identity and state context

- Preserve the case-sensitive base58 mint and verify it decodes to a 32-byte public key. Bind RPC evidence to cluster genesis identity (`getGenesisHash`), not only a provider's network label.
- Inspect the mint account's owning program, raw data, supply, decimals and authorities. Distinguish the legacy Token Program from Token-2022. Metadata, ticker and a launch-platform suffix do not authenticate affiliation.
- Prefer finalized reads when appropriate; retain commitment, request parameters, returned context slots and UTC retrieval times. `minContextSlot` is a lower bound, not an exact historical account-state selector. Related reads may reflect different slots; use a common-context batch where supported or disclose the drift.
- Bind historical transactions to signature, returned slot, successful `meta.err` status and available block identity. A transaction's recent blockhash is not the containing block's hash. Current account state cannot establish historical balances or authorities without retained historical evidence.

## Control and liquidity

- Inspect mint/freeze authority, account owner/delegate/close authority and all enabled mint/account extensions relevant to transferability, balances or custody. For Token-2022 include permanent delegate, transfer fees and withdrawal authority, transfer hooks and their authority, default frozen state, non-transferability, and amount-display transformations where present. Unrecognized material extensions remain unresolved.
- Distinguish an account's owning **program** from the token-account **owner authority**, and both from a beneficial investor. Resolve PDA control through the governing program and relevant configuration; an off-curve address is not proof of burned assets.
- Resolve material custom programs, loader/deployment form and upgrade authority where applicable. Revoked mint/freeze authority does not establish that surrounding market, treasury or reward programs are immutable.
- Search pools with the mint on either side and after launch-platform migration. Identify exact pool program, vaults, LP/position control, withdrawal paths and quote-asset issuer controls. A platform graduation or burned fungible LP balance does not establish that every position or side pool is locked.

## Execution and holder accounting

- Retain raw transaction/message data and metadata; resolve versioned-message address lookup tables/loaded addresses, top-level instructions, inner instructions and account indices. Check parsed output against raw data for material claims. Missing inner instructions or balances are coverage limits, not zero flow.
- Identify events by cluster, signature and instruction location (including inner/event ordinal as required by the decoder); retain slot/block evidence and decode revision. EVM log-index keys do not transfer automatically.
- Reconcile pre/post token balances with instruction flows, token-account ownership, SOL fees, rent deposits/refunds, wrapped SOL creation/closure and transfer fees. Use integer raw amounts, not rounded UI amounts. Failed transactions do not establish completed swaps even if logs describe attempted work.
- Separate pool movement, router hops, payer input, final recipient output and economic beneficiary. Do not sum each conversion in a multi-hop buyback as separate spending. Prove purchases, burns and distributions independently; a treasury purchase is not holder revenue, and a transfer to a labeled dead address is not a demonstrated supply burn.
- `getTokenLargestAccounts` returns a largest-account sample, not a full holder census. Aggregate accounts by resolved owner only within stated coverage; classify custody/pool vaults separately. Even a complete owner grouping does not prove common beneficial ownership. Do not report an exact total holder count from a top-account sample.
- For exit quotes, retain exact mint/route, amount, output asset, context/time, fees and extension support. Quotes and simulation are not realized exits. Never sign or submit a real trade for diligence.

## Manual packet acceptance

Verify exact mint/cluster across requested, queried and reported identities; hash retained source bytes; link findings to requests, account/transaction decoding and context. Record unknown authorities, unsupported versions/extensions, incomplete market/holder discovery and failed/truncated ranges per claim. Mark validation as manual and chain-specific: the bundled EVM validator does not validate this packet.

When using Jeetstreet, discover actual Solana capture/decoder coverage for the target and period. A Robinhood replay engine or a generic archive signature is not proof of Solana coverage. Use `research-evidence-manifest.md` for the handoff without coercing the mint into an EVM schema.

## Primary references

- [RPC account context](https://solana.com/docs/rpc/http/getaccountinfo) and [largest token accounts](https://solana.com/docs/rpc/http/gettokenlargestaccounts)
- [Transaction JSON structures](https://solana.com/docs/rpc/json-structures)
- [Token authority operations](https://solana.com/docs/tokens/basics) and [Token-2022 extensions](https://solana.com/docs/tokens/extensions)
- [Permanent delegate](https://solana.com/docs/tokens/extensions/permanent-delegate)
