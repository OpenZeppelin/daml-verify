"""Symbolic model of CNTS transfer logic.

Models Rules.daml:32-78 (transfer factory) and
Rules.daml:175-200 (archiveAndSumInputs).

Dogfooding (2026-02-20): Models validated against actual CNTS source.
Abstractions documented below. All transfer paths verified to be
conservation-preserving for the amount dimension.
"""

from z3 import Sum


def symbolic_archive_and_sum(inputs):
    """Model of archiveAndSumInputs (CNTS Rules.daml:175-200).

    Abstractions (valid for conservation proofs):
      - Per-input owner check (invariant #10) elided — precondition
      - Per-input instrumentId check (invariant #17) elided — precondition
      - Lock expiry handling elided — only affects whether input is accepted
      - Archive-per-input ordering elided — DAML transaction atomicity
    Precondition: all inputs have amount > 0 (SimpleHolding ensure clause).
    Precondition: all inputs belong to sender.
    Precondition: all inputs have matching instrumentId.
    Returns: sum of input amounts.
    """
    return Sum(inputs)


def symbolic_self_transfer(total_input, requested_amount):
    """Model of selfTransfer (CNTS Rules.daml:203-227).

    receiverAmount = transfer.amount (owned by sender, since sender==receiver)
    senderChange = totalInput - transfer.amount (only created when > 0,
    since SimpleHolding ensure amount > 0.0 prevents zero-amount holdings)
    """
    receiver_amount = requested_amount
    sender_change = total_input - requested_amount
    return receiver_amount, sender_change


def symbolic_direct_transfer(total_input, requested_amount):
    """Model of directTransfer (CNTS Rules.daml:231-244).

    Delegates to TransferPreapproval_Send (Preapproval.daml:26-66).
    Preapproval validates: instrumentId match, amount > 0, optional expiry.
    Amount logic identical to selfTransfer.
    """
    receiver_amount = requested_amount
    sender_change = total_input - requested_amount
    return receiver_amount, sender_change


def symbolic_two_step_lock(total_input, requested_amount):
    """Model of twoStepTransfer lock phase (CNTS Rules.daml:247-283).

    Creates LockedSimpleHolding with amount=transfer.amount and
    lock.expiresAt=Some transfer.executeBefore.
    Change = totalInput - transfer.amount (only created when > 0).
    """
    lock_amount = requested_amount
    sender_change = total_input - requested_amount
    return lock_amount, sender_change


def symbolic_two_step_accept(lock_amount):
    """Model of twoStepAccept (CNTS TransferInstruction.daml:30-60).

    Receiver gets transfer.amount as new SimpleHolding.
    Invariant: lock_amount == transfer.amount (by construction in
    twoStepTransfer, which creates LockedSimpleHolding with
    amount=transfer.amount; locked holdings cannot be modified).
    """
    return lock_amount
