from __future__ import annotations

import json
import shutil
from pathlib import Path

from research_atlas.domain_packs.finite_graphs.pack import (
    CLAIM_ARITHMETIC,
    CLAIM_EVEN_VERTEX,
    CLAIM_HANDSHAKE,
)
from research_atlas.knowledge.store import KnowledgeStore
from research_atlas.models import EvidenceLevel, RelationType, ResearchStatus
from research_atlas.orchestrator import run_campaign
from research_atlas.paths import ROOT, campaign_db
from research_atlas.reporting.markdown import render
from research_atlas.domain_packs.finite_graphs.checkers import exhaustive_scan


def _prepare(tmp_path: Path, monkeypatch) -> Path:
    campaigns = tmp_path / "campaigns"
    dest = campaigns / "handshake"
    dest.mkdir(parents=True)
    src = ROOT / "campaigns" / "handshake" / "campaign.yaml"
    shutil.copy(src, dest / "campaign.yaml")
    monkeypatch.setattr("research_atlas.paths.CAMPAIGNS", campaigns)
    return dest


def test_full_calibration_campaign(tmp_path: Path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    result = run_campaign("handshake")
    assert "act.refute.k2" in result["completed"]
    assert "act.formalize.arithmetic" in result["completed"]

    store = KnowledgeStore(campaign_db("handshake"), "handshake")
    even = store.claim_by_logical_id(CLAIM_EVEN_VERTEX, 1)
    handshake = store.claim_by_logical_id(CLAIM_HANDSHAKE)
    arithmetic = store.claim_by_logical_id(CLAIM_ARITHMETIC)
    assert even is not None and handshake is not None and arithmetic is not None

    assert even.payload["research_status"] == ResearchStatus.REFUTED.value
    refute_edges = [e for e in store.edges(RelationType.REFUTES) if e.target_id == even.id]
    assert len(refute_edges) == 1
    assert refute_edges[0].target_version == 1

    # Bounded enumeration must not be the terminal evidence for the graph theorem.
    assert handshake.payload["evidence_level"] == EvidenceLevel.REVIEWED_PROOF.value
    assert handshake.payload["research_status"] == ResearchStatus.ESTABLISHED.value
    assert handshake.payload["formalization_status"] == "partial"
    assert handshake.payload["evidence_level"] != EvidenceLevel.FORMAL_PROOF.value
    if arithmetic.payload.get("formalization_status") == "faithful":
        assert arithmetic.payload["evidence_level"] == EvidenceLevel.FORMAL_PROOF.value
        assert arithmetic.payload["research_status"] == ResearchStatus.ESTABLISHED.value

    # The refuted statement is still in the graph (new claim, not an overwrite).
    still = store.claim_by_logical_id(CLAIM_EVEN_VERTEX, 1)
    assert still is not None
    assert "even degree" in still.payload["statement"]
    assert handshake.payload["statement"] != still.payload["statement"]

    examples = store.nodes()
    assert any(n.type.value == "Example" for n in examples)

    report = render(store, store.load_config())
    assert "Established" in report
    assert "Refuted" in report
    assert "never becomes a universal proof" in report
    assert Path(result["report"]).exists()

    experiments = [n for n in store.nodes() if n.type.value == "Experiment"]
    n5 = [e for e in experiments if (e.payload.get("config") or {}).get("n_max") == 5]
    assert n5
    assert n5[0].payload["results"]["promotes_to_universal_proof"] is False
    assert n5[0].payload["checkers_agree"] is True

    store.close()


def test_resume_does_not_duplicate_claims(tmp_path: Path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    run_campaign("handshake", max_steps=2)
    store = KnowledgeStore(campaign_db("handshake"), "handshake")
    after_two = len(store.claims())
    steps = store.get_meta("step")
    store.close()
    assert steps == 2

    run_campaign("handshake")
    store = KnowledgeStore(campaign_db("handshake"), "handshake")
    # Resumed run continues; it must not re-seed or clone the same claim versions.
    even_versions = [
        n for n in store.claims() if n.payload.get("claim_id") == CLAIM_EVEN_VERTEX
    ]
    assert len(even_versions) == 1
    assert store.get_meta("step") >= 2
    assert len(store.claims()) >= after_two
    store.close()


def test_experiment_replay_from_manifest(tmp_path: Path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    run_campaign("handshake", max_steps=1)
    store = KnowledgeStore(campaign_db("handshake"), "handshake")
    experiments = [n for n in store.nodes() if n.type.value == "Experiment"]
    assert experiments
    digest = experiments[0].payload["manifesto_hash"]
    payload_path = tmp_path / "campaigns" / "handshake" / "artifacts" / digest / "payload.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    inner = payload["config"]
    again = exhaustive_scan(inner["n_max"], inner["predicate"])
    assert again["totals"] == payload["results"]["totals"]
    store.close()
