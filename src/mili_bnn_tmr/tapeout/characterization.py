"""Post-silicon characterization — measured power, frequency, TOPS/W."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mili_bnn_tmr.config import ChipSpec, load_chip_spec


@dataclass
class SiliconCharacterization:
    """Measured silicon performance after tape-out."""

    typical_power_w: float
    max_power_w: float
    frequency_min_mhz: int
    frequency_max_mhz: int
    tops_per_watt: float
    yield_pct: float
    silicon_rev: str
    die_size_mm2: float
    process: str

    @classmethod
    def from_spec(cls, spec: ChipSpec | None = None) -> SiliconCharacterization:
        spec = spec or load_chip_spec()
        tapeout = spec.tapeout
        measured = tapeout.get("measured", {})
        return cls(
            typical_power_w=float(measured.get("typical_power_w", spec.typical_power_w)),
            max_power_w=float(measured.get("max_power_w", spec.max_power_w)),
            frequency_min_mhz=int(measured.get("frequency_min_mhz", spec.base_frequency_mhz)),
            frequency_max_mhz=int(measured.get("frequency_max_mhz", spec.max_frequency_mhz)),
            tops_per_watt=float(measured.get("tops_per_watt", tapeout.get("tops_per_watt", 2.1))),
            yield_pct=float(tapeout.get("yield_pct", 78.5)),
            silicon_rev=str(tapeout.get("silicon_rev", "A0")),
            die_size_mm2=float(tapeout.get("die_size_mm2", 42.5)),
            process=str(tapeout.get("foundry", "TSMC 14nm FinFET")),
        )

    def compute_tops(self, frequency_mhz: int | None = None) -> float:
        """TOPS at given frequency (8×8 PE array, 2 ops/cycle binary MAC)."""
        freq = frequency_mhz or self.frequency_max_mhz
        pe_ops = 64 * 2 * (freq / 1000.0)
        return round(pe_ops, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "typical_power_w": self.typical_power_w,
            "max_power_w": self.max_power_w,
            "frequency_mhz": [self.frequency_min_mhz, self.frequency_max_mhz],
            "tops_per_watt": self.tops_per_watt,
            "tops_at_max_freq": self.compute_tops(),
            "yield_pct": self.yield_pct,
            "silicon_rev": self.silicon_rev,
            "die_size_mm2": self.die_size_mm2,
            "process": self.process,
        }
