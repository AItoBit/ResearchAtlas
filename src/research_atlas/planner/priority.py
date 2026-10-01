"""Explainable priority queue for the research frontier.

priority(a) = (w_I I + w_U U + w_R R + w_C C) / (1 + w_T T + w_B B)

These are operational estimates, not certified probabilities.
Cheap refutations are preferred to expensive proofs; conflicts are boosted;
a small exploration quota keeps alternative directions alive.
"""

from __future__ import annotations

from research_atlas.models import Action, PlannerWeights


def score(action: Action, weights: PlannerWeights) -> float:
    numer = (
        weights.I * action.information_gain
        + weights.U * action.uncertainty_resolution
        + weights.R * action.reuse_potential
        + weights.C * action.conflict_importance
    )
    denom = 1.0 + weights.T * action.estimated_time + weights.B * action.execution_cost
    return numer / denom


def explain(action: Action, weights: PlannerWeights) -> str:
    s = score(action, weights)
    return (
        f"priority={s:.3f} because I={action.information_gain:.2f}, "
        f"U={action.uncertainty_resolution:.2f}, R={action.reuse_potential:.2f}, "
        f"C={action.conflict_importance:.2f} over T={action.estimated_time:.2f}, "
        f"B={action.execution_cost:.2f} ({action.type.value})"
    )


def select(
    actions: list[Action],
    completed: set[str],
    weights: PlannerWeights,
    step: int,
    explore_every: int = 7,
) -> Action | None:
    ready = []
    for action in actions:
        if action.id in completed:
            continue
        if any(req not in completed for req in action.prerequisites):
            continue
        ready.append(action)
    if not ready:
        return None
    ranked = sorted(ready, key=lambda a: score(a, weights), reverse=True)
    chosen = ranked[0]
    if explore_every and step > 0 and step % explore_every == 0 and len(ranked) > 1:
        chosen = ranked[1]
    chosen.explanation = explain(chosen, weights)
    if chosen is not ranked[0]:
        chosen.explanation += " [exploration quota: not the top-scoring action]"
    return chosen
