"""Engineering sample lot tracking (10–50 units)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from mili_bnn_tmr.config import load_chip_spec


class SampleStatus(Enum):
    WAFER = "wafer"
    PACKAGED = "packaged"
    TESTED_PASS = "tested_pass"
    TESTED_FAIL = "tested_fail"
    SHIPPED = "shipped"


@dataclass
class EngineeringSample:
    unit_id: str
    wafer_id: str
    die_x: int
    die_y: int
    status: SampleStatus
    ate_passed: bool = False
    notes: str = ""


@dataclass
class EngineeringSampleLot:
    lot_id: str
    silicon_rev: str
    quantity: int
    samples: list[EngineeringSample] = field(default_factory=list)

    @classmethod
    def from_spec(cls) -> EngineeringSampleLot:
        spec = load_chip_spec()
        tapeout = spec.tapeout
        lot_id = str(tapeout.get("lot_id", "MILI-ES-A0-001"))
        rev = str(tapeout.get("silicon_rev", "A0"))
        qty = int(tapeout.get("engineering_samples", 25))
        yield_pct = float(tapeout.get("yield_pct", 78.5))

        pass_count = int(round(qty * yield_pct / 100))
        samples: list[EngineeringSample] = []
        for i in range(qty):
            passed = i < pass_count
            samples.append(
                EngineeringSample(
                    unit_id=f"ES-{rev}-{i+1:03d}",
                    wafer_id=f"W{1 + i // 12}",
                    die_x=i % 4,
                    die_y=(i // 4) % 3,
                    status=SampleStatus.TESTED_PASS if passed else SampleStatus.TESTED_FAIL,
                    ate_passed=passed,
                )
            )

        return cls(lot_id=lot_id, silicon_rev=rev, quantity=qty, samples=samples)

    @property
    def pass_count(self) -> int:
        return sum(1 for s in self.samples if s.ate_passed)

    @property
    def yield_pct(self) -> float:
        if not self.samples:
            return 0.0
        return round(100.0 * self.pass_count / len(self.samples), 1)

    def export(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "lot_id": self.lot_id,
            "silicon_rev": self.silicon_rev,
            "quantity": self.quantity,
            "yield_pct": self.yield_pct,
            "samples": [
                {**asdict(s), "status": s.status.value} for s in self.samples
            ],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def summary(self) -> dict[str, Any]:
        return {
            "lot_id": self.lot_id,
            "silicon_rev": self.silicon_rev,
            "quantity": self.quantity,
            "pass": self.pass_count,
            "fail": self.quantity - self.pass_count,
            "yield_pct": self.yield_pct,
        }
