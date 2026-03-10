"""Symbolic model of CNTS allocation logic.

Models the allocation lifecycle: allocate, execute, cancel, withdraw.

Dogfooding (2026-02-20): Models validated against actual CNTS source:
  - Rules.daml:90-162 (allocation factory)
  - Allocation.daml:28-78 (execute, cancel, withdraw choices)
  - All paths return full locked amount (no partial withdrawal/execution).
"""


def symbolic_allocate(holding_amount, alloc_amount):
    """Model of allocation: lock amount from sender's holdings.

    CNTS Rules.daml:125-142: creates LockedSimpleHolding with amount=leg.amount
    and change SimpleHolding with amount=totalInput-leg.amount (if > 0).
    Precondition: alloc_amount > 0, holding_amount >= alloc_amount.
    Returns: (locked_amount, remaining_balance).
    """
    locked = alloc_amount
    remaining = holding_amount - alloc_amount
    return locked, remaining


def symbolic_execute_transfer(locked_amount):
    """Model of execute-transfer on allocation (Allocation.daml:28-58).

    The locked amount is transferred to receiver. Real code creates
    receiver holding with amount=leg.amount (== locked_amount by construction).
    Change path exists but is unreachable: factory creates locked holding
    with amount=leg.amount, so lockedHolding.amount == leg.amount always.
    Returns: (receiver_amount, sender_return).
    """
    return locked_amount, 0


def symbolic_cancel_allocation(locked_amount):
    """Model of cancel allocation (Allocation.daml:60-61 -> releaseAllocatedFunds).

    Locked amount is returned to sender as unlocked SimpleHolding.
    Returns: (sender_return, receiver_amount).
    """
    return locked_amount, 0


def symbolic_withdraw(locked_amount):
    """Model of allocation withdraw (Allocation.daml:63-78).

    Sender withdraws before allocateBefore deadline.
    Full locked amount returned — no partial withdrawal.
    Guard: now < allocation.settlement.allocateBefore.
    Returns: (sender_return, receiver_amount).
    """
    return locked_amount, 0
