# Token-Scoped Research Evidence Handoff

Use alongside `indexed-chain-evidence.md` when an indexer or public-research track supports a token report. This is an adapter/output contract, not a deployed API or an executable validator. Prefer an existing compatible export; otherwise retain a small JSON or Markdown record from authorized bounded reads. Do not build or deploy infrastructure merely to fill this record.

## Capability preflight and manifest

Record explicit unknowns rather than inventing mandatory evidence:

| Group | Required information for the claims being investigated |
|---|---|
| Target | Requested/observed chain identity and exact contract or mint; metadata/raw units; decision question and requested depth |
| Implementation | Repository commit, decoder/schema revision, relevant deployment revision if known; supported chain/venue/event families; independent semantic-test status |
| Selection | Exact markets including target-as-quote discovery, event families, inclusive ranges, launch/graduation coverage, cohort inclusion/exclusion policy and denominators |
| State/availability | EVM canonical end block/hash or Solana commitment/context slots; retrieval and original observation times; later repair/evidence-availability times |
| Sources | Query and parameters, bounded snapshot identity, exact archived versions/checksums, ancestry/registry dependencies, provider dependencies and private/public classification |
| Reconciliation | Raw/index counts and unique identities; matched/raw-only/index-only/conflicting bodies; direction/amount checks; failed, unqueried and truncated ranges |
| Eligibility | Per finding: supported proposition, source IDs, semantic validity, coverage, point-in-time eligibility, unresolved blockers and staleness conditions |
| Release | Source scientific qualification, report editorial/publication status, exact report/artifact hashes and correction/supersession links |

Keep private locators, SQL credentials and operational identifiers in the private packet. Public reports can cite sanitized artifact identities and bounded methodology; artifact hashing does not grant publication authority.

## Claim-level admission

Avoid one global PASS. An exact receipt can establish a particular transfer while the same packet remains ineligible for launch-wide concentration, total-volume or predictive claims. Bind each derived table to its selection/query, decoder revision, quote denomination, denominator and source artifacts. Separate missing outcomes and censored observations from observed failures; never drop them silently from a success-rate denominator.

Research adapter support is chain-specific. Inspect schema literals, address validators, event identities and program/venue coverage. Reuse provenance and qualification standards across chains, but require a chain-native decoder and state-context model. Existing Solana ingestion elsewhere in a repository does not prove coverage of the target under review.

## Semantic replay and corrections

Matching hashes prove reproducibility under a chosen decoder, not economic correctness. Expected fixture outputs must not be calculated solely by that same decoder. For material direction/amount claims, test real retained successful executions against independently derived signed amounts and recipient balance flows, covering applicable currency orders and both directions.

If a corrected decoder disagrees with frozen canonical hashes, preserve the old raw bytes and derived artifacts as qualified legacy evidence. Produce a successor with new decoder/hash lineage, affected-consumer inventory, before/after reconciliation and updated availability/eligibility. Do not disable mismatch checks, silently replace old hashes or keep a known-wrong decoder merely to make current evidence pass.

For retrospective launch accounting, a verified later discovery within the same transaction may explain earlier mint/transfer instructions or logs. Require exact transaction identity and verified ancestry; propagate the later availability. Do not borrow discovery from a later transaction, infer pre-discovery trading knowledge, or equate reconstruction with repaired database coverage.

## Operational and scientific boundaries

Verify producer/consumer composition, not only isolated unit tests. For archive workflows, check that final-result objects coexist with recovery inventory rules and bounded limits; useful scenarios include run → retain → recover and incomplete-result/readback ambiguity. A durable result is not proof of worker quiescence, settled costs, released reservations or complete enumeration. These checks guide evidence acceptance; diligence does not authorize operational repairs.

Distinguish code merged, code deployed, history materialized, bounded replay verified, study qualified and publication approved. Current PR status must be rechecked, not baked into the skill. Exportable drafts are not automatically scientifically qualified or publicly releasable.

Qualified cohort benchmarks can later inform descriptive graduation, survival, concentration and exit distributions. Before applying them to an investment decision, verify the full inclusion universe, failures/censoring, outcome maturity, point-in-time availability, quote units, fees and executable-size assumptions. Provenance milestones alone supply neither success probabilities nor an investment edge.
