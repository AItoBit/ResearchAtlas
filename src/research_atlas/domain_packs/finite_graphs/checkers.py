"""Two independent checkers for degree-parity facts.

Repeating the same program can reproduce the same bug; the second checker
uses a different code path.
"""

from __future__ import annotations

from research_atlas.domain_packs.finite_graphs.graphs import SimpleGraph


def checker_a_odd_count_even(g: SimpleGraph) -> bool:
    """Count odd degrees from the adjacency list."""
    return g.odd_degree_count() % 2 == 0


def checker_b_handshake(g: SimpleGraph) -> bool:
    """Handshaking identity: sum(deg) == 2|E|, hence even, hence even odd-count.

    Implemented without calling odd_degree_count, so it cannot share that bug.
    """
    deg_sum = 0
    for u, v in g.edges:
        deg_sum += 2
    if deg_sum != 2 * g.edge_count():
        return False
    # Parity of the number of odds equals parity of the sum.
    odds = 0
    seen = [0] * g.n
    for u, v in g.edges:
        seen[u] += 1
        seen[v] += 1
    for d in seen:
        odds ^= d & 1
    return (deg_sum % 2 == 0) and (odds == 0)


def has_even_degree_vertex(g: SimpleGraph) -> bool:
    return g.has_even_degree_vertex()


def exhaustive_scan(n_max: int, predicate_name: str) -> dict:
    from research_atlas.domain_packs.finite_graphs.graphs import all_simple_graphs, graph_count

    universe = list(range(1, n_max + 1))
    completeness = (
        f"Labeled simple undirected graphs on n vertices, n in {universe}. "
        f"There are 2^(n(n-1)/2) such graphs; every adjacency subset is enumerated."
    )
    failures: list[dict] = []
    totals = {}
    for n in universe:
        count = 0
        fail = 0
        for g in all_simple_graphs(n):
            count += 1
            if predicate_name == "has_even_degree_vertex":
                ok = has_even_degree_vertex(g)
            elif predicate_name == "odd_count_even":
                ok_a = checker_a_odd_count_even(g)
                ok_b = checker_b_handshake(g)
                ok = ok_a and ok_b
                if ok_a != ok_b:
                    failures.append({"n": n, "edges": g.to_dict(), "reason": "checkers_disagree"})
            else:
                raise ValueError(predicate_name)
            if not ok:
                fail += 1
                if len(failures) < 8:
                    failures.append(g.to_dict())
        totals[str(n)] = {
            "enumerated": count,
            "expected": graph_count(n),
            "complete": count == graph_count(n),
            "failures": fail,
        }
    return {
        "universe": f"labeled simple graphs, n=1..{n_max}",
        "universe_ns": universe,
        "completeness_argument": completeness,
        "predicate": predicate_name,
        "totals": totals,
        "failures": failures,
        "promotes_to_universal_proof": False,
        "checkers": ["checker_a_odd_count_even", "checker_b_handshake"]
        if predicate_name == "odd_count_even"
        else ["has_even_degree_vertex"],
    }
