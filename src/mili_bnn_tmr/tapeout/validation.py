"""Phase 6 tape-out acceptance validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mili_bnn_tmr.config import ChipSpec, load_chip_spec
from mili_bnn_tmr.tapeout.characterization import SiliconCharacterization
from mili_bnn_tmr.tapeout.samples import EngineeringSampleLot
from mili_bnn_tmr.tapeout.signoff import SignoffRunner


@dataclass
class TapeoutValidationReport:
    signoff_passed: bool
    typical_power_w: float
    max_power_w: float
    frequency_range_mhz: tuple[int, int]
    yield_pct: float
    tops_per_watt: float
    engineering_samples: int
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


class TapeoutValidator:
    """Validate Phase 6 acceptance criteria against measured silicon."""

    def __init__(self, spec: ChipSpec | None = None) -> None:
        self._spec = spec or load_chip_spec()
        self._req = self._spec.requirements

    def validate(self) -> TapeoutValidationReport:
        signoff = SignoffRunner(self._spec).run_signoff()
        char = SiliconCharacterization.from_spec(self._spec)
        lot = EngineeringSampleLot.from_spec()

        passed = (
            signoff.passed
            and char.typical_power_w <= self._req.get("max_typical_power_w", 30)
            and char.max_power_w < self._req.get("max_power_w_limit", 50)
            and char.frequency_min_mhz <= self._spec.base_frequency_mhz
            and char.frequency_max_mhz >= self._spec.max_frequency_mhz
            and lot.yield_pct > self._req.get("min_yield_pct", 70)
            and char.tops_per_watt >= self._req.get("min_tops_per_watt", 2.0)
        )

        return TapeoutValidationReport(
            signoff_passed=signoff.passed,
            typical_power_w=char.typical_power_w,
            max_power_w=char.max_power_w,
            frequency_range_mhz=(char.frequency_min_mhz, char.frequency_max_mhz),
            yield_pct=lot.yield_pct,
            tops_per_watt=char.tops_per_watt,
            engineering_samples=lot.quantity,
            passed=passed,
            details={
                "signoff": signoff.to_dict(),
                "characterization": char.to_dict(),
                "sample_lot": lot.summary(),
                "targets": {
                    "max_typical_power_w": self._req.get("max_typical_power_w", 30),
                    "max_power_w": self._req.get("max_power_w_limit", 50),
                    "frequency_mhz": [
                        self._spec.base_frequency_mhz,
                        self._spec.max_frequency_mhz,
                    ],
                    "min_yield_pct": self._req.get("min_yield_pct", 70),
                    "min_tops_per_watt": self._req.get("min_tops_per_watt", 2.0),
                },
            },
        )
