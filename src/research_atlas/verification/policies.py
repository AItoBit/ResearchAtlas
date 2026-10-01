"""Verification policies: agents propose, only checks change scientific status.

A second model saying a proof looks good is not a formal verification.
Bounded exhaustive checks never become universal proofs.
"""

from __future__ import annotations

import re

from research_atlas.models import EvidenceLevel, FormalizationStatus

FORBIDDEN_LEAN_IDENTIFIERS = ("sorry", "admit", "axiom", "unsafe")

# Foundational dependencies the project accepts (Lean core, not ad-hoc axioms).
ACCEPTED_FOUNDATIONS = {"Lean.core", "Init", "omega"}


def evidence_may_establish(level: EvidenceLevel) -> bool:
    return level in {EvidenceLevel.REVIEWED_PROOF, EvidenceLevel.FORMAL_PROOF}


def bounded_cannot_be_universal(level: EvidenceLevel) -> None:
    if level == EvidenceLevel.FORMAL_PROOF:
        raise ValueError("bounded enumeration cannot be recorded as a formal proof")
    if level == EvidenceLevel.REVIEWED_PROOF:
        raise ValueError("bounded enumeration cannot be recorded as a reviewed proof")


def lean_source_allowed(source: str) -> tuple[bool, list[str]]:
    """Reject gap tactics and extra axioms. Comments are ignored."""
    without_block = re.sub(r"/-.*?-/", " ", source, flags=re.S)
    lines = []
    for line in without_block.splitlines():
        cut = line.split("--", 1)[0]
        lines.append(cut)
    text = "\n".join(lines)
    hits = [tok for tok in FORBIDDEN_LEAN_IDENTIFIERS if re.search(rf"\b{tok}\b", text)]
    return (not hits, hits)


def faithfulness_allows_formal_proof(status: FormalizationStatus, note: str) -> bool:
    if status != FormalizationStatus.FAITHFUL:
        return False
    return "partial" not in note.lower()
