# Token Due Diligence Report: BLEND (BlendPad)

**Address:** `0x875bd2fdb280740bf035026057d31c7c33c916ec`  
**Chain:** Robinhood Chain (L2)  
**Symbol:** BLEND  
**Name:** BlendPad  
**Decimals:** 18  
**Total Supply:** 1,000,000,000 BLEND  

---

## Verdict

**UNRESOLVED — Identity ambiguity and provenance limitations.**

The token at this address is **NOT** the native Fluent Network BLEND token. It is a *BlendPad* token deployed on Robinhood Chain, with significant attribution and operational risks that cannot be resolved without additional evidence.

---

## Key Findings

### A. Token Identity & Non-Authenticity
- **Claim:** "This is the official BLEND token"
- **Evidence:** This address deploys "BlendPad (BLEND)" — a **community/token project**, NOT Fluent Network's native token
- **Critical distinction:** Fluent Network's official BLEND token lives at `0xd8a271974e8edae9d7b58e3370dc1669427503f4` on Ethereum
- **Robinhood Chain has no official native token** per [Robinhood's own statements](https://crypto.news/is-there-a-robinhood-chain-token/) — BlendPad is a third-party token leveraging the name

### B. Supply Concentration (High)
- **Top 100 holders control 99.76%** of supply (2,128 holders)
- **Top 5 holders control 90.34%** of total supply
- **Whale concentration:** 98.51% of market cap held by 0.22% of holders

### C. Liquidity & Trading Activity
- **Transfers: 0** — No recorded transfers on-chain
- **Holders: 2,128** — Many addresses may be dust or unused
- **No trading pairs detected** — Cannot trace market impact

### D. Contract Controls (Unverified)
- No source code verified on Blockscout
- Creator: `0x3711ceA4feaDE896C913C68F01Eda97Cb06D1A42` (EOA)
- **Missing:** Proxy checks, upgrade authority verification, role assignments
- **Cannot verify:** Mint, burn, admin, or upgrade permissions without source

### E. Ponzinomics / Rug Pull Risk
- **Total supply: 1B tokens** — Fixed supply claimed, but mint function cannot be ruled out without verified source
- **Zero transfers** — Could indicate: (1) brand-new launch, (2) honeypot trap, or (3) no liquidity
- **Creator EOA:** No evidence of multisig or timelock governance

### F. Chain Context
- **Token deployed on:** Robinhood Chain (permissionless L2 launched July 1, 2026)
- **Fee token used:** WETH (`0x0Bd7D308f8E1639FAb988df18A801f41EAcAD73`)
- **No official token:** Robinhood explicitly states no native token, no airdrop, no snapshot exists

---

## Finding-to-Evidence Ledger

| ID | Proposition | Chain | Address | Pin | Artifact | Decoding Basis | Confidence | Coverage |
|----|-------------|-------|---------|-----|----------|----------------|------------|----------|
| F-001 | Token at `0x875...` is BlendPad, not Fluent BLEND | Robinhood Chain | 0x875bd2f...916ec | Blockscout snapshot | Blockscout token page | UI extraction | HIGH | Unknown |
| F-002 | Zero transfers indicates no trading activity | Robinhood Chain | 0x875bd2f...916ec | Blockscout snapshot | Token transfers tab | UI extraction | HIGH | Complete |
| F-003 | Robinhood Chain has no official token | External | N/A | 2026 docs | crypto.news article | Published source | HIGH | Complete |

---

## Unresolved Questions

1. **Source code verification:** Cannot verify mint/burn/control roles without source
2. **Creator identity:** EOA `0x37...1A42` — unknown entity
3. **Liquidity status:** No DEX pairs discovered; no execution evidence for exit
4. **Proxy patterns:** Cannot check for upgradeable contract patterns
5. **Whitelist/blacklist:** Unknown if transfer restrictions exist

---

## Recommendation

**DO NOT USE THIS TOKEN AS A substitute for Fluent Network's BLEND.**

If seeking Fluent Network's token, use the verified Ethereum address:
- **Ethereum:** `0xd8a271974e8edae9d7b58e3370dc1669427503f4`

The BlendPad token at the provided address appears to be a third-party token with extremely high whale concentration, zero observable trading activity, and no verified source code. This profile matches many "scam" token characteristics.

---

## Provenance

- **Model:** GLM-5.3-flash (Zhipu AI)
- **Runtime:** Hermes Agent on EC2 host (Linux 7.0.0-1011-aws)
- **Research methods:** Web extraction from Blockscout, CoinGecko, Robinhood docs, crypto.news
- **Verification:** Read-only investigation — no RPC calls, no signing, no broadcasts

---

## References

1. [Robinhood Chain Blockscout - BlendPad (BLEND)](https://robinhoodchain.blockscout.com/token/0x875BD2fDb280740BF035026057D31c7c33C916eC)
2. [Fluent Network BLEND Token - Etherscan](https://etherscan.io/token/0xd8a271974e8edae9d7b58e3370dc1669427503f4)
3. [Robinhood Chain Token Contracts](https://docs.robinhood.com/chain/contracts/)
4. [Crypto News: "Is there a Robinhood Chain token?"](https://crypto.news/is-there-a-robinhood-chain-token/)