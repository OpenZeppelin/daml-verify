from daml_verify.prover import run_proof, ProofStatus
from daml_verify.props.vault import (
    prop_fee_monotonicity,
    prop_collateral_ratio_guard,
    prop_liquidation_conservation,
    prop_division_safety_ratio,
    prop_division_safety_seize,
)


def test_fee_monotonicity():
    """V1: accrued debt >= original debt."""
    result = run_proof("V1", *prop_fee_monotonicity())
    assert result.status == ProofStatus.PROVED


def test_collateral_ratio_guard():
    """V2: ratio guard is correct."""
    result = run_proof("V2", *prop_collateral_ratio_guard())
    assert result.status == ProofStatus.PROVED


def test_liquidation_conservation():
    """V3: seized + remainder == total."""
    result = run_proof("V3", *prop_liquidation_conservation())
    assert result.status == ProofStatus.PROVED


def test_division_safety_ratio():
    """V4: debt > 0 prevents div-by-zero."""
    result = run_proof("V4", *prop_division_safety_ratio())
    assert result.status == ProofStatus.PROVED


def test_division_safety_seize():
    """V5: price > 0 prevents div-by-zero."""
    result = run_proof("V5", *prop_division_safety_seize())
    assert result.status == ProofStatus.PROVED
