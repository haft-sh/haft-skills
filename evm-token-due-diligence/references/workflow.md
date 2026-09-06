# Efficient Workflow

## Target Packet

Start with one target packet containing:
- Requested and observed chain/address
- Name, symbol, decimals, supply
- Block pin and captured header
- Runtime hash and proxy/implementation information
- Deployment or launch transaction when available
- Candidate pools and related contracts
- User's decision question, scope, materiality rules, and known limitations

## Architecture Pass

Make a cheap architecture pass identifying every contract or key that can change balances, restrict transfers, remove principal, upgrade behavior, collect fees, allocate rewards, or enforce claimed utility.

## Batching and Caching

Batch independent reads, cache responses by chain/address/block/query, and deduplicate identical runtimes by code hash.

## Parallel Agents

If authorized parallel agents are available, give each a bounded lane and the same frozen target packet. Require evidence rows, findings, and unresolved questions rather than separate reports. The skill must also work sequentially.

## Prioritization

Prioritize checks that can change the conclusion. Do not apply monetary materiality thresholds to discovery of mint, upgrade, seizure, transfer restriction, arbitrary-call, or LP-removal authority.
