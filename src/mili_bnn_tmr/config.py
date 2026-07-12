"""Chip specification loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_PACKAGE_ROOT = Path(__file__).resolve().parent
_DEFAULT_SPEC_PATH = _PACKAGE_ROOT.parent.parent / "config" / "chip_spec.yaml"


@dataclass(frozen=True)
class PowerState:
    name: str
    frequency_mhz: int
    power_w: float
    activation_us: int


@dataclass(frozen=True)
class ChipSpec:
    name: str
    technology_nm: int
    voltage_range_v: tuple[float, float]
    base_frequency_mhz: int
    max_frequency_mhz: int
    sram_mb: int
    pe_count: int
    max_power_w: float
    typical_power_w: float
    packaging: str
    interfaces: tuple[str, ...]
    operating_temp_c: tuple[int, int]
    supported_os: tuple[str, ...]
    model_formats: tuple[str, ...]
    silicon_rev: str
    power_states: dict[str, PowerState]
    requirements: dict[str, float]
    benchmark: dict[str, Any]
    radiation: dict[str, Any]
    tapeout: dict[str, Any]
    release: dict[str, Any]


def load_chip_spec(path: Path | None = None) -> ChipSpec:
    spec_path = path or _DEFAULT_SPEC_PATH
    with spec_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    chip = raw["chip"]
    power_states = {
        name: PowerState(name=name, **state)
        for name, state in raw["power_states"].items()
    }

    tapeout = raw.get("tapeout", {})

    return ChipSpec(
        name=chip["name"],
        technology_nm=chip["technology_nm"],
        voltage_range_v=tuple(chip["voltage_range_v"]),
        base_frequency_mhz=chip["base_frequency_mhz"],
        max_frequency_mhz=chip["max_frequency_mhz"],
        sram_mb=chip["sram_mb"],
        pe_count=chip["pe_count"],
        max_power_w=chip["max_power_w"],
        typical_power_w=chip["typical_power_w"],
        packaging=str(chip.get("packaging", tapeout.get("packaging", "BGA-484"))),
        interfaces=tuple(raw.get("interfaces", [])),
        operating_temp_c=tuple(chip.get("operating_temp_c", [-40, 85])),
        supported_os=tuple(raw.get("supported_os", [])),
        model_formats=tuple(raw.get("model_formats", [])),
        silicon_rev=str(tapeout.get("silicon_rev", "A0")),
        power_states=power_states,
        requirements=raw["requirements"],
        benchmark=raw["benchmark"],
        radiation=raw.get("radiation", {}),
        tapeout=tapeout,
        release=raw.get("release", {}),
    )
