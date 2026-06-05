"""Symbolic model of the SimpleToken admin layer (AccessControl / Pausable / D3 mint cap).

Mirrors, in canton-token-template:
  - `requireRole` / `scopeAuthorizes`  (SimpleToken/Admin/Capability.daml)
  - `consumeMintAllowance`             (SimpleToken/Admin/Capability.daml)
  - `assertNotPaused`                  (SimpleToken/Rules.daml)

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

from z3 import And, Or, Not


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
