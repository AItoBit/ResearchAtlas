"""Finite simple graphs domain pack: handshake-lemma calibration campaign.

Calibration path:
  question → experiment (n=1) → false conjecture → K2 counterexample
  → corrected statement → bounded enumeration → informal proof
  → Lean arithmetic certificate → map update.

Known results are used to check that the system records evidence honestly:
a bounded check never becomes a universal proof, and a partial Lean
development does not promote the graph-theoretic claim to formal_proof.
"""

from __future__ import annotations

import json

from research_atlas.domain_packs.base import DomainPack
from research_atlas.domain_packs.finite_graphs.checkers import exhaustive_scan
from research_atlas.domain_packs.finite_graphs.graphs import k2
from research_atlas.knowledge.store import KnowledgeStore
from research_atlas.models import (
    Action,
    ActionType,
    CampaignConfig,
    Edge,
    EvidenceLevel,
    ExamplePayload,
    ExperimentPayload,
    FormalizationStatus,
    Node,
    NodeType,
    ObstaclePayload,
    ProofAttemptPayload,
    Provenance,
    QuestionPayload,
    RelationType,
    ResearchStatus,
    ReviewStatus,
    Role,
    VerificationPayload,
)
from research_atlas.verification import write_artifact
from research_atlas.verification.counterexamples import check_counterexample
from research_atlas.verification.lean import try_compile


CLAIM_EVEN_VERTEX = "C-even-vertex"
CLAIM_HANDSHAKE = "C-handshake"
CLAIM_ARITHMETIC = "C-handshake-arithmetic"
QUESTION_DEGREES = "Q-degree-constraints"


def _prov(
    actor: str,
    notes: str = "",
    evidence_ids: list[str] | None = None,
    artifact_hashes: list[str] | None = None,
) -> Provenance:
    return Provenance(
        actor=actor,
        notes=notes,
        evidence_ids=evidence_ids or [],
        artifact_hashes=artifact_hashes or [],
    )


def _node(store: KnowledgeStore, type: NodeType, payload: dict, actor: str, notes: str = "") -> Node:
    return Node(
        campaign_id=store.campaign_id,
        type=type,
        payload=payload,
        provenance=_prov(actor, notes),
    )


