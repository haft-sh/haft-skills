# Output Standard

## Verdict Structure

Lead with a direct, conditional verdict answering the user's actual question.

Rate these separately:
- Token controls
- Canonical LP-principal custody
- Side-pool removal risk
- Sellability and exit depth
- Current concentration
- Historical launch integrity
- Admin, treasury, and reward custody
- Reward accounting and liveness
- Utility and redemption rights
- External dependencies
- Development and disclosure

For broad reports, include severity, likelihood, confidence, coverage, and time basis. Do not average a critical finding away with unrelated positive checks.

## Bounded Language

Use bounded language such as:
- "No current executable removal path found at the pinned block."
- "Sellable at the tested sizes under the quoted state."
- "Unknown because historical state was unavailable."
- "NO-GO under the stated requirement for rug resistance."

Do not issue an unconditional "safe" verdict or imply a favorable review predicts returns.

## Explanation Requirements

Explain the main reasons, strongest contrary evidence, unresolved questions, and specific evidence that could change the conclusion. Recommendations must address observed deficiencies.

## Finding-to-Evidence Ledger

Maintain a finding-to-evidence ledger with:
- Finding ID
- Exact proposition
- Chain
- Exact contract address or case-sensitive mint
- EVM pin/transaction, or Solana commitment/context slots and transaction signature
- Artifact/query
- Decoding basis
- Evidence type
- Confidence
- Alternatives
- Coverage
- Conditions that would make the claim stale

For discovery claims, record the search universe, block ranges or pagination, inclusion rules, and materiality thresholds.

For indexed/research-derived tables, bind the selection, decoder revision, quote unit, denominator and artifact IDs using `research-evidence-manifest.md`. Distinguish manual Solana evidence review from the bundled EVM packet validator, and scientific qualification from editorial approval or permission to publish.
