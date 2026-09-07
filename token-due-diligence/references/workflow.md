# Efficient Workflow

## Target Packet

Start with one target packet containing:
- Requested and observed chain/address
- Name, symbol, decimals, supply
- EVM block pin/header, or Solana genesis identity, commitment and response context slots
- EVM runtime/proxy identity, or Solana token-program ownership and relevant authority/program identities
- Deployment or launch transaction when available
- Candidate pools and related contracts
- User's decision question, scope, materiality rules, and known limitations

## Architecture Pass

Make a cheap architecture pass identifying every contract or key that can change balances, restrict transfers, remove principal, upgrade behavior, collect fees, allocate rewards, or enforce claimed utility.

## Batching and Caching

Batch independent reads and cache by chain, exact target, query and state context (EVM block hash; Solana commitment and returned context slot). Deduplicate identical EVM runtimes by code hash. Do not merge independently timed Solana reads into a fictional common snapshot.

When a user supplies an indexer/research project, use the optional adapter in `indexed-chain-evidence.md` before relying on derived data. Reuse exact archived bytes and verified ancestry, impose query/read budgets, and reconcile bounded raw/index identities before computing metrics. Distinguish local source, deployed code and in-flight research gates.

## Parallel Agents

If authorized parallel agents are available, give each a bounded lane and the same frozen target packet. Require evidence rows, findings, and unresolved questions rather than separate reports. The skill must also work sequentially.

## Prioritization

Prioritize checks that can change the conclusion. Do not apply monetary materiality thresholds to discovery of mint, upgrade, seizure, transfer restriction, arbitrary-call, or LP-removal authority.
