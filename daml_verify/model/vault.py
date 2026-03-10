"""Symbolic model of daml-stablecoin vault arithmetic.

Models Vault.daml:325-341 (accrueDebt, collateralRatio) and
Vault.daml:212-291 (Vault_Liquidate collateral seizure).
"""

from z3 import Real, Reals


def symbolic_accrue_debt(current_debt, annual_rate, elapsed_years):
    """Model of accrueDebt (Vault.daml:325-333).

    newDebt = currentDebt * (1 + annualRate * elapsedYears)
    Precondition: currentDebt >= 0, annualRate >= 0, elapsedYears >= 0.
    When currentDebt == 0 or annualRate == 0, returns currentDebt unchanged.
    For the symbolic model we use the general formula (the guard is optimization only).
    """
    return current_debt * (1 + annual_rate * elapsed_years)


def symbolic_collateral_ratio(collateral, debt, price):
    """Model of collateralRatio (Vault.daml:337-340).

    ratio = (collateral * price) / debt
    Precondition: debt > 0 (guarded by if debt == 0.0 then 999999.0).
    """
    return (collateral * price) / debt


def symbolic_collateral_to_seize(debt, bonus, price):
    """Model of collateralToSeize in Vault_Liquidate (Vault.daml:233).

    collateralToSeize = (accruedDebt * (1 + liquidationBonus)) / price
    Precondition: price > 0 (Oracle ensure clause).
    """
    return (debt * (1 + bonus)) / price
