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
from daml_verify.props.admin import (
    prop_capability_admin_gate,
    prop_capability_assignee_gate,
    prop_capability_role_gate,
    prop_scope_least_privilege,
    prop_scope_completeness,
    prop_mint_allowance_decrement,
    prop_mint_allowance_conservation,
    prop_pause_blocks_origination,
    prop_grant_requires_role_admin,
    prop_role_admin_grant_completeness,
    prop_no_privilege_escalation,
    prop_renounce_self_only,
    prop_timelock_not_bypassable,
    prop_freeze_blocks_origination,
    prop_freeze_gate_characterization,
    prop_admin_never_freezable,
    prop_freeze_change_non_idempotent,
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


# All properties with their names and constructor functions.
# Prefixes: C conservation · D division · T temporal · V vault · A admin layer.
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
    ("A1: capability admin gate", prop_capability_admin_gate),
    ("A2: capability assignee gate", prop_capability_assignee_gate),
    ("A3: capability role gate", prop_capability_role_gate),
    ("A4: scope least privilege", prop_scope_least_privilege),
    ("A5: scope completeness", prop_scope_completeness),
    ("A6: mint allowance decrement", prop_mint_allowance_decrement),
    ("A7: mint allowance conservation", prop_mint_allowance_conservation),
    ("A8: pause blocks origination", prop_pause_blocks_origination),
    ("A9: grant requires role admin", prop_grant_requires_role_admin),
    ("A10: role-admin grant completeness", prop_role_admin_grant_completeness),
    ("A11: no privilege escalation", prop_no_privilege_escalation),
    ("A12: renounce self-only", prop_renounce_self_only),
    ("A13: timelock not bypassable", prop_timelock_not_bypassable),
    ("A14: freeze blocks origination", prop_freeze_blocks_origination),
    ("A15: freeze gate characterization", prop_freeze_gate_characterization),
    ("A16: admin never freezable", prop_admin_never_freezable),
    ("A17: freeze change non-idempotent", prop_freeze_change_non_idempotent),
]


def run_all_properties():
    """Run all properties and collect results."""
    results = []
    for name, prop_fn in ALL_PROPERTIES:
        preconditions, goal = prop_fn()
        results.append(run_proof(name, preconditions, goal))
    return results
