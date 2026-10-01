from pathlib import Path

import pytest

from research_atlas.knowledge.loop import KnowledgeLoop, ProposalRejected
from research_atlas.knowledge.store import KnowledgeStore
from research_atlas.models import (
    Edge,
    EvidenceLevel,
    FormalizationStatus,
    GraphProposal,
    Node,
    NodeType,
    Provenance,
    RelationType,
    ResearchStatus,
)


def _store(tmp_path: Path) -> KnowledgeStore:
    return KnowledgeStore(tmp_path / "k.sqlite", "test")


def _claim(**payload) -> Node:
    base = {
        "claim_id": "C-x",
        "statement_version": 1,
        "statement": "Every widget is blue.",
        "quantifiers": "for all widgets",
        "assumptions": ["widgets are finite"],
        "mathematical_domain": "test",
        "research_status": ResearchStatus.PROPOSED.value,
        "evidence_level": EvidenceLevel.HEURISTIC.value,
        "evidence_ids": [],
        "dependency_ids": [],
        "review_status": "unreviewed",
        "formalization_status": FormalizationStatus.NONE.value,
    }
    base.update(payload)
    return Node(
        type=NodeType.CLAIM,
        campaign_id="test",
        payload=base,
        provenance=Provenance(actor="test"),
    )


def test_claim_is_not_overwritten(tmp_path: Path):
    store = _store(tmp_path)
    loop = KnowledgeLoop(store)
    first = _claim()
    loop.commit(GraphProposal(actor="t", add_nodes=[first]))
    with pytest.raises(ProposalRejected, match="no_overwrite"):
        loop._validate_node(_claim())


def test_refutes_requires_example_version_and_verification(tmp_path: Path):
    store = _store(tmp_path)
    loop = KnowledgeLoop(store)
    claim = _claim()
    example = Node(
        type=NodeType.EXAMPLE,
        campaign_id="test",
        payload={"description": "red widget", "object_repr": {"color": "red"}, "verified_properties": {}},
        provenance=Provenance(actor="refuter"),
    )
    loop.commit(GraphProposal(actor="t", add_nodes=[claim, example]))
    bad = Edge(
        campaign_id="test",
        relation=RelationType.REFUTES,
        source_id=example.id,
        target_id=claim.id,
        target_version=None,
        provenance=Provenance(actor="refuter"),
    )
    with pytest.raises(ProposalRejected, match="refutes.version"):
        loop._validate_edge(bad, {})


def test_bounded_enumeration_cannot_be_formal_proof(tmp_path: Path):
    store = _store(tmp_path)
    loop = KnowledgeLoop(store)
    claim = _claim(
        evidence_level=EvidenceLevel.FORMAL_PROOF.value,
        formalization_status=FormalizationStatus.FAITHFUL.value,
        universe_covered="n<=4",
        formal_statement_faithfulness="faithful",
    )
    with pytest.raises(ProposalRejected, match="bounded_not_universal"):
        loop._validate_node(claim)


def test_partial_lean_cannot_be_formal_proof(tmp_path: Path):
    store = _store(tmp_path)
    loop = KnowledgeLoop(store)
    claim = _claim(
        evidence_level=EvidenceLevel.FORMAL_PROOF.value,
        formalization_status=FormalizationStatus.PARTIAL.value,
        formal_statement_faithfulness="partial — arithmetic only",
    )
    with pytest.raises(ProposalRejected, match="no_unfaithful_formal_proof"):
        loop._validate_node(claim)


def test_experiment_must_record_universe(tmp_path: Path):
    store = _store(tmp_path)
    loop = KnowledgeLoop(store)
    node = Node(
        type=NodeType.EXPERIMENT,
        campaign_id="test",
        payload={
            "program": "scan",
            "config": {},
            "coverage": "bounded exhaustive n<=3",
            "results": {"promotes_to_universal_proof": False},
        },
        provenance=Provenance(actor="experimenter"),
    )
    with pytest.raises(ProposalRejected, match="enumeration.universe"):
        loop._validate_node(node)
