from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
CAMPAIGNS = ROOT / "campaigns"
LEAN = ROOT / "lean"
EXPERIMENTS = ROOT / "experiments"
TESTS = ROOT / "tests"


def campaign_dir(campaign_id: str) -> Path:
    return CAMPAIGNS / campaign_id


def campaign_db(campaign_id: str) -> Path:
    return campaign_dir(campaign_id) / "knowledge.sqlite"


def artifacts_dir(campaign_id: str) -> Path:
    return campaign_dir(campaign_id) / "artifacts"


def reports_dir(campaign_id: str) -> Path:
    return campaign_dir(campaign_id) / "reports"
