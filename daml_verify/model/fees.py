"""Symbolic model of Splice fee computation logic.

Models the fee functions that AUDIT3 found buggy (M11, M12).

Dogfooding (2026-02-20): Models validated against actual Splice source:
  - AmuletRules.daml: 6 division-by-amuletPrice sites (lines 231, 723, 898, 1246, 1265, 1681)
  - Issuance.daml:164-185: computeIssuanceTranche with capping logic
  - Fees.daml:87-108: chargeSteppedRate with initialRate + stepped tiers
"""

from z3 import If, RealVal


def symbolic_scale_fees(fee, amulet_price):
    """Model of scaleFees (Splice AmuletRules.daml:1234-1243).

    Applied at 6 sites in AmuletRules.daml (lines 231, 723, 898, 1246, 1265, 1681).
    All divide by amuletPrice with NO ensure clause on OpenMiningRound.
    OpenMiningRound.ensure only checks round.number >= 0 (Round.daml:33).
    Precondition to prove: amulet_price > 0.
    """
    return fee * (RealVal(1) / amulet_price)


def symbolic_compute_issuance_tranche(rewards_to_issue, cap_per_coupon, total_coupons):
    """Model of computeIssuanceTranche (Splice Issuance.daml:164-185).

    Real code guards totalCoupons <= 0 (early return) but NOT capPerCoupon == 0.
    validIssuanceConfig requires capPerCoupon >= 0 (not > 0), permitting zero.

    Actual formula (in the otherwise branch where totalCoupons > 0):
      scaledTotalCoupons = capPerCoupon * totalCoupons
      cappedRewardsToIssue = min(rewardsToIssue, scaledTotalCoupons)
      issuancePerCoupon = (cappedRewardsToIssue * capPerCoupon) / scaledTotalCoupons
    """
    scaled_total_coupons = cap_per_coupon * total_coupons
    capped_rewards = If(
        rewards_to_issue <= scaled_total_coupons,
        rewards_to_issue,
        scaled_total_coupons,
    )
    return (capped_rewards * cap_per_coupon) / scaled_total_coupons


def _smin(a, b):
    return If(a <= b, a, b)


def _smax(a, b):
    return If(a >= b, a, b)


def symbolic_charge_stepped_rate(initial_rate, steps, amount):
    """Model of chargeSteppedRate (Splice Fees.daml:87-108).

    Real code structure:
      1. Converts absolute thresholds to relative tier widths via fold
      2. goChargeSteppedRate processes tiers starting with initialRate
      3. initialRate applies to amounts BELOW the first step threshold
      4. Each step's rate applies to amounts ABOVE that step's threshold
      5. After all steps exhausted, last rate applies to remainder

    initial_rate: rate for the first tier (before any step boundary)
    steps: list of (absolute_threshold, rate_after_threshold) pairs
    amount: the amount to charge fees on
    """
    # Step 1: Convert absolute thresholds to relative tier widths
    # (mirrors the Haskell fold in chargeSteppedRate)
    step_diffs = []
    total = RealVal(0)
    for step, rate in steps:
        step_diffs.append((step - total, rate))
        total = total + step

    # Step 2: Process tiers starting with initialRate
    remainder = amount
    current_rate = initial_rate
    total_fee = RealVal(0)

    for tier_width, next_rate in step_diffs:
        charged = _smin(_smax(remainder, RealVal(0)), _smax(tier_width, RealVal(0)))
        total_fee = total_fee + charged * current_rate
        remainder = remainder - tier_width
        current_rate = next_rate

    # Step 3: Remainder beyond all steps charged at last rate
    leftover = _smax(remainder, RealVal(0))
    total_fee = total_fee + leftover * current_rate

    return total_fee
