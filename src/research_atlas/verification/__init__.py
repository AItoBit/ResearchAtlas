"""Hash-addressed artifacts and experiment manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from research_atlas.models import utcnow
from research_atlas.paths import artifacts_dir


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def write_artifact(
    campaign_id: str,
    kind: str,
    content: str | bytes,
    produced_by: str,
    metadata: dict[str, Any] | None = None,
    suffix: str = ".json",
) -> dict[str, Any]:
    raw = content.encode("utf-8") if isinstance(content, str) else content
    digest = sha256_bytes(raw)
    folder = artifacts_dir(campaign_id) / digest
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"payload{suffix}"
    path = folder / filename
    path.write_bytes(raw)
    manifest = {
        "sha256": digest,
        "kind": kind,
        "path": str(path),
        "produced_by": produced_by,
        "created_at": utcnow().isoformat(),
        "metadata": metadata or {},
    }
    (folder / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return manifest


def read_manifest(campaign_id: str, sha256: str) -> dict[str, Any]:
    path = artifacts_dir(campaign_id) / sha256 / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))
