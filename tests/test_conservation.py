from daml_verify.prover import run_proof, ProofStatus
from daml_verify.props.conservation import (
    prop_conservation_total,
    prop_conservation_receiver,
    prop_conservation_change,
)


def test_conservation_total():
    """C1: sum(outputs) == sum(inputs) for all positive amounts."""
    result = run_proof("C1", *prop_conservation_total())
    assert result.status == ProofStatus.PROVED


def test_conservation_receiver():
    """C2: receiver gets exactly requested amount."""
    result = run_proof("C2", *prop_conservation_receiver())
    assert result.status == ProofStatus.PROVED


def test_conservation_change():
    """C3: sender change == totalInput - requested."""
    result = run_proof("C3", *prop_conservation_change())
    assert result.status == ProofStatus.PROVED
