"""Silicon revision tracking (A0 → A1 → …)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SiliconRevision(str, Enum):
    """Known tape-out revisions in chronological order."""

    A0 = "A0"
    A1 = "A1"
    B0 = "B0"

    @classmethod
    def from_string(cls, value: str) -> SiliconRevision:
        normalized = value.strip().upper()
        try:
            return cls(normalized)
        except ValueError as exc:
            known = ", ".join(r.value for r in cls)
            raise ValueError(f"Unknown silicon revision '{value}'. Known: {known}") from exc

    def next_revision(self) -> SiliconRevision | None:
        order = list(SiliconRevision)
        idx = order.index(self)
        if idx + 1 < len(order):
            return order[idx + 1]
        return None


@dataclass(frozen=True)
class SiliconRevisionInfo:
    revision: SiliconRevision
    lot_id: str
    foundry: str
    packaging: str
    engineering_samples: int

    def to_dict(self) -> dict[str, Any]:
        nxt = self.revision.next_revision()
        return {
            "silicon_rev": self.revision.value,
            "next_rev": nxt.value if nxt else None,
            "lot_id": self.lot_id,
            "foundry": self.foundry,
            "packaging": self.packaging,
            "engineering_samples": self.engineering_samples,
        }
