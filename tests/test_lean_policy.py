from research_atlas.verification.lean import inspect_sources, try_compile
from research_atlas.verification.policies import lean_source_allowed
from research_atlas.paths import LEAN


def test_handshake_sources_forbid_gaps():
    project = LEAN / "ResearchAtlasLean"
    inspection = inspect_sources(project)
    assert inspection["violations"] == []
    handshake = (project / "ResearchAtlasLean" / "Handshake.lean").read_text(encoding="utf-8")
    ok, hits = lean_source_allowed(handshake)
    assert ok and not hits
    assert "sorry" not in handshake
    assert "twice_the_edge_count_is_even" in handshake


def test_certificate_records_faithfulness_gap():
    cert = try_compile()
    assert "partial" in cert["faithfulness"]
    assert cert["theorem"] == "ResearchAtlas.Handshake.twice_the_edge_count_is_even"
    assert cert["build_result"] in {"success", "lean_unavailable", "failed", "error"}
    if cert["build_result"] == "success":
        assert cert["file_hash"]
        assert cert["environment_hash"]
