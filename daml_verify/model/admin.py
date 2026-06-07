"""Symbolic model of the SimpleToken admin layer (AccessControl / Pausable / D3 mint cap).

Mirrors, in canton-token-template:
  - `requireRole` / `scopeAuthorizes`  (SimpleToken/Admin/Capability.daml)
  - `consumeMintAllowance`             (SimpleToken/Admin/Capability.daml)
  - `assertNotPaused`                  (SimpleToken/Rules.daml)
  - `requireRoleAdmin` + `delegableViaRoleAdmin`  (the AL-8 role-admin hierarchy:
    SimpleToken/Admin/Authority.daml + SimpleToken/Admin/Roles.daml)
  - `RoleCapability_Renounce`          (SimpleToken/Admin/Capability.daml, AL-8)
  - `requireTimelockElapsed`           (oz-access-control, the AL-8 timelocked
    default-admin handoff)

Modeling conventions:
  - Parties and roles are opaque Z3 Ints — distinct values are distinct
    principals/roles. The proofs are over ALL values, so concrete identities
    don't matter, only the equality structure the guards test.
  - `Optional InstrumentId` (a capability's `scope`, and an operation's required
    scope) is modeled as a `(is_scoped : Bool, instr : Int)` pair:
        is_scoped = False  ↔  None        (registry-wide)
        is_scoped = True   ↔  Some instr  (instrument-scoped)
  - A capped `mintAllowance` is a non-negative Real; mint amounts are Reals.

These models intentionally carry no concrete data — they reproduce the guard
logic so Z3 can prove the authorization/scope/allowance/pause invariants hold
for every input.
"""

from z3 import And, Or, Not, Function, IntSort


def symbolic_scope_authorizes(cap_is_scoped, cap_instr, req_is_scoped, req_instr):
    """Model of `scopeAuthorizes` (Capability.daml):

        scopeAuthorizes capScope requiredScope = case capScope of
          None   -> True
          Some s -> requiredScope == Some s

    None (registry-wide) authorizes any operation; an instrument-scoped cap
    authorizes only an operation on that exact instrument.
    """
    return Or(
        Not(cap_is_scoped),                          # None -> True
        And(req_is_scoped, cap_instr == req_instr),  # Some s -> requiredScope == Some s
    )


def symbolic_require_role(
    caller, role, expected_admin, req_is_scoped, req_instr,
    cap_admin, cap_assignee, cap_role, cap_is_scoped, cap_instr,
):
    """Model of `requireRole` (Capability.daml): authorization holds iff ALL four
    guards pass — admin (INV-27), assignee/anti-impersonation (INV-28), role
    (INV-29), and scope (INV-30)."""
    return And(
        cap_admin == expected_admin,   # INV-27: eCapabilityAdminMismatch
        cap_assignee == caller,        # INV-28: eCapabilityAssigneeMismatch
        cap_role == role,              # INV-29: eCapabilityRoleMismatch
        symbolic_scope_authorizes(cap_is_scoped, cap_instr, req_is_scoped, req_instr),  # INV-30
    )


def symbolic_consume_allowance(remaining, amount):
    """Model of the `Some`-branch of `consumeMintAllowance` (Capability.daml):
    a capped mint requires `amount <= remaining` (a precondition) and re-creates
    the capability with `remaining - amount`. Returns the new remaining."""
    return remaining - amount


def symbolic_assert_not_paused(paused):
    """Model of `assertNotPaused` (Rules.daml): a gated origination choice
    proceeds iff the registry is not paused."""
    return Not(paused)


def role_admin_relation():
    """An UNINTERPRETED function `roleAdmin : Role -> Role` (Int -> Int), modeling
    `SimpleToken.Admin.Roles.roleAdmin`. Leaving it uninterpreted means the proofs
    quantify over EVERY role->admin relation, so the role-admin mechanism is
    verified independent of the token's specific (flat-default) graph."""
    return Function("roleAdmin", IntSort(), IntSort())


def symbolic_require_role_admin(
    caller, target_role, expected_admin, root_role, role_admin_of,
    cap_admin, cap_assignee, cap_role, cap_is_scoped,
):
    """Model of the AL-8 delegated role-admin path — `requireRoleAdmin` plus the
    `delegableViaRoleAdmin` carve-out (Authority.daml / Roles.daml). A delegated
    grant or revoke of `target_role` is authorized iff ALL hold:

      - `target_role` is delegable at all — it is NOT the root role
        (`delegableViaRoleAdmin`: the `Admin`/`DEFAULT_ADMIN_ROLE` carve-out,
        decision C9 — root is never delegated through this path); AND
      - the presented capability is admin-signed by this registry (`cap_admin`),
        names the caller (`cap_assignee`), carries the admin role of `target_role`
        (`roleAdmin target_role`), and is registry-wide (`scopeAuthorizes None`
        admits only an unscoped cap for a registry-wide role-management op).

    Combining the carve-out and the `requireRole` gate here mirrors the token's
    single chokepoint, so any future delegated choice routed through it inherits
    both guards.
    """
    return And(
        target_role != root_role,                    # delegableViaRoleAdmin (Admin not delegable)
        cap_admin == expected_admin,                 # requireRole: admin gate (A1)
        cap_assignee == caller,                      # requireRole: assignee gate (A2)
        cap_role == role_admin_of(target_role),      # requireRole: holds roleAdmin(target_role) (A3)
        Not(cap_is_scoped),                          # scope: registry-wide op needs unscoped cap (A4)
    )


def symbolic_renounce_authorizes(cap_assignee, caller):
    """Model of `RoleCapability_Renounce` / `RoleGrant_Renounce` (AL-8): the choice
    is controlled by the capability's assignee, so it is authorized iff the caller
    is the assignee — self-only by construction (the `renounceRole` analogue)."""
    return cap_assignee == caller


def symbolic_timelock_elapsed(now, effective_time):
    """Model of `requireTimelockElapsed` (oz-access-control, AL-8): acceptance of a
    two-step default-admin handoff proceeds iff ledger time has reached
    `effectiveTime`."""
    return now >= effective_time
