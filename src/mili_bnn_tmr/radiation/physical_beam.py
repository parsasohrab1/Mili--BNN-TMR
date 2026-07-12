"""Physical radiation beam test protocol (Co-60 / proton) on engineering samples."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mili_bnn_tmr.config import ChipSpec, load_chip_spec
from mili_bnn_tmr.radiation.seu_emulator import RadiationProfile, SEUEmulator


class PhysicalTestStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    NOT_REQUIRED = "not_required"


@dataclass
class BeamTestPlan:
    profile: RadiationProfile
    facility: str
    beam_energy: str
    fluence_target_cm2: float
    sample_count: int
    temperature_c: float
    status: PhysicalTestStatus = PhysicalTestStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.value,
            "facility": self.facility,
            "beam_energy": self.beam_energy,
            "fluence_target_cm2": self.fluence_target_cm2,
            "sample_count": self.sample_count,
            "temperature_c": self.temperature_c,
            "status": self.status.value,
        }


@dataclass
class PhysicalBeamReport:
    profile: str
    software_validated: bool
    physical_status: PhysicalTestStatus
    seu_correction_pct_software: float
    seu_correction_pct_hardware: float | None
    mtbf_hours: float
    plans: list[BeamTestPlan] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "software_validated": self.software_validated,
            "physical_status": self.physical_status.value,
            "seu_correction_pct_software": self.seu_correction_pct_software,
            "seu_correction_pct_hardware": self.seu_correction_pct_hardware,
            "mtbf_hours": self.mtbf_hours,
            "plans": [p.to_dict() for p in self.plans],
            "passed": self.passed,
        }


_FACILITIES = {
    RadiationProfile.COBALT_60: ("Co-60 gamma chamber", "1.17/1.33 MeV"),
    RadiationProfile.PROTON_BEAM: ("Cyclotron facility", "62 MeV protons"),
}


class PhysicalBeamProtocol:
    """ECSS physical beam test planning and result tracking."""

    def __init__(self, spec: ChipSpec | None = None) -> None:
        self._spec = spec or load_chip_spec()
        self._radiation = self._spec.radiation

    def default_plans(self, sample_count: int | None = None) -> list[BeamTestPlan]:
        qty = sample_count or int(self._spec.tapeout.get("engineering_samples", 25))
        plans: list[BeamTestPlan] = []
        for profile in (RadiationProfile.COBALT_60, RadiationProfile.PROTON_BEAM):
            prof = self._radiation.get("profiles", {}).get(profile.value, {})
            facility, energy = _FACILITIES[profile]
            fluence_h = float(prof.get("fluence_rate_cm2_h", 50))
            plans.append(
                BeamTestPlan(
                    profile=profile,
                    facility=facility,
                    beam_energy=energy,
                    fluence_target_cm2=fluence_h * 8.0,
                    sample_count=min(qty, 10),
                    temperature_c=float(prof.get("temperature_c", 25)),
                    status=PhysicalTestStatus.PENDING,
                )
            )
        return plans

    def evaluate(
        self,
        software_seu_pct: float,
        hardware_seu_pct: float | None = None,
    ) -> PhysicalBeamReport:
        min_seu = float(self._spec.requirements.get("min_seu_correction_pct", 99))
        mtbf = SEUEmulator(RadiationProfile.COBALT_60).compute_mtbf()
        plans = self.default_plans()

        if hardware_seu_pct is not None:
            physical_status = PhysicalTestStatus.COMPLETE
            passed = hardware_seu_pct >= min_seu and software_seu_pct >= min_seu
        else:
            physical_status = PhysicalTestStatus.PENDING
            passed = software_seu_pct >= min_seu

        return PhysicalBeamReport(
            profile="cobalt_60+proton_beam",
            software_validated=software_seu_pct >= min_seu,
            physical_status=physical_status,
            seu_correction_pct_software=software_seu_pct,
            seu_correction_pct_hardware=hardware_seu_pct,
            mtbf_hours=mtbf.mtbf_hours,
            plans=plans,
            passed=passed,
        )
