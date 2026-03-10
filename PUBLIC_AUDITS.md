# daml-verify — Public Audit Results

Formal verification of DAML contract invariants using the Z3 SMT solver. Properties are proved to hold **for all possible inputs** under stated preconditions. All findings are **NOT VALIDATED** by the respective project teams — they are tool output only.

**Date:** 2026-03-04
**Tool version:** daml-verify v0.1.0 (Python 3.10+, z3-solver >= 4.12)
**Properties:** 14 (C1-C3 Conservation, D1-D3 Division, T1-T3 Temporal, V1-V5 Vault)

---

## Table of Contents

1. [Results Summary](#1-results-summary)
2. [Property Definitions](#2-property-definitions)
3. [Coverage by Project](#3-coverage-by-project)
4. [Splice Findings (Detailed)](#4-splice-findings-detailed)
5. [Canton-Vault Findings](#5-canton-vault-findings)
6. [Canton-ERC20 Applicability](#6-canton-erc20-applicability)
7. [daml-finance Applicability](#7-daml-finance-applicability)
8. [Canton-DEX-Platform Applicability](#8-canton-dex-platform-applicability)
9. [Key Precondition Dependencies](#9-key-precondition-dependencies)
10. [Model Corrections During Validation](#10-model-corrections-during-validation)

---

## 1. Results Summary

```
daml-verify: 14 properties, 14 proved, 0 disproved

  [PROVED] C1: conservation total
  [PROVED] C2: receiver amount
  [PROVED] C3: sender change
  [PROVED] D1: scaleFees safety
  [PROVED] D2: issuance safety
  [PROVED] D3: ensure sufficient
  [PROVED] T1: transfer temporal
  [PROVED] T2: allocation temporal
  [PROVED] T3: lock expiry
  [PROVED] V1: fee monotonicity
  [PROVED] V2: collateral ratio guard
  [PROVED] V3: liquidation conservation
  [PROVED] V4: division safety (ratio)
  [PROVED] V5: division safety (seize)
```

---

## 2. Property Definitions

| ID | Category | What It Proves |
|----|----------|----------------|
| C1 | Conservation | Total output equals total input across transfer paths |
| C2 | Conservation | Receiver gets exactly the requested amount |
| C3 | Conservation | Sender change equals `totalInput - requested` |
| D1 | Division | No division-by-zero when `amuletPrice > 0` in `scaleFees` |
| D2 | Division | No division-by-zero when `capPerCoupon > 0` and `totalCoupons > 0` in issuance |
| D3 | Division | `ensure amount > 0.0` guards all division sites |
| T1 | Temporal | `requestedAt < executeBefore` follows from preconditions |
| T2 | Temporal | Full temporal chain `requestedAt <= now < allocateBefore <= settleBefore` is consistent |
| T3 | Temporal | Lock is always active at creation time |
| V1 | Vault | Fees never decrease (monotonicity) |
| V2 | Vault | Collateral ratio checked before operations |
| V3 | Vault | Liquidation preserves total value |
| V4 | Vault | Ratio computation safe under preconditions |
| V5 | Vault | Seizure computation safe under preconditions |

---

## 3. Coverage by Project

| Property | canton-dex-platform | canton-erc20 | canton-vault | daml-finance | splice |
|----------|:-------------------:|:------------:|:------------:|:------------:|:------:|
| C1-C3 Conservation | Partial | Yes | Yes | Yes | Yes |
| D1-D3 Division | — | Yes | Yes | Partial | Yes |
| T1-T3 Temporal | — | Yes | — | — | Yes |
| V1-V5 Vault | — | — | Yes | — | — |

**Interpretation:**
- **Conservation (C1-C3):** Models the CIP-056 transfer factory logic. Applies to canton-erc20, canton-vault, and splice (all implement transfer factories). Partially applies to canton-dex-platform (DvP settlement pattern).
- **Division (D1-D3):** Proves fee computations and issuance calculations are safe under positive denominator preconditions. Applies to splice (amuletPrice), canton-erc20 (CIP-056), canton-vault (share price). Partial for daml-finance (ContingentClaims DivF is a different computation model).
- **Temporal (T1-T3):** Proves deadline ordering in transfer/allocation workflows. Applies to splice and canton-erc20 (both implement `requestedAt`/`executeBefore` patterns).
- **Vault (V1-V5):** Proves collateralized vault invariants. Specific to canton-vault and canton-stablecoin vault patterns.

---

## 4. Splice Findings (Detailed)

**GitHub:** [hyperledger-labs/splice](https://github.com/hyperledger-labs/splice)
**Commit:** [`6a0dcbba4`](https://github.com/hyperledger-labs/splice/commit/6a0dcbba4bdae0861cd6f5021bfd436c18fd5034)

### D1: scaleFees Division Safety — 6 Unguarded Sites

The `1.0 / openRound.amuletPrice` pattern appears at **6 sites** in AmuletRules.daml:

| Line | Context | Expression |
|------|---------|------------|
| 230 | `AmuletRules_BuyMemberTraffic` | `scaleFees (1.0 / openRound.amuletPrice) ...` |
| 722 | `AmuletRules_ConvertFeaturedAppActivityMarkers` | `amountUsd / round.amuletPrice` |
| 898 | `summarizeAndValidateContext` | `scaleFees (1.0 / openRound.amuletPrice) ...` |
| 1246 | `transferConfigAmuletFromOpenRound` | `scaleFees (1.0 / openRound.amuletPrice) ...` |
| 1265 | `computeSynchronizerFees` | Uses `contextMiningRound.amuletPrice` |
| 1681 | `computeTransferPreapprovalFee` | Uses `contextMiningRound.amuletPrice` |

**Root cause:** `OpenMiningRound` (Round.daml:20) ensure clause validates only `isDefinedRound round.number` (i.e., `round.number >= 0`). There is **no validation that `amuletPrice > 0`**. The field is set by DSO-controlled choices and accepts any `Decimal`, including `0.0`.

**Proof:** D1 proves that if `amuletPrice > 0` is added as a precondition, then `scaleFees(1.0 / amuletPrice, config)` never divides by zero. Z3: `amuletPrice > 0 AND NOT (1.0 / amuletPrice is defined)` returns **UNSAT**.

**Recommended fix:** Add `ensure amuletPrice > 0.0` to the `OpenMiningRound` template.

### D2: computeIssuanceTranche — capPerCoupon = 0 Permits Division by Zero

**The code** (Issuance.daml:164-185):

```daml
computeIssuanceTranche rewardsToIssue capPerCoupon totalCoupons
  | totalCoupons <= 0.0 = ...  -- early return, safe
  | otherwise =
      let scaledTotalCoupons = capPerCoupon * totalCoupons
          cappedRewardsToIssue = min rewardsToIssue scaledTotalCoupons
          issuancePerCoupon = (cappedRewardsToIssue * capPerCoupon) / scaledTotalCoupons
```

The guard only protects `totalCoupons <= 0`. `validIssuanceConfig` requires caps `>= 0.0` (non-negative), **not** `> 0.0`. So `capPerCoupon = 0.0` is permitted → `scaledTotalCoupons = 0.0` → division by zero.

**Proof:** D2 proves that if `capPerCoupon > 0` is added as a precondition, the division is safe. Z3 confirms: `capPerCoupon > 0 AND totalCoupons > 0 → scaledTotalCoupons > 0`.

**Recommended fix:** Change `validIssuanceConfig` to require `capPerCoupon > 0.0`, or guard: `if capPerCoupon == 0.0 then 0.0 else ...`

### Additional: Issuance.daml:139 Division by amuletPrice

```daml
(getValidatorFaucetCap config / amuletPrice)
```

Same class as D1 — divides by `amuletPrice` without a prior `> 0` guard. Would be fixed by the same `ensure amuletPrice > 0.0` on `OpenMiningRound`.

### D3: ensure sufficient

D3 proves that `ensure amount > 0.0` on the `SimpleHolding` template (from the Canton Token Standard) is sufficient to prevent all division-by-zero paths in the standard transfer/allocation logic.

### T1-T3: Temporal Properties

All three temporal properties proved for splice's transfer/allocation workflow:
- **T1:** `requestedAt < executeBefore` is guaranteed by the validation pipeline
- **T2:** Full chain `requestedAt <= now < allocateBefore <= settleBefore` is consistent
- **T3:** Lock `expiresAt > now` at creation time

### Safe Division Sites (Confirmed)

| Location | Divisor | Guard | Status |
|----------|---------|-------|--------|
| Issuance.daml:115 | `totalSvRewardWeight` | `== 0` early return | Safe |
| Issuance.daml:125 | `tickDuration` (microseconds) | `validAmuletConfig` requires `tickDuration > days 0` | Safe |
| Fees.daml:171 | `tickDuration` (microseconds) | Same config validation | Safe |

---

## 5. Canton-Vault Findings

**GitHub:** [ted-gc/canton-vault](https://github.com/ted-gc/canton-vault)
**Commit:** [`bb51d2c`](https://github.com/ted-gc/canton-vault/commit/bb51d2c5df89d506dc38af8a3760029013c1ffe7)

### V1-V5: Vault Properties

All 5 vault properties **PROVED**:

| Property | What It Proves | Relevance |
|----------|---------------|-----------|
| V1: fee monotonicity | Management fees never decrease | Fee accrual is additive |
| V2: collateral ratio guard | Collateral ratio checked before mint/redeem | Prevents undercollateralized operations |
| V3: liquidation conservation | Liquidation preserves total value | Seized assets + remaining = original |
| V4: division safety (ratio) | Share price computation safe | Under `totalShares > 0` precondition |
| V5: division safety (seize) | Seizure computation safe | Under `totalAssets > 0` precondition |

**Key insight:** V4 and V5 prove safety under `totalShares > 0` and `totalAssets > 0` preconditions respectively. However, canton-vault's actual guards check `totalShares == 0` at the function level while dividing by `totalAssets` — a mismatched guard pattern. If `totalAssets == 0` while `totalShares > 0` (vault loss scenario), V4's precondition is violated and division-by-zero occurs.

---

## 6. Canton-ERC20 Applicability

**GitHub:** [ChainSafe/canton-erc20](https://github.com/ChainSafe/canton-erc20)
**Commit:** [`e98a7db`](https://github.com/ChainSafe/canton-erc20/commit/e98a7db5b9e0bdb96331cac72052a39134a84dfc)

Canton-erc20 implements CIP-056 token interfaces. Conservation (C1-C3), Division (D1-D3), and Temporal (T1-T3) properties apply to its transfer factory logic. Key note: `CIP56Holding` template is missing `ensure amount > 0.0` — the D3 proof assumes this ensure clause exists. Without it, some division paths may not be guarded.

---

## 7. daml-finance Applicability

**GitHub:** [digital-asset/daml-finance](https://github.com/digital-asset/daml-finance)
**Commit:** [`155f931b`](https://github.com/digital-asset/daml-finance/commit/155f931b6ebe7d3662fd72788cb17f0bfb5a7ba6)

Conservation (C1-C3) properties apply to daml-finance's Settlement V4 module. Division (D1-D3) partially applies — the ContingentClaims `DivF` operator uses a different computation model (expression tree evaluation) not covered by daml-verify's current symbolic models.

---

## 8. Canton-DEX-Platform Applicability

**GitHub:** [0xalberto/canton-dex-platform](https://github.com/0xalberto/canton-dex-platform)
**Commit:** [`e9f01be`](https://github.com/0xalberto/canton-dex-platform/commit/e9f01be60369b9978dcf0e60aa5fa2ce02967a3f)

Conservation (C1-C3) partially applies to the DvP settlement pattern. The settlement uses opaque Text references rather than CIP-056 holdings, so the direct UTXO conservation model has limited applicability. The 4-party signatory pattern provides different guarantees (all parties must agree) rather than the algebraic conservation guaranteed by C1-C3.

---

## 9. Key Precondition Dependencies

All proofs hold **under stated preconditions**. These preconditions must be enforced by template `ensure` clauses:

| Precondition | Required By | Enforced? | Project |
|-------------|-------------|-----------|---------|
| `amuletPrice > 0.0` | D1 | **NOT enforced** on `OpenMiningRound` | splice |
| `capPerCoupon > 0.0` | D2 | Enforced as `>= 0.0` (insufficient) | splice |
| `totalCoupons > 0` | D2 | Not enforced (assumed by design) | splice |
| `amount > 0.0` | D3, C1-C3 | Enforced on `SimpleHolding` | splice, canton-vault |
| `amount > 0.0` | D3 | **NOT enforced** on `CIP56Holding` | canton-erc20 |
| `totalShares > 0` | V4 | Partially (function-level guard, not ensure) | canton-vault |
| `totalAssets > 0` | V5 | **NOT enforced** | canton-vault |

---

## 10. Model Corrections During Validation

Two symbolic models were corrected during validation against actual Splice source code:

### chargeSteppedRate (model/fees.py)

**Before:** Misassigned rates to tiers, missing `initialRate` phase.
**After:** Corrected to 3-phase model matching Fees.daml:87-108:
1. `initialRate` applies to amounts below first step threshold
2. Each step's rate applies to amounts above that threshold
3. After all steps exhausted, the last rate extends infinitely

No division occurs in `chargeSteppedRate`. It is purely multiplicative.

### computeIssuanceTranche (model/fees.py)

**Before:** Simplified to `totalIssuance / scaledTotalCoupons`.
**After:** Corrected to include min-capping and capPerCoupon multiplicand:
```
cappedRewardsToIssue = min(rewardsToIssue, scaledTotalCoupons)
issuancePerCoupon = (cappedRewardsToIssue * capPerCoupon) / scaledTotalCoupons
```

Division safety property (D2) is unaffected — it proves the denominator is positive regardless of numerator structure.

---

*Generated by daml-verify v0.1.0 | Audit date: 2026-03-04*
