"""Finite undirected simple graphs on labeled vertices."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterator


def _canon_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


@dataclass(frozen=True)
class SimpleGraph:
    n: int
    edges: frozenset[tuple[int, int]]

    def __post_init__(self) -> None:
        cleaned = frozenset(_canon_edge(u, v) for u, v in self.edges if u != v)
        object.__setattr__(self, "edges", cleaned)

    def to_dict(self) -> dict:
        return {"n": self.n, "edges": [list(e) for e in sorted(self.edges)]}

    @classmethod
    def from_dict(cls, data: dict) -> SimpleGraph:
        edges = frozenset(tuple(e) for e in data["edges"])
        return cls(n=int(data["n"]), edges=edges)

    def degrees(self) -> list[int]:
        deg = [0] * self.n
        for u, v in self.edges:
            deg[u] += 1
            deg[v] += 1
        return deg

    def odd_degree_vertices(self) -> list[int]:
        return [i for i, d in enumerate(self.degrees()) if d % 2 == 1]

    def odd_degree_count(self) -> int:
        return len(self.odd_degree_vertices())

    def has_even_degree_vertex(self) -> bool:
        return any(d % 2 == 0 for d in self.degrees())

    def degree_sum(self) -> int:
        return sum(self.degrees())

    def edge_count(self) -> int:
        return len(self.edges)


def complete(n: int) -> SimpleGraph:
    return SimpleGraph(n=n, edges=frozenset(combinations(range(n), 2)))


def empty(n: int) -> SimpleGraph:
    return SimpleGraph(n=n, edges=frozenset())


def path(n: int) -> SimpleGraph:
    return SimpleGraph(n=n, edges=frozenset((i, i + 1) for i in range(n - 1)))


def cycle(n: int) -> SimpleGraph:
    if n < 3:
        raise ValueError("cycle requires n >= 3")
    edges = {(i, i + 1) for i in range(n - 1)}
    edges.add((0, n - 1))
    return SimpleGraph(n=n, edges=frozenset(edges))


def k2() -> SimpleGraph:
    """Single edge: the standard counterexample to 'every graph has an even-degree vertex'."""
    return SimpleGraph(n=2, edges=frozenset({(0, 1)}))


def all_simple_graphs(n: int) -> Iterator[SimpleGraph]:
    possible = list(combinations(range(n), 2))
    m = len(possible)
    for mask in range(1 << m):
        edges = frozenset(possible[i] for i in range(m) if mask & (1 << i))
        yield SimpleGraph(n=n, edges=edges)


def graph_count(n: int) -> int:
    return 1 << (n * (n - 1) // 2)
