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
    role_admin_relation,
    symbolic_require_role_admin,
    symbolic_renounce_authorizes,
    symbolic_timelock_elapsed,
    frozen_relation,
    symbolic_assert_accounts_not_frozen,
    symbolic_can_originate,
    symbolic_set_account_frozen_authorized,
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


# --- AL-8: role-admin hierarchy, renounce, timelocked default-admin handoff ---


def _role_admin_vars():
    """Free symbolic operation + capability tuple for the delegated role-admin gate.
    `role_admin_of` is uninterpreted, so the proofs hold for every role graph."""
    caller, target_role, expected_admin, root_role = Ints(
        "caller targetRole expectedAdmin rootRole"
    )
    cap_admin, cap_assignee, cap_role = Ints("capAdmin capAssignee capRole")
    cap_is_scoped, = Bools("capIsScoped")
    role_admin_of = role_admin_relation()
    authorized = symbolic_require_role_admin(
        caller, target_role, expected_admin, root_role, role_admin_of,
        cap_admin, cap_assignee, cap_role, cap_is_scoped,
    )
    return locals()


def prop_grant_requires_role_admin():
    """A9 (AL-8): granting role R through the delegated path requires the caller to
    present a capability for R's admin role (`roleAdmin R`). A capability for any
    other role can never authorize the grant — holds for every role graph."""
    v = _role_admin_vars()
    goal = Implies(
        v["cap_role"] != v["role_admin_of"](v["target_role"]),
        Not(v["authorized"]),
    )
    return BoolVal(True), goal


def prop_role_admin_grant_completeness():
    """A10 (AL-8): non-vacuity + positive direction. When `target_role` is not the
    root role and the caller presents a registry-wide capability for
    `roleAdmin target_role` issued to it by this admin, the delegated grant IS
    authorized. Guards against a vacuously-true gate (A9/A11 are implications over
    this same gate that would hold trivially if it never authorized anything; A12
    and A13 use their own trivially-satisfiable models and need no such guard)."""
    v = _role_admin_vars()
    preconditions = And(
        v["target_role"] != v["root_role"],
        v["cap_admin"] == v["expected_admin"],
        v["cap_assignee"] == v["caller"],
        v["cap_role"] == v["role_admin_of"](v["target_role"]),
        Not(v["cap_is_scoped"]),
    )
    goal = v["authorized"]
    return preconditions, goal


def prop_no_privilege_escalation():
    """A11 (AL-8, C9): no privilege escalation through the delegated path — it can
    never grant or revoke the root role (`Admin`/`DEFAULT_ADMIN_ROLE`), whatever
    capability the caller holds. Re-delegating root is impossible; `Admin` moves
    only via the genesis root or the timelocked handoff."""
    v = _role_admin_vars()
    goal = Implies(v["target_role"] == v["root_role"], Not(v["authorized"]))
    return BoolVal(True), goal


def prop_renounce_self_only():
    """A12 (AL-8): `renounceRole` is self-only — a party can only renounce a
    capability that names it (the choice is controlled by the assignee), so a
    caller can never renounce someone else's role."""
    cap_assignee, caller = Ints("capAssignee caller")
    authorized = symbolic_renounce_authorizes(cap_assignee, caller)
    goal = Implies(cap_assignee != caller, Not(authorized))
    return BoolVal(True), goal


def prop_timelock_not_bypassable():
    """A13 (AL-8): the two-step default-admin handoff cannot complete before its
    timelock — acceptance is impossible while ledger time is before
    `effectiveTime`, so the delay window cannot be bypassed."""
    now, effective_time = Reals("now effectiveTime")
    proceeds = symbolic_timelock_elapsed(now, effective_time)
    goal = Implies(now < effective_time, Not(proceeds))
    return BoolVal(True), goal


# --- AL-10: account-level freeze / compliance hold ---

def _freeze_origination_vars():
    """Free symbolic origination + freeze tuple shared by the origination-gate props
    (A14, A15) — mirrors the `_capability_vars` convention."""
    is_frozen = frozen_relation()
    sender, receiver = Ints("sender receiver")
    paused, = Bools("paused")
    proceeds = symbolic_can_originate(paused, [sender, receiver], is_frozen)
    return locals()


def _set_frozen_vars():
    """Free symbolic `Rules_SetAccountFrozen` tuple shared by the set-frozen guard
    props (A16, A17)."""
    account, admin_party = Ints("account adminParty")
    frozen, currently_frozen = Bools("frozen currentlyFrozen")
    authorized = symbolic_set_account_frozen_authorized(
        account, admin_party, frozen, currently_frozen
    )
    return locals()


def prop_freeze_blocks_origination():
    """A14 (INV-40): a frozen party cannot originate. If EITHER the sender or the
    receiver of an origination is frozen, the unified `assertCanOriginate` gate
    rejects it — a frozen account can neither send nor receive new value."""
    v = _freeze_origination_vars()
    goal = Implies(
        Or(v["is_frozen"](v["sender"]), v["is_frozen"](v["receiver"])),
        Not(v["proceeds"]),
    )
    return BoolVal(True), goal


def prop_freeze_gate_characterization():
    """A15 (INV-25 ∧ INV-40): the unified gate is EXACTLY pause ∧ freeze. Proves the
    biconditional `assertCanOriginate ⟺ (not paused ∧ no involved party frozen)`
    against an independently-written reference — so it is NOT the vacuous `P → P`
    that a one-directional `Implies(condition, proceeds)` would be (that holds even
    if the gate dropped a conjunct). This characterization is the load-bearing freeze
    proof: it fails if `symbolic_can_originate` drops the freeze conjunct, drops the
    pause conjunct, or degenerates to always-false, so it also subsumes the
    pause-preservation claim (no separate `pause dominates` proof is needed — that
    would merely restate A8). A14 keeps the headline negative direction explicit."""
    v = _freeze_origination_vars()
    # Reference spec, written independently of `symbolic_can_originate`'s composition:
    expected = And(
        Not(v["paused"]),
        Not(v["is_frozen"](v["sender"])),
        Not(v["is_frozen"](v["receiver"])),
    )
    goal = v["proceeds"] == expected
    return BoolVal(True), goal


def prop_admin_never_freezable():
    """A16 (INV-42): the registry administrator can never be frozen — any attempt to
    set the admin party's hold to frozen is rejected (it co-signs every holding, so
    freezing it would brick the registry)."""
    v = _set_frozen_vars()
    goal = Implies(And(v["frozen"], v["account"] == v["admin_party"]), Not(v["authorized"]))
    return BoolVal(True), goal


def prop_freeze_change_non_idempotent():
    """A17 (INV-42): a redundant freeze change is rejected — re-freezing an
    already-held account or unfreezing one that is not held does not authorize (the
    OZ Pausable non-idempotency), so the frozen set stays duplicate-free."""
    v = _set_frozen_vars()
    goal = Implies(v["currently_frozen"] == v["frozen"], Not(v["authorized"]))
    return BoolVal(True), goal
