# daml-verify

Lightweight formal verification for DAML contracts using the [Z3 SMT solver](https://github.com/Z3Prover/z3). Proves that critical invariants hold **for all possible inputs** — not just the ones you thought to test.

## Properties

daml-verify ships with 9 properties across three categories:

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

## Quick start

```bash
# Clone and set up
git clone https://github.com/4meta5/daml-verify.git && cd daml-verify
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run all 9 proofs
python main.py
```

Expected output:

```
daml-verify: 9 properties, 9 proved, 0 disproved

  [PROVED] C1: conservation total
  [PROVED] C2: receiver amount
  [PROVED] C3: sender change
  [PROVED] D1: scaleFees safety
  [PROVED] D2: issuance safety
  [PROVED] D3: ensure sufficient
  [PROVED] T1: transfer temporal
  [PROVED] T2: allocation temporal
  [PROVED] T3: lock expiry
```

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

## License

Apache 2.0 — see [LICENSE](LICENSE).
