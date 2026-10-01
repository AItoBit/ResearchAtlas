"""ResearchAtlas command-line interface."""

from __future__ import annotations

from typing import Optional

import typer
import yaml

from research_atlas.knowledge.store import KnowledgeStore
from research_atlas.orchestrator import load_campaign_config, open_campaign, run_campaign, seed_if_needed
from research_atlas.paths import CAMPAIGNS, campaign_db, campaign_dir
from research_atlas.reporting.markdown import write_report

app = typer.Typer(help="ResearchAtlas — mathematical research with verifiable evidence.")


@app.command()
def init(
    campaign: str = typer.Option("handshake", help="Campaign id."),
    force: bool = typer.Option(False, help="Re-seed even if a database already exists."),
) -> None:
    """Create campaign storage and register the initial scientific memory."""
    cfg_path = campaign_dir(campaign) / "campaign.yaml"
    if not cfg_path.exists():
        raise typer.BadParameter(f"Missing {cfg_path}")
    config = load_campaign_config(cfg_path)
    db = campaign_db(campaign)
    if db.exists() and force:
        db.unlink()
    store, _loop, config = open_campaign(campaign, config)
    seed_if_needed(store, config)
    typer.echo(f"Initialized campaign '{campaign}' at {campaign_dir(campaign)}")
    store.close()


@app.command()
def run(
    campaign: str = typer.Option("handshake", help="Campaign id."),
    max_steps: Optional[int] = typer.Option(None, help="Override budget.max_steps."),
) -> None:
    """Run the sequential worker until stop criteria or budget."""
    result = run_campaign(campaign, max_steps=max_steps)
    typer.echo(f"Campaign {result['campaign']} finished after {result['steps']} steps.")
    typer.echo(f"Completed: {result['completed']}")
    typer.echo(f"Report: {result['report']}")


@app.command()
def report(
    campaign: str = typer.Option("handshake", help="Campaign id."),
) -> None:
    """Regenerate the Markdown campaign report from current memory."""
    store, _loop, config = open_campaign(campaign)
    path = write_report(store, config)
    typer.echo(f"Wrote {path}")
    store.close()


@app.command()
def status(
    campaign: str = typer.Option("handshake", help="Campaign id."),
) -> None:
    """Print frontier summary and claim table."""
    store, loop, config = open_campaign(campaign)
    frontier = loop.frontier_summary()
    typer.echo(f"{config.name} [{config.id}]")
    typer.echo(f"steps={store.get_meta('step')} completed={store.get_meta('completed_actions')}")
    typer.echo(f"frontier={frontier}")
    for claim in store.claims():
        p = claim.payload
        typer.echo(
            f"  {p.get('claim_id')} v{p.get('statement_version')}: "
            f"{p.get('research_status')}/{p.get('evidence_level')} :: {p.get('statement')[:80]}"
        )
    store.close()


@app.command("list-campaigns")
def list_campaigns() -> None:
    """List campaign directories that contain campaign.yaml."""
    if not CAMPAIGNS.exists():
        typer.echo("No campaigns directory.")
        raise typer.Exit()
    for path in sorted(CAMPAIGNS.iterdir()):
        yaml_path = path / "campaign.yaml"
        if yaml_path.exists():
            raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            typer.echo(f"{path.name}: {raw.get('name')}")


if __name__ == "__main__":
    app()
