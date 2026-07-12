"""Engineering sample lot tracking (10–50 units) with fab traceability."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

from mili_bnn_tmr.config import load_chip_spec


class SampleStatus(Enum):
    WAFER = "wafer"
    DICED = "diced"
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
    fab_lot: str = ""
    assembly_lot: str = ""
    package_lot: str = ""
    tracking_id: str = ""
    ship_date: str = ""
    customer_id: str = ""
    ate_passed: bool = False
    notes: str = ""


@dataclass
class EngineeringSampleLot:
    lot_id: str
    silicon_rev: str
    quantity: int
    fab: str = ""
    foundry_lot: str = ""
    assembly_site: str = ""
    ship_to: str = ""
    samples: list[EngineeringSample] = field(default_factory=list)

    @classmethod
    def from_spec(cls) -> EngineeringSampleLot:
        spec = load_chip_spec()
        tapeout = spec.tapeout
        lot_id = str(tapeout.get("lot_id", "MILI-ES-A0-001"))
        rev = str(tapeout.get("silicon_rev", "A0"))
        qty = int(tapeout.get("engineering_samples", 25))
        yield_pct = float(tapeout.get("yield_pct", 78.5))
        fab = str(tapeout.get("foundry", "TSMC 14nm FinFET"))
        foundry_lot = str(tapeout.get("foundry_lot", "TSM14-A0-2026Q2"))
        assembly = str(tapeout.get("assembly_site", "ASE-KH"))
        ship_to = str(tapeout.get("ship_to", "IThub Engineering Lab"))

        pass_count = int(round(qty * yield_pct / 100))
        samples: list[EngineeringSample] = []
        for i in range(qty):
            passed = i < pass_count
            samples.append(
                EngineeringSample(
                    unit_id=f"ES-{rev}-{i+1:03d}",
                    wafer_id=f"W{1 + i // 12:02d}",
                    die_x=i % 4,
                    die_y=(i // 4) % 3,
                    status=SampleStatus.SHIPPED if passed else SampleStatus.TESTED_FAIL,
                    fab_lot=foundry_lot,
                    assembly_lot=f"ASE-{lot_id}",
                    package_lot=f"BGA484-{lot_id}",
                    tracking_id=f"TRK-{lot_id}-{i+1:03d}",
                    ship_date=str(date.today()) if passed else "",
                    customer_id=ship_to if passed else "",
                    ate_passed=passed,
                )
            )

        return cls(
            lot_id=lot_id,
            silicon_rev=rev,
            quantity=qty,
            fab=fab,
            foundry_lot=foundry_lot,
            assembly_site=assembly,
            ship_to=ship_to,
            samples=samples,
        )

    @classmethod
    def from_manifest(cls, path: str | Path) -> EngineeringSampleLot:
        """Load lot from fab/ATE manifest JSON."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        samples = [
            EngineeringSample(
                unit_id=s["unit_id"],
                wafer_id=s.get("wafer_id", ""),
                die_x=int(s.get("die_x", 0)),
                die_y=int(s.get("die_y", 0)),
                status=SampleStatus(s.get("status", "packaged")),
                fab_lot=s.get("fab_lot", ""),
                assembly_lot=s.get("assembly_lot", ""),
                package_lot=s.get("package_lot", ""),
                tracking_id=s.get("tracking_id", ""),
                ship_date=s.get("ship_date", ""),
                customer_id=s.get("customer_id", ""),
                ate_passed=bool(s.get("ate_passed", False)),
                notes=s.get("notes", ""),
            )
            for s in data.get("samples", [])
        ]
        return cls(
            lot_id=data["lot_id"],
            silicon_rev=data.get("silicon_rev", "A0"),
            quantity=len(samples),
            fab=data.get("fab", ""),
            foundry_lot=data.get("foundry_lot", ""),
            assembly_site=data.get("assembly_site", ""),
            ship_to=data.get("ship_to", ""),
            samples=samples,
        )

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
            "fab": self.fab,
            "foundry_lot": self.foundry_lot,
            "assembly_site": self.assembly_site,
            "ship_to": self.ship_to,
            "samples": [{**asdict(s), "status": s.status.value} for s in self.samples],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def export_csv(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "unit_id", "wafer_id", "die_x", "die_y", "status",
            "fab_lot", "assembly_lot", "package_lot", "tracking_id",
            "ship_date", "customer_id", "ate_passed",
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for s in self.samples:
                row = {k: getattr(s, k) for k in fields if k != "status"}
                row["status"] = s.status.value
                w.writerow(row)

    def summary(self) -> dict[str, Any]:
        return {
            "lot_id": self.lot_id,
            "silicon_rev": self.silicon_rev,
            "quantity": self.quantity,
            "pass": self.pass_count,
            "fail": self.quantity - self.pass_count,
            "yield_pct": self.yield_pct,
            "foundry_lot": self.foundry_lot,
            "assembly_site": self.assembly_site,
        }
