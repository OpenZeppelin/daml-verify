"""Admin-layer properties (AL-4): AccessControl capability gates, scope
least-privilege, the D3 mint-allowance cap, and the Pausable origination guard.

Models `SimpleToken/Admin/Capability.daml` (`requireRole`, `scopeAuthorizes`,
`consumeMintAllowance`) and `SimpleToken/Rules.daml` (`assertNotPaused`) from
canton-token-template. Closes the `admin-authorization` / `scopeAuthorizes` /
capped-mint-conservation proof targets recorded in that repo's
docs/ADMIN-LAYER-PLAN.md §7 (invariants #25–#39) — lifting them from
Daml-Script-covered to Z3-proved.
"""

from z3 import And, Or, Not, Implies, Bools, Ints, Reals, BoolVal

from daml_verify.model.admin import (
    symbolic_require_role,
    symbolic_scope_authorizes,
    symbolic_consume_allowance,
    symbolic_assert_not_paused,
)


def _capability_vars():
    """Free symbolic operation + capability tuple shared by the gate properties."""
    caller, role, expected_admin, req_instr = Ints("caller role expectedAdmin reqInstr")
    cap_admin, cap_assignee, cap_role, cap_instr = Ints("capAdmin capAssignee capRole capInstr")
    req_is_scoped, cap_is_scoped = Bools("reqIsScoped capIsScoped")
    authorized = symbolic_require_role(
        caller, role, expected_admin, req_is_scoped, req_instr,
        cap_admin, cap_assignee, cap_role, cap_is_scoped, cap_instr,
    )
    return locals()


def prop_capability_admin_gate():
    """A1 (INV-27): a capability issued by a different registry admin never
    authorizes — capabilities are anchored to their issuing admin."""
    v = _capability_vars()
    goal = Implies(v["cap_admin"] != v["expected_admin"], Not(v["authorized"]))
    return BoolVal(True), goal


def prop_capability_assignee_gate():
    """A2 (INV-28): a capability never authorizes a caller it does not name —
    presenting someone else's capability fails (anti-impersonation)."""
    v = _capability_vars()
    goal = Implies(v["cap_assignee"] != v["caller"], Not(v["authorized"]))
    return BoolVal(True), goal


def prop_capability_role_gate():
    """A3 (INV-29): a capability for a different role never authorizes."""
    v = _capability_vars()
    goal = Implies(v["cap_role"] != v["role"], Not(v["authorized"]))
    return BoolVal(True), goal


def prop_scope_least_privilege():
    """A4 (INV-30): an instrument-scoped capability cannot authorize a
    registry-wide operation (e.g. an instrument-scoped Pauser cannot pause the
    whole registry; a scoped Minter cannot mint registry-wide)."""
    cap_instr, req_instr = Ints("capInstr reqInstr")
    cap_is_scoped, req_is_scoped = Bools("capIsScoped reqIsScoped")
    authorizes = symbolic_scope_authorizes(cap_is_scoped, cap_instr, req_is_scoped, req_instr)
    goal = Implies(And(cap_is_scoped, Not(req_is_scoped)), Not(authorizes))
    return BoolVal(True), goal


def prop_scope_completeness():
    """A5 (INV-30): a registry-wide capability authorizes any operation, and an
    instrument-scoped capability authorizes exactly the matching instrument."""
    cap_instr, req_instr = Ints("capInstr reqInstr")
    cap_is_scoped, req_is_scoped = Bools("capIsScoped reqIsScoped")
    authorizes = symbolic_scope_authorizes(cap_is_scoped, cap_instr, req_is_scoped, req_instr)
    goal = And(
        Implies(Not(cap_is_scoped), authorizes),                       # registry-wide → any
        Implies(And(cap_is_scoped, req_is_scoped),                     # instrument cap →
                authorizes == (cap_instr == req_instr)),               #   iff same instrument
    )
    return BoolVal(True), goal


def prop_mint_allowance_decrement():
    """A6 (INV-36): a capped mint within the remaining allowance leaves a
    non-negative remainder decremented by exactly the minted amount."""
    remaining, amount = Reals("remaining amount")
    preconditions = And(remaining >= 0, amount > 0, amount <= remaining)
    new_remaining = symbolic_consume_allowance(remaining, amount)
    goal = And(new_remaining == remaining - amount, new_remaining >= 0)
    return preconditions, goal


def prop_mint_allowance_conservation():
    """A7 (D3): two sequential capped mints can never mint more than the initial
    allowance, and the allowance never goes negative — the per-minter cap is a
    sound, conserved bound on supply."""
    r0, a, b = Reals("r0 a b")
    r1 = symbolic_consume_allowance(r0, a)        # after first mint of a
    preconditions = And(
        r0 >= 0, a > 0, b > 0,
        a <= r0,    # first mint authorized
        b <= r1,    # second mint authorized against the decremented allowance
    )
    goal = And(a + b <= r0, r0 - a - b >= 0)
    return preconditions, goal


def prop_pause_blocks_origination():
    """A8 (INV-25): while paused, a gated origination choice cannot proceed."""
    paused, = Bools("paused")
    proceeds = symbolic_assert_not_paused(paused)
    goal = Implies(paused, Not(proceeds))
    return BoolVal(True), goal
