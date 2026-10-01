"""Markdown campaign report: established results, gaps, and next experiments."""

from __future__ import annotations

from pathlib import Path

from research_atlas.knowledge.store import KnowledgeStore
from research_atlas.models import CampaignConfig, NodeType, RelationType
from research_atlas.paths import reports_dir


def render(store: KnowledgeStore, config: CampaignConfig) -> str:
    claims = store.claims()
    questions = store.nodes(NodeType.QUESTION)
    experiments = store.nodes(NodeType.EXPERIMENT)
    examples = store.nodes(NodeType.EXAMPLE)
    proofs = store.nodes(NodeType.PROOF_ATTEMPT)
    obstacles = store.nodes(NodeType.OBSTACLE)
    verifications = store.nodes(NodeType.VERIFICATION)
    edges = store.edges()
    events = store.events()

    def section_claims(status: str) -> list:
        return [c for c in claims if c.payload.get("research_status") == status]

    lines: list[str] = []
    lines.append(f"# ResearchAtlas campaign report: {config.name}")
    lines.append("")
    lines.append("This report separates **research status** from **evidence level**.")
    lines.append("A bounded exhaustive check never becomes a universal proof.")
    lines.append("")
    lines.append("## Campaign")
    lines.append("")
    lines.append(f"- **Id:** `{config.id}`")
    lines.append(f"- **Domain:** {config.domain}")
    lines.append(f"- **Domain pack:** `{config.domain_pack}`")
    lines.append(f"- **Central question:** {config.central_question.strip()}")
    lines.append(f"- **Steps executed:** {store.get_meta('step', 0)}")
    lines.append(f"- **Completed actions:** {', '.join(store.get_meta('completed_actions') or []) or '(none)'}")
    lines.append("")
    lines.append("## Result map")
    lines.append("")
    lines.append("| Claim | Version | Status | Evidence | Formalization | Statement |")
    lines.append("|---|---:|---|---|---|---|")
    for c in claims:
        p = c.payload
        statement = p.get("statement", "").replace("|", "\\|")
        lines.append(
            f"| `{p.get('claim_id')}` | {p.get('statement_version')} | "
            f"{p.get('research_status')} | {p.get('evidence_level')} | "
            f"{p.get('formalization_status')} | {statement} |"
        )
    lines.append("")
    lines.append("### Established")
    lines.append("")
    established = section_claims("established")
    if not established:
        lines.append("_None yet._")
    for c in established:
        p = c.payload
        lines.append(f"- **{p['claim_id']} v{p['statement_version']}** ({p['evidence_level']}): {p['statement']}")
        if p.get("formal_statement_faithfulness"):
            lines.append(f"  - Faithfulness: {p['formal_statement_faithfulness']}")
        if p.get("assumptions"):
            lines.append(f"  - Assumptions: {'; '.join(p['assumptions'])}")
    lines.append("")
    lines.append("### Refuted (retained; not overwritten)")
    lines.append("")
    refuted = section_claims("refuted")
    if not refuted:
        lines.append("_None yet._")
    for c in refuted:
        p = c.payload
        lines.append(f"- **{p['claim_id']} v{p['statement_version']}**: {p['statement']}")
    lines.append("")
    lines.append("### Open / proposed")
    lines.append("")
    opened = [c for c in claims if c.payload.get("research_status") in {"open", "proposed", "active"}]
    if not opened:
        lines.append("_None._")
    for c in opened:
        p = c.payload
        extra = ""
        if p.get("universe_covered"):
            extra = f" Bounded universe: {p['universe_covered']}."
        lines.append(
            f"- **{p['claim_id']} v{p['statement_version']}** ({p['evidence_level']}): {p['statement']}.{extra}"
        )
    lines.append("")
    lines.append("## Questions")
    lines.append("")
    for q in questions:
        p = q.payload
        if str(p.get("text", "")).startswith("Evidence update pending"):
            continue
        lines.append(f"- ({p.get('status')}) {p.get('text')}")
        lines.append(f"  - Resolve when: {p.get('resolution_criteria')}")
    lines.append("")
    lines.append("## Experiments (reproducible)")
    lines.append("")
    for e in experiments:
        p = e.payload
        lines.append(f"- Program `{p.get('program')}`")
        lines.append(f"  - Coverage: {p.get('coverage')}")
        lines.append(f"  - Manifest: `{p.get('manifesto_hash')}`")
        lines.append(f"  - Second checker: {p.get('second_checker')}; agree={p.get('checkers_agree')}")
        lines.append(f"  - Promotes to universal proof: {p.get('results', {}).get('promotes_to_universal_proof', False)}")
    lines.append("")
    lines.append("## Counterexamples")
    lines.append("")
    refutes = [e for e in edges if e.relation == RelationType.REFUTES]
    if not refutes:
        lines.append("_None recorded._")
    for edge in refutes:
        src = store.get_node(edge.source_id)
        tgt = store.get_node(edge.target_id)
        lines.append(
            f"- Example `{edge.source_id}` refutes claim `{tgt.payload.get('claim_id') if tgt else '?'}` "
            f"version **{edge.target_version}** (verification {edge.provenance.evidence_ids})."
        )
        if src:
            lines.append(f"  - {src.payload.get('description')}")
            lines.append(f"  - Object: `{src.payload.get('object_repr')}`")
    lines.append("")
    lines.append("## Proof attempts")
    lines.append("")
    for pnode in proofs:
        p = pnode.payload
        lines.append(f"- Target `{p.get('target_claim_id')}` v{p.get('target_version')} status={p.get('status')}")
        for i, step in enumerate(p.get("steps") or [], 1):
            lines.append(f"  {i}. {step}")
        if p.get("gaps"):
            lines.append(f"  - Gaps: {p['gaps']}")
        else:
            lines.append("  - Gaps: none")
    lines.append("")
    lines.append("## Obstacles")
    lines.append("")
    if not obstacles:
        lines.append("_None._")
    for o in obstacles:
        p = o.payload
        lines.append(f"- **{p.get('blocked_strategy')}**")
        lines.append(f"  - Cause: {p.get('cause')}")
        lines.append(f"  - Scope: {p.get('scope')}")
    lines.append("")
    lines.append("## Verifications")
    lines.append("")
    for v in verifications:
        p = v.payload
        lines.append(f"- `{p.get('verifier')}` → **{p.get('result')}** independent={p.get('independent')}")
        env = p.get("environment") or {}
        if env.get("build_result"):
            lines.append(
                f"  - Lean build={env.get('build_result')} toolchain={env.get('lean_toolchain')} "
                f"file_hash=`{env.get('file_hash')}`"
            )
            lines.append(f"  - Theorems: {env.get('theorems')}")
            lines.append(f"  - Axiomatic dependencies: {env.get('axiomatic_dependencies')}")
    lines.append("")
    lines.append("## Relations (with provenance)")
    lines.append("")
    lines.append("| Relation | From | To | Version | Actor | Notes |")
    lines.append("|---|---|---|---:|---|---|")
    for e in edges:
        lines.append(
            f"| {e.relation.value} | `{e.source_id}` | `{e.target_id}` | "
            f"{e.target_version if e.target_version is not None else ''} | "
            f"{e.provenance.actor} | {e.provenance.notes} |"
        )
    lines.append("")
    lines.append("## Frontier")
    lines.append("")
    completed = set(store.get_meta("completed_actions") or [])
    lines.append("Completed work items:")
    for item in sorted(completed):
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Event log (tail)")
    lines.append("")
    for ev in events[-20:]:
        lines.append(f"- `{ev.created_at}` **{ev.type}** `{ev.id}`")
    lines.append("")
    lines.append("## Out of scope reminders")
    lines.append("")
    lines.append("- Originality is not inferred from model non-recollection.")
    lines.append("- Numerical or bounded evidence is not a universal demonstration.")
    lines.append("- Results are not published automatically.")
    lines.append("")
    return "\n".join(lines)


def write_report(store: KnowledgeStore, config: CampaignConfig) -> Path:
    folder = reports_dir(store.campaign_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "campaign_report.md"
    path.write_text(render(store, config), encoding="utf-8")
    store.append_event("report_written", {"path": str(path)})
    return path
