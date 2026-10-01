"""Lean certificate handling.

A Lean certificate must identify toolchain versions, file/environment hashes,
the theorem checked, the build result, axiomatic dependencies, and whether the
formal statement faithfully represents the informal claim.

Gaps (`sorry`, `admit`) and extra axioms used to dodge a proof are forbidden.
"""

from __future__ import annotations

import copy
import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

from research_atlas.paths import LEAN
from research_atlas.verification.policies import ACCEPTED_FOUNDATIONS, lean_source_allowed


LEAN_PROJECT = LEAN / "ResearchAtlasLean"
_COMPILE_CACHE: dict[str, dict[str, Any]] = {}


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment_hash(project: Path) -> str:
    hasher = hashlib.sha256()
    toolchain = project / "lean-toolchain"
    lakefile = project / "lakefile.toml"
    for extra in (toolchain, lakefile):
        if extra.exists():
            hasher.update(extra.read_bytes())
    for lean_file in sorted(project.rglob("*.lean")):
        if ".lake" in lean_file.parts:
            continue
        hasher.update(str(lean_file.relative_to(project)).encode())
        hasher.update(lean_file.read_bytes())
    return hasher.hexdigest()


def inspect_sources(project: Path) -> dict[str, Any]:
    violations: list[str] = []
    files: list[str] = []
    for lean_file in sorted(project.rglob("*.lean")):
        if ".lake" in lean_file.parts:
            continue
        files.append(str(lean_file.relative_to(project)))
        source = lean_file.read_text(encoding="utf-8")
        ok, hits = lean_source_allowed(source)
        if not ok:
            violations.extend(f"{lean_file.name}: {h}" for h in hits)
    return {"files": files, "violations": violations}


def try_compile(project: Path | None = None, timeout: int = 120) -> dict[str, Any]:
    project = project or LEAN_PROJECT
    cache_key = str(project.resolve())
    if cache_key in _COMPILE_CACHE:
        return copy.deepcopy(_COMPILE_CACHE[cache_key])
    lake = shutil.which("lake")
    lean = shutil.which("lean")
    inspection = inspect_sources(project)
    handshake = project / "ResearchAtlasLean" / "Handshake.lean"
    file_hash = hash_file(handshake) if handshake.exists() else None
    env_hash = environment_hash(project) if project.exists() else None
    toolchain = ""
    toolchain_file = project / "lean-toolchain"
    if toolchain_file.exists():
        toolchain = toolchain_file.read_text(encoding="utf-8").strip()

    certificate: dict[str, Any] = {
        "lean_toolchain": toolchain,
        "mathlib": "none (core Lean only)",
        "file_hash": file_hash,
        "environment_hash": env_hash,
        "theorem": "ResearchAtlas.Handshake.twice_the_edge_count_is_even",
        "theorems": [
            "ResearchAtlas.Handshake.twice_the_edge_count_is_even",
            "ResearchAtlas.Handshake.odd_plus_odd_is_even",
        ],
        "build_result": "not_run",
        "axiomatic_dependencies": sorted(ACCEPTED_FOUNDATIONS),
        "forbidden_constructs": inspection["violations"],
        "lake_available": lake is not None,
        "lean_available": lean is not None,
        "log": "",
        "faithfulness": (
            "partial — arithmetic core of the handshake argument "
            "(2*|E| is even; odd+odd is even). Incidence graphs are not encoded. "
            "This must not be treated as a faithful formalization of the full "
            "graph-theoretic claim."
        ),
    }
    if inspection["violations"]:
        certificate["build_result"] = "rejected_policy"
        certificate["log"] = "Forbidden constructs: " + ", ".join(inspection["violations"])
        return _memo(project, certificate)
    if lake is None:
        certificate["build_result"] = "lean_unavailable"
        certificate["log"] = "lake not found on PATH; certificate recorded without compilation."
        return _memo(project, certificate)

    try:
        proc = subprocess.run(
            [lake, "build"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        certificate["log"] = (proc.stdout or "") + "\n" + (proc.stderr or "")
        certificate["build_result"] = "success" if proc.returncode == 0 else "failed"
        certificate["returncode"] = proc.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        certificate["build_result"] = "error"
        certificate["log"] = str(exc)
    return _memo(project, certificate)


def _memo(project: Path, certificate: dict[str, Any]) -> dict[str, Any]:
    _COMPILE_CACHE[str(project.resolve())] = copy.deepcopy(certificate)
    return certificate
