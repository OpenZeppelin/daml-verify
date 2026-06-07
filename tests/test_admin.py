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


def test_grant_requires_role_admin():
    """A9: granting role R requires presenting a capability for roleAdmin(R)."""
    result = run_proof("A9", *prop_grant_requires_role_admin())
    assert result.status == ProofStatus.PROVED


def test_role_admin_grant_completeness():
    """A10: the role-admin gate authorizes when all conditions hold (non-vacuity)."""
    result = run_proof("A10", *prop_role_admin_grant_completeness())
    assert result.status == ProofStatus.PROVED


def test_no_privilege_escalation():
    """A11: the delegated path can never grant/revoke the root Admin role."""
    result = run_proof("A11", *prop_no_privilege_escalation())
    assert result.status == ProofStatus.PROVED


def test_renounce_self_only():
    """A12: renounceRole only ever affects a capability that names the caller."""
    result = run_proof("A12", *prop_renounce_self_only())
    assert result.status == ProofStatus.PROVED


def test_timelock_not_bypassable():
    """A13: the default-admin handoff cannot complete before its timelock."""
    result = run_proof("A13", *prop_timelock_not_bypassable())
    assert result.status == ProofStatus.PROVED


def test_freeze_blocks_origination():
    """A14 (AL-10): a frozen sender or receiver cannot originate."""
    result = run_proof("A14", *prop_freeze_blocks_origination())
    assert result.status == ProofStatus.PROVED


def test_freeze_gate_characterization():
    """A15 (AL-10): the unified gate is exactly pause ∧ freeze (non-vacuous
    biconditional — catches a dropped pause/freeze conjunct or an always-false gate)."""
    result = run_proof("A15", *prop_freeze_gate_characterization())
    assert result.status == ProofStatus.PROVED


def test_admin_never_freezable():
    """A16 (AL-10): the registry administrator can never be frozen."""
    result = run_proof("A16", *prop_admin_never_freezable())
    assert result.status == ProofStatus.PROVED


def test_freeze_change_non_idempotent():
    """A17 (AL-10): a redundant freeze change does not authorize."""
    result = run_proof("A17", *prop_freeze_change_non_idempotent())
    assert result.status == ProofStatus.PROVED
