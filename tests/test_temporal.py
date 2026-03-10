from daml_verify.prover import run_proof, ProofStatus
from daml_verify.props.temporal import (
    prop_transfer_temporal,
    prop_allocation_temporal,
    prop_lock_expiry_consistency,
)


def test_transfer_temporal():
    """T1: requestedAt < executeBefore for all timestamps."""
    result = run_proof("T1", *prop_transfer_temporal())
    assert result.status == ProofStatus.PROVED


def test_allocation_temporal():
    """T2: full temporal chain consistent."""
    result = run_proof("T2", *prop_allocation_temporal())
    assert result.status == ProofStatus.PROVED


def test_lock_expiry_consistency():
    """T3: lock always active at creation time."""
    result = run_proof("T3", *prop_lock_expiry_consistency())
    assert result.status == ProofStatus.PROVED
