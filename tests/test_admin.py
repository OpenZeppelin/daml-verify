from daml_verify.prover import run_proof, ProofStatus
from daml_verify.props.admin import (
    prop_capability_admin_gate,
    prop_capability_assignee_gate,
    prop_capability_role_gate,
    prop_scope_least_privilege,
    prop_scope_completeness,
    prop_mint_allowance_decrement,
    prop_mint_allowance_conservation,
    prop_pause_blocks_origination,
)


def test_capability_admin_gate():
    """A1: a capability from a different registry admin never authorizes."""
    result = run_proof("A1", *prop_capability_admin_gate())
    assert result.status == ProofStatus.PROVED


def test_capability_assignee_gate():
    """A2: a capability never authorizes a caller it does not name."""
    result = run_proof("A2", *prop_capability_assignee_gate())
    assert result.status == ProofStatus.PROVED


def test_capability_role_gate():
    """A3: a capability for the wrong role never authorizes."""
    result = run_proof("A3", *prop_capability_role_gate())
    assert result.status == ProofStatus.PROVED


def test_scope_least_privilege():
    """A4: an instrument-scoped capability cannot authorize a registry-wide op."""
    result = run_proof("A4", *prop_scope_least_privilege())
    assert result.status == ProofStatus.PROVED


def test_scope_completeness():
    """A5: registry-wide authorizes any op; instrument cap authorizes its instrument."""
    result = run_proof("A5", *prop_scope_completeness())
    assert result.status == ProofStatus.PROVED


def test_mint_allowance_decrement():
    """A6: a capped mint decrements exactly and stays non-negative."""
    result = run_proof("A6", *prop_mint_allowance_decrement())
    assert result.status == ProofStatus.PROVED


def test_mint_allowance_conservation():
    """A7: two sequential capped mints never exceed the initial allowance."""
    result = run_proof("A7", *prop_mint_allowance_conservation())
    assert result.status == ProofStatus.PROVED


def test_pause_blocks_origination():
    """A8: while paused, a gated origination choice cannot proceed."""
    result = run_proof("A8", *prop_pause_blocks_origination())
    assert result.status == ProofStatus.PROVED
