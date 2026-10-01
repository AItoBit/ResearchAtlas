from research_atlas.domain_packs.base import DomainPack
from research_atlas.domain_packs.finite_graphs.pack import FiniteGraphsPack

PACKS: dict[str, type[DomainPack]] = {
    "finite_graphs": FiniteGraphsPack,
}


def load_pack(name: str) -> DomainPack:
    if name not in PACKS:
        raise KeyError(f"Unknown domain pack: {name}")
    return PACKS[name]()
