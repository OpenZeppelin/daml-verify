"""Output formatting: proved/disproved/unknown with counterexample display."""

from daml_verify.prover import ProofResult, ProofStatus


def report_results(results: list[ProofResult]) -> str:
    """Format all proof results into a summary report."""
    total = len(results)
    proved = sum(1 for r in results if r.status == ProofStatus.PROVED)
    disproved = sum(1 for r in results if r.status == ProofStatus.DISPROVED)

    lines = [
        f"daml-verify: {total} properties, {proved} proved, {disproved} disproved",
        "",
    ]
    for r in results:
        lines.append(format_result(r))
    return "\n".join(lines)


def format_result(r: ProofResult) -> str:
    """Format a single proof result."""
    if r.status == ProofStatus.PROVED:
        return f"  [PROVED] {r.name}"
    elif r.status == ProofStatus.DISPROVED:
        ce = _indent(r.counterexample or "")
        return f"  [DISPROVED] {r.name}\n    Counterexample:\n{ce}"
    else:
        return f"  [UNKNOWN] {r.name} ({r.counterexample or 'no reason'})"


def _indent(text: str) -> str:
    return "\n".join(f"      {line}" for line in text.splitlines())
