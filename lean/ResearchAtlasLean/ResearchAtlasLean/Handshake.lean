/-
  ResearchAtlas Lean certificate (handshake campaign).

  Informal claim C-handshake:
    In every finite simple undirected graph, the number of odd-degree
    vertices is even.

  Informal argument:
    Each edge contributes 2 to the degree sum, so ∑ deg(v) = 2|E|.
    An even sum has even odd-count, because odd + odd is even.

  Formal coverage:
    This file proves the arithmetic facts used in that argument.
    It does **not** encode incidence graphs, so it is a faithful
    formalization of C-handshake-arithmetic and only a **partial**
    formalization of C-handshake.

  Policy: no proof gaps and no extra axioms.
-/

namespace ResearchAtlas.Handshake

/-- Twice the number of edges is even. -/
theorem twice_the_edge_count_is_even (edgeCount : Nat) :
    (2 * edgeCount) % 2 = 0 := by
  omega

/-- Two odd numbers sum to an even number (pairing odd-degree vertices). -/
theorem odd_plus_odd_is_even (a b : Nat)
    (ha : a % 2 = 1) (hb : b % 2 = 1) :
    (a + b) % 2 = 0 := by
  omega

/-- Two even numbers sum to an even number. -/
theorem even_plus_even_is_even (a b : Nat)
    (ha : a % 2 = 0) (hb : b % 2 = 0) :
    (a + b) % 2 = 0 := by
  omega

end ResearchAtlas.Handshake
