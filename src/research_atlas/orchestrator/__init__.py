"""Campaign lifecycle: load config, seed graph, run sequential loop, resume."""

from __future__ import annotations

import time
from pathlib import Path

import yaml

from research_atlas.domain_packs import load_pack
from research_atlas.knowledge.loop import KnowledgeLoop
from research_atlas.knowledge.store import KnowledgeStore
from research_atlas.models import CampaignConfig
from research_atlas.paths import campaign_db, campaign_dir
from research_atlas.planner.priority import select
from research_atlas.reporting.markdown import write_report
from research_atlas.workers import SequentialWorker


def load_campaign_config(path: Path) -> CampaignConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CampaignConfig.model_validate(raw)


def open_campaign(campaign_id: str, config: CampaignConfig | None = None) -> tuple[KnowledgeStore, KnowledgeLoop, CampaignConfig]:
    store = KnowledgeStore(campaign_db(campaign_id), campaign_id)
    if config is not None:
        store.save_config(config)
    loaded = store.load_config()
    if loaded is None:
        raise RuntimeError(f"Campaign {campaign_id} has no saved configuration.")
    return store, KnowledgeLoop(store), loaded


def seed_if_needed(store: KnowledgeStore, config: CampaignConfig) -> None:
    if store.get_meta("seeded"):
        return
    pack = load_pack(config.domain_pack)
    nodes, edges = pack.initial_nodes(config)
    loop = KnowledgeLoop(store)
    from research_atlas.models import GraphProposal

    loop.commit(
        GraphProposal(actor="seed", add_nodes=nodes, add_edges=edges, notes="campaign seed")
    )
    store.set_meta("seeded", True)
    store.set_meta("completed_actions", [])
    store.set_meta("step", 0)
    store.append_event("campaign_seeded", {"campaign": config.id})


def stop_reason(store: KnowledgeStore, config: CampaignConfig) -> str | None:
    budget = config.budget
    step = int(store.get_meta("step") or 0)
    if step >= budget.max_steps:
        return "budget.max_steps"
    claims = store.claims()
    statuses = {c.payload.get("claim_id"): c.payload for c in claims}
    criteria = set(config.stop_criteria)
    has_refuted = any(p.get("research_status") == "refuted" for p in statuses.values())
    has_proof = any(
        p.get("evidence_level") in {"reviewed_proof", "formal_proof"} for p in statuses.values()
    )
    if "at_least_one_refuted_claim" in criteria and "at_least_one_reviewed_or_formal_proof" in criteria:
        if has_refuted and has_proof and step > 0:
            # Do not stop before the planned calibration path finishes Lean.
            completed = set(store.get_meta("completed_actions") or [])
            if "act.formalize.arithmetic" in completed:
                return "stop_criteria_met"
    return None


def run_campaign(campaign_id: str, max_steps: int | None = None) -> dict:
    yaml_path = campaign_dir(campaign_id) / "campaign.yaml"
    config = load_campaign_config(yaml_path)
    if max_steps is not None:
        config.budget.max_steps = max_steps
    campaign_dir(campaign_id).mkdir(parents=True, exist_ok=True)
    store, knowledge, config = open_campaign(campaign_id, config)
    seed_if_needed(store, config)
    pack = load_pack(config.domain_pack)
    worker = SequentialWorker(store, knowledge, pack)
    actions = pack.seed_actions(config, store)
    started = time.perf_counter()
    history: list[dict] = []

    while True:
        reason = stop_reason(store, config)
        if reason:
            store.append_event("campaign_stopped", {"reason": reason})
            break
        step = int(store.get_meta("step") or 0)
        completed = set(store.get_meta("completed_actions") or [])
        action = select(actions, completed, config.weights, step=step)
        if action is None:
            store.append_event("campaign_stopped", {"reason": "frontier_empty"})
            break
        store.append_event(
            "replan",
            {"next": action.id, "explanation": action.explanation, "step": step},
        )
        move = worker.run_move(action)
        completed.add(action.id)
        store.set_meta("completed_actions", sorted(completed))
        store.set_meta("step", step + 1)
        history.append(
            {
                "step": step,
                "action": action.id,
                "role": action.role.value,
                "explanation": action.explanation,
                "notes": (move.get("result") or {}).get("notes"),
            }
        )
        if step + 1 >= config.budget.max_steps:
            store.append_event("campaign_stopped", {"reason": "budget.max_steps"})
            break

    elapsed = time.perf_counter() - started
    store.set_meta("seconds_used", elapsed)
    report_path = write_report(store, config)
    return {
        "campaign": campaign_id,
        "steps": store.get_meta("step"),
        "completed": store.get_meta("completed_actions"),
        "seconds": elapsed,
        "report": str(report_path),
        "frontier": knowledge.frontier_summary(),
        "history": history,
    }
