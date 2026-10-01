"""Typed scientific memory: nodes, edges, evidence, and work items.

A single status label is not enough. Research status and evidence level are
independent: a conjecture may have millions of checked cases and still be open.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "") -> str:
    token = uuid4().hex[:12]
    return f"{prefix}{token}" if prefix else token


class ResearchStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    OPEN = "open"
    ESTABLISHED = "established"
    REFUTED = "refuted"
    ARCHIVED = "archived"


class EvidenceLevel(str, Enum):
    NONE = "none"
    HEURISTIC = "heuristic"
    EXPERIMENT = "experiment"
    BOUNDED_ENUMERATION = "bounded_enumeration"
    REVIEWED_PROOF = "reviewed_proof"
    FORMAL_PROOF = "formal_proof"


class NodeType(str, Enum):
    CLAIM = "Claim"
    DEFINITION = "Definition"
    SOURCE = "Source"
    PROOF_ATTEMPT = "ProofAttempt"
    EXPERIMENT = "Experiment"
    EXAMPLE = "Example"
    VERIFICATION = "Verification"
    OBSTACLE = "Obstacle"
    QUESTION = "Question"


class RelationType(str, Enum):
    USES = "uses"
    SUPPORTS = "supports"
    REFUTES = "refutes"
    GENERALIZES = "generalizes"
    SPECIALIZES = "specializes"
    EQUIVALENT_TO = "equivalent_to"
    DERIVED_FROM = "derived_from"
    BLOCKS = "blocks"
    VERIFIED_BY = "verified_by"


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    OBJECTED = "objected"
    NEEDS_REVALIDATION = "needs_revalidation"


class FormalizationStatus(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    FAITHFUL = "faithful"
    MISMATCH = "mismatch"
    UNAVAILABLE = "unavailable"


class ActionType(str, Enum):
    READ = "read"
    EXPERIMENT = "experiment"
    CONJECTURE = "conjecture"
    REFUTE = "refute"
    PROVE = "prove"
    REVIEW = "review"
    FORMALIZE = "formalize"
    CURATE = "curate"
    RECONCILE = "reconcile"


class Role(str, Enum):
    READER = "reader"
    EXPERIMENTER = "experimenter"
    CONJECTURER = "conjecturer"
    REFUTER = "refuter"
    PROVER = "prover"
    REVIEWER = "reviewer"
    FORMALIZER = "formalizer"
    CURATOR = "curator"


class Provenance(BaseModel):
    actor: str
    timestamp: datetime = Field(default_factory=utcnow)
    evidence_ids: list[str] = Field(default_factory=list)
    artifact_hashes: list[str] = Field(default_factory=list)
    notes: str = ""
    source_ids: list[str] = Field(default_factory=list)


class Node(BaseModel):
    id: str = Field(default_factory=lambda: new_id("n_"))
    type: NodeType
    campaign_id: str
    payload: dict[str, Any]
    created_at: datetime = Field(default_factory=utcnow)
    provenance: Provenance


class Edge(BaseModel):
    id: str = Field(default_factory=lambda: new_id("e_"))
    campaign_id: str
    relation: RelationType
    source_id: str
    target_id: str
    provenance: Provenance
    # A refutes edge must name the exact statement version it contradicts.
    target_version: int | None = None
    created_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimPayload(BaseModel):
    claim_id: str
    statement_version: int = 1
    statement: str
    quantifiers: str
    assumptions: list[str] = Field(default_factory=list)
    mathematical_domain: str
    research_status: ResearchStatus = ResearchStatus.PROPOSED
    evidence_level: EvidenceLevel = EvidenceLevel.NONE
    evidence_ids: list[str] = Field(default_factory=list)
    dependency_ids: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    formalization_status: FormalizationStatus = FormalizationStatus.NONE
    universe_covered: str | None = None
    completeness_argument: str | None = None
    formal_statement_faithfulness: str | None = None
    parent_claim_id: str | None = None
    superseded_by: str | None = None


class DefinitionPayload(BaseModel):
    name: str
    text: str
    notation: str = ""
    scope: str = ""


class SourcePayload(BaseModel):
    title: str
    locator: str
    section: str = ""
    notes: str = ""


class ProofAttemptPayload(BaseModel):
    target_claim_id: str
    target_version: int
    steps: list[str]
    dependencies: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    status: Literal["draft", "reviewed", "rejected", "accepted"] = "draft"


class ExperimentPayload(BaseModel):
    program: str
    config: dict[str, Any]
    coverage: str
    results: dict[str, Any] = Field(default_factory=dict)
    manifesto_hash: str | None = None
    seed: int | None = None
    second_checker: str | None = None
    checkers_agree: bool | None = None


class ExamplePayload(BaseModel):
    description: str
    object_repr: dict[str, Any]
    verified_properties: dict[str, Any] = Field(default_factory=dict)


class VerificationPayload(BaseModel):
    verifier: str
    input_ref: str
    result: Literal["pass", "fail", "error"]
    log: str
    environment: dict[str, Any] = Field(default_factory=dict)
    independent: bool = False


class ObstaclePayload(BaseModel):
    failed_attempt: str
    cause: str
    scope: str
    blocked_strategy: str


class QuestionPayload(BaseModel):
    text: str
    resolution_criteria: str
    status: Literal["open", "resolved", "blocked"] = "open"
    parent_question_id: str | None = None


class Action(BaseModel):
    id: str = Field(default_factory=lambda: new_id("a_"))
    type: ActionType
    role: Role
    description: str
    verification_plan: str
    target_ids: list[str] = Field(default_factory=list)
    information_gain: float = 0.5
    uncertainty_resolution: float = 0.5
    reuse_potential: float = 0.3
    conflict_importance: float = 0.0
    estimated_time: float = 1.0
    execution_cost: float = 1.0
    prerequisites: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    explanation: str = ""


class GraphProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: new_id("p_"))
    actor: str
    add_nodes: list[Node] = Field(default_factory=list)
    add_edges: list[Edge] = Field(default_factory=list)
    notes: str = ""


class StatusUpdateRejected(BaseModel):
    reason: str
    rule: str


class Budget(BaseModel):
    max_steps: int = 20
    max_model_calls: int = 0
    max_seconds: float = 300.0
    max_lean_attempts: int = 2
    steps_used: int = 0
    model_calls_used: int = 0
    seconds_used: float = 0.0
    lean_attempts_used: int = 0

    def remaining_steps(self) -> int:
        return max(0, self.max_steps - self.steps_used)

    def exhausted(self) -> bool:
        if self.steps_used >= self.max_steps:
            return True
        if self.max_model_calls > 0 and self.model_calls_used >= self.max_model_calls:
            return True
        if self.seconds_used >= self.max_seconds:
            return True
        return False


class PlannerWeights(BaseModel):
    I: float = 1.0
    U: float = 1.2
    R: float = 0.8
    C: float = 1.5
    T: float = 0.5
    B: float = 0.7


class CampaignConfig(BaseModel):
    id: str
    name: str
    domain: str
    domain_pack: str
    central_question: str
    budget: Budget = Field(default_factory=Budget)
    stop_criteria: list[str] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    weights: PlannerWeights = Field(default_factory=PlannerWeights)
    initial_corpus: list[dict[str, Any]] = Field(default_factory=list)


class WorkMove(BaseModel):
    step: int
    action: Action
    proposal: GraphProposal | None = None
    verification_ids: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    error: str | None = None


class Event(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ev_"))
    campaign_id: str
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)


class ArtifactManifest(BaseModel):
    sha256: str
    kind: str
    path: str
    produced_by: str
    created_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
