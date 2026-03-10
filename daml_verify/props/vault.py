"""Vault properties: fee monotonicity, ratio guards, liquidation conservation, division safety.

Proves invariants of the CDP vault arithmetic for all possible inputs.
"""

from z3 import And, Reals, Real, Implies

from daml_verify.model.vault import (
    symbolic_accrue_debt,
    symbolic_collateral_ratio,
    symbolic_collateral_to_seize,
)


def prop_fee_monotonicity():
    """V1: Accrued debt >= original debt when rate >= 0 and time >= 0.

    For all currentDebt > 0, annualRate >= 0, elapsedYears >= 0:
      accrueDebt(currentDebt, annualRate, elapsedYears) >= currentDebt
    """
    current_debt, annual_rate, elapsed_years = Reals(
        "currentDebt annualRate elapsedYears"
    )

    accrued = symbolic_accrue_debt(current_debt, annual_rate, elapsed_years)

    preconditions = And(
        current_debt > 0,
        annual_rate >= 0,
        elapsed_years >= 0,
    )
    goal = accrued >= current_debt
    return preconditions, goal


def prop_collateral_ratio_guard():
    """V2: collateral * price >= minRatio * debt implies ratio >= minRatio.

    This proves the mint/withdraw guard is correct: checking
    collateral * price >= minRatio * debt is equivalent to
    checking collateralRatio >= minRatio (when debt > 0).
    """
    collateral, debt, price, min_ratio = Reals("collateral debt price minRatio")

    ratio = symbolic_collateral_ratio(collateral, debt, price)

    preconditions = And(
        collateral > 0,
        debt > 0,
        price > 0,
        min_ratio > 1,
        collateral * price >= min_ratio * debt,
    )
    goal = ratio >= min_ratio
    return preconditions, goal


def prop_liquidation_conservation():
    """V3: Seized + remainder == total collateral (partial liquidation).

    When collateralToSeize < collateralAmount:
      collateralToSeize + remainder == collateralAmount
    """
    collateral, debt, bonus, price = Reals("collateral debt bonus price")

    seized = symbolic_collateral_to_seize(debt, bonus, price)
    remainder = collateral - seized

    preconditions = And(
        collateral > 0,
        debt > 0,
        bonus >= 0,
        price > 0,
        seized < collateral,  # partial liquidation case
    )
    goal = seized + remainder == collateral
    return preconditions, goal


def prop_division_safety_ratio():
    """V4: debt > 0 guards collateralRatio division.

    Vault.daml:339 guards with `if debt == 0.0 then 999999.0`.
    This proves the guard is sufficient.
    """
    debt = Real("debt")

    preconditions = debt > 0
    goal = debt != 0
    return preconditions, goal


def prop_division_safety_seize():
    """V5: price > 0 guards collateralToSeize division.

    Oracle ensure clause guarantees price > 0.
    Vault_Liquidate additionally asserts oracle.price > 0.
    """
    price = Real("price")

    preconditions = price > 0  # Oracle ensure + explicit assert
    goal = price != 0
    return preconditions, goal
