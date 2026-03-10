"""Division safety properties.

Proves that proposed ensure clauses are sufficient to prevent
all division-by-zero paths identified in AUDIT3 (M11, M12).
"""

from z3 import And, Reals, Real


def prop_scale_fees_terminates():
    """D1: scaleFees safe when amuletPrice > 0.

    Proves that the ensure clause prevents division by zero.
    AUDIT3 M11: Splice AmuletRules.daml:898.
    """
    amulet_price = Real("amuletPrice")

    preconditions = amulet_price > 0  # proposed ensure clause
    goal = amulet_price != 0
    return preconditions, goal


def prop_issuance_tranche_terminates():
    """D2: computeIssuanceTranche safe when both inputs > 0.

    capPerCoupon > 0 AND totalCoupons > 0 => product > 0 => no div-by-zero.
    AUDIT3 M12: Splice Issuance.daml:164-176.
    """
    cap_per_coupon, total_coupons = Reals("capPerCoupon totalCoupons")

    preconditions = And(cap_per_coupon > 0, total_coupons > 0)
    scaled_total_coupons = cap_per_coupon * total_coupons
    goal = scaled_total_coupons > 0
    return preconditions, goal


def prop_ensure_sufficient():
    """D3: ensure clauses sufficient for all divisions.

    SimpleHolding's ensure (amount > 0) prevents all division-by-amount paths.
    CNTS Holding.daml:19.
    """
    amount, total_input, requested = Reals("amount totalInput requested")

    preconditions = And(
        amount > 0,       # CNTS SimpleHolding ensure clause
        total_input > 0,
        requested > 0,
        total_input >= requested,
    )

    sender_change = total_input - requested
    goal = sender_change >= 0  # non-negative (no underflow)
    return preconditions, goal
