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

## Offline evidence-packet validator

`scripts/validate_report.py` uses only Python 3.9+ standard-library modules. It makes no network/database calls and never signs. Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_validate_report.py
python3 scripts/validate_report.py <manifest.json>
```

The input is a **new, explicit evidence schema**, not an arbitrary prose report or a legacy self-attested `manifest_match` flag. Preserve old reports unchanged; adapt them in a separate manifest only using evidence actually retained. If a provider does not support the required hash-selected capture, record the limitation and use the manual validation checklist; do not manufacture a request/response or silently weaken the binding.

Required top-level fields for `schema_version: "evm-diligence-evidence-v1"`:

| Field | Required shape and checks |
|---|---|
| `target` | `requested`, `queried`, `reported`, each `{chain_id: positive integer, address: EVM address}`; identities must match |
| `metadata` | `observed` and `reported` each contain `name`, `symbol`, `decimals`, `supply`; `unresolved` maps unresolved field names to nonempty reasons |
| `pin` | `chain_id`, decimal integer `number`, nonzero 32-byte `hash`, integer UNIX-seconds `timestamp`, `chain_source` and `header_source` source IDs |
| `sources` | Nonempty list of unique `{id, path, bytes, sha256}`; lowercase SHA-256 of actual file bytes, paths relative to the manifest directory |
| `scope_addresses` | Nonempty list of `{chain_id, address, role, provenance_sources, runtime_status}`, including the target |
| `findings` | Nonempty list of `{id, claim, source_ids, confidence, coverage, assessment}` |
| `safety` | `no_real_signing: true`, `no_broadcast: true`, `fork_mode: "none"` or `"isolated_unsigned"` |

Metadata name/symbol are nonempty strings, decimals an integer 0–255, supply a nonnegative **raw-unit decimal string**, not a float. A missing value must be null with an explicit unresolved reason; discrepancies require such a reason too. The validator compares the manifest's metadata copies, not arbitrary prose or decoded getter truth.

RPC sources are captured JSON envelopes containing `request: {id, method, params}` and `response: {id, result}`; IDs must match and error responses are rejected. Keep actual raw bytes, adding no fabricated request context. Capture transport metadata privately as needed without secrets.

- `chain_source`: actual `eth_chainId` request with empty params and hex quantity result.
- `header_source`: actual `eth_getBlockByHash` with `[pin.hash, false]`; response header number/hash/timestamp must match the pin.
- Scope `runtime_status` is `code`, `no_code` or `unresolved`. Resolved states require `runtime_source` naming an `eth_getCode` capture for that exact address at `{blockHash: pin.hash, requireCanonical: true}`. Unresolved states need a nonempty `reason`. Nonempty code does not classify custody or resolve a proxy.

All scope entries belong to this manifest's chain. For cross-chain dependencies, use separately validated chain-specific manifests and explicit linking evidence; do not coerce bridge legs onto the target chain.

Finding confidence is `high|medium|low`, coverage `complete|partial|unknown`, assessment `pass|risk|unresolved`. “Pass” requires complete coverage **for the precise bounded claim**, not all chain history. Unknown or partial coverage must not be converted into a pass. Each finding/provenance reference must resolve to hashed source bytes.

The validator rejects duplicate JSON keys/source IDs, changed/missing files, path/symlink escapes, malformed identities, response mismatches and unbound runtime calls. Limits are 4 MiB per parsed JSON, 64 MiB per artifact and 1 GiB total source bytes; subdivide large evidence into bounded artifacts or retain separate manual coverage rather than silently ignoring it. Keep the bundle immutable during validation.

Passing verifies declared identities, selected captured bytes, header/runtime-call binding and structural consistency. It does **not** recompute a consensus block hash, authenticate the provider, decode arbitrary ABI/source, inspect report prose, prove log completeness, establish ownership, audit exploit safety, or authorize publishing private evidence. Those remain investigative/manual checks.

## Synthetic Test Cases

Run meaningful validation on helper scripts. Include synthetic cases demonstrating rejection of:

1. A same-symbol token substituted from another chain
2. A report referring to the wrong target
3. A fake or inconsistent block pin
4. An unknown check presented as a pass
5. Matching counts with different event identities, and matching identities with reversed swap sides (behavioral review)
6. Hashed but inconsistent RPC requests/responses, metadata conflicts, altered bytes, unsafe paths and missing sources (automated)

The included synthetic tests exercise the actual CLI and validator failure paths without live chain reads. The event-reconciliation behavior remains a review obligation, not a claim that this manifest validator reconciles databases.

## Behavioral Examples

Include behavioral examples covering:

- Locked canonical liquidity with removable side liquidity
- Fixed supply with severe holder-sized exit degradation
- An upgradeable reward layer surrounding an immutable token
- Launch wallets selling and rebuying for new recipients
- A vault holding synthetic claims without a proven underlying exit
- An RPC failure that must remain a coverage limitation

Do not fabricate live findings to test the skill.
