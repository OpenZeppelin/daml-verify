# daml-verify

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

> [!WARNING]
> This software is experimental and not intended for production use. Use at your own risk.

Lightweight formal verification for DAML contracts using the [Z3 SMT solver](https://github.com/Z3Prover/z3). Proves that critical invariants hold **for all possible inputs** — not just the ones you thought to test.

## Properties

daml-verify ships with 31 properties across five categories — conservation (C),
division (D), temporal (T), vault (V), and admin layer (A):

| ID | Property | What it proves |
|----|----------|----------------|
| C1 | Conservation total | Total output equals total input across transfer paths |
| C2 | Receiver amount | Receiver gets exactly the requested amount |
| C3 | Sender change | Sender change equals `totalInput - requested` |
| D1 | scaleFees safety | No division-by-zero when `amuletPrice > 0` |
| D2 | Issuance safety | No division-by-zero when `capPerCoupon > 0` and `totalCoupons > 0` |
| D3 | Ensure sufficient | `ensure amount > 0.0` guards all division sites |
| T1 | Transfer temporal | `requestedAt < executeBefore` follows from preconditions |
| T2 | Allocation temporal | Full temporal chain is consistent |
| T3 | Lock expiry | Lock is always active at creation time |
| V1 | Fee monotonicity | Stablecoin fee grows monotonically with input |
| V2 | Collateral ratio guard | Under-collateralized positions are rejected |
| V3 | Liquidation conservation | Liquidation conserves value |
| V4 | Division safety (ratio) | Collateral-ratio division is guarded |
| V5 | Division safety (seize) | Seize-amount division is guarded |
| A1 | Capability admin gate | A capability from a different registry admin never authorizes |
| A2 | Capability assignee gate | A capability never authorizes a caller it does not name (anti-impersonation) |
| A3 | Capability role gate | A capability for the wrong role never authorizes |
| A4 | Scope least privilege | An instrument-scoped capability cannot authorize a registry-wide op |
| A5 | Scope completeness | Registry-wide authorizes any op; an instrument cap authorizes its instrument |
| A6 | Mint allowance decrement | A capped mint decrements exactly and stays non-negative |
| A7 | Mint allowance conservation | Sequential capped mints never exceed the initial allowance |
| A8 | Pause blocks origination | While paused, a gated origination choice cannot proceed |
| A9 | Grant requires role admin | Granting role R requires presenting a capability for R's admin role (`roleAdmin R`) — for every role graph |
| A10 | Role-admin grant completeness | The role-admin gate authorizes when all conditions hold (non-vacuity guard for A9/A11) |
| A11 | No privilege escalation | The delegated path can never grant/revoke the root `Admin`/`DEFAULT_ADMIN_ROLE` (no re-delegation of root) |
| A12 | Renounce self-only | `renounceRole` only ever affects a capability that names the caller |
| A13 | Timelock not bypassable | The two-step default-admin handoff cannot complete before its timelock elapses |
| A14 | Freeze blocks origination | A frozen sender or receiver cannot originate — the AL-10 compliance hold |
| A15 | Freeze gate characterization | The unified `assertCanOriginate` gate is **exactly** `not paused ∧ no involved party frozen` (biconditional vs an independent spec — non-vacuous: fails if either conjunct is dropped or the gate degenerates; subsumes pause-preservation) |
| A16 | Admin never freezable | The registry administrator can never be set frozen (it co-signs every holding) |
| A17 | Freeze change non-idempotent | A redundant freeze change (re-freeze held / unfreeze unheld) does not authorize |

The admin-layer (A) properties model `SimpleToken/Admin/Capability.daml`
(`requireRole`, `scopeAuthorizes`, `consumeMintAllowance`), `Rules.daml`
(`assertNotPaused`, the unified `assertCanOriginate` gate, and the AL-10 account
freeze `assertAccountsNotFrozen` / `Rules_SetAccountFrozen`), and the AL-8
role-admin hierarchy (`Admin/Authority.daml` `requireRoleAdmin` + `Admin/Roles.daml`
`delegableViaRoleAdmin`, `RoleCapability_Renounce`, and the `oz-access-control`
timelocked default-admin handoff `requireTimelockElapsed`) from the OpenZeppelin
canton-token-template — its AccessControl / Pausable / per-minter-cap /
role-admin-hierarchy / account-freeze layer. A9–A11 leave `roleAdmin : Role -> Role`
and A14–A17 leave `isFrozen : Party -> Bool` **uninterpreted**, so they hold for
every role->admin graph and every frozen set, not just the token's flat default.

Scope of the freeze proofs (A14–A17): they verify the **gate logic** —
`assertCanOriginate` is exactly `pause ∧ freeze`, the admin is unfreezable, and the
change is non-idempotent. They model an abstract single-party gate; they do **not**
verify (a) that the gate is actually invoked at each of the token's origination
chokepoints, (b) the V2 `accountParties` owner+provider expansion, or (c) the
cold-path mint-accept re-check — those are covered by the token's daml-script tests.

## Quick start

```bash
# Clone and set up
git clone https://github.com/OpenZeppelin/daml-verify.git && cd daml-verify
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run all proofs
python main.py
```

Expected output:

```
daml-verify: 31 properties, 31 proved, 0 disproved

  [PROVED] C1: conservation total
  ...
  [PROVED] V5: division safety (seize)
  [PROVED] A1: capability admin gate
  ...
  [PROVED] A8: pause blocks origination
  [PROVED] A9: grant requires role admin
  [PROVED] A10: role-admin grant completeness
  [PROVED] A11: no privilege escalation
  [PROVED] A12: renounce self-only
  [PROVED] A13: timelock not bypassable
  [PROVED] A14: freeze blocks origination
  [PROVED] A15: freeze gate characterization
  [PROVED] A16: admin never freezable
  [PROVED] A17: freeze change non-idempotent
```

Run a single category with `python main.py --class admin` (or `conservation`,
`division`, `temporal`, `vault`).

## Usage

```bash
# Run all properties
python main.py

# Run a single property class
python main.py --class conservation   # C1, C2, C3
python main.py --class division       # D1, D2, D3
python main.py --class temporal       # T1, T2, T3

# Run a single property
python main.py C1

# Run tests
pytest
```

The exit code is `0` if all proofs pass, `1` if any fail.

## How it works

Each property is expressed as a **precondition/goal** pair over symbolic variables (Z3 reals or integers). The prover checks whether `preconditions AND NOT goal` is satisfiable:

- **UNSAT** — the property holds for all inputs (proved).
- **SAT** — a counterexample exists (disproved), and the model is printed.
- **UNKNOWN** — the solver could not decide within its limits.

The symbolic models in `daml_verify/model/` mirror the logic of the corresponding DAML contract functions. Properties in `daml_verify/props/` state what should be true about those models.

## Project structure

```
daml_verify/
  prover.py          # Z3 solver integration
  reporter.py        # Output formatting
  model/
    transfer.py      # CNTS transfer logic
    allocation.py    # CNTS allocation logic
    fees.py          # Splice fee computation
  props/
    conservation.py  # Conservation invariants (C1-C3)
    division.py      # Division safety (D1-D3)
    temporal.py      # Temporal ordering (T1-T3)
tests/               # pytest suite (one test per property)
main.py              # CLI entry point
```

## Adding your own properties

1. **Model** your DAML contract logic in `daml_verify/model/` using Z3 symbolic variables.
2. **Define a property** in `daml_verify/props/` as a function returning `(preconditions, goal)`.
3. **Register it** in `ALL_PROPERTIES` in `daml_verify/prover.py`.
4. **Add a test** in `tests/` that asserts `ProofStatus.PROVED`.

Example property:

```python
from z3 import Reals, And

def prop_my_invariant():
    x, y = Reals("x y")
    preconditions = And(x > 0, y > 0)
    goal = x + y > 0
    return preconditions, goal
```

## Requirements

- Python 3.10+
- z3-solver >= 4.12

