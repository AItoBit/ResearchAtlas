from __future__ import annotations

from abc import ABC, abstractmethod

from research_atlas.knowledge.store import KnowledgeStore
from research_atlas.models import Action, CampaignConfig


class DomainPack(ABC):
    """What varies between mathematical projects.

    The traceability protocol stays stable; mathematical strategy is configurable.
    """

    name: str

    @abstractmethod
    def seed_actions(self, config: CampaignConfig, store: KnowledgeStore) -> list[Action]:
        raise NotImplementedError

    @abstractmethod
    def initial_nodes(self, config: CampaignConfig) -> tuple[list, list]:
        """Return (nodes, edges) that must exist before the first work move."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, action: Action, store: KnowledgeStore) -> dict:
        raise NotImplementedError
