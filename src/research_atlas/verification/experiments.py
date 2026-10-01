"""Re-run an experiment from its recorded manifesto."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

Checker = Callable[[dict[str, Any]], dict[str, Any]]


def replay(manifest_path: Path, runner: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload_path = Path(manifest["path"])
    config = json.loads(payload_path.read_text(encoding="utf-8"))
    result = runner(config)
    return {"manifest": manifest, "replayed": result}
