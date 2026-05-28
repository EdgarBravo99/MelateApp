from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TicketReview:
    label: str | None
    numbers: list[int]
    hits: int
    hit_numbers: list[int]
    missed_ticket_numbers: list[int]
    missed_draw_numbers: list[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "numbers": self.numbers,
            "hits": self.hits,
            "hit_numbers": self.hit_numbers,
            "missed_ticket_numbers": self.missed_ticket_numbers,
            "missed_draw_numbers": self.missed_draw_numbers,
        }


@dataclass(frozen=True)
class Graph:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "metadata": self.metadata,
        }