class FiniteGraphsPack(DomainPack):
    name = "finite_graphs"

    def initial_nodes(self, config: CampaignConfig) -> tuple[list[Node], list[Edge]]:
        cid = config.id
        defs = [
            Node(
                campaign_id=cid,
                type=NodeType.DEFINITION,
                payload={
                    "name": "finite_simple_undirected_graph",
                    "text": (
                        "A finite simple undirected graph is a pair G=(V,E) with V finite, "
                        "E a set of unordered pairs of distinct vertices, and no loops or "
                        "multiple edges."
                    ),
                    "notation": "G=(V,E)",
                    "scope": "this campaign; labeled vertices {0,...,n-1}",
                },
                provenance=_prov("seed", "domain convention"),
            ),
            Node(
                campaign_id=cid,
                type=NodeType.DEFINITION,
                payload={
                    "name": "degree",
                    "text": "The degree of v in G is the number of edges incident to v.",
                    "notation": "deg(v)",
                    "scope": "finite simple undirected graphs",
                },
                provenance=_prov("seed", "domain convention"),
            ),
        ]
        source = Node(
            campaign_id=cid,
            type=NodeType.SOURCE,
            payload={
                "title": "Handshaking lemma (classical)",
                "locator": "standard graph-theory textbooks; Euler 1736 incidence counting",
                "section": "sum of degrees = 2|E|",
                "notes": "Used as a calibration target, not as a claim of originality.",
            },
            provenance=_prov("seed", "initial corpus"),
        )
        question = Node(
            campaign_id=cid,
            type=NodeType.QUESTION,
            payload=QuestionPayload(
                text=config.central_question.strip(),
                resolution_criteria=(
                    "Produce a precise, refutable statement about vertex-degree parity; "
                    "refute false variants; prove a corrected statement; record evidence "
                    "level honestly."
                ),
                status="open",
            ).model_dump(),
            provenance=_prov("seed", "central question"),
        )
        return defs + [source, question], []

    def seed_actions(self, config: CampaignConfig, store: KnowledgeStore) -> list[Action]:
        q = _question_node(store)
        qid = q.id if q else ""
        return [
            Action(
                id="act.experiment.n1",
                type=ActionType.EXPERIMENT,
                role=Role.EXPERIMENTER,
                description="Enumerate all labeled simple graphs on 1 vertex and test even-degree vertices.",
                verification_plan="Re-run enumeration from the manifesto; compare expected 2^{0}=1 graph.",
                target_ids=[qid],
                information_gain=0.6,
                uncertainty_resolution=0.4,
                reuse_potential=0.5,
                conflict_importance=0.0,
                estimated_time=0.4,
                execution_cost=0.2,
                payload={"n_max": 1, "predicate": "has_even_degree_vertex"},
            ),
            Action(
                id="act.conjecture.even_vertex",
                type=ActionType.CONJECTURE,
                role=Role.CONJECTURER,
                description="Propose: every finite simple graph has a vertex of even degree.",
                verification_plan="Statement must be precise and refutable; no evidence promotion yet.",
                target_ids=[qid],
                information_gain=0.7,
                uncertainty_resolution=0.8,
                reuse_potential=0.4,
                estimated_time=0.2,
                execution_cost=0.1,
                prerequisites=["act.experiment.n1"],
            ),
            Action(
                id="act.refute.k2",
                type=ActionType.REFUTE,
                role=Role.REFUTER,
                description="Search n=2 for a graph with no even-degree vertex (expect K2).",
                verification_plan="Independent checkers: hypotheses hold and conclusion fails on K2.",
                target_ids=[qid],
                information_gain=0.9,
                uncertainty_resolution=1.0,
                reuse_potential=0.6,
                conflict_importance=0.2,
                estimated_time=0.3,
                execution_cost=0.2,
                prerequisites=["act.conjecture.even_vertex"],
            ),
            Action(
                id="act.conjecture.handshake",
                type=ActionType.CONJECTURE,
                role=Role.CONJECTURER,
                description="Corrected statement: the number of odd-degree vertices is even.",
                verification_plan="New version; do not overwrite the refuted claim.",
                target_ids=[qid],
                information_gain=0.8,
                uncertainty_resolution=0.9,
                reuse_potential=1.0,
                conflict_importance=0.5,
                estimated_time=0.2,
                execution_cost=0.1,
                prerequisites=["act.refute.k2"],
            ),
            Action(
                id="act.experiment.n5",
                type=ActionType.EXPERIMENT,
                role=Role.EXPERIMENTER,
                description="Bounded exhaustive check of the handshake claim on n<=5 labeled graphs.",
                verification_plan="Two checkers must agree; record universe and completeness argument.",
                target_ids=[qid],
                information_gain=0.7,
                uncertainty_resolution=0.5,
                reuse_potential=0.5,
                estimated_time=1.2,
                execution_cost=0.8,
                prerequisites=["act.conjecture.handshake"],
                payload={"n_max": 5, "predicate": "odd_count_even"},
            ),
            Action(
                id="act.prove.handshake",
                type=ActionType.PROVE,
                role=Role.PROVER,
                description="Informal handshake proof: sum(deg)=2|E|, hence even odd-count.",
                verification_plan="Reviewer checks steps, cases, and dependencies; no gaps allowed.",
                target_ids=[qid],
                information_gain=0.8,
                uncertainty_resolution=0.9,
                reuse_potential=1.0,
                estimated_time=0.6,
                execution_cost=0.4,
                prerequisites=["act.experiment.n5"],
            ),
            Action(
                id="act.review.handshake",
                type=ActionType.REVIEW,
                role=Role.REVIEWER,
                description="Review the informal proof's steps and dependencies.",
                verification_plan="Accept only if gaps is empty and each step cites a permitted dependency.",
                target_ids=[qid],
                information_gain=0.4,
                uncertainty_resolution=0.7,
                reuse_potential=0.6,
                estimated_time=0.4,
                execution_cost=0.3,
                prerequisites=["act.prove.handshake"],
            ),
            Action(
                id="act.formalize.arithmetic",
                type=ActionType.FORMALIZE,
                role=Role.FORMALIZER,
                description="Compile the Lean arithmetic core and record a faithfulness certificate.",
                verification_plan="lake build; forbid sorry/admit; record hashes and axiom policy.",
                target_ids=[qid],
                information_gain=0.6,
                uncertainty_resolution=0.5,
                reuse_potential=0.8,
                estimated_time=2.0,
                execution_cost=1.5,
                prerequisites=["act.review.handshake"],
            ),
        ]

    def execute(self, action: Action, store: KnowledgeStore) -> dict:
        dispatch = {
            "act.experiment.n1": self._experiment,
            "act.experiment.n5": self._experiment,
            "act.conjecture.even_vertex": self._conjecture_even_vertex,
            "act.refute.k2": self._refute_k2,
            "act.conjecture.handshake": self._conjecture_handshake,
            "act.prove.handshake": self._prove_handshake,
            "act.review.handshake": self._review_handshake,
            "act.formalize.arithmetic": self._formalize,
        }
        handler = dispatch.get(action.id)
        if handler is None:
            raise KeyError(f"No handler for action {action.id}")
        return handler(action, store)

    def _experiment(self, action: Action, store: KnowledgeStore) -> dict:
        n_max = int(action.payload["n_max"])
        predicate = str(action.payload["predicate"])
        results = exhaustive_scan(n_max, predicate)
        config = {
            "program": "research_atlas.domain_packs.finite_graphs.checkers.exhaustive_scan",
            "n_max": n_max,
            "predicate": predicate,
            "universe": results["universe"],
            "seed": None,
        }
        manifest = write_artifact(
            store.campaign_id,
            kind="experiment_manifest",
            content=json.dumps({"config": config, "results": results}, indent=2),
            produced_by=action.role.value,
            metadata={"action": action.id},
        )
        store.record_artifact(
            manifest["sha256"], "experiment_manifest", manifest["path"], action.role.value, manifest
        )
        checkers_agree = True
        if predicate == "odd_count_even":
            checkers_agree = not any(
                isinstance(f, dict) and f.get("reason") == "checkers_disagree"
                for f in results["failures"]
            )
        experiment = _node(
            store,
            NodeType.EXPERIMENT,
            ExperimentPayload(
                program=config["program"],
                config=config,
                coverage=results["completeness_argument"],
                results=results,
                manifesto_hash=manifest["sha256"],
                seed=None,
                second_checker="checker_b_handshake" if predicate == "odd_count_even" else None,
                checkers_agree=checkers_agree,
            ).model_dump(),
            action.role.value,
            "reproducible enumeration",
        )
        verification = _node(
            store,
            NodeType.VERIFICATION,
            VerificationPayload(
                verifier="exhaustive_scan",
                input_ref=manifest["sha256"],
                result="pass" if checkers_agree else "fail",
                log=json.dumps({k: results["totals"][k] for k in results["totals"]}),
                environment={"program": config["program"]},
                independent=predicate == "odd_count_even",
            ).model_dump(),
            "verifier",
            "enumeration completeness recorded",
        )
        nodes = [experiment, verification]
        edges = [
            Edge(
                campaign_id=store.campaign_id,
                relation=RelationType.VERIFIED_BY,
                source_id=experiment.id,
                target_id=verification.id,
                provenance=_prov("verifier", "experiment replayable from manifesto", [verification.id]),
            )
        ]
        if predicate == "odd_count_even":
            claim = store.claim_by_logical_id(CLAIM_HANDSHAKE)
            if claim is not None:
                edges.append(
                    Edge(
                        campaign_id=store.campaign_id,
                        relation=RelationType.SUPPORTS,
                        source_id=experiment.id,
                        target_id=claim.id,
                        target_version=claim.payload["statement_version"],
                        provenance=_prov(
                            "experimenter",
                            "bounded support only; not a universal proof",
                            [verification.id],
                        ),
                    )
                )
        return {"nodes": nodes, "edges": edges, "notes": f"enumerated n<= {n_max} for {predicate}"}

    def _conjecture_even_vertex(self, action: Action, store: KnowledgeStore) -> dict:
        claim = _node(
            store,
            NodeType.CLAIM,
            {
                "claim_id": CLAIM_EVEN_VERTEX,
                "statement_version": 1,
                "statement": "Every finite simple undirected graph has at least one vertex of even degree.",
                "quantifiers": "for all finite simple undirected graphs G, exists v in V(G)",
                "assumptions": [
                    "G is finite",
                    "G is simple and undirected",
                    "loops and multiple edges are forbidden",
                ],
                "mathematical_domain": "finite_undirected_simple_graphs",
                "research_status": ResearchStatus.PROPOSED.value,
                "evidence_level": EvidenceLevel.HEURISTIC.value,
                "evidence_ids": [],
                "dependency_ids": [],
                "review_status": ReviewStatus.UNREVIEWED.value,
                "formalization_status": FormalizationStatus.NONE.value,
                "universe_covered": "labeled simple graphs on n=1 (from preceding experiment)",
                "completeness_argument": None,
                "formal_statement_faithfulness": None,
                "parent_claim_id": None,
                "superseded_by": None,
            },
            action.role.value,
            "pattern from n=1 enumeration; not established",
        )
        q = _question_node(store)
        edges = []
        if q:
            edges.append(
                Edge(
                    campaign_id=store.campaign_id,
                    relation=RelationType.DERIVED_FROM,
                    source_id=q.id,
                    target_id=claim.id,
                    provenance=_prov(action.role.value, "conjecture from central question"),
                )
            )
        return {"nodes": [claim], "edges": edges, "notes": "false conjecture recorded as version 1"}

    def _refute_k2(self, action: Action, store: KnowledgeStore) -> dict:
        g = k2()
        obj = g.to_dict()
        check = check_counterexample(
            obj,
            hypotheses=[
                lambda d: d["n"] >= 1,
                lambda d: all(u != v for u, v in d["edges"]),
            ],
            conclusion=lambda d: k2_from(d).has_even_degree_vertex(),
        )
        # Force the concrete object through both degree checkers.
        from research_atlas.domain_packs.finite_graphs.checkers import (
            checker_a_odd_count_even,
            has_even_degree_vertex,
        )

        independent = {
            "has_even_degree_vertex": has_even_degree_vertex(g),
            "odd_count_even": checker_a_odd_count_even(g),
            "degrees": g.degrees(),
        }
        example = _node(
            store,
            NodeType.EXAMPLE,
            ExamplePayload(
                description="K2: two vertices joined by a single edge. Degrees [1,1].",
                object_repr=obj,
                verified_properties={**check, **independent},
            ).model_dump(),
            action.role.value,
            "counterexample candidate",
        )
        verification = _node(
            store,
            NodeType.VERIFICATION,
            VerificationPayload(
                verifier="counterexample.check_counterexample+degree_list",
                input_ref=example.id,
                result="pass" if check["is_counterexample"] else "fail",
                log=json.dumps({"check": check, "independent": independent}),
                environment={"object": "K2"},
                independent=True,
            ).model_dump(),
            "verifier",
            "independent property check",
        )
        obstacle = _node(
            store,
            NodeType.OBSTACLE,
            ObstaclePayload(
                failed_attempt="Conjecture that every graph has an even-degree vertex",
                cause="K2 has degrees 1 and 1; both odd. The n=1 universe missed this object.",
                scope="The conjecture is false for finite simple graphs in full generality.",
                blocked_strategy="Inferring a universal degree-existence statement from n=1 enumeration",
            ).model_dump(),
            action.role.value,
            "failure has scope; does not discard degree-parity questions",
        )
        claim = store.claim_by_logical_id(CLAIM_EVEN_VERTEX, 1)
        nodes = [example, verification, obstacle]
        edges = [
            Edge(
                campaign_id=store.campaign_id,
                relation=RelationType.VERIFIED_BY,
                source_id=example.id,
                target_id=verification.id,
                provenance=_prov("verifier", "counterexample properties", [verification.id]),
            ),
            Edge(
                campaign_id=store.campaign_id,
                relation=RelationType.BLOCKS,
                source_id=obstacle.id,
                target_id=claim.id if claim else example.id,
                provenance=_prov(action.role.value, "blocks n=1 overgeneralization"),
            ),
        ]
        if claim is not None and check["is_counterexample"]:
            edges.append(
                Edge(
                    campaign_id=store.campaign_id,
                    relation=RelationType.REFUTES,
                    source_id=example.id,
                    target_id=claim.id,
                    target_version=1,
                    provenance=_prov(
                        action.role.value,
                        "K2 refutes C-even-vertex v1",
                        [verification.id],
                    ),
                )
            )
        return {
            "nodes": nodes,
            "edges": edges,
            "notes": "K2 counterexample",
            "refute_claim_id": CLAIM_EVEN_VERTEX if check["is_counterexample"] else None,
            "refute_reason": "K2 has no even-degree vertex",
        }

    def _conjecture_handshake(self, action: Action, store: KnowledgeStore) -> dict:
        previous = store.claim_by_logical_id(CLAIM_EVEN_VERTEX, 1)
        claim = _node(
            store,
            NodeType.CLAIM,
            {
                "claim_id": CLAIM_HANDSHAKE,
                "statement_version": 1,
                "statement": (
                    "In every finite simple undirected graph, the number of odd-degree "
                    "vertices is even."
                ),
                "quantifiers": "for all finite simple undirected graphs G",
                "assumptions": [
                    "G is finite",
                    "G is simple and undirected",
                    "degree is the number of incident edges",
                ],
                "mathematical_domain": "finite_undirected_simple_graphs",
                "research_status": ResearchStatus.OPEN.value,
                "evidence_level": EvidenceLevel.NONE.value,
                "evidence_ids": [],
                "dependency_ids": [],
                "review_status": ReviewStatus.UNREVIEWED.value,
                "formalization_status": FormalizationStatus.NONE.value,
                "universe_covered": None,
                "completeness_argument": None,
                "formal_statement_faithfulness": None,
                "parent_claim_id": CLAIM_EVEN_VERTEX,
                "superseded_by": None,
            },
            action.role.value,
            "corrected statement after K2; new claim, not an overwrite",
        )
        edges = []
        if previous is not None:
            edges.append(
                Edge(
                    campaign_id=store.campaign_id,
                    relation=RelationType.DERIVED_FROM,
                    source_id=previous.id,
                    target_id=claim.id,
                    provenance=_prov(action.role.value, "hypothesis repaired after refutation"),
                )
            )
        return {"nodes": [claim], "edges": edges, "notes": "handshake claim opened"}

    def _prove_handshake(self, action: Action, store: KnowledgeStore) -> dict:
        claim = store.claim_by_logical_id(CLAIM_HANDSHAKE)
        if claim is None:
            return {"nodes": [], "edges": [], "notes": "missing handshake claim"}
        arithmetic = _node(
            store,
            NodeType.CLAIM,
            {
                "claim_id": CLAIM_ARITHMETIC,
                "statement_version": 1,
                "statement": (
                    "For every natural number e, 2e is even. The sum of two odd "
                    "natural numbers is even."
                ),
                "quantifiers": "for all e in Nat; for all finite lists of Nat",
                "assumptions": ["standard arithmetic of natural numbers"],
                "mathematical_domain": "natural_number_arithmetic",
                "research_status": ResearchStatus.OPEN.value,
                "evidence_level": EvidenceLevel.NONE.value,
                "evidence_ids": [],
                "dependency_ids": [],
                "review_status": ReviewStatus.UNREVIEWED.value,
                "formalization_status": FormalizationStatus.NONE.value,
                "universe_covered": None,
                "completeness_argument": None,
                "formal_statement_faithfulness": None,
                "parent_claim_id": None,
                "superseded_by": None,
            },
            action.role.value,
            "arithmetic core split out for faithful Lean targeting",
        )
        proof = _node(
            store,
            NodeType.PROOF_ATTEMPT,
            ProofAttemptPayload(
                target_claim_id=CLAIM_HANDSHAKE,
                target_version=claim.payload["statement_version"],
                steps=[
                    "Each edge contributes 1 to the degree of each endpoint, hence 2 to the degree sum.",
                    "Therefore sum_v deg(v) = 2|E|, which is even.",
                    "The sum of even numbers is even, so the parity of the degree sum equals the parity of the number of odd degrees.",
                    "An even sum therefore forces an even number of odd-degree vertices.",
                ],
                dependencies=[arithmetic.payload["claim_id"]],
                gaps=[],
                status="draft",
            ).model_dump(),
            action.role.value,
            "structured informal proof",
        )
        edges = [
            Edge(
                campaign_id=store.campaign_id,
                relation=RelationType.USES,
                source_id=proof.id,
                target_id=arithmetic.id,
                provenance=_prov(action.role.value, "proof uses arithmetic core"),
            ),
            Edge(
                campaign_id=store.campaign_id,
                relation=RelationType.SUPPORTS,
                source_id=proof.id,
                target_id=claim.id,
                target_version=claim.payload["statement_version"],
                provenance=_prov(action.role.value, "candidate proof of handshake"),
            ),
        ]
        return {"nodes": [arithmetic, proof], "edges": edges, "notes": "informal proof drafted"}

    def _review_handshake(self, action: Action, store: KnowledgeStore) -> dict:
        proofs = [
            n
            for n in store.nodes(NodeType.PROOF_ATTEMPT)
            if n.payload.get("target_claim_id") == CLAIM_HANDSHAKE
        ]
        if not proofs:
            return {"nodes": [], "edges": [], "notes": "no proof to review"}
        proof = proofs[-1]
        gaps = proof.payload.get("gaps") or []
        accepted = not gaps
        verification = _node(
            store,
            NodeType.VERIFICATION,
            VerificationPayload(
                verifier="reviewer.step_dependency_check",
                input_ref=proof.id,
                result="pass" if accepted else "fail",
                log="gaps empty; each step is a standard incidence or parity fact."
                if accepted
                else f"gaps: {gaps}",
                environment={"role": "reviewer"},
                independent=True,
            ).model_dump(),
            action.role.value,
            "human-style structured review (deterministic in calibration)",
        )
        nodes = [verification]
        edges = [
            Edge(
                campaign_id=store.campaign_id,
                relation=RelationType.VERIFIED_BY,
                source_id=proof.id,
                target_id=verification.id,
                provenance=_prov(action.role.value, "review of informal proof", [verification.id]),
            )
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "notes": "informal proof reviewed",
            "accept_proof": accepted,
            "proof_id": proof.id,
            "verification_id": verification.id,
        }

    def _formalize(self, action: Action, store: KnowledgeStore) -> dict:
        cert = try_compile()
        manifest = write_artifact(
            store.campaign_id,
            kind="lean_certificate",
            content=json.dumps(cert, indent=2),
            produced_by=action.role.value,
            metadata={"action": action.id},
            suffix=".json",
        )
        store.record_artifact(
            manifest["sha256"], "lean_certificate", manifest["path"], action.role.value, cert
        )
        build_ok = cert["build_result"] in {"success", "lean_unavailable"}
        # lean_unavailable is recorded honestly; it is not treated as a compiled proof.
        compiled = cert["build_result"] == "success"
        policy_ok = not cert.get("forbidden_constructs")
        result = "pass" if compiled and policy_ok else ("fail" if not policy_ok or cert["build_result"] == "failed" else "error")
        if cert["build_result"] == "lean_unavailable":
            result = "error"
        verification = _node(
            store,
            NodeType.VERIFICATION,
            VerificationPayload(
                verifier="lean.lake_build",
                input_ref=manifest["sha256"],
                result=result,  # type: ignore[arg-type]
                log=cert.get("log", "")[:4000],
                environment={
                    "lean_toolchain": cert.get("lean_toolchain"),
                    "file_hash": cert.get("file_hash"),
                    "environment_hash": cert.get("environment_hash"),
                    "build_result": cert.get("build_result"),
                    "axiomatic_dependencies": cert.get("axiomatic_dependencies"),
                    "theorems": cert.get("theorems"),
                },
                independent=True,
            ).model_dump(),
            action.role.value,
            "Lean certificate",
        )
        arithmetic = store.claim_by_logical_id(CLAIM_ARITHMETIC)
        handshake = store.claim_by_logical_id(CLAIM_HANDSHAKE)
        nodes = [verification]
        edges = []
        if arithmetic is not None:
            edges.append(
                Edge(
                    campaign_id=store.campaign_id,
                    relation=RelationType.VERIFIED_BY,
                    source_id=arithmetic.id,
                    target_id=verification.id,
                    provenance=_prov(action.role.value, "Lean certificate for arithmetic core", [verification.id]),
                )
            )
            if compiled and policy_ok:
                edges.append(
                    Edge(
                        campaign_id=store.campaign_id,
                        relation=RelationType.SUPPORTS,
                        source_id=verification.id,
                        target_id=arithmetic.id,
                        target_version=arithmetic.payload["statement_version"],
                        provenance=_prov(
                            action.role.value,
                            "compiled Lean theorems; faithfulness of arithmetic claim is high",
                            [verification.id],
                            artifact_hashes=[manifest["sha256"]],
                        ),
                    )
                )
        if handshake is not None:
            # Explicitly do not mark the graph-theoretic claim as formally proved.
            edges.append(
                Edge(
                    campaign_id=store.campaign_id,
                    relation=RelationType.USES,
                    source_id=handshake.id,
                    target_id=arithmetic.id if arithmetic else verification.id,
                    provenance=_prov(
                        action.role.value,
                        "graph claim uses arithmetic lemma; formalization is partial relative to C-handshake",
                    ),
                )
            )
        return {
            "nodes": nodes,
            "edges": edges,
            "notes": f"lean build_result={cert['build_result']}",
            "lean_certificate": cert,
            "lean_compiled": compiled and policy_ok,
            "verification_id": verification.id,
            "artifact": manifest["sha256"],
        }


def k2_from(data: dict):
    from research_atlas.domain_packs.finite_graphs.graphs import SimpleGraph

    return SimpleGraph.from_dict(data)


def _question_node(store: KnowledgeStore) -> Node | None:
    questions = store.nodes(NodeType.QUESTION)
    return questions[0] if questions else None


