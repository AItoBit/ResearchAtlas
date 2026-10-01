"""Independent checkers for counterexamples.

A valid counterexample must satisfy the hypotheses and fail the conclusion
of the exact statement version it targets.
"""

from __future__ import annotations

from typing import Any, Callable

Predicate = Callable[[dict[str, Any]], bool]


def check_counterexample(
    obj: dict[str, Any],
    hypotheses: list[Callable[[dict[str, Any]], bool]],
    conclusion: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    hyp_results = [h(obj) for h in hypotheses]
    hypotheses_hold = all(hyp_results)
    conclusion_holds = conclusion(obj)
    is_counterexample = hypotheses_hold and not conclusion_holds
    return {
        "hypotheses_hold": hypotheses_hold,
        "hypothesis_results": hyp_results,
        "conclusion_holds": conclusion_holds,
        "is_counterexample": is_counterexample,
    }
