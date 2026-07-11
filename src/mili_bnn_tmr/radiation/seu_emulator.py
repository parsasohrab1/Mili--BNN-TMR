"""Radiation environment emulator (Co-60, proton beam, orbit profiles)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from mili_bnn_tmr.config import load_chip_spec


class RadiationProfile(Enum):
    COBALT_60 = "cobalt_60"
    PROTON_BEAM = "proton_beam"
    LEO_ORBIT = "leo_orbit"
    GEO_ORBIT = "geo_orbit"


@dataclass
class SEUEventSpec:
    cycle: int
    bit_index: int
    fault_lane: int
    temperature_c: float


@dataclass
class MTBFResult:
    profile: str
    mtbf_hours: float
    seu_rate_per_hour: float
    sensitive_bits: int
    meets_aerospace_standard: bool


class SEUEmulator:
    """
    Software SEU emulator for radiation test campaigns.

  Profiles align with aerospace screening (Co-60 / proton beam) and
  mission orbit models referenced in ECSS-Q-ST-60-15C.
    """

    AEROSPACE_MTBF_MIN_HOURS = 10_000

    def __init__(self, profile: RadiationProfile = RadiationProfile.COBALT_60) -> None:
        self._spec = load_chip_spec()
        self._rad_cfg = self._spec.radiation
        self.profile = profile
        self._profile_cfg = self._rad_cfg["profiles"][profile.value]

    @property
    def temperature_c(self) -> float:
        return float(self._profile_cfg.get("temperature_c", 25))

    def seu_rate_per_hour(self) -> float:
        fluence = float(self._profile_cfg["fluence_rate_cm2_h"])
        cross_section = float(self._profile_cfg["seu_cross_section_cm2"])
        sensitive_bits = int(self._rad_cfg["sensitive_bits"])
        return fluence * cross_section * sensitive_bits

    def compute_mtbf(self) -> MTBFResult:
        rate = self.seu_rate_per_hour()
        mtbf = 1.0 / rate if rate > 0 else float("inf")
        return MTBFResult(
            profile=self.profile.value,
            mtbf_hours=round(mtbf, 1),
            seu_rate_per_hour=rate,
            sensitive_bits=int(self._rad_cfg["sensitive_bits"]),
            meets_aerospace_standard=mtbf >= self.AEROSPACE_MTBF_MIN_HOURS,
        )

    def generate_events(
        self,
        num_cycles: int,
        seed: int = 42,
        temperature_c: float | None = None,
    ) -> list[SEUEventSpec]:
        """Poisson-distributed SEU events over a compute campaign."""
        temp = temperature_c if temperature_c is not None else self.temperature_c
        rate = self.seu_rate_per_hour()
        expected = rate * (num_cycles / 3_600_000)
        rng = np.random.default_rng(seed)
        num_events = int(rng.poisson(max(expected, num_cycles * 0.001)))

        events: list[SEUEventSpec] = []
        sensitive_bits = int(self._rad_cfg["sensitive_bits"])
        for _ in range(num_events):
            events.append(
                SEUEventSpec(
                    cycle=int(rng.integers(0, num_cycles)),
                    bit_index=int(rng.integers(0, sensitive_bits)),
                    fault_lane=int(rng.integers(0, 3)),
                    temperature_c=temp,
                )
            )
        return events

    def thermal_derating_factor(self, temperature_c: float) -> float:
        """Performance derating model for -40°C to +85°C envelope."""
        t_min, t_max = -40.0, 85.0
        t = max(t_min, min(t_max, temperature_c))
        if t <= 25:
            return 1.0 - 0.0003 * (25 - t)
        return 1.0 - 0.00083 * (t - 25)

    def profile_info(self) -> dict[str, Any]:
        return {
            "profile": self.profile.value,
            "description": self._profile_cfg.get("description", ""),
            "temperature_c": self.temperature_c,
            "mtbf": self.compute_mtbf().__dict__,
        }
