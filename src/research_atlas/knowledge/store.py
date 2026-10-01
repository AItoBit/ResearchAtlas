"""SQLite scientific memory: nodes, versioned claims, edges, events, artifacts.

Important claim edits are versioned. A refuted conjecture is never overwritten;
a corrected statement is a new version (or a new claim derived from the old one).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from research_atlas.models import (
    CampaignConfig,
    Edge,
    Event,
    Node,
    NodeType,
    RelationType,
    utcnow,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    provenance TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_version INTEGER,
    provenance TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    sha256 TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    produced_by TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(created_at);
"""


def _dump(model: Any) -> str:
    if hasattr(model, "model_dump"):
        return json.dumps(model.model_dump(mode="json"), ensure_ascii=True)
    return json.dumps(model, ensure_ascii=True, default=str)


class KnowledgeStore:
    def __init__(self, db_path: Path, campaign_id: str):
        self.db_path = Path(db_path)
        self.campaign_id = campaign_id
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> KnowledgeStore:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def set_meta(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            (key, json.dumps(value, default=str)),
        )
        self._conn.commit()

    def get_meta(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return json.loads(row["value"])

    def save_config(self, config: CampaignConfig) -> None:
        self.set_meta("config", config.model_dump(mode="json"))
        self.append_event("campaign_configured", {"config_id": config.id})

    def load_config(self) -> CampaignConfig | None:
        raw = self.get_meta("config")
        return CampaignConfig.model_validate(raw) if raw else None

    def append_event(self, event_type: str, payload: dict[str, Any] | None = None) -> Event:
        event = Event(
            campaign_id=self.campaign_id,
            type=event_type,
            payload=payload or {},
        )
        self._conn.execute(
            "INSERT INTO events(id, campaign_id, type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                event.id,
                event.campaign_id,
                event.type,
                json.dumps(event.payload, default=str),
                event.created_at.isoformat(),
            ),
        )
        self._conn.commit()
        return event

    def events(self) -> list[Event]:
        rows = self._conn.execute(
            "SELECT * FROM events ORDER BY created_at ASC, id ASC"
        ).fetchall()
        return [
            Event(
                id=row["id"],
                campaign_id=row["campaign_id"],
                type=row["type"],
                payload=json.loads(row["payload"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def add_node(self, node: Node) -> Node:
        self._conn.execute(
            "INSERT INTO nodes(id, type, campaign_id, payload, provenance, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                node.id,
                node.type.value,
                node.campaign_id,
                json.dumps(node.payload, default=str),
                _dump(node.provenance),
                node.created_at.isoformat(),
            ),
        )
        self._conn.commit()
        self.append_event("node_added", {"node_id": node.id, "type": node.type.value})
        return node

    def add_edge(self, edge: Edge) -> Edge:
        self._conn.execute(
            "INSERT INTO edges(id, campaign_id, relation, source_id, target_id, "
            "target_version, provenance, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                edge.id,
                edge.campaign_id,
                edge.relation.value,
                edge.source_id,
                edge.target_id,
                edge.target_version,
                _dump(edge.provenance),
                json.dumps(edge.metadata, default=str),
                edge.created_at.isoformat(),
            ),
        )
        self._conn.commit()
        self.append_event(
            "edge_added",
            {
                "edge_id": edge.id,
                "relation": edge.relation.value,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "target_version": edge.target_version,
            },
        )
        return edge

    def get_node(self, node_id: str) -> Node | None:
        row = self._conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return self._row_to_node(row) if row else None

    def nodes(self, type: NodeType | None = None) -> list[Node]:
        if type is None:
            rows = self._conn.execute("SELECT * FROM nodes ORDER BY created_at ASC").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM nodes WHERE type = ? ORDER BY created_at ASC",
                (type.value,),
            ).fetchall()
        return [self._row_to_node(r) for r in rows]

    def edges(self, relation: RelationType | None = None) -> list[Edge]:
        if relation is None:
            rows = self._conn.execute("SELECT * FROM edges ORDER BY created_at ASC").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM edges WHERE relation = ? ORDER BY created_at ASC",
                (relation.value,),
            ).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def edges_to(self, target_id: str) -> list[Edge]:
        rows = self._conn.execute(
            "SELECT * FROM edges WHERE target_id = ?", (target_id,)
        ).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def edges_from(self, source_id: str) -> list[Edge]:
        rows = self._conn.execute(
            "SELECT * FROM edges WHERE source_id = ?", (source_id,)
        ).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def claims(self) -> list[Node]:
        return self.nodes(NodeType.CLAIM)

    def claim_by_logical_id(self, claim_id: str, version: int | None = None) -> Node | None:
        matches = [
            n
            for n in self.claims()
            if n.payload.get("claim_id") == claim_id
            and (version is None or n.payload.get("statement_version") == version)
        ]
        if not matches:
            return None
        return max(matches, key=lambda n: n.payload.get("statement_version", 1))

    def latest_claim_version(self, claim_id: str) -> int:
        versions = [
            n.payload.get("statement_version", 1)
            for n in self.claims()
            if n.payload.get("claim_id") == claim_id
        ]
        return max(versions) if versions else 0

    def record_artifact(
        self,
        sha256: str,
        kind: str,
        path: str,
        produced_by: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO artifacts(sha256, kind, path, produced_by, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                sha256,
                kind,
                path,
                produced_by,
                json.dumps(metadata or {}, default=str),
                utcnow().isoformat(),
            ),
        )
        self._conn.commit()
        self.append_event("artifact_recorded", {"sha256": sha256, "kind": kind})

    def artifacts(self) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM artifacts").fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> Node:
        from research_atlas.models import Provenance

        return Node(
            id=row["id"],
            type=NodeType(row["type"]),
            campaign_id=row["campaign_id"],
            payload=json.loads(row["payload"]),
            provenance=Provenance.model_validate(json.loads(row["provenance"])),
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_edge(row: sqlite3.Row) -> Edge:
        from research_atlas.models import Provenance

        return Edge(
            id=row["id"],
            campaign_id=row["campaign_id"],
            relation=RelationType(row["relation"]),
            source_id=row["source_id"],
            target_id=row["target_id"],
            target_version=row["target_version"],
            provenance=Provenance.model_validate(json.loads(row["provenance"])),
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
        )

    def statement_duplicates(self) -> list[tuple[str, list[str]]]:
        buckets: dict[str, list[str]] = {}
        for node in self.claims():
            key = _normalize_statement(node.payload.get("statement", ""))
            buckets.setdefault(key, []).append(node.id)
        return [(k, ids) for k, ids in buckets.items() if len(ids) > 1]


def _normalize_statement(text: str) -> str:
    return " ".join(text.lower().split())
