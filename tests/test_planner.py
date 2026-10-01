from research_atlas.models import Action, ActionType, PlannerWeights, Role
from research_atlas.planner.priority import explain, score, select


def test_priority_formula():
    weights = PlannerWeights(I=1, U=1, R=1, C=1, T=1, B=1)
    action = Action(
        type=ActionType.REFUTE,
        role=Role.REFUTER,
        description="cheap refutation",
        verification_plan="check object",
        information_gain=1,
        uncertainty_resolution=0,
        reuse_potential=0,
        conflict_importance=0,
        estimated_time=0,
        execution_cost=0,
    )
    assert score(action, weights) == 1.0
    action.execution_cost = 1
    assert score(action, weights) == 0.5


def test_select_respects_prerequisites_and_explains():
    weights = PlannerWeights()
    a1 = Action(
        id="a1",
        type=ActionType.EXPERIMENT,
        role=Role.EXPERIMENTER,
        description="first",
        verification_plan="rerun",
        information_gain=0.1,
        uncertainty_resolution=0.1,
    )
    a2 = Action(
        id="a2",
        type=ActionType.REFUTE,
        role=Role.REFUTER,
        description="second",
        verification_plan="counterexample",
        information_gain=1.0,
        uncertainty_resolution=1.0,
        prerequisites=["a1"],
    )
    chosen = select([a1, a2], completed=set(), weights=weights, step=0)
    assert chosen is not None
    assert chosen.id == "a1"
    assert "priority=" in explain(chosen, weights)
    chosen2 = select([a1, a2], completed={"a1"}, weights=weights, step=1)
    assert chosen2 is not None
    assert chosen2.id == "a2"
