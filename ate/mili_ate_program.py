"""Mili BNN-TMR ATE (Automated Test Equipment) production test program."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from mili_bnn_tmr.config import ChipSpec, load_chip_spec

_ATE_DIR = Path(__file__).resolve().parents[2] / "ate"


class TestPhase(Enum):
    CP = "wafer_cp"
    FT = "final_test"
    ES = "engineering_sample"


@dataclass
class ATEStep:
    name: str
    register: str
    expected: int
    mask: int
    limit_min: float | None = None
    limit_max: float | None = None
    unit: str = ""


@dataclass
class ATEResult:
    unit_id: str
    phase: TestPhase
    passed: bool
    steps: list[dict[str, Any]] = field(default_factory=list)
    power_w: float = 0.0
    freq_mhz: int = 0


class ATEProgram:
    """Production test program for CP/FT/ES screening."""

    def __init__(self, spec: ChipSpec | None = None) -> None:
        self._spec = spec or load_chip_spec()
        self._limits = self._load_limits()

    def _load_limits(self) -> dict[str, Any]:
        path = _ATE_DIR / "test_limits.yaml"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    @property
    def steps(self) -> list[ATEStep]:
        return [
            ATEStep("power_on_reset", "STATUS", 0x01, 0x01),
            ATEStep("sram_init", "STATUS", 0x05, 0x05),
            ATEStep("tmr_enable", "TMR_CTRL", 0x01, 0x01),
            ATEStep("dpm_normal", "DPM_STAT", 0x02, 0x03),
            ATEStep(
                "iddq",
                "TEMP_STAT",
                0,
                0,
                limit_min=0,
                limit_max=self._limits.get("max_iddq_ma", 500),
                unit="mA",
            ),
            ATEStep(
                "infer_smoke",
                "INFER_STAT",
                0x02,
                0x02,
                limit_min=0,
                limit_max=self._limits.get("max_infer_latency_ms", 10),
                unit="ms",
            ),
            ATEStep(
                "power_typical",
                "DPM_STAT",
                0,
                0,
                limit_min=0,
                limit_max=self._limits.get("max_typical_power_w", 30),
                unit="W",
            ),
            ATEStep(
                "freq_sweep",
                "CLK_CFG",
                0,
                0,
                limit_min=self._limits.get("min_freq_mhz", 400),
                limit_max=self._limits.get("max_freq_mhz", 800),
                unit="MHz",
            ),
        ]

    def run_unit_test(
        self,
        unit_id: str,
        phase: TestPhase = TestPhase.FT,
        seed: int = 0,
    ) -> ATEResult:
        """Simulate ATE test execution for one die/package."""
        import hashlib

        digest = int(hashlib.md5(f"{unit_id}:{seed}".encode()).hexdigest()[:8], 16)
        yield_sim = 70 + (digest % 25)
        passed = yield_sim > 70

        power_w = round(26.0 + (digest % 30) / 10.0, 1)
        if power_w > 30:
            passed = False
        freq_mhz = 400 + (digest % 401)

        step_results = []
        for step in self.steps:
            step_pass = passed
            if step.name == "power_typical" and power_w > 30:
                step_pass = False
            step_results.append({
                "name": step.name,
                "passed": step_pass,
                "register": step.register,
            })

        return ATEResult(
            unit_id=unit_id,
            phase=phase,
            passed=passed and power_w <= 30 and 400 <= freq_mhz <= 800,
            steps=step_results,
            power_w=min(power_w, 30.0),
            freq_mhz=min(freq_mhz, 800),
        )

    def run_lot(self, unit_ids: list[str], phase: TestPhase = TestPhase.ES) -> dict[str, Any]:
        results = [self.run_unit_test(uid, phase, seed=i) for i, uid in enumerate(unit_ids)]
        passed = sum(1 for r in results if r.passed)
        return {
            "phase": phase.value,
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "yield_pct": round(100.0 * passed / len(results), 1) if results else 0,
            "results": [
                {"unit_id": r.unit_id, "passed": r.passed, "power_w": r.power_w}
                for r in results
            ],
        }
