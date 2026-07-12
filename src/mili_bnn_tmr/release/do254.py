"""DO-254 DAL-B design assurance evidence package builder."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mili_bnn_tmr.config import ChipSpec, load_chip_spec

_ROOT = Path(__file__).resolve().parents[3]
_EVIDENCE_DIR = _ROOT / "release" / "certifications" / "do254_evidence"


@dataclass
class EvidenceArtifact:
    artifact_id: str
    title: str
    category: str
    path: str
    status: str
    dal_objective: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DO254EvidencePackage:
    standard: str = "DO-254"
    dal_level: str = "DAL-B"
    design_name: str = "Mili BNN-TMR"
    version: str = "1.0.0"
    artifacts: list[EvidenceArtifact] = field(default_factory=list)
    completion_pct: float = 0.0
    ready_for_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "standard": self.standard,
            "dal_level": self.dal_level,
            "design_name": self.design_name,
            "version": self.version,
            "completion_pct": self.completion_pct,
            "ready_for_review": self.ready_for_review,
            "artifacts": [a.to_dict() for a in self.artifacts],
        }


_ARTIFACT_CATALOG: list[dict[str, str]] = [
    {
        "artifact_id": "DALB-HW-REQ-001",
        "title": "Hardware requirements (chip_spec.yaml)",
        "category": "requirements",
        "path": "config/chip_spec.yaml",
        "dal_objective": "6.1.1",
    },
    {
        "artifact_id": "DALB-HW-DES-001",
        "title": "RTL design (SystemVerilog)",
        "category": "design",
        "path": "rtl/mili_chip_top.sv",
        "dal_objective": "6.2.1",
    },
    {
        "artifact_id": "DALB-HW-VER-001",
        "title": "Verilator RTL signoff gate",
        "category": "verification",
        "path": "sim/verilator/signoff_gate.sh",
        "dal_objective": "6.3.1",
    },
    {
        "artifact_id": "DALB-HW-VER-002",
        "title": "Python system test suite + coverage",
        "category": "verification",
        "path": "tests/",
        "dal_objective": "6.3.2",
    },
    {
        "artifact_id": "DALB-HW-TMR-001",
        "title": "TMR / SEU validation (Phase 5)",
        "category": "safety",
        "path": "docs/RADIATION_VALIDATION.md",
        "dal_objective": "6.3.3",
    },
    {
        "artifact_id": "DALB-HW-CON-001",
        "title": "Timing constraints (SDC)",
        "category": "configuration",
        "path": "tapeout/constraints/mili_chip.sdc",
        "dal_objective": "6.2.2",
    },
    {
        "artifact_id": "DALB-HW-SIG-001",
        "title": "DRC/LVS/timing signoff reports",
        "category": "implementation",
        "path": "tapeout/signoff/",
        "dal_objective": "6.4.1",
    },
    {
        "artifact_id": "DALB-HW-TRC-001",
        "title": "Requirements traceability matrix",
        "category": "traceability",
        "path": "release/certifications/do254_evidence/traceability_matrix.yaml",
        "dal_objective": "6.1.2",
    },
    {
        "artifact_id": "DALB-HW-REV-001",
        "title": "Design review checklist",
        "category": "review",
        "path": "release/certifications/do254_evidence/review_checklist.yaml",
        "dal_objective": "6.5.1",
    },
    {
        "artifact_id": "DALB-HW-CFG-001",
        "title": "Configuration index (SDK manifest)",
        "category": "configuration",
        "path": "release/sdk_manifest.yaml",
        "dal_objective": "6.6.1",
    },
]


class DO254EvidenceBuilder:
    """Assemble DO-254 DAL-B evidence package from repository artifacts."""

    def __init__(self, spec: ChipSpec | None = None) -> None:
        self._spec = spec or load_chip_spec()
        self._root = _ROOT

    def _artifact_status(self, rel_path: str) -> str:
        path = self._root / rel_path
        if path.is_file():
            return "complete"
        if path.is_dir() and any(path.iterdir()):
            return "complete"
        return "missing"

    def build(self) -> DO254EvidencePackage:
        version = str(self._spec.release.get("version", "1.0.0"))
        artifacts: list[EvidenceArtifact] = []
        complete = 0

        for entry in _ARTIFACT_CATALOG:
            status = self._artifact_status(entry["path"])
            if status == "complete":
                complete += 1
            artifacts.append(
                EvidenceArtifact(
                    artifact_id=entry["artifact_id"],
                    title=entry["title"],
                    category=entry["category"],
                    path=entry["path"],
                    status=status,
                    dal_objective=entry["dal_objective"],
                )
            )

        pct = round(100.0 * complete / max(len(artifacts), 1), 1)
        ready = pct >= 90.0 and all(
            a.status == "complete"
            for a in artifacts
            if a.category in ("requirements", "design", "verification", "safety")
        )

        return DO254EvidencePackage(
            dal_level="DAL-B",
            design_name=self._spec.name,
            version=version,
            artifacts=artifacts,
            completion_pct=pct,
            ready_for_review=ready,
        )

    def export(self, output_dir: str | Path | None = None) -> Path:
        out = Path(output_dir or _EVIDENCE_DIR)
        out.mkdir(parents=True, exist_ok=True)

        package = self.build()
        manifest_path = out / "evidence_manifest.json"
        manifest_path.write_text(json.dumps(package.to_dict(), indent=2), encoding="utf-8")

        summary = {
            "standard": "DO-254",
            "dal_level": package.dal_level,
            "completion_pct": package.completion_pct,
            "ready_for_review": package.ready_for_review,
            "artifact_count": len(package.artifacts),
            "complete_count": sum(1 for a in package.artifacts if a.status == "complete"),
        }
        (out / "package_summary.yaml").write_text(
            yaml.safe_dump(summary, sort_keys=False),
            encoding="utf-8",
        )
        return manifest_path
