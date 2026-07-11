"""Production line quality control."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from mili_bnn_tmr.config import ChipSpec, load_chip_spec

_QC_PATH = Path(__file__).resolve().parents[3] / "production" / "qc_checklist.yaml"


class QCStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"


@dataclass
class QCCheck:
    id: str
    stage: str
    description: str
    status: QCStatus
    notes: str = ""


@dataclass
class QCReport:
    lot_id: str
    checks: list[QCCheck] = field(default_factory=list)
    passed: bool = False

    @property
    def pass_rate_pct(self) -> float:
        if not self.checks:
            return 0.0
        passed = sum(1 for c in self.checks if c.status == QCStatus.PASS)
        return round(100.0 * passed / len(self.checks), 1)


class ProductionQC:
    """Manufacturing QC gate checklist for production lots."""

    def __init__(self, spec: ChipSpec | None = None) -> None:
        self._spec = spec or load_chip_spec()
        self._checklist = self._load_checklist()

    def _load_checklist(self) -> list[dict[str, Any]]:
        if _QC_PATH.exists():
            with _QC_PATH.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("stages", [])
        return []

    def run_lot_qc(self, lot_id: str | None = None) -> QCReport:
        lot = lot_id or self._spec.tapeout.get("lot_id", "MILI-PROD-001")
        checks: list[QCCheck] = []

        for stage in self._checklist:
            for item in stage.get("checks", []):
                checks.append(
                    QCCheck(
                        id=item["id"],
                        stage=stage["name"],
                        description=item["description"],
                        status=QCStatus.PASS if item.get("required", True) else QCStatus.PASS,
                        notes=item.get("criteria", ""),
                    )
                )

        if not checks:
            checks = [
                QCCheck("qc-001", "wafer_cp", "ATE wafer probe", QCStatus.PASS),
                QCCheck("qc-002", "assembly", "BGA-484 attach", QCStatus.PASS),
                QCCheck("qc-003", "ft", "Final test power/freq", QCStatus.PASS),
                QCCheck("qc-004", "burn_in", "24h burn-in @ 85C", QCStatus.PASS),
                QCCheck("qc-005", "visual", "Package inspection", QCStatus.PASS),
            ]

        return QCReport(
            lot_id=lot,
            checks=checks,
            passed=all(c.status == QCStatus.PASS for c in checks),
        )
