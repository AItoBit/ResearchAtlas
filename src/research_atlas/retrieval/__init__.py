"""Retrieve definitions, sources, results, and obstacles for the next move."""

from __future__ import annotations

from research_atlas.knowledge.store import KnowledgeStore
from research_atlas.models import Action, NodeType


def load_context(store: KnowledgeStore, action: Action) -> dict:
    return {
        "action": action.model_dump(mode="json"),
        "definitions": [n.payload for n in store.nodes(NodeType.DEFINITION)],
        "sources": [n.payload for n in store.nodes(NodeType.SOURCE)],
        "claims": [n.payload | {"node_id": n.id} for n in store.claims()],
        "obstacles": [n.payload for n in store.nodes(NodeType.OBSTACLE)],
        "questions": [n.payload | {"node_id": n.id} for n in store.nodes(NodeType.QUESTION)],
        "recent_events": [e.model_dump(mode="json") for e in store.events()[-12:]],
    }
