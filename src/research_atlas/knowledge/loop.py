"""Knowledge loop: validate proposals, version claims, detect conflicts.

Agents propose; verifiers produce evidence; system rules control state changes.
Workers never write scientific status directly.
"""

from __future__ import annotations

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
    ReviewStatus,
)

# Evidence that may never be promoted to a universal proof by itself.
NON_UNIVERSAL = {
    EvidenceLevel.NONE,
    EvidenceLevel.HEURISTIC,
    EvidenceLevel.EXPERIMENT,
    EvidenceLevel.BOUNDED_ENUMERATION,
}


class ProposalRejected(ValueError):
    def __init__(self, rule: str, reason: str):
        super().__init__(f"[{rule}] {reason}")
        self.rule = rule
        self.reason = reason


class KnowledgeLoop:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    def commit(self, proposal: GraphProposal) -> dict:
        """Validate a worker proposal and persist accepted changes."""
        report: dict = {
            "proposal_id": proposal.proposal_id,
            "accepted_nodes": [],
            "accepted_edges": [],
            "rejected": [],
            "conflicts": [],
            "invalidations": [],
            "duplicates": [],
        }

        pending_nodes: list[Node] = []
        for node in proposal.add_nodes:
            try:
                self._validate_node(node)
                pending_nodes.append(node)
            except ProposalRejected as exc:
                report["rejected"].append({"node": node.id, "rule": exc.rule, "reason": exc.reason})

        node_index = {n.id: n for n in pending_nodes}
        pending_edges: list[Edge] = []
        for edge in proposal.add_edges:
            try:
                self._validate_edge(edge, node_index)
                pending_edges.append(edge)
            except ProposalRejected as exc:
                report["rejected"].append({"edge": edge.id, "rule": exc.rule, "reason": exc.reason})

        for node in pending_nodes:
            self.store.add_node(node)
            report["accepted_nodes"].append(node.id)
        for edge in pending_edges:
            self.store.add_edge(edge)
            report["accepted_edges"].append(edge.id)

        report["conflicts"] = self.detect_conflicts()
        report["invalidations"] = self.invalidate_dependents()
        report["duplicates"] = self.store.statement_duplicates()
        self._open_reconciliation_questions(report["conflicts"])
        self.store.append_event("graph_committed", report)
        return report

    def _validate_node(self, node: Node) -> None:
        if node.type == NodeType.CLAIM:
            payload = node.payload
            if not payload.get("statement"):
                raise ProposalRejected("claim.statement", "Claim must have a precise statement.")
            if not payload.get("assumptions") and payload.get("quantifiers") != "none":
                # Empty assumptions are allowed only when explicitly recorded as such.
                if payload.get("assumptions") is None:
                    raise ProposalRejected("claim.hypotheses", "Hypotheses must be explicit (use [] if none).")
            if not payload.get("claim_id"):
                raise ProposalRejected("claim.id", "claim_id is required for versioning.")
            if payload.get("evidence_level") == EvidenceLevel.FORMAL_PROOF.value:
                faithfulness = payload.get("formal_statement_faithfulness") or ""
                if payload.get("formalization_status") != FormalizationStatus.FAITHFUL.value:
                    raise ProposalRejected(
                        "no_unfaithful_formal_proof",
                        "Formal proof evidence requires a faithful formalization of the informal statement.",
                    )
                if "partial" in faithfulness.lower():
                    raise ProposalRejected(
                        "no_unfaithful_formal_proof",
                        "Partial Lean coverage cannot promote a claim to formal_proof.",
                    )
            if payload.get("evidence_level") == EvidenceLevel.FORMAL_PROOF.value and payload.get(
                "universe_covered"
            ):
                raise ProposalRejected(
                    "bounded_not_universal",
                    "A bounded check must not be recorded as a universal formal proof.",
                )
            existing = self.store.claim_by_logical_id(
                payload["claim_id"], payload.get("statement_version")
            )
            if existing is not None:
                raise ProposalRejected(
                    "no_overwrite",
                    f"Claim {payload['claim_id']} v{payload.get('statement_version')} already exists; "
                    "create a new version instead of overwriting.",
                )

        if node.type == NodeType.EXPERIMENT:
            results = node.payload.get("results") or {}
            coverage = node.payload.get("coverage") or ""
            if results.get("promotes_to_universal_proof"):
                raise ProposalRejected(
                    "bounded_not_universal",
                    "An experiment must not declare itself a universal proof.",
                )
            if "exhaustive" in coverage.lower() or "bounded" in coverage.lower():
                if not node.payload.get("config", {}).get("universe"):
                    raise ProposalRejected(
                        "enumeration.universe",
                        "Bounded exhaustive checks must record the finite universe they cover.",
                    )

        if node.type == NodeType.PROOF_ATTEMPT:
            gaps = node.payload.get("gaps") or []
            if gaps and node.payload.get("status") == "accepted":
                raise ProposalRejected(
                    "no_gaps",
                    "A proof attempt with recorded gaps cannot be accepted.",
                )

    def _validate_edge(self, edge: Edge, pending: dict[str, Node]) -> None:
        source = pending.get(edge.source_id) or self.store.get_node(edge.source_id)
        target = pending.get(edge.target_id) or self.store.get_node(edge.target_id)
        if source is None or target is None:
            raise ProposalRejected("edge.endpoints", "Both endpoints of an edge must exist.")

        if not edge.provenance.actor:
            raise ProposalRejected("edge.provenance", "Every relation must have provenance.")

        if edge.relation == RelationType.REFUTES:
            if source.type != NodeType.EXAMPLE:
                raise ProposalRejected("refutes.source", "A refutation must come from a concrete example.")
            if target.type != NodeType.CLAIM:
                raise ProposalRejected("refutes.target", "A refutation must target a claim.")
            version = target.payload.get("statement_version")
            if edge.target_version is None or edge.target_version != version:
                raise ProposalRejected(
                    "refutes.version",
                    "A refutes edge must identify the exact statement version it contradicts.",
                )
            if not edge.provenance.evidence_ids:
                raise ProposalRejected(
                    "refutes.evidence",
                    "A refutes edge must cite the verification that checked the counterexample.",
                )

        if edge.relation == RelationType.SUPPORTS:
            if target.type != NodeType.CLAIM:
                raise ProposalRejected("supports.target", "supports must target a claim.")
            if edge.target_version is not None and edge.target_version != target.payload.get(
                "statement_version"
            ):
                raise ProposalRejected(
                    "supports.version",
                    "Evidence must be bound to the exact claim version it supports.",
                )

    def detect_conflicts(self) -> list[dict]:
        conflicts: list[dict] = []
        by_logical: dict[str, list[Node]] = {}
        for claim in self.store.claims():
            by_logical.setdefault(claim.payload["claim_id"], []).append(claim)

        for claim in self.store.claims():
            supports = [e for e in self.store.edges_to(claim.id) if e.relation == RelationType.SUPPORTS]
            refutes = [e for e in self.store.edges_to(claim.id) if e.relation == RelationType.REFUTES]
            if supports and refutes:
                conflicts.append(
                    {
                        "type": "support_and_refute",
                        "claim_node": claim.id,
                        "claim_id": claim.payload.get("claim_id"),
                        "version": claim.payload.get("statement_version"),
                        "questions": [
                            "Do the results use the same definition?",
                            "Do their domains and quantifiers match?",
                            "Is a hypothesis missing?",
                            "Is there an experimental error?",
                            "Does the formalization express a different claim?",
                        ],
                    }
                )
            if (
                claim.payload.get("research_status") == ResearchStatus.REFUTED.value
                and claim.payload.get("evidence_level")
                in {EvidenceLevel.REVIEWED_PROOF.value, EvidenceLevel.FORMAL_PROOF.value}
            ):
                conflicts.append(
                    {
                        "type": "refuted_but_proved",
                        "claim_node": claim.id,
                        "claim_id": claim.payload.get("claim_id"),
                    }
                )
        return conflicts

    def invalidate_dependents(self) -> list[dict]:
        """When a claim is refuted, dependents that use it need revalidation.

        A failure has scope: it blocks a strategy under stated conditions; it does
        not automatically falsify every related result.
        """
        invalidations: list[dict] = []
        refuted = [
            n
            for n in self.store.claims()
            if n.payload.get("research_status") == ResearchStatus.REFUTED.value
        ]
        for claim in refuted:
            for edge in self.store.edges_from(claim.id):
                if edge.relation != RelationType.USES:
                    continue
                dependent = self.store.get_node(edge.target_id)
                if dependent is None or dependent.type != NodeType.CLAIM:
                    continue
                if dependent.payload.get("review_status") == ReviewStatus.NEEDS_REVALIDATION.value:
                    continue
                dependent.payload["review_status"] = ReviewStatus.NEEDS_REVALIDATION.value
                self._rewrite_node_payload(dependent)
                invalidations.append(
                    {
                        "from": claim.id,
                        "dependent": dependent.id,
                        "scope": "uses_refuted_claim",
                        "note": "Dependent marked for revalidation; not automatically false.",
                    }
                )
        return invalidations

    def apply_refutation(self, claim_node: Node, reason: str) -> Node:
        """Mark a specific version refuted without deleting it."""
        if claim_node.payload.get("research_status") == ResearchStatus.REFUTED.value:
            return claim_node
        claim_node.payload["research_status"] = ResearchStatus.REFUTED.value
        claim_node.payload["review_status"] = ReviewStatus.OBJECTED.value
        self.update_payload(claim_node)
        self.store.append_event(
            "claim_refuted",
            {
                "node_id": claim_node.id,
                "claim_id": claim_node.payload.get("claim_id"),
                "version": claim_node.payload.get("statement_version"),
                "reason": reason,
            },
        )
        return claim_node

    def new_claim_version(self, previous: Node, updates: dict, provenance: Provenance) -> Node:
        """Create a successor version. The refuted (or previous) record stays intact."""
        payload = dict(previous.payload)
        next_version = self.store.latest_claim_version(payload["claim_id"]) + 1
        payload.update(updates)
        payload["statement_version"] = next_version
        payload["parent_claim_id"] = previous.payload["claim_id"]
        node = Node(
            type=NodeType.CLAIM,
            campaign_id=self.store.campaign_id,
            payload=payload,
            provenance=provenance,
        )
        previous.payload["superseded_by"] = node.id
        self._rewrite_node_payload(previous)
        return node

    def _open_reconciliation_questions(self, conflicts: list[dict]) -> None:
        existing = {
            n.payload.get("text")
            for n in self.store.nodes(NodeType.QUESTION)
            if n.payload.get("text", "").startswith("Reconcile:")
        }
        for conflict in conflicts:
            text = (
                f"Reconcile: claim {conflict.get('claim_id')} "
                f"v{conflict.get('version')} has type {conflict.get('type')}"
            )
            if text in existing:
                continue
            node = Node(
                type=NodeType.QUESTION,
                campaign_id=self.store.campaign_id,
                payload={
                    "text": text,
                    "resolution_criteria": " ; ".join(conflict.get("questions") or ["Resolve incompatibility."]),
                    "status": "open",
                    "parent_question_id": None,
                },
                provenance=Provenance(actor="knowledge_loop", notes="auto-opened from conflict"),
            )
            self.store.add_node(node)

    def update_payload(self, node: Node) -> None:
        """Persist status/evidence flags. Never changes statement text or version."""
        if node.type == NodeType.CLAIM:
            level = node.payload.get("evidence_level")
            if level == EvidenceLevel.FORMAL_PROOF.value:
                if node.payload.get("formalization_status") != FormalizationStatus.FAITHFUL.value:
                    raise ProposalRejected(
                        "no_unfaithful_formal_proof",
                        "Cannot store formal_proof unless the formal statement is faithful.",
                    )
                if node.payload.get("universe_covered"):
                    raise ProposalRejected(
                        "bounded_not_universal",
                        "A claim that records a bounded universe cannot be a formal proof.",
                    )
            if level in {
                EvidenceLevel.FORMAL_PROOF.value,
                EvidenceLevel.REVIEWED_PROOF.value,
            } and (node.payload.get("universe_covered") and level == EvidenceLevel.FORMAL_PROOF.value):
                raise ProposalRejected("bounded_not_universal", "Bounded coverage is not a formal proof.")
        self._rewrite_node_payload(node)

    def _rewrite_node_payload(self, node: Node) -> None:
        """Internal payload mutation for status flags. Not a statement overwrite."""
        import json

        self.store._conn.execute(
            "UPDATE nodes SET payload = ? WHERE id = ?",
            (json.dumps(node.payload, default=str), node.id),
        )
        self.store._conn.commit()
        self.store.append_event(
            "node_payload_updated",
            {
                "node_id": node.id,
                "type": node.type.value,
                "research_status": node.payload.get("research_status"),
                "review_status": node.payload.get("review_status"),
                "evidence_level": node.payload.get("evidence_level"),
            },
        )

    def frontier_summary(self) -> dict:
        claims = self.store.claims()
        questions = self.store.nodes(NodeType.QUESTION)
        obstacles = self.store.nodes(NodeType.OBSTACLE)
        return {
            "open_questions": [n.id for n in questions if n.payload.get("status") == "open"],
            "open_claims": [
                n.id
                for n in claims
                if n.payload.get("research_status")
                in {ResearchStatus.PROPOSED.value, ResearchStatus.ACTIVE.value, ResearchStatus.OPEN.value}
            ],
            "refuted_claims": [
                n.id for n in claims if n.payload.get("research_status") == ResearchStatus.REFUTED.value
            ],
            "established_claims": [
                n.id for n in claims if n.payload.get("research_status") == ResearchStatus.ESTABLISHED.value
            ],
            "obstacles": [n.id for n in obstacles],
            "conflicts": self.detect_conflicts(),
        }
