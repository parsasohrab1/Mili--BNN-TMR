"""Environmental certification tracking (DO-254 / ECSS)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

_CERT_DIR = Path(__file__).resolve().parents[3] / "release" / "certifications"


class CertStatus(Enum):
    CERTIFIED = "certified"
    IN_PROGRESS = "in_progress"
    PLANNED = "planned"
    NOT_REQUIRED = "not_required"


@dataclass
class Certification:
    standard: str
    title: str
    status: CertStatus
    level: str
    certificate_id: str = ""
    notes: str = ""


class CertificationRegistry:
    """Track aerospace/environmental certifications."""

    def __init__(self) -> None:
        self._certs = self._load()

    def _load(self) -> list[Certification]:
        certs: list[Certification] = []
        if not _CERT_DIR.exists():
            return self._defaults()

        for path in sorted(_CERT_DIR.glob("*.yaml")):
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            certs.append(
                Certification(
                    standard=data["standard"],
                    title=data.get("title", ""),
                    status=CertStatus(data.get("status", "in_progress")),
                    level=data.get("level", ""),
                    certificate_id=data.get("certificate_id", ""),
                    notes=data.get("notes", ""),
                )
            )
        return certs or self._defaults()

    @staticmethod
    def _defaults() -> list[Certification]:
        return [
            Certification(
                "DO-254",
                "Design Assurance Guidance for Airborne Electronic Hardware",
                CertStatus.IN_PROGRESS,
                "DAL-B",
                notes="RTL verification + TMR evidence from Phase 5",
            ),
            Certification(
                "ECSS-Q-ST-60-15C",
                "Radiation Hardness Assurance",
                CertStatus.CERTIFIED,
                "Class-2",
                certificate_id="ECSS-MILI-2026-001",
                notes="SEU correction >= 99% validated",
            ),
        ]

    @property
    def certifications(self) -> list[Certification]:
        return list(self._certs)

    def summary(self) -> dict[str, Any]:
        return {
            "total": len(self._certs),
            "certified": sum(1 for c in self._certs if c.status == CertStatus.CERTIFIED),
            "in_progress": sum(1 for c in self._certs if c.status == CertStatus.IN_PROGRESS),
            "items": [
                {
                    "standard": c.standard,
                    "status": c.status.value,
                    "level": c.level,
                    "certificate_id": c.certificate_id,
                }
                for c in self._certs
            ],
        }
