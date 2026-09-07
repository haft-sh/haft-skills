# Validation

## Target-Integrity Manifest

For broad reports, maintain a target-integrity manifest and validate it. The manifest should check:

- **Requested, queried, and reported chain/address consistency** — every artifact must bind to the same target
- **Metadata consistency** — name, symbol, decimals, supply must match across all references; explicit unresolved states flagged
- **Block pins against captured headers** — block number, hash, timestamp must match RPC
- **Chain, role, provenance, and runtime status for material scope addresses** — every contract referenced must be identified
- **Report-source identity against the manifest** — no unknown sources
- **No-real-signing/no-broadcast declarations and any fork restrictions** — safety constraints documented

## Rejection Criteria

Reject placeholder pins, malformed addresses, conflicting identities, missing evidence, and inconsistent scope chains.

Explain that passing validates internal consistency, not RPC honesty, discovery completeness, or protocol safety.

## Synthetic Test Cases

Run meaningful validation on helper scripts. Include synthetic cases demonstrating rejection of:

1. A same-symbol token substituted from another chain
2. A report referring to the wrong target
3. A fake or inconsistent block pin
4. An unknown check presented as a pass

## Behavioral Examples

Include behavioral examples covering:

- Locked canonical liquidity with removable side liquidity
- Fixed supply with severe holder-sized exit degradation
- An upgradeable reward layer surrounding an immutable token
- Launch wallets selling and rebuying for new recipients
- A vault holding synthetic claims without a proven underlying exit
- An RPC failure that must remain a coverage limitation

Do not fabricate live findings to test the skill.
