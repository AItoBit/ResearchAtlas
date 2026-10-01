from research_atlas.domain_packs.finite_graphs.checkers import (
    checker_a_odd_count_even,
    checker_b_handshake,
    exhaustive_scan,
    has_even_degree_vertex,
)
from research_atlas.domain_packs.finite_graphs.graphs import all_simple_graphs, graph_count, k2, path


def test_k2_is_counterexample_to_even_vertex():
    g = k2()
    assert g.degrees() == [1, 1]
    assert not has_even_degree_vertex(g)
    assert checker_a_odd_count_even(g)
    assert checker_b_handshake(g)


def test_path3_has_even_and_odd_vertices():
    g = path(3)
    assert g.degrees() == [1, 2, 1]
    assert has_even_degree_vertex(g)
    assert checker_a_odd_count_even(g)


def test_two_checkers_agree_on_all_n4():
    for g in all_simple_graphs(4):
        assert checker_a_odd_count_even(g) is checker_b_handshake(g)


def test_exhaustive_scan_is_complete_and_not_a_proof():
    result = exhaustive_scan(4, "odd_count_even")
    assert result["promotes_to_universal_proof"] is False
    for n, row in result["totals"].items():
        assert row["complete"] is True
        assert row["enumerated"] == graph_count(int(n))
        assert row["failures"] == 0
    assert "Labeled simple undirected graphs" in result["completeness_argument"]


def test_even_vertex_scan_finds_failures():
    result = exhaustive_scan(2, "has_even_degree_vertex")
    assert result["totals"]["2"]["failures"] >= 1
    assert result["promotes_to_universal_proof"] is False
