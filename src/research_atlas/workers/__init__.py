"""Sequential worker: one role per turn, proposals only.

Select → retrieve → propose → execute → verify (inside the domain pack)
→ record as a GraphProposal → knowledge loop commits.
"""

from __future__ import annotations

from research_atlas.domain_packs.base import DomainPack
from research_atlas.domain_packs.finite_graphs.pack import CLAIM_ARITHMETIC, CLAIM_HANDSHAKE
from research_atlas.knowledge.loop import KnowledgeLoop
from research_atlas.knowledge.store import KnowledgeStore
from research_atlas.models import (
    Action,
    EvidenceLevel,
    FormalizationStatus,
    GraphProposal,
    NodeType,
    ResearchStatus,
    ReviewStatus,
)
from research_atlas.retrieval import load_context


class SequentialWorker:
    def __init__(self, store: KnowledgeStore, knowledge: KnowledgeLoop, pack: DomainPack):
        self.store = store
        self.knowledge = knowledge
        self.pack = pack

    def run_move(self, action: Action) -> dict:
        context = load_context(self.store, action)
        self.store.append_event(
            "action_selected",
            {
                "action_id": action.id,
                "role": action.role.value,
                "explanation": action.explanation,
                "verification_plan": action.verification_plan,
                "context_claim_count": len(context["claims"]),
            },
        )
        result = self.pack.execute(action, self.store)
        proposal = GraphProposal(
            actor=action.role.value,
            add_nodes=result.get("nodes") or [],
            add_edges=result.get("edges") or [],
            notes=result.get("notes") or "",
        )
        commit = self.knowledge.commit(proposal)
        post = self._after_commit(action, result)
        self.store.append_event(
            "action_executed",
            {"action_id": action.id, "commit": _summarize(commit), "post": post},
        )
        return {"action": action, "commit": commit, "post": post, "result": result}

    def _after_commit(self, action: Action, result: dict) -> dict:
        notes: dict = {}
        if result.get("refute_claim_id"):
            claim = self.store.claim_by_logical_id(result["refute_claim_id"], 1)
            if claim is not None:
                self.knowledge.apply_refutation(claim, result.get("refute_reason", "counterexample"))
                notes["refuted"] = claim.id

        if action.id == "act.experiment.n5":
            claim = self.store.claim_by_logical_id(CLAIM_HANDSHAKE)
            if claim is not None:
                experiments = self.store.nodes(NodeType.EXPERIMENT)
                latest = experiments[-1] if experiments else None
                claim.payload["evidence_level"] = EvidenceLevel.BOUNDED_ENUMERATION.value
                claim.payload["research_status"] = ResearchStatus.OPEN.value
                if latest:
                    claim.payload["evidence_ids"] = list(
                        dict.fromkeys(claim.payload.get("evidence_ids", []) + [latest.id])
                    )
                    claim.payload["universe_covered"] = (latest.payload.get("config") or {}).get("universe")
                    claim.payload["completeness_argument"] = latest.payload.get("coverage")
                self.knowledge.update_payload(claim)
                notes["bounded_evidence_bound"] = claim.id

        if result.get("accept_proof"):
            proof = self.store.get_node(result["proof_id"])
            if proof is not None:
                proof.payload["status"] = "accepted"
                self.knowledge.update_payload(proof)
            claim = self.store.claim_by_logical_id(CLAIM_HANDSHAKE)
            if claim is not None:
                claim.payload["research_status"] = ResearchStatus.ESTABLISHED.value
                claim.payload["evidence_level"] = EvidenceLevel.REVIEWED_PROOF.value
                claim.payload["review_status"] = ReviewStatus.ACCEPTED.value
                claim.payload["formalization_status"] = FormalizationStatus.NONE.value
                if result.get("verification_id"):
                    claim.payload["evidence_ids"] = list(
                        dict.fromkeys(
                            claim.payload.get("evidence_ids", []) + [result["verification_id"]]
                        )
                    )
                self.knowledge.update_payload(claim)
                notes["established_reviewed"] = claim.id

        if "lean_compiled" in result:
            arithmetic = self.store.claim_by_logical_id(CLAIM_ARITHMETIC)
            handshake = self.store.claim_by_logical_id(CLAIM_HANDSHAKE)
            cert = result.get("lean_certificate") or {}
            if arithmetic is not None:
                arithmetic.payload["formal_statement_faithfulness"] = (
                    "faithful for the two arithmetic theorems; does not encode graphs"
                )
                if result.get("lean_compiled"):
                    arithmetic.payload["formalization_status"] = FormalizationStatus.FAITHFUL.value
                    arithmetic.payload["evidence_level"] = EvidenceLevel.FORMAL_PROOF.value
                    arithmetic.payload["research_status"] = ResearchStatus.ESTABLISHED.value
                    arithmetic.payload["review_status"] = ReviewStatus.ACCEPTED.value
                else:
                    arithmetic.payload["formalization_status"] = (
                        FormalizationStatus.UNAVAILABLE.value
                        if cert.get("build_result") == "lean_unavailable"
                        else FormalizationStatus.PARTIAL.value
                    )
                if result.get("verification_id"):
                    arithmetic.payload["evidence_ids"] = list(
                        dict.fromkeys(
                            arithmetic.payload.get("evidence_ids", []) + [result["verification_id"]]
                        )
                    )
                self.knowledge.update_payload(arithmetic)
                notes["arithmetic"] = arithmetic.payload["formalization_status"]
            if handshake is not None:
                handshake.payload["formalization_status"] = FormalizationStatus.PARTIAL.value
                handshake.payload["formal_statement_faithfulness"] = cert.get("faithfulness")
                # Must remain a reviewed proof, not a formal proof of the graph theorem.
                if handshake.payload.get("evidence_level") == EvidenceLevel.FORMAL_PROOF.value:
                    handshake.payload["evidence_level"] = EvidenceLevel.REVIEWED_PROOF.value
                self.knowledge.update_payload(handshake)
                notes["handshake_faithfulness"] = "partial"
            for question in self.store.nodes(NodeType.QUESTION):
                if question.payload.get("status") != "open":
                    continue
                if str(question.payload.get("text", "")).startswith("Reconcile:"):
                    continue
                question.payload["status"] = "resolved"
                self.knowledge.update_payload(question)
                notes["question_resolved"] = question.id
        return notes


def _summarize(commit: dict) -> dict:
    return {
        "accepted_nodes": commit.get("accepted_nodes"),
        "accepted_edges": commit.get("accepted_edges"),
        "rejected": commit.get("rejected"),
        "conflicts": commit.get("conflicts"),
    }
