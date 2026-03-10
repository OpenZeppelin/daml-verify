"""SBV-equivalent prover: Z3 integration for proving/disproving properties."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from z3 import Solver, Not, unsat, sat

from daml_verify.props.conservation import (
    prop_conservation_total,
    prop_conservation_receiver,
    prop_conservation_change,
)
from daml_verify.props.division import (
    prop_scale_fees_terminates,
    prop_issuance_tranche_terminates,
    prop_ensure_sufficient,
)
from daml_verify.props.temporal import (
    prop_transfer_temporal,
    prop_allocation_temporal,
    prop_lock_expiry_consistency,
)
from daml_verify.props.vault import (
    prop_fee_monotonicity,
    prop_collateral_ratio_guard,
    prop_liquidation_conservation,
    prop_division_safety_ratio,
    prop_division_safety_seize,
)


class ProofStatus(Enum):
    PROVED = "proved"
    DISPROVED = "disproved"
    UNKNOWN = "unknown"


@dataclass
class ProofResult:
    name: str
    status: ProofStatus
    counterexample: Optional[str] = None


def run_proof(name, preconditions, goal):
    """Prove that preconditions => goal holds for all inputs.

    Checks satisfiability of (preconditions AND NOT goal).
    If unsat: property proved for all inputs.
    If sat: counterexample found.
    """
    s = Solver()
    s.add(preconditions)
    s.add(Not(goal))
    result = s.check()

    if result == unsat:
        return ProofResult(name, ProofStatus.PROVED)
    elif result == sat:
        return ProofResult(name, ProofStatus.DISPROVED, str(s.model()))
    else:
        return ProofResult(name, ProofStatus.UNKNOWN, str(result))


# All 9 properties with their names and constructor functions.
ALL_PROPERTIES = [
    ("C1: conservation total", prop_conservation_total),
    ("C2: receiver amount", prop_conservation_receiver),
    ("C3: sender change", prop_conservation_change),
    ("D1: scaleFees safety", prop_scale_fees_terminates),
    ("D2: issuance safety", prop_issuance_tranche_terminates),
    ("D3: ensure sufficient", prop_ensure_sufficient),
    ("T1: transfer temporal", prop_transfer_temporal),
    ("T2: allocation temporal", prop_allocation_temporal),
    ("T3: lock expiry", prop_lock_expiry_consistency),
    ("V1: fee monotonicity", prop_fee_monotonicity),
    ("V2: collateral ratio guard", prop_collateral_ratio_guard),
    ("V3: liquidation conservation", prop_liquidation_conservation),
    ("V4: division safety (ratio)", prop_division_safety_ratio),
    ("V5: division safety (seize)", prop_division_safety_seize),
]


def run_all_properties():
    """Run all 14 properties and collect results."""
    results = []
    for name, prop_fn in ALL_PROPERTIES:
        preconditions, goal = prop_fn()
        results.append(run_proof(name, preconditions, goal))
    return results
