"""Conservation properties: total output equals total input.

Proves that for all positive input amounts and valid requested amounts,
the transfer conserves tokens exactly.
"""

from z3 import And, Reals, Real

from daml_verify.model.transfer import symbolic_archive_and_sum, symbolic_self_transfer


def prop_conservation_total():
    """C1: Total output equals total input.

    For all positive input amounts and positive requested amount
    where sum(inputs) >= requested:
      receiverAmount + senderChange == sum(inputs)
    """
    a1, a2, a3 = Reals("input1 input2 input3")
    requested = Real("requested")

    total_input = symbolic_archive_and_sum([a1, a2, a3])
    receiver_amt, sender_change = symbolic_self_transfer(total_input, requested)

    preconditions = And(
        a1 > 0, a2 > 0, a3 > 0,
        requested > 0,
        total_input >= requested,
    )
    goal = receiver_amt + sender_change == total_input
    return preconditions, goal


def prop_conservation_receiver():
    """C2: Receiver gets exactly requested amount."""
    total_input, requested = Reals("totalInput requested")

    preconditions = And(
        total_input > 0,
        requested > 0,
        total_input >= requested,
    )

    receiver_amt, _ = symbolic_self_transfer(total_input, requested)
    goal = receiver_amt == requested
    return preconditions, goal


def prop_conservation_change():
    """C3: Sender change is exactly the difference."""
    total_input, requested = Reals("totalInput requested")

    preconditions = And(
        total_input > 0,
        requested > 0,
        total_input >= requested,
    )

    _, sender_change = symbolic_self_transfer(total_input, requested)
    goal = sender_change == total_input - requested
    return preconditions, goal
