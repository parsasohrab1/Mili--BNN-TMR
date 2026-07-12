"""Hardware SEU campaign on engineering samples (FPGA / ASIC ES)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from mili_bnn_tmr.config import ChipSpec, load_chip_spec
from mili_bnn_tmr.integration.backend import HardwareBackend
from mili_bnn_tmr.integration.backend_factory import create_backend
from mili_bnn_tmr.radiation.monitor import TMRMonitor
from mili_bnn_tmr.radiation.seu_emulator import RadiationProfile
from mili_bnn_tmr.tapeout.samples import EngineeringSampleLot


@dataclass
class UnitSEResult:
    unit_id: str
    trials: int
    corrected: int
    correction_pct: float
    backend: str
    passed: bool


@dataclass
class HardwareCampaignReport:
    lot_id: str
    profile: str
    backend: str
    units_tested: int
    total_trials: int
    overall_correction_pct: float
    unit_results: list[UnitSEResult] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "lot_id": self.lot_id,
            "profile": self.profile,
            "backend": self.backend,
            "units_tested": self.units_tested,
            "total_trials": self.total_trials,
            "overall_correction_pct": self.overall_correction_pct,
            "passed": self.passed,
            "units": [asdict(u) for u in self.unit_results],
        }


class HardwareRadiationCampaign:
    """Run CSR fault-injection SEU trials on each engineering sample unit."""

    def __init__(
        self,
        spec: ChipSpec | None = None,
        backend: HardwareBackend | None = None,
        profile: RadiationProfile = RadiationProfile.COBALT_60,
    ) -> None:
        self._spec = spec or load_chip_spec()
        kind = os.environ.get("MILI_BACKEND", "fpga")
        self._backend = backend or create_backend(kind)
        self._profile = profile
        self._monitor = TMRMonitor()
        self._trials_per_unit = int(self._spec.radiation.get("hw_trials_per_unit", 20))
        self._min_seu = float(self._spec.requirements.get("min_seu_correction_pct", 99))

    def _run_unit_trials(self, unit_id: str) -> UnitSEResult:
        if not hasattr(self._backend, "inject_tmr_fault"):
            raise RuntimeError("Backend does not support CSR fault injection")

        corrected = 0
        for i in range(self._trials_per_unit):
            lane = i % 3
            self._backend.inject_tmr_fault(lane)
            self._backend.start_inference(1)
            self._backend.wait_inference_done()
            stats = self._backend.get_tmr_stats()
            detected = bool(stats.get("disagree"))
            corr = detected
            self._monitor.log_hardware_event(lane, detected, corr)
            if corr:
                corrected += 1
            self._backend.clear_tmr_fault()

        pct = round(100.0 * corrected / self._trials_per_unit, 2)
        return UnitSEResult(
            unit_id=unit_id,
            trials=self._trials_per_unit,
            corrected=corrected,
            correction_pct=pct,
            backend=self._backend.backend_type.value,
            passed=pct >= self._min_seu,
        )

    def run_on_lot(
        self,
        lot: EngineeringSampleLot | None = None,
        max_units: int | None = None,
    ) -> HardwareCampaignReport:
        lot = lot or EngineeringSampleLot.from_spec()
        units = [s for s in lot.samples if s.ate_passed]
        if max_units:
            units = units[:max_units]

        results: list[UnitSEResult] = []
        for sample in units:
            results.append(self._run_unit_trials(sample.unit_id))

        total_corr = sum(u.corrected for u in results)
        total_trials = sum(u.trials for u in results)
        overall = round(100.0 * total_corr / max(total_trials, 1), 2)

        return HardwareCampaignReport(
            lot_id=lot.lot_id,
            profile=self._profile.value,
            backend=self._backend.backend_type.value,
            units_tested=len(results),
            total_trials=total_trials,
            overall_correction_pct=overall,
            unit_results=results,
            passed=overall >= self._min_seu and all(u.passed for u in results),
        )

    def export(self, report: HardwareCampaignReport, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
