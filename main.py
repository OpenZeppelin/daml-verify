#!/usr/bin/env python3
"""daml-verify CLI: run all properties, run by class, or run individual property."""

import sys

from daml_verify.prover import ALL_PROPERTIES, run_proof, ProofStatus
from daml_verify.reporter import report_results


def main():
    args = sys.argv[1:]

    if not args:
        properties = ALL_PROPERTIES
    elif args == ["--class", "conservation"] or args == ["-c", "conservation"]:
        properties = [(n, f) for n, f in ALL_PROPERTIES if n.startswith("C")]
    elif args == ["--class", "division"] or args == ["-c", "division"]:
        properties = [(n, f) for n, f in ALL_PROPERTIES if n.startswith("D")]
    elif args == ["--class", "temporal"] or args == ["-c", "temporal"]:
        properties = [(n, f) for n, f in ALL_PROPERTIES if n.startswith("T")]
    elif args == ["--class", "vault"] or args == ["-c", "vault"]:
        properties = [(n, f) for n, f in ALL_PROPERTIES if n.startswith("V")]
    elif len(args) == 1:
        query = args[0]
        properties = [(n, f) for n, f in ALL_PROPERTIES if n.startswith(query)]
        if not properties:
            print(f"Unknown property: {query}")
            print("Available properties:")
            for name, _ in ALL_PROPERTIES:
                print(f"  {name}")
            sys.exit(1)
    else:
        print("Usage: python main.py [--class conservation|division|temporal] [property-id]")
        sys.exit(1)

    results = []
    for name, prop_fn in properties:
        preconditions, goal = prop_fn()
        results.append(run_proof(name, preconditions, goal))

    print(report_results(results))

    if all(r.status == ProofStatus.PROVED for r in results):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
