from daml_verify.prover import run_proof, ProofStatus
from daml_verify.props.division import (
    prop_scale_fees_terminates,
    prop_issuance_tranche_terminates,
    prop_ensure_sufficient,
)


def test_scale_fees_terminates():
    """D1: ensure amuletPrice > 0 prevents division by zero."""
    result = run_proof("D1", *prop_scale_fees_terminates())
    assert result.status == ProofStatus.PROVED


def test_issuance_tranche_terminates():
    """D2: ensure capPerCoupon > 0 AND totalCoupons > 0 sufficient."""
    result = run_proof("D2", *prop_issuance_tranche_terminates())
    assert result.status == ProofStatus.PROVED


def test_ensure_sufficient():
    """D3: SimpleHolding ensure amount > 0 is sufficient."""
    result = run_proof("D3", *prop_ensure_sufficient())
    assert result.status == ProofStatus.PROVED
