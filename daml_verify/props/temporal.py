"""Temporal ordering properties.

Proves that factory preconditions ensure well-formed temporal ordering
for all possible timestamp values.
"""

from z3 import And, Ints, Int


def prop_transfer_temporal():
    """T1: Transfer temporal ordering.

    requestedAt <= now AND executeBefore > now => requestedAt < executeBefore.
    CNTS invariants #2 and #3.
    """
    requested_at, now, execute_before = Ints("requestedAt now executeBefore")

    # Factory checks (CNTS Rules.daml:42-46)
    preconditions = And(
        requested_at <= now,
        execute_before > now,
    )
    goal = requested_at < execute_before
    return preconditions, goal


def prop_allocation_temporal():
    """T2: Allocation temporal ordering.

    Full chain: requestedAt <= now < allocateBefore <= settleBefore.
    CNTS invariant #5.
    """
    requested_at, now, allocate_before, settle_before = Ints(
        "requestedAt now allocateBefore settleBefore"
    )

    # Factory checks (CNTS Rules.daml:101-108)
    preconditions = And(
        requested_at <= now,
        allocate_before > now,
        allocate_before <= settle_before,
    )
    goal = And(
        requested_at <= now,
        now < allocate_before,
        allocate_before <= settle_before,
    )
    return preconditions, goal


def prop_lock_expiry_consistency():
    """T3: Lock expiry consistency.

    For two-step transfers: lock.expiresAt == executeBefore.
    Proves lock is not expired at creation time.
    CNTS invariant #12.
    """
    execute_before, now, lock_expires_at = Ints(
        "executeBefore now lockExpiresAt"
    )

    # Factory sets lock.expiresAt = Some executeBefore (CNTS Rules.daml:257)
    preconditions = And(
        lock_expires_at == execute_before,
        execute_before > now,
    )
    goal = now < lock_expires_at
    return preconditions, goal
